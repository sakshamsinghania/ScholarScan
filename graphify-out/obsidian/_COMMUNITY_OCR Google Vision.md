---
type: community
cohesion: 0.13
members: 23
---

# OCR Google Vision

**Cohesion:** 0.13 - loosely connected
**Members:** 23 nodes

## Members
- [[Build and return a Google Vision ImageAnnotatorClient.      Args         creden]] - rationale - backend/core/ocr_google_vision.py
- [[Detect and correct tilt in a binarized image.]] - rationale - backend/core/ocr_google_vision.py
- [[Encode a NumPy image array to PNG bytes for the Vision API.]] - rationale - backend/core/ocr_google_vision.py
- [[Extract text from a PDF by converting each page to an image and running OCR.]] - rationale - backend/core/ocr_google_vision.py
- [[Extract text from an image or PDF file using Google Cloud Vision API.      Args]] - rationale - backend/core/ocr_google_vision.py
- [[Fallback OCR using the local Tesseract binary.]] - rationale - backend/core/ocr_google_vision.py
- [[Full image preprocessing pipeline before sending to Vision API.      Steps]] - rationale - backend/core/ocr_google_vision.py
- [[Load image from disk and convert to grayscale NumPy array.      Raises]] - rationale - backend/core/ocr_google_vision.py
- [[Prefer Google Vision and fall back to local Tesseract when unavailable.]] - rationale - backend/core/ocr_google_vision.py
- [[Run the full OCR pipeline on a single image file.]] - rationale - backend/core/ocr_google_vision.py
- [[Send a preprocessed image to Cloud Vision and return extracted text.      Uses D]] - rationale - backend/core/ocr_google_vision.py
- [[_deskew()]] - code - backend/core/ocr_google_vision.py
- [[_extract_with_fallback()]] - code - backend/core/ocr_google_vision.py
- [[_get_vision_client()]] - code - backend/core/ocr_google_vision.py
- [[_load_image()]] - code - backend/core/ocr_google_vision.py
- [[_numpy_to_png_bytes()]] - code - backend/core/ocr_google_vision.py
- [[_ocr_pdf()]] - code - backend/core/ocr_google_vision.py
- [[_ocr_single_image()]] - code - backend/core/ocr_google_vision.py
- [[_preprocess_image()]] - code - backend/core/ocr_google_vision.py
- [[_run_tesseract_ocr()]] - code - backend/core/ocr_google_vision.py
- [[_run_vision_ocr()]] - code - backend/core/ocr_google_vision.py
- [[extract_text()]] - code - backend/core/ocr_google_vision.py
- [[ocr_google_vision.py]] - code - backend/core/ocr_google_vision.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/OCR_Google_Vision
SORT file.name ASC
```
