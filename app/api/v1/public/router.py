from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.api.schemas import AppointmentCreate, AppointmentLookupRequest, AppointmentOut, AvailabilityOut, AvailabilityQuery, LocationOut, PublicStaffOut, ServiceOut, StaffOut
from app.application.services.services import AppointmentService, LocationService, SchedulingService, ServiceService, StaffService, TenantService
from app.infrastructure.database import get_db

router = APIRouter(prefix="/api/v1/public/{tenant_slug}", tags=["public"])


async def tenant(slug: str, db: AsyncSession):
    return await TenantService(db).resolve(slug)


@router.get("/services", response_model=list[ServiceOut])
async def services(tenant_slug: str, db: AsyncSession = Depends(get_db)):
    current = await tenant(tenant_slug, db)
    return await ServiceService(db).list(current.id)


@router.get("/staff", response_model=list[PublicStaffOut])
async def staff(tenant_slug: str, db: AsyncSession = Depends(get_db)):
    current = await tenant(tenant_slug, db)
    staff_members = await StaffService(db).list_active(current.id)
    return [
        {
            "id": member.id,
            "name": member.name,
            "role": member.role or "",
            "avatar": member.avatar or "",
            "bio": member.bio or "",
            "active": member.is_active,
            "experience_years": member.experience_years,
            "rating": member.rating,
            "specialties": member.specialties,
        }
        for member in staff_members
    ]


@router.get("/services/{service_id}/staff", response_model=list[StaffOut])
async def service_staff(tenant_slug: str, service_id: UUID, db: AsyncSession = Depends(get_db)):
    current = await tenant(tenant_slug, db)
    return await StaffService(db).list_for_service(current.id, service_id)


@router.get("/locations", response_model=list[LocationOut])
async def locations(tenant_slug: str, db: AsyncSession = Depends(get_db)):
    current = await tenant(tenant_slug, db)
    return await LocationService(db).list(current.id)


@router.get("/availability", response_model=list[AvailabilityOut])
async def availability(tenant_slug: str, query: AvailabilityQuery = Depends(), db: AsyncSession = Depends(get_db)):
    current = await tenant(tenant_slug, db)
    return await SchedulingService(db).availability(current.id, query.service_id, query.location_id, query.day, query.staff_id)


@router.post("/appointments", response_model=AppointmentOut, status_code=201)
async def book(tenant_slug: str, payload: AppointmentCreate, db: AsyncSession = Depends(get_db)):
    current = await tenant(tenant_slug, db)
    return await AppointmentService(db).book(current.id, payload.service_id, payload.staff_id, payload.location_id, payload.starts_at, {"name": payload.customer_name, "phone": payload.customer_phone, "email": payload.customer_email})


@router.post("/appointments/lookup", response_model=AppointmentOut)
async def lookup_appointment(tenant_slug: str, payload: AppointmentLookupRequest, db: AsyncSession = Depends(get_db)):
    current = await tenant(tenant_slug, db)
    appointment = await AppointmentService(db).lookup(current.id, payload.reference_code, payload.customer_phone)
    if not appointment:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "نوبتی با این مشخصات یافت نشد"})
    staff_member = await StaffService(db).get_by_id(current.id, appointment.staff_id)
    response = AppointmentOut.model_validate(appointment).model_dump()
    response["staff_name"] = staff_member.name if staff_member else None
    return response
