from datetime import datetime, timezone
from pathlib import Path
import re

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .deps import get_current_user, require_role
from .models import (
    Credential,
    Device,
    Dispute,
    Notification,
    PaymentIntent,
    Quote,
    RepairEvidence,
    RepairInspection,
    RepairPassportEvent,
    RepairRequest,
    Review,
    TechnicianPayout,
    TechnicianProfile,
    User,
)
from .payments import MpesaConfigurationError, mpesa_gateway
from .schemas import (
    AuthResponse,
    CredentialCreate,
    DeviceCreate,
    DeviceOut,
    DisputeCreate,
    EvidenceOut,
    InspectionCreate,
    LoginRequest,
    NotificationOut,
    PaymentStart,
    PayoutUpdate,
    DisputeResolution,
    QuoteCreate,
    QuoteOut,
    RegisterRequest,
    RepairRequestCreate,
    RepairRequestOut,
    ReviewCreate,
    StatusUpdate,
    TechnicianApproval,
    TechnicianMatchOut,
    TechnicianProfileUpdate,
    UserOut,
)
from .security import create_access_token, hash_password, new_csrf_token, verify_password
from .services import (
    TECHNICIAN_STATUSES,
    create_warranty_and_passport,
    ensure_customer_owns_device,
    ensure_request_access,
    matching_technicians,
    notify,
    technician_is_ready,
    verified_kinds,
)
from .storage import StorageError, storage

router = APIRouter(prefix="/v1")


def set_auth_cookies(response, access_token: str) -> None:
    common = {
        "secure": settings.session_cookie_secure,
        "samesite": "lax",
        "domain": settings.session_cookie_domain,
        "path": "/",
    }
    response.set_cookie(
        settings.session_cookie_name,
        access_token,
        httponly=True,
        max_age=settings.jwt_expires_minutes * 60,
        **common,
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        new_csrf_token(),
        httponly=False,
        max_age=settings.jwt_expires_minutes * 60,
        **common,
    )


def clear_auth_cookies(response) -> None:
    response.delete_cookie(settings.session_cookie_name, domain=settings.session_cookie_domain, path="/")
    response.delete_cookie(settings.csrf_cookie_name, domain=settings.session_cookie_domain, path="/")


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0") and len(digits) == 10:
        digits = "254" + digits[1:]
    elif digits.startswith("7") and len(digits) == 9:
        digits = "254" + digits
    if not re.fullmatch(r"2547\d{8}", digits):
        raise HTTPException(422, "Use a valid Kenyan M-Pesa mobile number")
    return digits


def accepted_quote(db: Session, request_id: str) -> Quote | None:
    return db.scalar(select(Quote).where(Quote.repair_request_id == request_id, Quote.customer_accepted.is_(True)))


@router.get("/healthz")
def healthz():
    return {"status": "ok", "service": "fixora-api", "version": "1.1.0"}


@router.post("/auth/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    email = payload.email.lower()
    phone = payload.phone.strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    if db.scalar(select(User).where(User.phone == phone)):
        raise HTTPException(409, "Phone already registered")
    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        phone=phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.flush()
    if user.role == "technician":
        db.add(TechnicianProfile(user_id=user.id))
    db.commit()
    token = create_access_token(user.id, user.role)
    set_auth_cookies(response, token)
    return AuthResponse(access_token=token, user=user)


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    token = create_access_token(user.id, user.role)
    set_auth_cookies(response, token)
    return AuthResponse(access_token=token, user=user)


@router.post("/auth/logout", status_code=204)
def logout(response):
    clear_auth_cookies(response)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/devices", response_model=DeviceOut, status_code=201)
def create_device(payload: DeviceCreate, db: Session = Depends(get_db), user: User = Depends(require_role("customer"))):
    device = Device(customer_id=user.id, **payload.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db), user: User = Depends(require_role("customer"))):
    return db.scalars(select(Device).where(Device.customer_id == user.id).order_by(Device.created_at.desc())).all()


