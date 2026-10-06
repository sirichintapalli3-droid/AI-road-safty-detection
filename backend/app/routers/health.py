from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}
