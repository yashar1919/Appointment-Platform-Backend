from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    duration_minutes: int
    price: Decimal
    image: str | None
    is_featured: bool
    is_popular: bool
    included_items: list[str] | None
    care_instructions: str | None


class StaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str


class PublicStaffOut(BaseModel):
    id: UUID
    name: str
    role: str
    avatar: str
    bio: str
    active: bool
    experience_years: int | None
    rating: float | None
    specialties: list[str] | None


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    address: str
    city: str | None
    postal_code: str | None
    directions: str | None


class AvailabilityOut(BaseModel):
    starts_at: datetime
    ends_at: datetime
    is_available: bool
    staff_ids: list[UUID]


class AvailabilityQuery(BaseModel):
    service_id: UUID
    location_id: UUID
    day: date
    staff_id: UUID | None = None


class AppointmentCreate(BaseModel):
    service_id: UUID
    staff_id: UUID
    location_id: UUID
    starts_at: datetime
    customer_name: str = Field(min_length=1, max_length=160)
    customer_phone: str = Field(min_length=3, max_length=40)
    customer_email: str | None = None


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    reference: str
    starts_at: datetime
    ends_at: datetime
    status: str
    service_name: str
    service_duration_minutes: int
    service_price: Decimal


class Envelope(BaseModel):
    data: object
