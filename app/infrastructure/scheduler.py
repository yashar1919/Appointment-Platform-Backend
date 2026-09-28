from datetime import datetime, timedelta, timezone
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from app.application.events import Event, bus
from app.domain.models import Appointment, AppointmentStatus
from app.infrastructure.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def publish_reminders() -> None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        appointments = list((await db.scalars(select(Appointment).where(Appointment.status == AppointmentStatus.CONFIRMED, Appointment.starts_at > now, Appointment.starts_at <= now + timedelta(hours=24)))).all())
    for appointment in appointments:
        hours = (appointment.starts_at - now).total_seconds() / 3600
        if hours <= 12.0:
            window = "12h"
        elif hours <= 24.0:
            window = "24h"
        else:
            continue
        await bus.publish(Event("appointment.reminder", {"tenant_id": appointment.tenant_id, "appointment_id": appointment.id, "reminder_window": window}))


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(publish_reminders, "interval", hours=1, id="appointment-reminders", replace_existing=True)
    return scheduler