@router.post("/repair-requests", response_model=RepairRequestOut, status_code=201)
def create_repair(payload: RepairRequestCreate, db: Session = Depends(get_db), user: User = Depends(require_role("customer"))):
    ensure_customer_owns_device(db, user, payload.device_id)
    repair = RepairRequest(customer_id=user.id, **payload.model_dump())
    db.add(repair)
    db.commit()
    db.refresh(repair)
    return repair


@router.get("/repair-requests", response_model=list[RepairRequestOut])
def list_repairs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "customer":
        query = select(RepairRequest).where(RepairRequest.customer_id == user.id).order_by(RepairRequest.created_at.desc())
        return db.scalars(query.limit(100)).all()

    if user.role == "technician":
        tech = user.technician_profile
        if not tech or not technician_is_ready(db, tech) or not tech.available:
            return []
        assigned = db.scalars(
            select(RepairRequest).where(RepairRequest.assigned_technician_id == tech.id).order_by(RepairRequest.created_at.desc())
        ).all()
        open_requests = db.scalars(
            select(RepairRequest)
            .where(RepairRequest.status == "requested", RepairRequest.assigned_technician_id.is_(None))
            .order_by(RepairRequest.created_at.asc())
            .limit(100)
        ).all()
        visible = {r.id: r for r in assigned}
        for repair in open_requests:
            if any(candidate.id == tech.id for candidate, _ in matching_technicians(db, repair, limit=20)):
                visible[repair.id] = repair
        return list(visible.values())

    return db.scalars(select(RepairRequest).order_by(RepairRequest.created_at.desc()).limit(100)).all()


@router.get("/repair-requests/{request_id}/matches", response_model=list[TechnicianMatchOut])
def get_matches(request_id: str, db: Session = Depends(get_db), user: User = Depends(require_role("customer"))):
    repair = db.get(RepairRequest, request_id)
    if not repair or repair.customer_id != user.id:
        raise HTTPException(404, "Repair request not found")
    rows = []
    for tech, distance in matching_technicians(db, repair):
        rows.append(
            TechnicianMatchOut(
                technician_id=tech.id,
                name=tech.user.full_name,
                years_experience=tech.years_experience,
                average_rating=tech.average_rating,
                completed_jobs=tech.completed_jobs,
                background_verified=tech.background_verified,
                credentials=sorted(verified_kinds(db, tech.id) & {"apple_certified", "aasp", "irp"}),
                distance_km=round(distance, 2) if distance is not None else None,
            )
        )
    return rows


