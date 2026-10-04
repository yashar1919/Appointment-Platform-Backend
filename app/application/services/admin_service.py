from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.admin_schemas import LocationCreate, LocationUpdate, ServiceCategoryCreate, ServiceCategoryUpdate, ServiceCreate, ServiceUpdate, StaffCreate, StaffUpdate, TenantProfileUpdate
from app.core.errors import ConflictError, NotFoundError
from app.domain.models import Appointment, AppointmentStatus, Location, Service, ServiceCategory, Staff, StaffService
from app.infrastructure.repositories.admin import AdminRepository
from fastapi import HTTPException


class AdminService:
    def __init__(self, db: AsyncSession, tenant_id: UUID, tenant_timezone: str) -> None:
        self.db, self.tenant_id, self.tenant_timezone, self.repo = db, tenant_id, tenant_timezone, AdminRepository(db)

    async def list_appointments(self, appointment_date: date | None, status: AppointmentStatus | None) -> list[dict]:
        return await self.repo.appointments(self.tenant_id, appointment_date, status)

    async def cancel_appointment(self, appointment_id: UUID) -> dict:
        appointment = await self.db.get(Appointment, appointment_id)
        if not appointment or appointment.tenant_id != self.tenant_id:
            raise NotFoundError("Appointment not found")
        if appointment.status == AppointmentStatus.CANCELLED:
            return await self.repo.appointment(self.tenant_id, appointment_id)
        now = datetime.now(ZoneInfo(self.tenant_timezone))
        if appointment.starts_at <= now:
            raise HTTPException(status_code=400, detail="امکان لغو نوبت‌های گذشته وجود ندارد.")
        if appointment.starts_at <= now + timedelta(hours=24):
            raise HTTPException(status_code=400, detail="لغو نوبت تنها تا ۲۴ ساعت قبل از زمان مراجعه امکان‌پذیر است. برای لغو فوری لطفاً تماس بگیرید.")
        appointment.status = AppointmentStatus.CANCELLED
        await self.db.commit()
        return await self.repo.appointment(self.tenant_id, appointment_id)

    async def update_appointment_status(self, appointment_id: UUID, status: AppointmentStatus) -> dict:
        appointment = await self.db.get(Appointment, appointment_id)
        if not appointment or appointment.tenant_id != self.tenant_id:
            raise NotFoundError("Appointment not found")
        appointment.status = status
        await self.db.commit()
        return await self.repo.appointment(self.tenant_id, appointment_id)

    async def list_services(self) -> list[Service]:
        return await self.repo.services(self.tenant_id)

    async def create_service(self, payload: ServiceCreate) -> Service:
        service = Service(tenant_id=self.tenant_id, **payload.model_dump())
        self.db.add(service)
        try:
            await self.db.commit()
        except Exception as exc:
            await self.db.rollback()
            raise ConflictError("Service could not be created") from exc
        await self.db.refresh(service)
        return service

    async def update_service(self, service_id: UUID, payload: ServiceUpdate) -> Service:
        service = await self.repo.service(self.tenant_id, service_id)
        if not service: raise NotFoundError("Service not found")
        for key, value in payload.model_dump().items(): setattr(service, key, value)
        await self.db.commit()
        await self.db.refresh(service)
        return service

    async def delete_service(self, service_id: UUID) -> None:
        service = await self.repo.service(self.tenant_id, service_id)
        if not service: raise NotFoundError("Service not found")
        service.is_active = False
        await self.db.commit()

    async def list_staff(self) -> list[Staff]:
        return await self.repo.staff(self.tenant_id)

    async def create_staff(self, payload: StaffCreate) -> Staff:
        staff = Staff(tenant_id=self.tenant_id, name=payload.name, role=payload.role)
        self.db.add(staff)
        await self.db.flush()
        await self.repo.link_services(staff, payload.service_ids, self.tenant_id)
        await self.db.commit()
        await self.db.refresh(staff)
        return staff

    async def update_staff(self, staff_id: UUID, payload: StaffUpdate) -> Staff:
        staff = await self.repo.staff_member(self.tenant_id, staff_id)
        if not staff: raise NotFoundError("Staff member not found")
        staff.name, staff.role, staff.is_active = payload.name, payload.role, payload.is_active
        await self.db.execute(delete(StaffService).where(StaffService.staff_id == staff.id))
        self.db.add_all([StaffService(staff_id=staff.id, service_id=service_id) for service_id in payload.service_ids])
        await self.db.commit()
        await self.db.refresh(staff)
        return staff

    async def delete_staff(self, staff_id: UUID) -> None:
        staff = await self.repo.staff_member(self.tenant_id, staff_id)
        if not staff: raise NotFoundError("Staff member not found")
        staff.is_active = False
        await self.db.commit()

    async def list_categories(self) -> list[ServiceCategory]:
        return await self.repo.categories(self.tenant_id)

    async def create_category(self, payload: ServiceCategoryCreate) -> ServiceCategory:
        category = ServiceCategory(tenant_id=self.tenant_id, **payload.model_dump())
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def update_category(self, category_id: UUID, payload: ServiceCategoryUpdate) -> ServiceCategory:
        category = await self.repo.category(self.tenant_id, category_id)
        if not category: raise NotFoundError("Service category not found")
        for key, value in payload.model_dump().items(): setattr(category, key, value)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def delete_category(self, category_id: UUID) -> None:
        category = await self.repo.category(self.tenant_id, category_id)
        if not category: raise NotFoundError("Service category not found")
        await self.db.delete(category)
        await self.db.commit()

    async def list_locations(self) -> list[Location]:
        return await self.repo.locations(self.tenant_id)

    async def create_location(self, payload: LocationCreate) -> Location:
        location = Location(tenant_id=self.tenant_id, **payload.model_dump())
        self.db.add(location)
        await self.db.commit()
        await self.db.refresh(location)
        return location

    async def update_location(self, location_id: UUID, payload: LocationUpdate) -> Location:
        location = await self.repo.location(self.tenant_id, location_id)
        if not location: raise NotFoundError("Location not found")
        for key, value in payload.model_dump().items(): setattr(location, key, value)
        await self.db.commit()
        await self.db.refresh(location)
        return location

    async def delete_location(self, location_id: UUID) -> None:
        location = await self.repo.location(self.tenant_id, location_id)
        if not location: raise NotFoundError("Location not found")
        location.is_active = False
        await self.db.commit()

    async def get_tenant(self):
        tenant = await self.repo.tenant(self.tenant_id)
        if not tenant: raise NotFoundError("Tenant not found")
        return tenant

    async def update_tenant(self, payload: TenantProfileUpdate):
        tenant = await self.get_tenant()
        for key, value in payload.model_dump(exclude_unset=True).items(): setattr(tenant, key, value)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant
