from fastapi import APIRouter, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.ai.number_plate import get_number_plate_service
from app.ai.vehicle_detection import decode_image
from app.schemas.detection import NumberPlateResponse
from app.services.alerts import alert_manager, create_alert


router = APIRouter(prefix="/number-plates", tags=["number plates"])
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


@router.post("/image", response_model=NumberPlateResponse)
async def read_number_plates(file: UploadFile = File(...)) -> NumberPlateResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a JPEG, PNG, or WebP image.")
    contents = await file.read(MAX_IMAGE_SIZE_BYTES + 1)
    if len(contents) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image exceeds the 10 MB limit.")
    image = decode_image(contents)
    if image is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is not a valid image.")
    try:
        service = await run_in_threadpool(get_number_plate_service)
        readings = await run_in_threadpool(service.read, image)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Number-plate detection or OCR is unavailable. Configure trained plate weights and OCR access.",
        ) from error
    response = NumberPlateResponse(model=service.model_name, readings=readings)
    for reading in readings:
        await alert_manager.broadcast(create_alert("NUMBER_PLATE_DETECTED", f"Number plate detected: {reading.plate_text}", reading.model_dump()))
    return response