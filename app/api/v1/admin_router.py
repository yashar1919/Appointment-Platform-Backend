from datetime import date
from uuid import UUID
import uuid # ✅ اضافه شد
from fastapi import APIRouter, Depends, Query, status, HTTPException # ✅ HTTPException اضافه شد
from sqlalchemy import select # ✅ اضافه شد
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_auth import require_admin_key
from app.api.admin_schemas import (
    AdminAppointmentOut, AdminLocationOut, AdminServiceCategoryOut, 
    AdminServiceOut, AdminStaffOut, AdminTenantOut, AppointmentStatusUpdate, 
    LocationCreate, LocationUpdate, ServiceCategoryCreate, ServiceCategoryUpdate, 
    ServiceCreate, ServiceUpdate, StaffCreate, StaffUpdate, TenantProfileUpdate, 
    TestSMSRequest, AdminAppointmentCreate # ✅ اضافه شد
)
from app.application.events import Event, bus
from app.application.services.admin_service import AdminService
from app.application.services.services import TenantService
from app.domain.models import AppointmentStatus, Tenant, Customer, Service, Appointment # ✅ مدل‌ها اضافه شدند
from app.infrastructure.database import get_db, AsyncSessionLocal
from app.infrastructure.notifications import NotificationService
from app.core.config import get_settings

router = APIRouter(prefix="/api/v1/admin/{tenant_slug}", tags=["admin"], dependencies=[Depends(require_admin_key)])
test_router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_admin_key)])


@test_router.post("/test-sms")
async def test_sms(payload: TestSMSRequest):
    # Protected by the router-level admin key dependency.
    try:
        rec_id = await NotificationService(AsyncSessionLocal, get_settings()).send_test_sms(payload.phone, payload.message)
        return {"status": "sent", "rec_id": rec_id}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


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
    await bus.publish(Event("appointment.cancelled", {"tenant_id": admin.tenant_id, "appointment_id": appointment["id"]}))
    return appointment


@router.patch("/appointments/{appointment_id}/status", response_model=AdminAppointmentOut)
async def update_appointment_status(tenant_slug: str, appointment_id: UUID, payload: AppointmentStatusUpdate, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).update_appointment_status(appointment_id, payload.status)


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


@router.get("/categories", response_model=list[AdminServiceCategoryOut])
async def list_categories(tenant_slug: str, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).list_categories()


@router.post("/categories", response_model=AdminServiceCategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(tenant_slug: str, payload: ServiceCategoryCreate, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).create_category(payload)


@router.put("/categories/{category_id}", response_model=AdminServiceCategoryOut)
async def update_category(tenant_slug: str, category_id: UUID, payload: ServiceCategoryUpdate, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).update_category(category_id, payload)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(tenant_slug: str, category_id: UUID, db: AsyncSession = Depends(get_db)):
    await (await service(tenant_slug, db)).delete_category(category_id)


@router.get("/locations", response_model=list[AdminLocationOut])
async def list_locations(tenant_slug: str, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).list_locations()


@router.post("/locations", response_model=AdminLocationOut, status_code=status.HTTP_201_CREATED)
async def create_location(tenant_slug: str, payload: LocationCreate, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).create_location(payload)


@router.put("/locations/{location_id}", response_model=AdminLocationOut)
async def update_location(tenant_slug: str, location_id: UUID, payload: LocationUpdate, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).update_location(location_id, payload)


@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(tenant_slug: str, location_id: UUID, db: AsyncSession = Depends(get_db)):
    await (await service(tenant_slug, db)).delete_location(location_id)


@router.get("/profile", response_model=AdminTenantOut)
async def get_profile(tenant_slug: str, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).get_tenant()


@router.put("/profile", response_model=AdminTenantOut)
async def update_profile(tenant_slug: str, payload: TenantProfileUpdate, db: AsyncSession = Depends(get_db)):
    return await (await service(tenant_slug, db)).update_tenant(payload)


@router.post(
    "/appointments", 
    response_model=AdminAppointmentOut, 
    status_code=status.HTTP_201_CREATED
)
async def create_admin_appointment(
    tenant_slug: str,
    payload: AdminAppointmentCreate,
    db: AsyncSession = Depends(get_db), # ✅ تغییر به AsyncSession
):
    # ۱. پیدا کردن Tenant (به روش Async)
    tenant_result = await db.execute(select(Tenant).filter(Tenant.slug == tenant_slug))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # ۲. پیدا کردن یا ساختن Customer (به روش Async)
    customer_result = await db.execute(
        select(Customer).filter(
            Customer.tenant_id == tenant.id,
            Customer.phone == payload.customer_phone
        )
    )
    customer = customer_result.scalar_one_or_none()
    
    if not customer:
        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name=payload.customer_name,
            phone=payload.customer_phone,
            email=None
        )
        db.add(customer)
    else:
        if customer.name != payload.customer_name:
            customer.name = payload.customer_name

    # ۳. دریافت اطلاعات Service برای قیمت و نام (به روش Async)
    service_result = await db.execute(select(Service).filter(Service.id == payload.service_id))
    service_obj = service_result.scalar_one_or_none()
    final_price = payload.price if payload.price is not None else (service_obj.price if service_obj else 0)

    # ۴. ساخت Appointment
    new_appointment = Appointment(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        customer_id=customer.id,
        service_id=payload.service_id,
        staff_id=payload.staff_id,
        location_id=payload.location_id,
        reference=f"APT-{uuid.uuid4().hex[:8].upper()}",
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        status=payload.status,
        service_name=service_obj.name if service_obj else "Unknown",
        service_duration_minutes=service_obj.duration_minutes if service_obj else 0,
        service_price=final_price,
        reminder_sent=False
    )
    
    db.add(new_appointment)
    await db.commit()
    await db.refresh(new_appointment)

    # ۵. بازگرداندن داده با فرمت AdminAppointmentOut
    return {
        "id": new_appointment.id,
        "reference": new_appointment.reference,
        "starts_at": new_appointment.starts_at,
        "ends_at": new_appointment.ends_at,
        "status": new_appointment.status,
        "service_name": new_appointment.service_name,
        "service_price": str(new_appointment.service_price),
        "staff_id": new_appointment.staff_id,
        "location_id": new_appointment.location_id,
        "customer_name": customer.name,
        "customer_phone": customer.phone
    }