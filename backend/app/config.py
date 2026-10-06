from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Road Safety System"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api"
    database_url: str = "mysql+pymysql://road_safety:road_safety@localhost:3306/road_safety"
    frontend_origins: str = "http://localhost:5173,http://localhost:5176"
    max_upload_size_mb: int = 200
    yolo_model_path: str = "yolo11n.pt"
    yolo_confidence: float = 0.25
    yolo_device: str = "cpu"
    helmet_model_path: str = "models/helmet.pt"
    helmet_confidence: float = 0.35
    plate_model_path: str = "models/number_plate.pt"
    plate_confidence: float = 0.35
    ocr_languages: str = "en"
    density_medium_threshold: int = 5
    density_high_threshold: int = 15
    density_very_high_threshold: int = 30
    pixels_per_meter: float = 0.0
    speed_limit_kmh: float = 50.0
    allowed_direction_degrees: float = 0.0
    wrong_way_min_displacement_pixels: float = 15.0
    accident_iou_threshold: float = 0.2
    accident_min_motion_pixels: float = 5.0
    jwt_secret: str = "change-this-development-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
