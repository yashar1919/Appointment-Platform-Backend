from datetime import date, datetime, time, timedelta, timezone
import logging
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ConflictError, NotFoundError
from app.application.events import Event, bus
from app.domain.models import Appointment, AppointmentStatus, Customer
from app.infrastructure.repositories import AppointmentRepository, CustomerRepository, LocationRepository, SchedulingRepository, ServiceRepository, StaffRepository, TenantRepository

logger = logging.getLogger(__name__)


class TenantService:
    def __init__(self, db: AsyncSession) -> None: self.repo = TenantRepository(db)
    async def resolve(self, slug: str):
        tenant = await self.repo.get_by_slug(slug)
        if not tenant: raise NotFoundError("Tenant not found")
        return tenant


class ServiceService:
    def __init__(self, db: AsyncSession) -> None: self.repo = ServiceRepository(db)
    async def list(self, tenant_id: UUID): return await self.repo.list_active(tenant_id)


class StaffService:
    def __init__(self, db: AsyncSession) -> None: self.repo = StaffRepository(db)
    async def list_active(self, tenant_id: UUID): return await self.repo.list_active(tenant_id)
    async def list_for_service(self, tenant_id: UUID, service_id: UUID): return await self.repo.list_for_service(tenant_id, service_id)


class LocationService:
    def __init__(self, db: AsyncSession) -> None: self.repo = LocationRepository(db)
    async def list(self, tenant_id: UUID): return await self.repo.list_active(tenant_id)


class SchedulingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db, self.services, self.staff, self.locations, self.schedule, self.tenants = db, ServiceRepository(db), StaffRepository(db), LocationRepository(db), SchedulingRepository(db), TenantRepository(db)
    async def availability(self, tenant_id: UUID, service_id: UUID, location_id: UUID, day: date, staff_id: UUID | None = None) -> list[dict]:
        service = await self.services.get_active(tenant_id, service_id)
        location = await self.locations.get_active(tenant_id, location_id)
        tenant = await self.tenants.get_by_id(tenant_id)
        if not service or not location or not tenant: raise NotFoundError("Service, location, or tenant not found")
        tenant_zone = ZoneInfo(tenant.timezone)
        now_local = datetime.now(tenant_zone)
        logger.debug("Availability timezone=%s current_local=%s day=%s", tenant.timezone, now_local.isoformat(), day.isoformat())
        staff_members = [await self.staff.get_eligible(tenant_id, staff_id, service_id)] if staff_id else await self.staff.list_for_service(tenant_id, service_id)
        staff_members = [member for member in staff_members if member]
        hours = await self.schedule.hours(tenant_id, location_id, day.weekday())
        if not hours: return []
        start = datetime.combine(day, hours.start_time, tzinfo=tenant_zone).astimezone(timezone.utc)
        close = datetime.combine(day, hours.end_time, tzinfo=tenant_zone).astimezone(timezone.utc)
        slots, cursor = [], start
        step = timedelta(minutes=service.duration_minutes)
        slot_increment = timedelta(minutes=hours.slot_duration_minutes)
        while cursor + step <= close:
            end = cursor + step
            slot_start_local = cursor.astimezone(tenant_zone)
            slot_end_local = end.astimezone(tenant_zone)
            if cursor.astimezone(tenant_zone) <= now_local:
                slots.append({"starts_at": slot_start_local, "ends_at": slot_end_local, "is_available": False, "staff_ids": []})
                logger.debug("Availability slot start=%s end=%s is_available=False reason=past", slot_start_local.isoformat(), slot_end_local.isoformat())
                cursor += slot_increment
                continue
            available_staff = []
            for member in staff_members:
                is_blocked = await self.schedule.blocked(tenant_id, location_id, member.id, cursor, end)
                overlapping = await self.schedule.overlapping(tenant_id, member.id, cursor, end)
                if overlapping:
                    logger.debug("Overlapping appointments staff_id=%s slot_start=%s references=%s", member.id, slot_start_local.isoformat(), [appointment.reference for appointment in overlapping])
                if not is_blocked and not overlapping: available_staff.append(member.id)
            is_available = bool(available_staff)
            slots.append({"starts_at": slot_start_local, "ends_at": slot_end_local, "is_available": is_available, "staff_ids": available_staff})
            logger.debug("Availability slot start=%s end=%s is_available=%s staff_ids=%s", slot_start_local.isoformat(), slot_end_local.isoformat(), is_available, available_staff)
            cursor += slot_increment
        return slots


class CustomerService:
    def __init__(self, db: AsyncSession) -> None: self.repo = CustomerRepository(db)


class AppointmentService:
    def __init__(self, db: AsyncSession) -> None: self.db, self.appointments, self.customers, self.services, self.staff, self.locations, self.schedule = db, AppointmentRepository(db), CustomerRepository(db), ServiceRepository(db), StaffRepository(db), LocationRepository(db), SchedulingRepository(db)
    async def book(self, tenant_id: UUID, service_id: UUID, staff_id: UUID, location_id: UUID, starts_at: datetime, customer_data: dict) -> Appointment:
        if starts_at.tzinfo is None: raise ConflictError("starts_at must include a timezone")
        starts_at = starts_at.astimezone(timezone.utc)
        if starts_at <= datetime.now(timezone.utc): raise ConflictError("Appointment must be in the future")
        service = await self.services.get_active(tenant_id, service_id)
        staff = await self.staff.get_eligible(tenant_id, staff_id, service_id)
        location = await self.locations.get_active(tenant_id, location_id)
        if not service or not staff or not location: raise NotFoundError("Service, staff, or location not found")
        ends_at = starts_at + timedelta(minutes=service.duration_minutes)
        if await self.schedule.blocked(tenant_id, location_id, staff_id, starts_at, ends_at) or await self.schedule.occupied(tenant_id, staff_id, starts_at, ends_at): raise ConflictError("Requested time is no longer available")
        customer = await self.customers.get_or_create(tenant_id, **customer_data)
        appointment = Appointment(tenant_id=tenant_id, service_id=service.id, staff_id=staff.id, location_id=location.id, customer_id=customer.id, reference=f"APT-{uuid4().hex[:10].upper()}", starts_at=starts_at, ends_at=ends_at, status=AppointmentStatus.CONFIRMED, service_name=service.name, service_duration_minutes=service.duration_minutes, service_price=service.price)
        try:
            await self.appointments.create(appointment)
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError("Requested time is no longer available") from exc
        await bus.publish(Event("appointment.created", {"tenant_id": tenant_id, "appointment_id": appointment.id}))
        return appointment
