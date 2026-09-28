from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
import logging
import httpx
import jdatetime
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.application.events import Event, EventBus
from app.core.config import Settings
from app.domain.models import Appointment, Customer, NotificationLog, Staff, Tenant

logger = logging.getLogger(__name__)


class SMSProvider(ABC):
    @abstractmethod
    async def send(self, to_number: str, text: str) -> str:
        """Send an SMS and return the provider message identifier."""


class MeliPayamakProvider(SMSProvider):
    endpoint = "https://rest.payamak-panel.com/api/SendSMS/SendSMS"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send(self, to_number: str, text: str) -> str:
        payload = {"username": self.settings.meli_payamak_username, "password": self.settings.meli_payamak_password, "from": self.settings.meli_payamak_from_number, "to": to_number, "text": text}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(self.endpoint, json=payload)
            response.raise_for_status()
            body: Any = response.json()
        if isinstance(body, dict):
            return str(body.get("Value") or body.get("value") or body.get("RetStatus") or "accepted")
        return str(body)


class NotificationService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], settings: Settings, provider: SMSProvider | None = None) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.provider = provider or MeliPayamakProvider(settings)

    async def send_test_sms(self, phone: str, message: str) -> str:
        return await self.provider.send(phone, message)

    async def handle(self, event: Event) -> None:
        appointment_id = event.payload.get("appointment_id")
        if not appointment_id:
            return
        async with self.session_factory() as db:
            appointment = await db.scalar(select(Appointment).where(Appointment.id == appointment_id, Appointment.tenant_id == event.payload["tenant_id"]))
            customer = await db.scalar(select(Customer).where(Customer.id == appointment.customer_id)) if appointment else None
            staff = await db.scalar(select(Staff).where(Staff.id == appointment.staff_id)) if appointment else None
            tenant = await db.scalar(select(Tenant).where(Tenant.id == event.payload["tenant_id"]))
            if not appointment or not customer or not customer.phone:
                return
            event_key = f"{event.name}.{event.payload.get('reminder_window')}" if event.payload.get("reminder_window") else event.name
            if await db.scalar(select(NotificationLog.id).where(NotificationLog.appointment_id == appointment.id, NotificationLog.event_type == event_key)):
                return
            text = self._template(event.name, appointment, customer, staff, tenant)
            log = NotificationLog(tenant_id=appointment.tenant_id, appointment_id=appointment.id, event_type=event_key, recipient=customer.phone, status="pending")
            db.add(log)
            try:
                provider_id = await self.provider.send(customer.phone, text)
                log.status, log.provider_message_id, log.sent_at = "sent", provider_id, datetime.now(timezone.utc)
            except Exception as exc:
                log.status, log.error_message = "failed", str(exc)[:1000]
                logger.exception("SMS notification failed", extra={"event": event.name, "appointment_id": str(appointment.id)})
            await db.commit()

    @staticmethod
    def _template(event_name: str, appointment: Appointment, customer: Customer, staff: Staff | None, tenant: Tenant | None) -> str:
        tenant_name = tenant.name if tenant else "کلینیک"
        tenant_zone = ZoneInfo(tenant.timezone) if tenant else timezone.utc
        local_start = appointment.starts_at.astimezone(tenant_zone)
        jalali_start = jdatetime.datetime.fromgregorian(datetime=local_start.replace(tzinfo=None))
        weekdays = ("دوشنبه", "سه شنبه", "چهارشنبه", "پنج شنبه", "جمعه", "شنبه", "یکشنبه")
        months = ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند")
        digits = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        date_text = f"{weekdays[local_start.weekday()]} {jalali_start.day} {months[jalali_start.month - 1]} {jalali_start.year}".translate(digits)
        time_text = local_start.strftime("%H:%M").translate(digits)
        staff_name = staff.name if staff else "پزشک"
        if event_name == "appointment.cancelled":
            return f"{tenant_name}: نوبت {appointment.reference} شما در تاریخ {date_text} ساعت {time_text} لغو شد."
        if event_name == "appointment.reminder":
            return f"یادآوری نوبت: {customer.name} عزیز، نوبت شما برای {appointment.service_name} در تاریخ {date_text} ساعت {time_text} رزرو شده است.\nکد رهگیری: {appointment.reference}\nمنتظر دیدار شما هستیم.\n{tenant_name}\nلغو11"
        return f"{customer.name} عزیز، نوبت شما برای {appointment.service_name} در تاریخ {date_text} ساعت {time_text} با موفقیت ثبت شد.\nکد رهگیری: {appointment.reference}\n{tenant_name}\nلغو11"


def register_notification_handlers(bus: EventBus, service: NotificationService) -> None:
    for event_name in ("appointment.created", "appointment.cancelled", "appointment.reminder"):
        bus.subscribe(event_name, service.handle)
