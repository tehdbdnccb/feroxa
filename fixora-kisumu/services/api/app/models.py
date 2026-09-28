from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="customer", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    technician_profile: Mapped["TechnicianProfile | None"] = relationship(back_populates="user", uselist=False)


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(150), index=True)
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100), default="Kisumu")
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    provider_type: Mapped[str] = mapped_column(String(30), default="independent")


class TechnicianProfile(Base):
    __tablename__ = "technician_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"))
    bio: Mapped[str] = mapped_column(Text, default="")
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    available: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    background_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    network_approved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    average_rating: Mapped[float] = mapped_column(Float, default=0.0)
    completed_jobs: Mapped[int] = mapped_column(Integer, default=0)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    service_radius_km: Mapped[float] = mapped_column(Float, default=15.0)
    user: Mapped[User] = relationship(back_populates="technician_profile")


class Credential(Base):
    __tablename__ = "credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    technician_id: Mapped[str] = mapped_column(ForeignKey("technician_profiles.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    reference: Mapped[str] = mapped_column(String(160))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    model: Mapped[str] = mapped_column(String(120))
    serial_last4: Mapped[str | None] = mapped_column(String(4))
    imei_last4: Mapped[str | None] = mapped_column(String(4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RepairRequest(Base):
    __tablename__ = "repair_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    assigned_technician_id: Mapped[str | None] = mapped_column(ForeignKey("technician_profiles.id"), index=True)
    issue: Mapped[str] = mapped_column(String(120))
    notes: Mapped[str] = mapped_column(Text, default="")
    service_mode: Mapped[str] = mapped_column(String(20))
    address: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="requested", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    repair_request_id: Mapped[str] = mapped_column(ForeignKey("repair_requests.id"), unique=True, index=True)
    technician_id: Mapped[str] = mapped_column(ForeignKey("technician_profiles.id"), index=True)
    parts_amount: Mapped[int] = mapped_column(Integer)
    labour_amount: Mapped[int] = mapped_column(Integer)
    callout_amount: Mapped[int] = mapped_column(Integer, default=0)
    warranty_days: Mapped[int] = mapped_column(Integer, default=90)
    part_tier: Mapped[str] = mapped_column(String(30), default="compatible")
    customer_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    @property
    def total_amount(self) -> int:
        return self.parts_amount + self.labour_amount + self.callout_amount


class RepairInspection(Base):
    __tablename__ = "repair_inspections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    repair_request_id: Mapped[str] = mapped_column(ForeignKey("repair_requests.id"), index=True)
    stage: Mapped[str] = mapped_column(String(20))
    screen_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    camera_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    face_id_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    speaker_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    microphone_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    charging_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RepairEvidence(Base):
    __tablename__ = "repair_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    repair_request_id: Mapped[str] = mapped_column(ForeignKey("repair_requests.id"), index=True)
    uploaded_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    stage: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(40))
    object_key: Mapped[str] = mapped_column(String(255), unique=True)
    original_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    byte_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Warranty(Base):
    __tablename__ = "warranties"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    repair_request_id: Mapped[str] = mapped_column(ForeignKey("repair_requests.id"), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RepairPassportEvent(Base):
    __tablename__ = "repair_passport_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    repair_request_id: Mapped[str] = mapped_column(ForeignKey("repair_requests.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    repair_request_id: Mapped[str | None] = mapped_column(ForeignKey("repair_requests.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    repair_request_id: Mapped[str] = mapped_column(ForeignKey("repair_requests.id"), unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    technician_id: Mapped[str] = mapped_column(ForeignKey("technician_profiles.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Dispute(Base):
    __tablename__ = "disputes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    repair_request_id: Mapped[str] = mapped_column(ForeignKey("repair_requests.id"), unique=True, index=True)
    opened_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(String(60))
    details: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    resolution: Mapped[str] = mapped_column(Text, default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    repair_request_id: Mapped[str] = mapped_column(ForeignKey("repair_requests.id"), unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    phone: Mapped[str] = mapped_column(String(30))
    amount: Mapped[int] = mapped_column(Integer)
    platform_fee_amount: Mapped[int] = mapped_column(Integer, default=0)
    technician_amount: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    merchant_request_id: Mapped[str | None] = mapped_column(String(80))
    checkout_request_id: Mapped[str | None] = mapped_column(String(80), index=True)
    receipt_number: Mapped[str | None] = mapped_column(String(80))
    transaction_date: Mapped[str | None] = mapped_column(String(40))
    result_code: Mapped[str | None] = mapped_column(String(30))
    result_description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TechnicianPayout(Base):
    __tablename__ = "technician_payouts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    repair_request_id: Mapped[str] = mapped_column(ForeignKey("repair_requests.id"), unique=True, index=True)
    technician_id: Mapped[str] = mapped_column(ForeignKey("technician_profiles.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
