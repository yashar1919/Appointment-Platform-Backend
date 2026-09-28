from fastapi import Header
from app.core.config import get_settings
from app.core.errors import AppError


async def require_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    expected = get_settings().admin_api_key
    if not expected or x_admin_key != expected:
        raise AppError("admin_unauthorized", "Valid X-Admin-Key header required", 401)
