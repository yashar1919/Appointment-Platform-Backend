import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.public.router import router as public_router
from app.api.v1.admin_router import router as admin_router, test_router as admin_test_router
from app.application.events import bus
from app.core.config import get_settings
from app.core.errors import AppError
from app.infrastructure.database import AsyncSessionLocal, close_database
from app.infrastructure.notifications import NotificationService, register_notification_handlers

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    notification_service = NotificationService(AsyncSessionLocal, settings)
    register_notification_handlers(bus, notification_service)
    yield
    await close_database()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *settings.cors_origin_list,
        "http://localhost:3000",
        "http://localhost:3001",
        "https://appointment-two-beta.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.include_router(public_router)
app.include_router(admin_router)
app.include_router(admin_test_router)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}})


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, __: Exception) -> JSONResponse:
    logging.exception("Unhandled application error")
    return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": "Internal server error"}})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
