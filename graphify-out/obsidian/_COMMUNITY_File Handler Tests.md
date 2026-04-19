---
type: community
cohesion: 0.11
members: 19
---

# File Handler Tests

**Cohesion:** 0.11 - loosely connected
**Members:** 19 nodes

## Members
- [[.test_accepts_valid_jpeg()]] - code - backend/tests/test_image_file_handler.py
- [[.test_accepts_valid_png()]] - code - backend/tests/test_image_file_handler.py
- [[.test_cleanup_ignores_missing_file()]] - code - backend/tests/test_image_file_handler.py
- [[.test_cleanup_removes_file()]] - code - backend/tests/test_image_file_handler.py
- [[.test_rejects_corrupt_image()]] - code - backend/tests/test_image_file_handler.py
- [[.test_rejects_disallowed_extension()]] - code - backend/tests/test_image_file_handler.py
- [[.test_rejects_empty_filename()]] - code - backend/tests/test_image_file_handler.py
- [[.test_rejects_none_file()]] - code - backend/tests/test_image_file_handler.py
- [[.test_rejects_oversized_file()]] - code - backend/tests/test_image_file_handler.py
- [[.test_save_creates_file()]] - code - backend/tests/test_image_file_handler.py
- [[.test_save_uses_uuid_filename()]] - code - backend/tests/test_image_file_handler.py
- [[Create a handler with a temp upload directory.]] - rationale - backend/tests/test_image_file_handler.py
- [[Create a minimal valid JPEG image in memory.]] - rationale - backend/tests/test_image_file_handler.py
- [[TestSaveAndCleanup]] - code - backend/tests/test_image_file_handler.py
- [[TestValidateImage]] - code - backend/tests/test_image_file_handler.py
- [[Tests for FileHandler — validates image and PDF uploads.]] - rationale - backend/tests/test_image_file_handler.py
- [[handler()]] - code - backend/tests/test_image_file_handler.py
- [[test_image_file_handler.py]] - code - backend/tests/test_image_file_handler.py
- [[valid_image_bytes()]] - code - backend/tests/test_image_file_handler.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/File_Handler_Tests
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_App Bootstrap & Services]]

## Top bridge nodes
- [[TestValidateImage]] - degree 9, connects to 1 community
- [[TestSaveAndCleanup]] - degree 6, connects to 1 community
- [[Tests for FileHandler — validates image and PDF uploads.]] - degree 2, connects to 1 community
- [[Create a handler with a temp upload directory.]] - degree 2, connects to 1 community
- [[Create a minimal valid JPEG image in memory.]] - degree 2, connects to 1 community