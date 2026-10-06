from collections import defaultdict
from dataclasses import dataclass, field
import math
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
from ultralytics import YOLO

from app.config import get_settings
from app.schemas.detection import BoundingBox, Detection
from app.schemas.detection import AccidentAnalysisSummary, AccidentEvent, SpeedAnalysisSummary, TrackingSummary


SUPPORTED_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}
VEHICLE_CLASSES = {"bicycle", "car", "motorcycle", "bus", "truck"}


@dataclass
class VehicleDetectionService:
    model: YOLO
    model_name: str
    inference_lock: Lock = field(default_factory=Lock, repr=False)

    def detect(self, image: np.ndarray) -> list[Detection]:
        results = self.model.predict(
            source=image,
            conf=get_settings().yolo_confidence,
            device=get_settings().yolo_device,
            verbose=False,
        )
        detections: list[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                class_name = SUPPORTED_CLASSES.get(class_id)
                if class_name is None:
                    continue
                coordinates = box.xyxy[0].tolist()
                detections.append(
                    Detection(
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
        return detections

    def track_video(self, video_path: str) -> TrackingSummary:
        with self.inference_lock:
            self.model.predictor = None
            capture = cv2.VideoCapture(video_path)
            if not capture.isOpened():
                raise ValueError("The uploaded video could not be opened.")

            frame_count = 0
            fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
            seen_ids: dict[str, set[int]] = defaultdict(set)
            visible_vehicle_total = 0
            peak_visible_vehicles = 0
            try:
                while True:
                    has_frame, frame = capture.read()
                    if not has_frame:
                        break
                    frame_count += 1
                    results = self.model.track(
                        source=frame,
                        conf=get_settings().yolo_confidence,
                        device=get_settings().yolo_device,
                        tracker="bytetrack.yaml",
                        persist=True,
                        verbose=False,
                    )
                    boxes = results[0].boxes if results else None
                    if boxes is None or boxes.id is None:
                        continue
                    visible_ids: set[int] = set()
                    for class_value, track_value in zip(boxes.cls, boxes.id):
                        class_name = SUPPORTED_CLASSES.get(int(class_value.item()))
                        if class_name in VEHICLE_CLASSES:
                            track_id = int(track_value.item())
                            visible_ids.add(track_id)
                            seen_ids[class_name].add(track_id)
                    visible_vehicle_total += len(visible_ids)
                    peak_visible_vehicles = max(peak_visible_vehicles, len(visible_ids))
            finally:
                capture.release()

            counts = {class_name: len(seen_ids[class_name]) for class_name in sorted(VEHICLE_CLASSES)}
            average_visible_vehicles = visible_vehicle_total / frame_count if frame_count else 0
            return TrackingSummary(
                model=self.model_name,
                tracker="ByteTrack",
                processed_frames=frame_count,
                video_fps=round(fps, 2),
                duration_seconds=round(frame_count / fps, 2) if fps > 0 else 0,
                total_unique_vehicles=sum(counts.values()),
                vehicle_counts=counts,
                peak_visible_vehicles=peak_visible_vehicles,
                average_visible_vehicles=round(average_visible_vehicles, 2),
                density_level=traffic_density(peak_visible_vehicles),
            )

    def analyze_speed(self, video_path: str) -> SpeedAnalysisSummary:
        settings = get_settings()
        with self.inference_lock:
            self.model.predictor = None
            capture = cv2.VideoCapture(video_path)
            if not capture.isOpened():
                raise ValueError("The uploaded video could not be opened.")
            fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
            frame_count = 0
            previous_centers: dict[int, tuple[float, float]] = {}
            first_centers: dict[int, tuple[float, float]] = {}
            maximum_speeds: dict[int, float] = {}
            wrong_way_ids: set[int] = set()
            try:
                while True:
                    has_frame, frame = capture.read()
                    if not has_frame:
                        break
                    frame_count += 1
                    results = self.model.track(
                        source=frame,
                        conf=settings.yolo_confidence,
                        device=settings.yolo_device,
                        tracker="bytetrack.yaml",
                        persist=True,
                        verbose=False,
                    )
                    boxes = results[0].boxes if results else None
                    if boxes is None or boxes.id is None:
                        continue
                    for coordinates, class_value, track_value in zip(boxes.xyxy, boxes.cls, boxes.id):
                        class_name = SUPPORTED_CLASSES.get(int(class_value.item()))
                        if class_name not in VEHICLE_CLASSES:
                            continue
                        track_id = int(track_value.item())
                        x1, y1, x2, y2 = coordinates.tolist()
                        center = ((x1 + x2) / 2, (y1 + y2) / 2)
                        first_centers.setdefault(track_id, center)
                        previous = previous_centers.get(track_id)
                        if previous and settings.pixels_per_meter > 0 and fps > 0:
                            pixels = math.dist(previous, center)
                            speed = pixels * fps / settings.pixels_per_meter * 3.6
                            maximum_speeds[track_id] = max(maximum_speeds.get(track_id, 0), speed)
                        origin = first_centers[track_id]
                        displacement = math.dist(origin, center)
                        if displacement >= settings.wrong_way_min_displacement_pixels:
                            movement_angle = math.degrees(math.atan2(center[1] - origin[1], center[0] - origin[0])) % 360
                            angle_difference = abs((movement_angle - settings.allowed_direction_degrees + 180) % 360 - 180)
                            if angle_difference >= 120:
                                wrong_way_ids.add(track_id)
                        previous_centers[track_id] = center
            finally:
                capture.release()

            speeds = {str(track_id): round(speed, 2) for track_id, speed in maximum_speeds.items()}
            overspeeding = [str(track_id) for track_id, speed in maximum_speeds.items() if speed > settings.speed_limit_kmh]
            return SpeedAnalysisSummary(
                model=self.model_name,
                tracker="ByteTrack",
                processed_frames=frame_count,
                video_fps=round(fps, 2),
                calibrated=settings.pixels_per_meter > 0,
                speed_limit_kmh=settings.speed_limit_kmh,
                allowed_direction_degrees=settings.allowed_direction_degrees,
                maximum_speed_kmh=round(maximum_speeds[max(maximum_speeds, key=maximum_speeds.get)], 2) if maximum_speeds else None,
                vehicle_speeds_kmh=speeds,
                overspeeding_vehicle_ids=overspeeding,
                wrong_way_vehicle_ids=sorted(str(track_id) for track_id in wrong_way_ids),
            )

    def detect_accidents(self, video_path: str) -> AccidentAnalysisSummary:
        settings = get_settings()
        with self.inference_lock:
            self.model.predictor = None
            capture = cv2.VideoCapture(video_path)
            if not capture.isOpened():
                raise ValueError("The uploaded video could not be opened.")
            fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
            frame_count = 0
            previous_centers: dict[int, tuple[float, float]] = {}
            last_event_frame: dict[tuple[int, int], int] = {}
            events: list[AccidentEvent] = []
            try:
                while True:
                    has_frame, frame = capture.read()
                    if not has_frame:
                        break
                    frame_count += 1
                    results = self.model.track(
                        source=frame,
                        conf=settings.yolo_confidence,
                        device=settings.yolo_device,
                        tracker="bytetrack.yaml",
                        persist=True,
                        verbose=False,
                    )
                    boxes = results[0].boxes if results else None
                    if boxes is None or boxes.id is None:
                        continue
                    tracked: list[tuple[int, list[float], tuple[float, float], float]] = []
                    for coordinates, class_value, track_value in zip(boxes.xyxy, boxes.cls, boxes.id):
                        class_name = SUPPORTED_CLASSES.get(int(class_value.item()))
                        if class_name not in VEHICLE_CLASSES:
                            continue
                        track_id = int(track_value.item())
                        box = coordinates.tolist()
                        center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
                        motion = math.dist(previous_centers[track_id], center) if track_id in previous_centers else 0
                        tracked.append((track_id, box, center, motion))

                    for first_index, first in enumerate(tracked):
                        for second in tracked[first_index + 1:]:
                            first_id, first_box, _, first_motion = first
                            second_id, second_box, _, second_motion = second
                            overlap = intersection_over_union(first_box, second_box)
                            pair = tuple(sorted((first_id, second_id)))
                            cooldown = int(fps) if fps > 0 else 1
                            if overlap >= settings.accident_iou_threshold and max(first_motion, second_motion) >= settings.accident_min_motion_pixels and frame_count - last_event_frame.get(pair, -cooldown) >= cooldown:
                                confidence = min(0.99, 0.55 + overlap * 0.35 + min(max(first_motion, second_motion) / 100, 0.1))
                                events.append(
                                    AccidentEvent(
                                        frame_number=frame_count,
                                        timestamp_seconds=round(frame_count / fps, 2) if fps > 0 else 0,
                                        vehicle_ids=[str(pair[0]), str(pair[1])],
                                        confidence=round(confidence, 4),
                                        reason="Tracked vehicle boxes overlapped during motion; possible collision requires review.",
                                    )
                                )
                                last_event_frame[pair] = frame_count
                    previous_centers = {track_id: center for track_id, _, center, _ in tracked}
            finally:
                capture.release()
            return AccidentAnalysisSummary(
                model=self.model_name,
                tracker="ByteTrack",
                processed_frames=frame_count,
                video_fps=round(fps, 2),
                possible_accidents=events,
            )


_service: VehicleDetectionService | None = None
_service_lock = Lock()


def get_vehicle_detector() -> VehicleDetectionService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                settings = get_settings()
                model_path = Path(settings.yolo_model_path)
                if not model_path.is_absolute():
                    model_path = Path(__file__).resolve().parents[3] / model_path
                _service = VehicleDetectionService(
                    model=YOLO(str(model_path)),
                    model_name=model_path.name,
                )
    return _service


def decode_image(contents: bytes) -> np.ndarray | None:
    image = cv2.imdecode(np.frombuffer(contents, dtype=np.uint8), cv2.IMREAD_COLOR)
    return image


def traffic_density(vehicle_count: int) -> str:
    settings = get_settings()
    if vehicle_count >= settings.density_very_high_threshold:
        return "VERY_HIGH"
    if vehicle_count >= settings.density_high_threshold:
        return "HIGH"
    if vehicle_count >= settings.density_medium_threshold:
        return "MEDIUM"
    return "LOW"


def intersection_over_union(first_box: list[float], second_box: list[float]) -> float:
    left = max(first_box[0], second_box[0])
    top = max(first_box[1], second_box[1])
    right = min(first_box[2], second_box[2])
    bottom = min(first_box[3], second_box[3])
    intersection = max(0, right - left) * max(0, bottom - top)
    first_area = max(0, first_box[2] - first_box[0]) * max(0, first_box[3] - first_box[1])
    second_area = max(0, second_box[2] - second_box[0]) * max(0, second_box[3] - second_box[1])
    union = first_area + second_area - intersection
    return intersection / union if union else 0
