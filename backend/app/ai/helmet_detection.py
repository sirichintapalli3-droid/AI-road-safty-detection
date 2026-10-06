from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import numpy as np
from ultralytics import YOLO

from app.config import get_settings
from app.schemas.detection import BoundingBox, HelmetDetection


ALLOWED_CLASSES = {"helmet", "no_helmet"}


@dataclass
class HelmetDetectionService:
    model: YOLO
    model_name: str
    inference_lock: Lock

    def detect(self, image: np.ndarray) -> tuple[str, list[HelmetDetection]]:
        with self.inference_lock:
            results = self.model.predict(
                source=image,
                conf=get_settings().helmet_confidence,
                device=get_settings().yolo_device,
                verbose=False,
            )
        detections: list[HelmetDetection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                class_name = str(result.names.get(class_id, "")).lower().replace(" ", "_")
                if class_name not in ALLOWED_CLASSES:
                    continue
                coordinates = box.xyxy[0].tolist()
                detections.append(
                    HelmetDetection(
                        class_name=class_name,
                        confidence=round(float(box.conf[0].item()), 4),
                        box=BoundingBox(
                            x1=round(coordinates[0], 2),
                            y1=round(coordinates[1], 2),
                            x2=round(coordinates[2], 2),
                            y2=round(coordinates[3], 2),
                        ),
                    )
                )
        if not detections:
            status = "UNKNOWN"
        elif any(item.class_name == "no_helmet" for item in detections):
            status = "NO_HELMET_DETECTED"
        else:
            status = "HELMET_DETECTED"
        return status, detections


_service: HelmetDetectionService | None = None
_service_lock = Lock()


def get_helmet_detector() -> HelmetDetectionService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                settings = get_settings()
                model_path = Path(settings.helmet_model_path)
                if not model_path.is_absolute():
                    model_path = Path(__file__).resolve().parents[3] / model_path
                _service = HelmetDetectionService(YOLO(str(model_path)), model_path.name, Lock())
    return _service