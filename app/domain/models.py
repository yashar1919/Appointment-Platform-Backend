from __future__ import annotations
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Time, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, ExcludeConstraint, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.base import Base


class AppointmentStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    headline: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(String(1000))
    phone: Mapped[str | None] = mapped_column(String(40))
    address: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(120))
    currency: Mapped[str | None] = mapped_column(String(8))
    currency_symbol: Mapped[str | None] = mapped_column(String(16))
    image: Mapped[str | None] = mapped_column(String(500))
    logo: Mapped[str | None] = mapped_column(String(500))
    cover_image: Mapped[str | None] = mapped_column(String(500))
    rating: Mapped[float | None] = mapped_column(Float)
    reviews_count: Mapped[int | None] = mapped_column(Integer)
    min_notice_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    services: Mapped[list[Service]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    staff: Mapped[list[Staff]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    locations: Mapped[list[Location]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class ServiceCategory(Base):
    __tablename__ = "service_categories"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(500))
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_category_tenant_name"), UniqueConstraint("tenant_id", "external_id", name="uq_category_tenant_external_id"))


class Service(Base):
    __tablename__ = "services"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("service_categories.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    image: Mapped[str | None] = mapped_column(String(500))
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_popular: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    included_items: Mapped[list[str] | None] = mapped_column(JSONB)
    care_instructions: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tenant: Mapped[Tenant] = relationship(back_populates="services")
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_service_tenant_name"), CheckConstraint("duration_minutes > 0", name="ck_service_duration_positive"), CheckConstraint("price >= 0", name="ck_service_price_nonnegative"))


class Staff(Base):
    __tablename__ = "staff"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str | None] = mapped_column(String(300))
    bio: Mapped[str | None] = mapped_column(String(1000))
    avatar: Mapped[str | None] = mapped_column(String(500))
    experience_years: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[float | None] = mapped_column(Float)
    specialties: Mapped[list[str] | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tenant: Mapped[Tenant] = relationship(back_populates="staff")
    service_links: Mapped[list[StaffService]] = relationship(cascade="all, delete-orphan")


class StaffService(Base):
    __tablename__ = "staff_services"
    staff_id: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="CASCADE"), primary_key=True)
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"), primary_key=True)


class Location(Base):
    __tablename__ = "locations"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str | None] = mapped_column(String(120))
    postal_code: Mapped[str | None] = mapped_column(String(30))
    directions: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tenant: Mapped[Tenant] = relationship(back_populates="locations")
    working_hours: Mapped[list[WorkingHours]] = relationship(cascade="all, delete-orphan")


class WorkingHours(Base):
    __tablename__ = "working_hours"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    location_id: Mapped[UUID] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    __table_args__ = (UniqueConstraint("location_id", "day_of_week", name="uq_working_location_day"), CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_working_day"), CheckConstraint("start_time < end_time", name="ck_working_times"), CheckConstraint("slot_duration_minutes > 0", name="ck_working_slot_duration_positive"), Index("ix_working_tenant_location_day", "tenant_id", "location_id", "day_of_week"))


class BlockedTime(Base):
    __tablename__ = "blocked_times"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    location_id: Mapped[UUID] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    staff_id: Mapped[UUID | None] = mapped_column(ForeignKey("staff.id", ondelete="CASCADE"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(300))
    __table_args__ = (CheckConstraint("starts_at < ends_at", name="ck_blocked_times"), Index("ix_blocked_tenant_range", "tenant_id", "location_id", "starts_at", "ends_at"))


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    __table_args__ = (UniqueConstraint("tenant_id", "phone", name="uq_customer_tenant_phone"),)


class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id"), nullable=False)
    staff_id: Mapped[UUID] = mapped_column(ForeignKey("staff.id"), nullable=False)
    location_id: Mapped[UUID] = mapped_column(ForeignKey("locations.id"), nullable=False)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    reference: Mapped[str] = mapped_column(String(24), unique=True, nullable=False, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(String(20), default=AppointmentStatus.CONFIRMED, nullable=False)
    service_name: Mapped[str] = mapped_column(String(160), nullable=False)
    service_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    service_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    __table_args__ = (CheckConstraint("starts_at < ends_at", name="ck_appointment_times"), Index("ix_appointment_tenant_start", "tenant_id", "starts_at"), ExcludeConstraint((text("staff_id"), "="), (text("tstzrange(starts_at, ends_at, '[)')"), "&&"), where=text("status IN ('confirmed', 'pending')"), name="ex_appointment_staff_no_overlap", using="gist"))


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_id: Mapped[UUID] = mapped_column(ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(200))
    error_message: Mapped[str | None] = mapped_column(String(1000))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("appointment_id", "event_type", name="uq_notification_appointment_event"),)
