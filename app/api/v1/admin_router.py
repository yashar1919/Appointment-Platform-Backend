from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.admin_auth import require_admin_key
from app.api.admin_schemas import AdminAppointmentOut, AdminServiceOut, AdminStaffOut, ServiceCreate, ServiceUpdate, StaffCreate, StaffUpdate
from app.application.events import Event, bus
from app.application.services.admin_service import AdminService
from app.application.services.services import TenantService
from app.domain.models import AppointmentStatus
from app.infrastructure.database import get_db

router = APIRouter(prefix="/api/v1/admin/{tenant_slug}", tags=["admin"], dependencies=[Depends(require_admin_key)])


async def service(tenant_slug: str, db: AsyncSession) -> AdminService:
    tenant = await TenantService(db).resolve(tenant_slug)
    return AdminService(db, tenant.id, tenant.timezone)


@router.get("/appointments", response_model=list[AdminAppointmentOut])
async def appointments(tenant_slug: str, appointment_date: date | None = Query(None, alias="date"), appointment_status: AppointmentStatus | None = Query(None, alias="status"), db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).list_appointments(appointment_date, appointment_status)


@router.patch("/appointments/{appointment_id}/cancel", response_model=AdminAppointmentOut)
async def cancel_appointment(tenant_slug: str, appointment_id: UUID, db: AsyncSession = Depends(get_db)):
    admin = await service(tenant_slug, db)
    appointment = await admin.cancel_appointment(appointment_id)
    await bus.publish(Event("appointment.cancelled", {"tenant_id": admin.tenant_id, "appointment_id": appointment.id}))
    return appointment


@router.get("/services", response_model=list[AdminServiceOut])
async def list_services(tenant_slug: str, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).list_services()


@router.post("/services", response_model=AdminServiceOut, status_code=status.HTTP_201_CREATED)
async def create_service(tenant_slug: str, payload: ServiceCreate, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).create_service(payload)


@router.put("/services/{service_id}", response_model=AdminServiceOut)
async def update_service(tenant_slug: str, service_id: UUID, payload: ServiceUpdate, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).update_service(service_id, payload)


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(tenant_slug: str, service_id: UUID, db: AsyncSession = Depends(get_db)):
    await (await service(tenant_slug, db)).delete_service(service_id)


@router.get("/staff", response_model=list[AdminStaffOut])
async def list_staff(tenant_slug: str, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).list_staff()


@router.post("/staff", response_model=AdminStaffOut, status_code=status.HTTP_201_CREATED)
async def create_staff(tenant_slug: str, payload: StaffCreate, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).create_staff(payload)


@router.put("/staff/{staff_id}", response_model=AdminStaffOut)
async def update_staff(tenant_slug: str, staff_id: UUID, payload: StaffUpdate, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).update_staff(staff_id, payload)


@router.delete("/staff/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_staff(tenant_slug: str, staff_id: UUID, db: AsyncSession = Depends(get_db)):
    await (await service(tenant_slug, db)).delete_staff(staff_id)
