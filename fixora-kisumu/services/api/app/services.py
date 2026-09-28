from datetime import timedelta
from math import atan2, cos, radians, sin, sqrt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import (
    Credential,
    Device,
    Notification,
    Quote,
    RepairInspection,
    RepairPassportEvent,
    RepairRequest,
    TechnicianProfile,
    TechnicianPayout,
    User,
    Warranty,
    utcnow,
)


OPEN_STATUSES = {"requested", "assigned", "quoted"}
TECHNICIAN_STATUSES = {
    "accepted": {"en_route", "cancelled"},
    "assigned": {"en_route", "cancelled"},
    "en_route": {"arrived", "cancelled"},
    "arrived": {"inspecting", "cancelled"},
    "inspecting": {"in_repair", "cancelled"},
    "in_repair": {"awaiting_payment", "cancelled"},
}


def ensure_customer_owns_device(db: Session, customer: User, device_id: str) -> Device:
    device = db.get(Device, device_id)
    if not device or device.customer_id != customer.id:
        raise HTTPException(404, "Device not found")
    return device


def ensure_request_access(db: Session, user: User, request_id: str) -> RepairRequest:
    repair = db.get(RepairRequest, request_id)
    if not repair:
        raise HTTPException(404, "Repair request not found")
    if user.role == "customer" and repair.customer_id != user.id:
        raise HTTPException(403, "Forbidden")
    if user.role == "technician":
        tech = user.technician_profile
        if not tech or repair.assigned_technician_id != tech.id:
            raise HTTPException(403, "Repair is not assigned to you")
    return repair


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return radius * 2 * atan2(sqrt(a), sqrt(1 - a))


def verified_kinds(db: Session, technician_id: str) -> set[str]:
    now = utcnow()
    creds = db.scalars(select(Credential).where(Credential.technician_id == technician_id)).all()
    return {
        c.kind
        for c in creds
        if c.verified_at is not None and (c.expires_at is None or c.expires_at > now)
    }


def technician_is_ready(db: Session, tech: TechnicianProfile) -> bool:
    kinds = verified_kinds(db, tech.id)
    return tech.network_approved and "identity" in kinds and "business" in kinds


def matching_technicians(db: Session, repair: RepairRequest, limit: int = 10) -> list[tuple[TechnicianProfile, float | None]]:
    candidates = db.scalars(select(TechnicianProfile).where(TechnicianProfile.available.is_(True), TechnicianProfile.network_approved.is_(True))).all()
    scored: list[tuple[TechnicianProfile, float | None, float]] = []
    for tech in candidates:
        if not technician_is_ready(db, tech):
            continue
        distance: float | None = None
        if repair.latitude is not None and repair.longitude is not None and tech.latitude is not None and tech.longitude is not None:
            distance = haversine_km(repair.latitude, repair.longitude, tech.latitude, tech.longitude)
            if distance > tech.service_radius_km:
                continue
        distance_penalty = distance if distance is not None else 10.0
        score = (tech.average_rating * 20) + min(tech.completed_jobs, 100) * 0.2 + tech.years_experience * 0.5 - distance_penalty
        scored.append((tech, distance, score))
    scored.sort(key=lambda row: row[2], reverse=True)
    return [(tech, distance) for tech, distance, _ in scored[:limit]]


def notify(db: Session, user_id: str, kind: str, title: str, body: str, repair_request_id: str | None = None) -> None:
    db.add(Notification(user_id=user_id, repair_request_id=repair_request_id, kind=kind, title=title, body=body))


def add_passport_event(db: Session, repair: RepairRequest, event_type: str, description: str) -> None:
    db.add(
        RepairPassportEvent(
            device_id=repair.device_id,
            repair_request_id=repair.id,
            event_type=event_type,
            description=description,
        )
    )


def create_warranty_and_passport(db: Session, repair: RepairRequest, quote: Quote) -> None:
    if not db.scalar(select(Warranty).where(Warranty.repair_request_id == repair.id)):
        db.add(Warranty(repair_request_id=repair.id, expires_at=utcnow() + timedelta(days=quote.warranty_days)))
    if not db.scalar(select(TechnicianPayout).where(TechnicianPayout.repair_request_id == repair.id)):
        gross = quote.total_amount
        fee = int(round(gross * settings.platform_fee_percent / 100))
        db.add(TechnicianPayout(repair_request_id=repair.id, technician_id=quote.technician_id, amount=gross - fee))
    add_passport_event(
        db,
        repair,
        "repair_completed",
        f"{repair.issue} completed; tier={quote.part_tier}; warranty={quote.warranty_days} days",
    )
