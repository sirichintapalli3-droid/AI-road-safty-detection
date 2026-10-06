import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routers.auth import router as auth_router
from app.routers.detection import router as detection_router
from app.routers.alerts import router as alerts_router
from app.routers.helmet import router as helmet_router
from app.routers.number_plate import router as number_plate_router
from app.routers.health import router as health_router

settings = get_settings()
logging.basicConfig(level=logging.INFO)
app = FastAPI(title=settings.app_name, version=settings.app_version)


@app.on_event("startup")
def initialize_database() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        logging.getLogger(__name__).warning("Database unavailable during startup; retry after the database is ready.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.frontend_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(detection_router, prefix=settings.api_prefix)
app.include_router(alerts_router, prefix=settings.api_prefix)
app.include_router(helmet_router, prefix=settings.api_prefix)
app.include_router(number_plate_router, prefix=settings.api_prefix)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"message": "Road safety API is running", "docs": "/docs"}
