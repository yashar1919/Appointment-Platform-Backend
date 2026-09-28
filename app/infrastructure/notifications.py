from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
import logging
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.application.events import Event, EventBus
from app.core.config import Settings
from app.domain.models import Appointment, Customer, NotificationLog, Tenant

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

    async def handle(self, event: Event) -> None:
        appointment_id = event.payload.get("appointment_id")
        if not appointment_id:
            return
        async with self.session_factory() as db:
            appointment = await db.scalar(select(Appointment).where(Appointment.id == appointment_id, Appointment.tenant_id == event.payload["tenant_id"]))
            customer = await db.scalar(select(Customer).where(Customer.id == appointment.customer_id)) if appointment else None
            tenant = await db.scalar(select(Tenant).where(Tenant.id == event.payload["tenant_id"]))
            if not appointment or not customer or not customer.phone:
                return
            event_key = f"{event.name}.{event.payload.get('reminder_window')}" if event.payload.get("reminder_window") else event.name
            if await db.scalar(select(NotificationLog.id).where(NotificationLog.appointment_id == appointment.id, NotificationLog.event_type == event_key)):
                return
            text = self._template(event.name, appointment, tenant)
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
    def _template(event_name: str, appointment: Appointment, tenant: Tenant | None) -> str:
        tenant_name = tenant.name if tenant else "your provider"
        when = appointment.starts_at.strftime("%Y-%m-%d %H:%M UTC")
        if event_name == "appointment.cancelled":
            return f"{tenant_name}: your appointment {appointment.reference} on {when} has been cancelled."
        if event_name == "appointment.reminder":
            return f"Reminder from {tenant_name}: appointment {appointment.reference} starts on {when}."
        return f"{tenant_name}: appointment {appointment.reference} is confirmed for {when}."


def register_notification_handlers(bus: EventBus, service: NotificationService) -> None:
    for event_name in ("appointment.created", "appointment.cancelled", "appointment.reminder"):
        bus.subscribe(event_name, service.handle)
