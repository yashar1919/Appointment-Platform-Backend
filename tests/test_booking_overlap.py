import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.application.services.services import AppointmentService
from app.core.errors import ConflictError


class BookingOverlapTests(unittest.TestCase):
    def test_booking_inside_existing_two_hour_booking_is_rejected(self) -> None:
        async def scenario() -> None:
            service_id, staff_id, location_id, tenant_id = uuid4(), uuid4(), uuid4(), uuid4()
            booking_service = AppointmentService.__new__(AppointmentService)
            booking_service.services = SimpleNamespace(get_active=AsyncMock(return_value=SimpleNamespace(id=service_id, duration_minutes=30, price=Decimal("100"))))
            booking_service.staff = SimpleNamespace(get_eligible=AsyncMock(return_value=SimpleNamespace(id=staff_id)))
            booking_service.locations = SimpleNamespace(get_active=AsyncMock(return_value=SimpleNamespace(id=location_id)))
            booking_service.schedule = SimpleNamespace(blocked=AsyncMock(return_value=False), occupied=AsyncMock(return_value=True))

            with self.assertRaises(ConflictError):
                await booking_service.book(tenant_id, service_id, staff_id, location_id, datetime.now(timezone.utc) + timedelta(hours=1), {"name": "Test", "phone": "000"})

            booking_service.schedule.occupied.assert_awaited_once()

        asyncio.run(scenario())