@router.post("/repair-requests/{request_id}/claim", response_model=RepairRequestOut)
def claim_job(request_id: str, db: Session = Depends(get_db), user: User = Depends(require_role("technician"))):
    repair = db.get(RepairRequest, request_id)
    tech = user.technician_profile
    if not repair or not tech:
        raise HTTPException(404, "Repair request not found")
    if repair.assigned_technician_id is not None:
        raise HTTPException(409, "Repair has already been claimed")
    if repair.status != "requested":
        raise HTTPException(409, "Repair is no longer open")
    if not tech.available or not technician_is_ready(db, tech):
        raise HTTPException(403, "Your technician profile is not approved and online")
    if not any(candidate.id == tech.id for candidate, _ in matching_technicians(db, repair, limit=20)):
        raise HTTPException(403, "This repair is outside your service area or does not match your approved network status")
    result = db.execute(
        update(RepairRequest)
        .where(
            RepairRequest.id == repair.id,
            RepairRequest.status == "requested",
            RepairRequest.assigned_technician_id.is_(None),
        )
        .values(
            assigned_technician_id=tech.id,
            status="assigned",
            updated_at=datetime.now(timezone.utc),
        )
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Repair has already been claimed")
    notify(db, repair.customer_id, "assignment", "Technician assigned", f"{user.full_name} accepted your {repair.issue.lower()} request.", repair.id)
    db.commit()
    db.refresh(repair)
    return repair


@router.post("/repair-requests/{request_id}/quotes", response_model=QuoteOut, status_code=201)
def create_quote(request_id: str, payload: QuoteCreate, db: Session = Depends(get_db), user: User = Depends(require_role("technician"))):
    repair = db.get(RepairRequest, request_id)
    tech = user.technician_profile
    if not repair or not tech or repair.assigned_technician_id != tech.id:
        raise HTTPException(404, "Repair not found or not assigned to you")
    if repair.status not in {"assigned", "quoted"}:
        raise HTTPException(409, "Request is no longer accepting a quote")
    existing = db.scalar(select(Quote).where(Quote.repair_request_id == request_id))
    if existing:
        if existing.technician_id != tech.id:
            raise HTTPException(409, "Another technician already quoted this repair")
        raise HTTPException(409, "A quote already exists for this repair")
    quote = Quote(repair_request_id=request_id, technician_id=tech.id, **payload.model_dump())
    repair.status = "quoted"
    repair.updated_at = datetime.now(timezone.utc)
    db.add(quote)
    notify(db, repair.customer_id, "quote", "Repair quote ready", f"{user.full_name} sent you a KSh {quote.total_amount:,} quote with {quote.warranty_days}-day workmanship coverage.", repair.id)
    db.commit()
    db.refresh(quote)
    return quote


@router.get("/repair-requests/{request_id}/quotes", response_model=list[QuoteOut])
def list_quotes(request_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repair = db.get(RepairRequest, request_id)
    if not repair:
        raise HTTPException(404, "Repair request not found")
    if user.role == "customer" and repair.customer_id != user.id:
        raise HTTPException(404, "Repair request not found")
    if user.role == "technician" and repair.assigned_technician_id != (user.technician_profile.id if user.technician_profile else None):
        raise HTTPException(403, "Forbidden")
    return db.scalars(select(Quote).where(Quote.repair_request_id == request_id).order_by(Quote.created_at.desc())).all()


@router.post("/quotes/{quote_id}/accept", response_model=QuoteOut)
def accept_quote(quote_id: str, db: Session = Depends(get_db), user: User = Depends(require_role("customer"))):
    quote = db.get(Quote, quote_id)
    if not quote:
        raise HTTPException(404, "Quote not found")
    repair = db.get(RepairRequest, quote.repair_request_id)
    if not repair or repair.customer_id != user.id:
        raise HTTPException(403, "Forbidden")
    if repair.status not in {"quoted"}:
        raise HTTPException(409, "Quote can no longer be accepted")
    for other in db.scalars(select(Quote).where(Quote.repair_request_id == repair.id)).all():
        other.customer_accepted = other.id == quote.id
    repair.status = "accepted"
    repair.updated_at = datetime.now(timezone.utc)
    notify(db, quote.technician_id and db.get(TechnicianProfile, quote.technician_id).user_id, "quote_accepted", "Quote accepted", "Your repair quote was accepted. You can now start the service workflow.", repair.id)
    db.commit()
    db.refresh(quote)
    return quote


@router.patch("/repair-requests/{request_id}/status", response_model=RepairRequestOut)
def update_status(request_id: str, payload: StatusUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repair = ensure_request_access(db, user, request_id)
    next_status = payload.status

    if user.role == "customer":
        if next_status != "completed" or repair.status != "awaiting_payment":
            raise HTTPException(403, "Customers can only confirm a paid repair")
        payment = db.scalar(select(PaymentIntent).where(PaymentIntent.repair_request_id == repair.id))
        if not payment or payment.status != "success":
            raise HTTPException(409, "Payment must be completed before confirming handover")
        quote = accepted_quote(db, repair.id)
        if not quote:
            raise HTTPException(409, "Accepted quote required")
        create_warranty_and_passport(db, repair, quote)
        repair.status = "completed"
        repair.updated_at = datetime.now(timezone.utc)
        tech = db.get(TechnicianProfile, repair.assigned_technician_id) if repair.assigned_technician_id else None
        if tech:
            tech.completed_jobs += 1
        if tech:
            notify(db, tech.user_id, "completed", "Repair completed", "The customer confirmed handover. Your payout is now queued.", repair.id)
        db.commit()
        db.refresh(repair)
        return repair

    if next_status == "cancelled":
        if repair.status in {"completed", "cancelled"}:
            raise HTTPException(409, "Repair is already closed")
    else:
        allowed = TECHNICIAN_STATUSES.get(repair.status, set())
        if next_status not in allowed:
            raise HTTPException(409, f"Cannot move repair from {repair.status} to {next_status}")
        if next_status == "in_repair" and not accepted_quote(db, repair.id):
            raise HTTPException(409, "Customer must accept the quote before repair work starts")
        if next_status == "awaiting_payment":
            if not db.scalar(select(RepairInspection).where(RepairInspection.repair_request_id == repair.id, RepairInspection.stage == "post")):
                raise HTTPException(409, "Post-repair inspection is required")

    repair.status = next_status
    repair.updated_at = datetime.now(timezone.utc)
    customer_message = {
        "en_route": "Your technician is on the way.",
        "arrived": "Your technician has arrived.",
        "inspecting": "The pre-repair condition check is underway.",
        "in_repair": "Repair work has started after your approved quote.",
        "awaiting_payment": "Repair is complete. Complete payment and confirm handover.",
        "cancelled": "Your repair request was cancelled.",
    }.get(next_status, "Repair status updated.")
    notify(db, repair.customer_id, "status", "Repair update", customer_message, repair.id)
    db.commit()
    db.refresh(repair)
    return repair


@router.post("/repair-requests/{request_id}/inspections", status_code=201)
def inspection(request_id: str, payload: InspectionCreate, db: Session = Depends(get_db), user: User = Depends(require_role("technician"))):
    repair = ensure_request_access(db, user, request_id)
    has_pre = db.scalar(select(RepairInspection).where(RepairInspection.repair_request_id == repair.id, RepairInspection.stage == "pre")) is not None
    has_post = db.scalar(select(RepairInspection).where(RepairInspection.repair_request_id == repair.id, RepairInspection.stage == "post")) is not None
    if not has_pre:
        if repair.status != "arrived":
            raise HTTPException(409, "Pre-repair inspection is available only after arrival")
        stage = "pre"
        repair.status = "inspecting"
    elif not has_post:
        if repair.status != "in_repair":
            raise HTTPException(409, "Post-repair inspection is available only during an active repair")
        stage = "post"
        repair.status = "awaiting_payment"
    else:
        raise HTTPException(409, "Both inspections have already been recorded")
    record = RepairInspection(repair_request_id=repair.id, stage=stage, **payload.model_dump())
    db.add(record)
    repair.updated_at = datetime.now(timezone.utc)
    notify(db, repair.customer_id, "inspection", "Inspection recorded", f"The {stage}-repair device check is now part of your repair record.", repair.id)
    db.commit()
    return {"inspection_id": record.id, "stage": stage, "status": repair.status}


@router.get("/repair-requests/{request_id}/evidence", response_model=list[EvidenceOut])
def list_evidence(request_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repair = ensure_request_access(db, user, request_id)
    return db.scalars(select(RepairEvidence).where(RepairEvidence.repair_request_id == repair.id).order_by(RepairEvidence.created_at.asc())).all()


@router.post("/repair-requests/{request_id}/evidence", response_model=EvidenceOut, status_code=201)
async def upload_evidence(
    request_id: str,
    stage: str,
    kind: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repair = ensure_request_access(db, user, request_id)
    if stage not in {"pre", "post", "general"} or kind not in {"device_condition", "repair_part", "completion", "other"}:
        raise HTTPException(422, "Invalid evidence stage or kind")
    allowed_types = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
    if file.content_type not in allowed_types:
        raise HTTPException(415, "Evidence must be JPEG, PNG, WebP or PDF")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(413, f"Evidence exceeds the {settings.max_upload_mb}MB limit")
    original = Path(file.filename or "evidence").name[:255]
    try:
        object_key, sha256 = storage.put(data, file.content_type, original)
    except StorageError as exc:
        raise HTTPException(503, str(exc)) from exc
    evidence = RepairEvidence(
        repair_request_id=repair.id,
        uploaded_by_user_id=user.id,
        stage=stage,
        kind=kind,
        object_key=object_key,
        original_name=original,
        content_type=file.content_type,
        byte_size=len(data),
        sha256=sha256,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/evidence/{evidence_id}/download")
def download_evidence(evidence_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    evidence = db.get(RepairEvidence, evidence_id)
    if not evidence:
        raise HTTPException(404, "Evidence not found")
    ensure_request_access(db, user, evidence.repair_request_id)
    url = storage.download_url(evidence.object_key)
    if url:
        return RedirectResponse(url)
    path = storage.local_path(evidence.object_key)
    if not path.exists():
        raise HTTPException(404, "Evidence object not found")
    return FileResponse(path, media_type=evidence.content_type, filename=evidence.original_name)


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(50)).all()


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(notification_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    notification.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification)
    return notification


@router.get("/devices/{device_id}/passport")
def passport(device_id: str, db: Session = Depends(get_db), user: User = Depends(require_role("customer"))):
    device = db.get(Device, device_id)
    if not device or device.customer_id != user.id:
        raise HTTPException(404, "Device not found")
    events = db.scalars(select(RepairPassportEvent).where(RepairPassportEvent.device_id == device_id).order_by(RepairPassportEvent.created_at.desc())).all()
    return [{"id": e.id, "event_type": e.event_type, "description": e.description, "created_at": e.created_at} for e in events]


@router.get("/technicians/me")
def technician_me(db: Session = Depends(get_db), user: User = Depends(require_role("technician"))):
    profile = user.technician_profile
    if not profile:
        raise HTTPException(409, "Technician profile required")
    return {
        "available": profile.available,
        "years_experience": profile.years_experience,
        "bio": profile.bio,
        "latitude": profile.latitude,
        "longitude": profile.longitude,
        "service_radius_km": profile.service_radius_km,
        "network_approved": profile.network_approved,
        "credentials": sorted(verified_kinds(db, profile.id)),
    }


@router.patch("/technicians/me")
def update_technician_profile(payload: TechnicianProfileUpdate, db: Session = Depends(get_db), user: User = Depends(require_role("technician"))):
    profile = user.technician_profile
    if not profile:
        raise HTTPException(409, "Technician profile required")
    values = payload.model_dump(exclude_none=True)
    if "available" in values and values["available"] and not technician_is_ready(db, profile):
        raise HTTPException(403, "Your profile must be network-approved with verified identity and business credentials before going online")
    for field, value in values.items():
        setattr(profile, field, value)
    if profile.available and (profile.latitude is None or profile.longitude is None):
        profile.available = False
        db.commit()
        raise HTTPException(422, "Location is required before going online")
    db.commit()
    db.refresh(profile)
    return {
        "available": profile.available,
        "years_experience": profile.years_experience,
        "bio": profile.bio,
        "latitude": profile.latitude,
        "longitude": profile.longitude,
        "service_radius_km": profile.service_radius_km,
        "network_approved": profile.network_approved,
        "credentials": sorted(verified_kinds(db, profile.id)),
    }


@router.get("/technicians")
def list_technicians(db: Session = Depends(get_db)):
    rows = db.scalars(select(TechnicianProfile).where(TechnicianProfile.available.is_(True), TechnicianProfile.network_approved.is_(True))).all()
    return [
        {
            "id": tech.id,
            "name": tech.user.full_name,
            "years_experience": tech.years_experience,
            "average_rating": tech.average_rating,
            "completed_jobs": tech.completed_jobs,
            "background_verified": tech.background_verified,
            "credentials": sorted(verified_kinds(db, tech.id) & {"apple_certified", "aasp", "irp"}),
            "latitude": tech.latitude,
            "longitude": tech.longitude,
        }
        for tech in rows
    ]


@router.get("/admin/technicians")
def admin_technicians(db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    rows = db.scalars(select(TechnicianProfile)).all()
    return [
        {
            "id": tech.id,
            "name": tech.user.full_name,
            "email": tech.user.email,
            "available": tech.available,
            "network_approved": tech.network_approved,
            "years_experience": tech.years_experience,
            "background_verified": tech.background_verified,
            "completed_jobs": tech.completed_jobs,
            "average_rating": tech.average_rating,
            "credentials": [
                {"id": c.id, "kind": c.kind, "reference": c.reference, "verified_at": c.verified_at, "expires_at": c.expires_at}
                for c in db.scalars(select(Credential).where(Credential.technician_id == tech.id)).all()
            ],
        }
        for tech in rows
    ]


@router.post("/admin/technicians/{technician_id}/credentials", status_code=201)
def add_credential(technician_id: str, payload: CredentialCreate, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    tech = db.get(TechnicianProfile, technician_id)
    if not tech:
        raise HTTPException(404, "Technician not found")
    credential = Credential(
        technician_id=technician_id,
        kind=payload.kind,
        reference=payload.reference.strip(),
        verified_at=datetime.now(timezone.utc),
        expires_at=payload.expires_at,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


@router.patch("/admin/technicians/{technician_id}/approval")
def approve_technician(technician_id: str, payload: TechnicianApproval, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    tech = db.get(TechnicianProfile, technician_id)
    if not tech:
        raise HTTPException(404, "Technician not found")
    if payload.approved and not {"identity", "business"}.issubset(verified_kinds(db, technician_id)):
        raise HTTPException(409, "Verify identity and business credentials before approving network access")
    tech.network_approved = payload.approved
    if payload.background_verified is not None:
        tech.background_verified = payload.background_verified
    if not payload.approved:
        tech.available = False
    db.commit()
    return {"network_approved": tech.network_approved, "background_verified": tech.background_verified}


@router.post("/repair-requests/{request_id}/payments/mpesa")
async def start_mpesa_payment(request_id: str, payload: PaymentStart, db: Session = Depends(get_db), user: User = Depends(require_role("customer"))):
    repair = db.get(RepairRequest, request_id)
    if not repair or repair.customer_id != user.id:
        raise HTTPException(404, "Repair request not found")
    if repair.status != "awaiting_payment":
        raise HTTPException(409, "Payment is available after the post-repair inspection")
    quote = accepted_quote(db, repair.id)
    if not quote:
        raise HTTPException(409, "Accept a quote before payment")
    phone = normalize_phone(payload.phone or user.phone)
    existing = db.scalar(select(PaymentIntent).where(PaymentIntent.repair_request_id == repair.id))
    if existing and existing.status == "success":
        return {"payment_id": existing.id, "status": existing.status, "receipt_number": existing.receipt_number}
    amount = quote.total_amount
    fee = int(round(amount * settings.platform_fee_percent / 100))
    if existing and existing.status == "submitted":
        return {"payment_id": existing.id, "status": existing.status, "checkout_request_id": existing.checkout_request_id}
    intent = existing or PaymentIntent(repair_request_id=repair.id, customer_id=user.id, phone=phone, amount=amount)
    intent.phone = phone
    intent.amount = amount
    intent.platform_fee_amount = fee
    intent.technician_amount = amount - fee
    intent.status = "pending"
    db.add(intent)
    db.commit()
    try:
        response = await mpesa_gateway.stk_push(
            phone=intent.phone,
            amount=intent.amount,
            account_reference=f"FIXORA-{repair.id[:8]}",
            transaction_desc=f"Repair {repair.id[:8]}",
        )
    except (MpesaConfigurationError, ValueError) as exc:
        intent.status = "failed"
        intent.result_description = str(exc)
        db.commit()
        raise HTTPException(503, str(exc)) from exc
    intent.merchant_request_id = response.get("MerchantRequestID")
    intent.checkout_request_id = response.get("CheckoutRequestID")
    intent.status = "submitted" if response.get("ResponseCode") == "0" else "failed"
    intent.result_code = response.get("ResponseCode")
    intent.result_description = response.get("ResponseDescription") or response.get("CustomerMessage")
    intent.updated_at = datetime.now(timezone.utc)
    notify(db, user.id, "payment", "M-Pesa payment requested", response.get("CustomerMessage", "Complete the M-Pesa prompt on your phone."), repair.id)
    db.commit()
    return {
        "payment_id": intent.id,
        "status": intent.status,
        "checkout_request_id": intent.checkout_request_id,
        "response_code": response.get("ResponseCode"),
        "customer_message": response.get("CustomerMessage"),
    }


@router.get("/repair-requests/{request_id}/payment")
def payment_status(request_id: str, db: Session = Depends(get_db), user: User = Depends(require_role("customer"))):
    repair = db.get(RepairRequest, request_id)
    if not repair or repair.customer_id != user.id:
        raise HTTPException(404, "Repair request not found")
    payment = db.scalar(select(PaymentIntent).where(PaymentIntent.repair_request_id == repair.id))
    if not payment:
        return {"status": "not_started"}
    return {
        "id": payment.id,
        "status": payment.status,
        "amount": payment.amount,
        "receipt_number": payment.receipt_number,
        "updated_at": payment.updated_at,
    }


@router.post("/payments/mpesa/callback/{callback_token}")
def mpesa_callback(callback_token: str, payload: dict, db: Session = Depends(get_db)):
    if not settings.mpesa_callback_token or callback_token != settings.mpesa_callback_token:
        raise HTTPException(404, "Not found")
    body = payload.get("Body", {}).get("stkCallback", {})
    checkout = body.get("CheckoutRequestID")
    if not checkout:
        return {"ResultCode": 0, "ResultDesc": "Accepted"}
    intent = db.scalar(select(PaymentIntent).where(PaymentIntent.checkout_request_id == checkout))
    if not intent:
        return {"ResultCode": 0, "ResultDesc": "Accepted"}
    result_code = str(body.get("ResultCode", ""))
    intent.result_code = result_code
    intent.result_description = body.get("ResultDesc")
    if result_code == "0":
        intent.status = "success"
        metadata = {item.get("Name"): item.get("Value") for item in body.get("CallbackMetadata", {}).get("Item", []) if item.get("Name")}
        intent.receipt_number = str(metadata.get("MpesaReceiptNumber")) if metadata.get("MpesaReceiptNumber") else None
        intent.transaction_date = str(metadata.get("TransactionDate")) if metadata.get("TransactionDate") else None
        notify(
            db,
            intent.customer_id,
            "payment_success",
            "Payment received",
            f"Payment of KSh {intent.amount:,} was received. Confirm handover when ready.",
            intent.repair_request_id,
        )
        payout = db.scalar(select(TechnicianPayout).where(TechnicianPayout.repair_request_id == intent.repair_request_id))
        if not payout:
            repair = db.get(RepairRequest, intent.repair_request_id)
            if repair and repair.assigned_technician_id:
                payout = TechnicianPayout(
                    repair_request_id=repair.id,
                    technician_id=repair.assigned_technician_id,
                    amount=intent.technician_amount,
                    status="pending",
                )
                db.add(payout)
    else:
        intent.status = "failed"
    intent.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.post("/repair-requests/{request_id}/review", status_code=201)
def create_review(request_id: str, payload: ReviewCreate, db: Session = Depends(get_db), user: User = Depends(require_role("customer"))):
    repair = db.get(RepairRequest, request_id)
    if not repair or repair.customer_id != user.id:
        raise HTTPException(404, "Repair request not found")
    if repair.status != "completed" or not repair.assigned_technician_id:
        raise HTTPException(409, "A review is available after completion")
    if db.scalar(select(Review).where(Review.repair_request_id == repair.id)):
        raise HTTPException(409, "A review already exists")
    review = Review(
        repair_request_id=repair.id,
        customer_id=user.id,
        technician_id=repair.assigned_technician_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    db.flush()
    technician = db.get(TechnicianProfile, repair.assigned_technician_id)
    ratings = db.scalar(select(func.avg(Review.rating)).where(Review.technician_id == technician.id)) or 0.0
    technician.average_rating = round(float(ratings), 2)
    db.commit()
    return {"id": review.id, "rating": review.rating, "comment": review.comment}


@router.post("/repair-requests/{request_id}/dispute", status_code=201)
def create_dispute(request_id: str, payload: DisputeCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repair = db.get(RepairRequest, request_id)
    if not repair:
        raise HTTPException(404, "Repair request not found")
    if user.role == "customer" and repair.customer_id != user.id:
        raise HTTPException(404, "Repair request not found")
    if user.role == "technician" and repair.assigned_technician_id != (user.technician_profile.id if user.technician_profile else None):
        raise HTTPException(403, "Forbidden")
    if db.scalar(select(Dispute).where(Dispute.repair_request_id == repair.id)):
        raise HTTPException(409, "A dispute already exists")
    dispute = Dispute(repair_request_id=repair.id, opened_by_user_id=user.id, reason=payload.reason, details=payload.details)
    db.add(dispute)
    repair.status = "disputed"
    repair.updated_at = datetime.now(timezone.utc)
    notify(db, repair.customer_id, "dispute", "Repair dispute opened", "Your case has been routed to the Fixora trust team.", repair.id)
    if repair.assigned_technician_id:
        tech = db.get(TechnicianProfile, repair.assigned_technician_id)
        notify(db, tech.user_id, "dispute", "Repair dispute opened", "A dispute has been opened for this repair. Check the trust center workflow.", repair.id)
    db.commit()
    db.refresh(dispute)
    return dispute


@router.get("/admin/disputes")
def admin_disputes(db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    rows = db.scalars(select(Dispute).order_by(Dispute.created_at.desc()).limit(200)).all()
    return rows


@router.patch("/admin/disputes/{dispute_id}")
def resolve_dispute(dispute_id: str, payload: DisputeResolution, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    dispute = db.get(Dispute, dispute_id)
    if not dispute:
        raise HTTPException(404, "Dispute not found")
    dispute.status = payload.status
    dispute.resolution = payload.resolution
    dispute.resolved_at = datetime.now(timezone.utc) if payload.status != "open" else None
    repair = db.get(RepairRequest, dispute.repair_request_id)
    if repair and payload.status != "open":
        repair.status = "completed" if payload.status == "resolved" else "cancelled"
        repair.updated_at = datetime.now(timezone.utc)
        notify(db, repair.customer_id, "dispute_resolved", "Dispute update", payload.resolution, repair.id)
        if repair.assigned_technician_id:
            tech = db.get(TechnicianProfile, repair.assigned_technician_id)
            notify(db, tech.user_id, "dispute_resolved", "Dispute update", payload.resolution, repair.id)
    db.commit()
    return dispute


@router.get("/admin/payouts")
def admin_payouts(db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    rows = db.scalars(select(TechnicianPayout).order_by(TechnicianPayout.created_at.desc()).limit(200)).all()
    return [
        {
            "id": payout.id,
            "repair_request_id": payout.repair_request_id,
            "technician_id": payout.technician_id,
            "amount": payout.amount,
            "status": payout.status,
            "notes": payout.notes,
            "created_at": payout.created_at,
            "paid_at": payout.paid_at,
        }
        for payout in rows
    ]


@router.patch("/admin/payouts/{payout_id}")
def update_payout(payout_id: str, payload: PayoutUpdate, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    payout = db.get(TechnicianPayout, payout_id)
    if not payout:
        raise HTTPException(404, "Payout not found")
    payout.status = payload.status
    payout.notes = payload.notes
    payout.paid_at = datetime.now(timezone.utc) if payload.status == "paid" else payout.paid_at
    db.commit()
    return {"id": payout.id, "status": payout.status, "amount": payout.amount, "paid_at": payout.paid_at}
