from datetime import datetime
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models import Appointment, AppointmentStatus, BlockedTime, Customer, Location, Service, Staff, StaffService, Tenant, WorkingHours


class TenantRepository:
    def __init__(self, db: AsyncSession) -> None: self.db = db
    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        return await self.db.scalar(select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active.is_(True)))
    async def get_by_slug(self, slug: str) -> Tenant | None:
        return await self.db.scalar(select(Tenant).where(Tenant.slug == slug, Tenant.is_active.is_(True)))


class ServiceRepository:
    def __init__(self, db: AsyncSession) -> None: self.db = db
    async def list_active(self, tenant_id: UUID) -> list[Service]:
        return list((await self.db.scalars(select(Service).where(Service.tenant_id == tenant_id, Service.is_active.is_(True)).order_by(Service.name))).all())
    async def get_active(self, tenant_id: UUID, service_id: UUID) -> Service | None:
        return await self.db.scalar(select(Service).where(Service.id == service_id, Service.tenant_id == tenant_id, Service.is_active.is_(True)))


class StaffRepository:
    def __init__(self, db: AsyncSession) -> None: self.db = db
    async def list_active(self, tenant_id: UUID) -> list[Staff]:
        query = select(Staff).where(Staff.tenant_id == tenant_id, Staff.is_active.is_(True)).order_by(Staff.name)
        return list((await self.db.scalars(query)).all())
    async def list_for_service(self, tenant_id: UUID, service_id: UUID) -> list[Staff]:
        query = select(Staff).join(StaffService, StaffService.staff_id == Staff.id).where(Staff.tenant_id == tenant_id, StaffService.service_id == service_id, Staff.is_active.is_(True)).order_by(Staff.name)
        return list((await self.db.scalars(query)).all())
    async def get_eligible(self, tenant_id: UUID, staff_id: UUID, service_id: UUID) -> Staff | None:
        query = select(Staff).join(StaffService, StaffService.staff_id == Staff.id).where(Staff.id == staff_id, Staff.tenant_id == tenant_id, StaffService.service_id == service_id, Staff.is_active.is_(True))
        return await self.db.scalar(query)


class LocationRepository:
    def __init__(self, db: AsyncSession) -> None: self.db = db
    async def list_active(self, tenant_id: UUID) -> list[Location]:
        return list((await self.db.scalars(select(Location).where(Location.tenant_id == tenant_id, Location.is_active.is_(True)).order_by(Location.name))).all())
    async def get_active(self, tenant_id: UUID, location_id: UUID) -> Location | None:
        return await self.db.scalar(select(Location).where(Location.id == location_id, Location.tenant_id == tenant_id, Location.is_active.is_(True)))


class SchedulingRepository:
    def __init__(self, db: AsyncSession) -> None: self.db = db
    async def hours(self, tenant_id: UUID, location_id: UUID, day: int) -> WorkingHours | None:
        return await self.db.scalar(select(WorkingHours).where(WorkingHours.tenant_id == tenant_id, WorkingHours.location_id == location_id, WorkingHours.day_of_week == day))
    async def blocked(self, tenant_id: UUID, location_id: UUID, staff_id: UUID, start: datetime, end: datetime) -> bool:
        query = select(BlockedTime.id).where(BlockedTime.tenant_id == tenant_id, BlockedTime.location_id == location_id, (BlockedTime.staff_id.is_(None) | (BlockedTime.staff_id == staff_id)), BlockedTime.starts_at < end, BlockedTime.ends_at > start).limit(1)
        return await self.db.scalar(query) is not None
    async def occupied(self, tenant_id: UUID, staff_id: UUID, start: datetime, end: datetime) -> bool:
        return bool(await self.overlapping(tenant_id, staff_id, start, end, limit=1))
    async def overlapping(self, tenant_id: UUID, staff_id: UUID, start: datetime, end: datetime, limit: int | None = None) -> list[Appointment]:
        query = select(Appointment).where(Appointment.tenant_id == tenant_id, Appointment.staff_id == staff_id, Appointment.status.in_([AppointmentStatus.CONFIRMED, "pending"]), Appointment.starts_at < end, Appointment.ends_at > start).order_by(Appointment.starts_at)
        if limit is not None:
            query = query.limit(limit)
        return list((await self.db.scalars(query)).all())


class CustomerRepository:
    def __init__(self, db: AsyncSession) -> None: self.db = db
    async def get_or_create(self, tenant_id: UUID, name: str, phone: str, email: str | None) -> Customer:
        customer = await self.db.scalar(select(Customer).where(Customer.tenant_id == tenant_id, Customer.phone == phone))
        if customer:
            customer.name, customer.email = name, email
            return customer
        customer = Customer(tenant_id=tenant_id, name=name, phone=phone, email=email)
        self.db.add(customer)
        await self.db.flush()
        return customer


class AppointmentRepository:
    def __init__(self, db: AsyncSession) -> None: self.db = db
    async def create(self, appointment: Appointment) -> Appointment:
        self.db.add(appointment)
        await self.db.flush()
        return appointment
    async def get_by_reference(self, tenant_id: UUID, reference: str) -> Appointment | None:
        return await self.db.scalar(select(Appointment).where(Appointment.tenant_id == tenant_id, Appointment.reference == reference))
