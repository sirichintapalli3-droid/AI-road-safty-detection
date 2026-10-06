# YOLO models

Phase 2 uses Ultralytics YOLO with the model path configured by `YOLO_MODEL_PATH`.

The default `yolo11n.pt` file is downloaded by Ultralytics on first inference if it is not present. This is a general COCO model: it supports person, bicycle, car, motorcycle, bus, and truck. Helmet, number plate, rickshaw, and other custom classes require a separately trained model in later phases.

For reproducible deployments, download and validate the chosen model before starting the API, then set `YOLO_MODEL_PATH` to its local path.
