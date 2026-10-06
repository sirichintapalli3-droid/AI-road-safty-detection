from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

import numpy as np
from ultralytics import YOLO

from app.config import get_settings
from app.schemas.detection import BoundingBox, NumberPlateReading


PLATE_CLASSES = {"license_plate", "number_plate", "plate"}


@dataclass
class NumberPlateService:
    model: YOLO
    reader: Any
    model_name: str
    inference_lock: Lock

    def read(self, image: np.ndarray) -> list[NumberPlateReading]:
        with self.inference_lock:
            results = self.model.predict(
                source=image,
                conf=get_settings().plate_confidence,
                device=get_settings().yolo_device,
                verbose=False,
            )
            readings: list[NumberPlateReading] = []
            for result in results:
                if result.boxes is None:
                    continue
                for box in result.boxes:
                    class_id = int(box.cls[0].item())
                    class_name = str(result.names.get(class_id, "")).lower().replace(" ", "_")
                    if class_name not in PLATE_CLASSES:
                        continue
                    coordinates = [int(value) for value in box.xyxy[0].tolist()]
                    x1, y1, x2, y2 = coordinates
                    crop = image[max(0, y1):y2, max(0, x1):x2]
                    if crop.size == 0:
                        continue
                    ocr_results = self.reader.readtext(crop, detail=1, paragraph=False)
                    for _, text, confidence in ocr_results:
                        normalized = "".join(character for character in text.upper() if character.isalnum())
                        if normalized:
                            readings.append(
                                NumberPlateReading(
                                    plate_text=normalized,
                                    ocr_confidence=round(float(confidence), 4),
                                    box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                                )
                            )
                            break
            return readings


_service: NumberPlateService | None = None
_service_lock = Lock()


def get_number_plate_service() -> NumberPlateService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                settings = get_settings()
                import easyocr

                model_path = Path(settings.plate_model_path)
                if not model_path.is_absolute():
                    model_path = Path(__file__).resolve().parents[3] / model_path
                languages = [language.strip() for language in settings.ocr_languages.split(",") if language.strip()]
                _service = NumberPlateService(
                    model=YOLO(str(model_path)),
                    reader=easyocr.Reader(languages or ["en"], gpu=False),
                    model_name=model_path.name,
                    inference_lock=Lock(),
                )
    return _service