from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.domain.models import AppointmentStatus


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


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    duration_minutes: int = Field(gt=0)
    price: Decimal = Field(ge=0)


class ServiceUpdate(ServiceCreate):
    is_active: bool = True


class AdminServiceOut(ServiceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    is_active: bool


class StaffCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    service_ids: list[UUID] = []


class StaffUpdate(StaffCreate):
    is_active: bool = True


class AdminStaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    is_active: bool
