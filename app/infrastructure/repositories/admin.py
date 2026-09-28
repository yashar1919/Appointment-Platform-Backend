from datetime import date
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models import Appointment, AppointmentStatus, Service, Staff, StaffService


class AdminRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def appointments(self, tenant_id: UUID, day: date | None, status: AppointmentStatus | None) -> list[Appointment]:
        query = select(Appointment).where(Appointment.tenant_id == tenant_id).order_by(Appointment.starts_at)
        if day: query = query.where(Appointment.starts_at >= day, Appointment.starts_at < day.fromordinal(day.toordinal() + 1))
        if status: query = query.where(Appointment.status == status)
        return list((await self.db.scalars(query)).all())

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
