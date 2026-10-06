from fastapi import APIRouter, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.ai.vehicle_detection import decode_image
from app.ai.helmet_detection import get_helmet_detector
from app.services.alerts import alert_manager, create_alert
from app.schemas.detection import HelmetDetectionResponse


router = APIRouter(prefix="/helmet", tags=["helmet"])
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


@router.post("/image", response_model=HelmetDetectionResponse)
async def detect_helmet(file: UploadFile = File(...)) -> HelmetDetectionResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a JPEG, PNG, or WebP image.")
    contents = await file.read(MAX_IMAGE_SIZE_BYTES + 1)
    if len(contents) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image exceeds the 10 MB limit.")
    image = decode_image(contents)
    if image is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is not a valid image.")
    try:
        detector = await run_in_threadpool(get_helmet_detector)
        helmet_status, detections = await run_in_threadpool(detector.detect, image)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Helmet model is unavailable. Configure HELMET_MODEL_PATH with trained weights.",
        ) from error
    response = HelmetDetectionResponse(model=detector.model_name, helmet_status=helmet_status, detections=detections)
    if helmet_status == "NO_HELMET_DETECTED":
        await alert_manager.broadcast(create_alert("NO_HELMET", "Possible no-helmet violation detected", {"detections": [item.model_dump() for item in detections]}))
    return response