from datetime import date
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models import Appointment, AppointmentStatus, Customer, Location, Service, ServiceCategory, Staff, StaffService, Tenant


class AdminRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def appointments(self, tenant_id: UUID, day: date | None, status: AppointmentStatus | None) -> list[dict]:
        query = select(Appointment, Customer.name, Customer.phone).join(Customer, Customer.id == Appointment.customer_id).where(Appointment.tenant_id == tenant_id).order_by(Appointment.starts_at)
        if day: query = query.where(Appointment.starts_at >= day, Appointment.starts_at < day.fromordinal(day.toordinal() + 1))
        if status: query = query.where(Appointment.status == status)
        return [self._appointment_record(appointment, customer_name, customer_phone) for appointment, customer_name, customer_phone in (await self.db.execute(query)).all()]

    async def appointment(self, tenant_id: UUID, appointment_id: UUID) -> dict | None:
        query = select(Appointment, Customer.name, Customer.phone).join(Customer, Customer.id == Appointment.customer_id).where(Appointment.id == appointment_id, Appointment.tenant_id == tenant_id)
        row = (await self.db.execute(query)).first()
        return self._appointment_record(*row) if row else None

    @staticmethod
    def _appointment_record(appointment: Appointment, customer_name: str, customer_phone: str) -> dict:
        # Join customer data here because Appointment has a foreign key but no ORM relationship.
        return {
            "id": appointment.id,
            "reference": appointment.reference,
            "starts_at": appointment.starts_at,
            "ends_at": appointment.ends_at,
            "status": appointment.status,
            "service_name": appointment.service_name,
            "service_price": appointment.service_price,
            "staff_id": appointment.staff_id,
            "location_id": appointment.location_id,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
        }

    async def service(self, tenant_id: UUID, service_id: UUID) -> Service | None:
        return await self.db.scalar(select(Service).where(Service.id == service_id, Service.tenant_id == tenant_id))

    async def services(self, tenant_id: UUID) -> list[Service]:
        return list((await self.db.scalars(select(Service).where(Service.tenant_id == tenant_id).order_by(Service.name))).all())

    async def staff(self, tenant_id: UUID) -> list[Staff]:
        return list((await self.db.scalars(select(Staff).where(Staff.tenant_id == tenant_id).order_by(Staff.name))).all())

    async def staff_member(self, tenant_id: UUID, staff_id: UUID) -> Staff | None:
        return await self.db.scalar(select(Staff).where(Staff.id == staff_id, Staff.tenant_id == tenant_id))

    async def link_services(self, staff: Staff, service_ids: list[UUID], tenant_id: UUID) -> None:
        valid = list((await self.db.scalars(select(Service.id).where(Service.tenant_id == tenant_id, Service.id.in_(service_ids)))).all())
        staff.service_links.clear()
        staff.service_links.extend(StaffService(staff_id=staff.id, service_id=service_id) for service_id in valid)

    async def categories(self, tenant_id: UUID) -> list[ServiceCategory]:
        return list((await self.db.scalars(select(ServiceCategory).where(ServiceCategory.tenant_id == tenant_id).order_by(ServiceCategory.name))).all())

    async def category(self, tenant_id: UUID, category_id: UUID) -> ServiceCategory | None:
        return await self.db.scalar(select(ServiceCategory).where(ServiceCategory.id == category_id, ServiceCategory.tenant_id == tenant_id))

    async def locations(self, tenant_id: UUID) -> list[Location]:
        return list((await self.db.scalars(select(Location).where(Location.tenant_id == tenant_id).order_by(Location.name))).all())

    async def location(self, tenant_id: UUID, location_id: UUID) -> Location | None:
        return await self.db.scalar(select(Location).where(Location.id == location_id, Location.tenant_id == tenant_id))

    async def tenant(self, tenant_id: UUID) -> Tenant | None:
        return await self.db.get(Tenant, tenant_id)
