# Training data

Phase 6 custom models need labeled images; the general COCO model does not contain helmet or number-plate classes.

Recommended starting points:

- UFPR-ALPR: vehicle and Brazilian plate images for plate localization/OCR research.
- CCPD: large-scale Chinese road plate dataset for plate detection and recognition research.
- Indian Number Plate Dataset or a carefully licensed regional equivalent for Indian plate formats.
- A project-specific helmet dataset captured from the target camera angle and lighting conditions.

Before training, confirm each dataset license and relabel classes to match the API contract:

- Helmet model: `helmet`, `no_helmet`
- Plate model: `license_plate`, `number_plate`, or `plate`

Keep train, validation, and test scenes separate by camera/location to avoid overly optimistic results.
