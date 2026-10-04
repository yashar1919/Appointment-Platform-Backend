from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.domain.models import AppointmentStatus
from typing import Optional


class TestSMSRequest(BaseModel):
    phone: str
    message: str = "این یک پیامک تست از سیستم رزرو نوبت است."


class AdminAppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    reference: str
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    service_name: str
    service_price: Decimal
    staff_id: UUID
    location_id: UUID
    # Added customer fields for Admin Panel compatibility; nullable preserves older clients.
    customer_name: str | None = None
    customer_phone: str | None = None


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    duration_minutes: int = Field(gt=0)
    price: Decimal = Field(ge=0)
    category_id: UUID | None = None


class ServiceUpdate(ServiceCreate):
    is_active: bool = True


class AdminServiceOut(ServiceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    is_active: bool


class StaffCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    role: str | None = Field(default=None, max_length=300)
    service_ids: list[UUID] = []


class StaffUpdate(StaffCreate):
    is_active: bool = True


class AdminStaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    role: str | None = None
    is_active: bool


class ServiceCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    external_id: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=500)


class ServiceCategoryUpdate(ServiceCategoryCreate):
    pass


class AdminServiceCategoryOut(ServiceCategoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    address: str = Field(min_length=1, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=30)
    directions: str | None = Field(default=None, max_length=1000)


class LocationUpdate(LocationCreate):
    is_active: bool = True


class AdminLocationOut(LocationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    is_active: bool


class TenantProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)


class AdminTenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    slug: str
    timezone: str
    phone: str | None = None
    address: str | None = None
    city: str | None = None


class AdminAppointmentCreate(BaseModel):
    customer_name: str = Field(..., min_length=2)
    customer_phone: str = Field(..., min_length=11)
    service_id: UUID
    staff_id: UUID
    location_id: UUID
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus = AppointmentStatus.CONFIRMED
    price: Optional[Decimal] = None
    notes: Optional[str] = ""