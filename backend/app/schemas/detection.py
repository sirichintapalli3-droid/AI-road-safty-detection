from datetime import datetime

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class Detection(BaseModel):
    class_name: str
    confidence: float = Field(ge=0, le=1)
    box: BoundingBox


class DetectionResponse(BaseModel):
    model: str
    image_width: int
    image_height: int
    detections: list[Detection]


class AccidentImageResponse(BaseModel):
    model: str
    assessment: str
    possible_accident: bool
    confidence: float = Field(ge=0, le=1)
    reason: str
    detections: list[Detection]


class TrackingSummary(BaseModel):
    model: str
    tracker: str
    processed_frames: int
    video_fps: float
    duration_seconds: float
    total_unique_vehicles: int
    vehicle_counts: dict[str, int]
    peak_visible_vehicles: int
    average_visible_vehicles: float
    density_level: str


class HelmetDetection(BaseModel):
    class_name: str
    confidence: float = Field(ge=0, le=1)
    box: BoundingBox


class HelmetDetectionResponse(BaseModel):
    model: str
    helmet_status: str
    detections: list[HelmetDetection]


class NumberPlateReading(BaseModel):
    plate_text: str
    ocr_confidence: float = Field(ge=0, le=1)
    box: BoundingBox


class NumberPlateResponse(BaseModel):
    model: str
    readings: list[NumberPlateReading]


class SpeedAnalysisSummary(BaseModel):
    model: str
    tracker: str
    processed_frames: int
    video_fps: float
    calibrated: bool
    speed_limit_kmh: float
    allowed_direction_degrees: float
    maximum_speed_kmh: float | None
    vehicle_speeds_kmh: dict[str, float]
    overspeeding_vehicle_ids: list[str]
    wrong_way_vehicle_ids: list[str]


class AccidentEvent(BaseModel):
    frame_number: int
    timestamp_seconds: float
    vehicle_ids: list[str]
    confidence: float = Field(ge=0, le=1)
    reason: str


class AccidentAnalysisSummary(BaseModel):
    model: str
    tracker: str
    processed_frames: int
    video_fps: float
    possible_accidents: list[AccidentEvent]


class AlertMessage(BaseModel):
    alert_type: str
    message: str
    timestamp: datetime
    details: dict[str, object] = Field(default_factory=dict)
