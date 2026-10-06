import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.ai.vehicle_detection import VEHICLE_CLASSES, decode_image, get_vehicle_detector, intersection_over_union
from app.config import get_settings
from app.services.alerts import alert_manager, create_alert
from app.schemas.detection import AccidentAnalysisSummary, AccidentImageResponse, DetectionResponse, SpeedAnalysisSummary, TrackingSummary

router = APIRouter(prefix="/detection", tags=["detection"])
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/avi", "video/quicktime", "video/x-msvideo"}
MAX_VIDEO_SIZE_BYTES = 200 * 1024 * 1024


@router.post("/image", response_model=DetectionResponse)
async def detect_vehicles(file: UploadFile = File(...)) -> DetectionResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPEG, PNG, or WebP image.",
        )

    contents = await file.read(MAX_IMAGE_SIZE_BYTES + 1)
    if len(contents) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image exceeds the 10 MB limit.")

    image = decode_image(contents)
    if image is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is not a valid image.")

    try:
        detector = await run_in_threadpool(get_vehicle_detector)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YOLO model is unavailable. Check YOLO_MODEL_PATH and model download access.",
        ) from error
    detections = await run_in_threadpool(detector.detect, image)
    return DetectionResponse(
        model=detector.model_name,
        image_width=image.shape[1],
        image_height=image.shape[0],
        detections=detections,
    )


@router.post("/accident-image", response_model=AccidentImageResponse)
async def assess_accident_image(file: UploadFile = File(...)) -> AccidentImageResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a JPEG, PNG, or WebP image.")
    contents = await file.read(MAX_IMAGE_SIZE_BYTES + 1)
    if len(contents) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image exceeds the 10 MB limit.")
    image = decode_image(contents)
    if image is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is not a valid image.")
    try:
        detector = await run_in_threadpool(get_vehicle_detector)
        detections = await run_in_threadpool(detector.detect, image)
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="YOLO model is unavailable.") from error

    vehicle_detections = [item for item in detections if item.class_name in VEHICLE_CLASSES]
    overlap = 0.0
    involved_ids: list[str] = []
    for index, first in enumerate(vehicle_detections):
        for second in vehicle_detections[index + 1:]:
            current_overlap = intersection_over_union(
                [first.box.x1, first.box.y1, first.box.x2, first.box.y2],
                [second.box.x1, second.box.y1, second.box.x2, second.box.y2],
            )
            if current_overlap > overlap:
                overlap = current_overlap
                involved_ids = [first.class_name, second.class_name]

    possible_accident = overlap >= get_settings().accident_iou_threshold
    confidence = min(0.99, 0.55 + overlap * 0.35) if possible_accident else 0.0
    reason = "Vehicle boxes overlap in this frame; possible collision requires review." if possible_accident else "No overlapping vehicle boxes detected; one image cannot confirm or rule out an accident."
    result = AccidentImageResponse(
        model=detector.model_name,
        assessment="POSSIBLE_ACCIDENT" if possible_accident else "NO_ACCIDENT_EVIDENCE",
        possible_accident=possible_accident,
        confidence=round(confidence, 4),
        reason=reason,
        detections=detections,
    )
    if possible_accident:
        await alert_manager.broadcast(create_alert("ACCIDENT_SUSPECTED", "Possible collision detected in uploaded image", {"vehicle_types": involved_ids, "confidence": result.confidence}))
    return result


@router.post("/video/track", response_model=TrackingSummary)
async def track_video(file: UploadFile = File(...)) -> TrackingSummary:
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload an MP4, AVI, or MOV video.")

    contents = await file.read(MAX_VIDEO_SIZE_BYTES + 1)
    if len(contents) > MAX_VIDEO_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Video exceeds the 200 MB limit.")

    suffix = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
            temporary_file.write(contents)
            temporary_path = temporary_file.name
        detector = await run_in_threadpool(get_vehicle_detector)
        return await run_in_threadpool(detector.track_video, temporary_path)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="YOLO tracking is unavailable.") from error
    finally:
        if temporary_path:
            os.unlink(temporary_path)


@router.post("/video/analyze-speed", response_model=SpeedAnalysisSummary)
async def analyze_speed(file: UploadFile = File(...)) -> SpeedAnalysisSummary:
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload an MP4, AVI, or MOV video.")
    contents = await file.read(MAX_VIDEO_SIZE_BYTES + 1)
    if len(contents) > MAX_VIDEO_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Video exceeds the 200 MB limit.")
    suffix = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
            temporary_file.write(contents)
            temporary_path = temporary_file.name
        detector = await run_in_threadpool(get_vehicle_detector)
        result = await run_in_threadpool(detector.analyze_speed, temporary_path)
        for vehicle_id in result.overspeeding_vehicle_ids:
            await alert_manager.broadcast(create_alert("OVERSPEEDING", f"Vehicle {vehicle_id} exceeded the configured speed limit", {"vehicle_id": vehicle_id, "speed_limit_kmh": result.speed_limit_kmh}))
        for vehicle_id in result.wrong_way_vehicle_ids:
            await alert_manager.broadcast(create_alert("WRONG_WAY", f"Vehicle {vehicle_id} is moving in the wrong direction", {"vehicle_id": vehicle_id, "allowed_direction_degrees": result.allowed_direction_degrees}))
        return result
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Speed analysis is unavailable.") from error
    finally:
        if temporary_path:
            os.unlink(temporary_path)


@router.post("/video/detect-accidents", response_model=AccidentAnalysisSummary)
async def detect_accidents(file: UploadFile = File(...)) -> AccidentAnalysisSummary:
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload an MP4, AVI, or MOV video.")
    contents = await file.read(MAX_VIDEO_SIZE_BYTES + 1)
    if len(contents) > MAX_VIDEO_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Video exceeds the 200 MB limit.")
    suffix = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
            temporary_file.write(contents)
            temporary_path = temporary_file.name
        detector = await run_in_threadpool(get_vehicle_detector)
        result = await run_in_threadpool(detector.detect_accidents, temporary_path)
        for event in result.possible_accidents:
            await alert_manager.broadcast(create_alert("ACCIDENT_SUSPECTED", "Possible accident requires review", event.model_dump()))
        return result
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Accident analysis is unavailable.") from error
    finally:
        if temporary_path:
            os.unlink(temporary_path)
