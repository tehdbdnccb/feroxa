from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=30)
    password: str = Field(min_length=10, max_length=128)
    role: str = Field(default="customer", pattern="^(customer|technician)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    phone: str
    role: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DeviceCreate(BaseModel):
    model: str = Field(min_length=2, max_length=120)
    serial_last4: str | None = Field(default=None, pattern="^[A-Za-z0-9]{4}$")
    imei_last4: str | None = Field(default=None, pattern=r"^\d{4}$")


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model: str
    serial_last4: str | None
    imei_last4: str | None


class RepairRequestCreate(BaseModel):
    device_id: str
    issue: str = Field(min_length=3, max_length=120)
    notes: str = Field(default="", max_length=2000)
    service_mode: str = Field(pattern="^(mobile|pickup|workshop)$")
    address: str = Field(min_length=5, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class RepairRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    device_id: str
    assigned_technician_id: str | None
    issue: str
    notes: str
    service_mode: str
    address: str
    latitude: float | None
    longitude: float | None
    status: str
    created_at: datetime
    updated_at: datetime


class QuoteCreate(BaseModel):
    parts_amount: int = Field(ge=0, le=1000000)
    labour_amount: int = Field(ge=0, le=1000000)
    callout_amount: int = Field(default=0, ge=0, le=1000000)
    warranty_days: int = Field(default=90, ge=0, le=3650)
    part_tier: str = Field(pattern="^(genuine|compatible|used)$")


class QuoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repair_request_id: str
    technician_id: str
    parts_amount: int
    labour_amount: int
    callout_amount: int
    warranty_days: int
    part_tier: str
    customer_accepted: bool
    created_at: datetime
    total_amount: int


class InspectionCreate(BaseModel):
    screen_ok: bool
    camera_ok: bool
    face_id_ok: bool
    speaker_ok: bool
    microphone_ok: bool
    charging_ok: bool
    notes: str = Field(default="", max_length=2000)


class StatusUpdate(BaseModel):
    status: str = Field(
        pattern="^(en_route|arrived|inspecting|in_repair|awaiting_payment|completed|cancelled)$"
    )


class TechnicianProfileUpdate(BaseModel):
    available: bool | None = None
    years_experience: int | None = Field(default=None, ge=0, le=60)
    bio: str | None = Field(default=None, max_length=2000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    service_radius_km: float | None = Field(default=None, ge=1, le=100)


class CredentialCreate(BaseModel):
    kind: str = Field(pattern="^(apple_certified|aasp|irp|identity|business)$")
    reference: str = Field(min_length=3, max_length=160)
    expires_at: datetime | None = None


class TechnicianApproval(BaseModel):
    approved: bool
    background_verified: bool | None = None
    reason: str = Field(default="", max_length=500)


class TechnicianMatchOut(BaseModel):
    technician_id: str
    name: str
    years_experience: int
    average_rating: float
    completed_jobs: int
    background_verified: bool
    credentials: list[str]
    distance_km: float | None


class EvidenceOut(BaseModel):
    id: str
    stage: str
    kind: str
    original_name: str
    content_type: str
    byte_size: int
    sha256: str
    created_at: datetime


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repair_request_id: str | None
    kind: str
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


class DisputeCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=60)
    details: str = Field(min_length=10, max_length=3000)


class PaymentStart(BaseModel):
    phone: str | None = Field(default=None, min_length=7, max_length=30)


class DisputeResolution(BaseModel):
    status: str = Field(pattern="^(open|resolved|rejected)$")
    resolution: str = Field(min_length=3, max_length=3000)


class PayoutUpdate(BaseModel):
    status: str = Field(pattern="^(pending|paid|held)$")
    notes: str = Field(default="", max_length=1000)
