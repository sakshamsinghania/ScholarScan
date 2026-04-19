---
type: community
cohesion: 0.22
members: 9
---

# Image File Handler

**Cohesion:** 0.22 - loosely connected
**Members:** 9 nodes

## Members
- [[.get_file_type()]] - code - backend/file_handling/image_file_handler.py
- [[.save_temp()]] - code - backend/file_handling/image_file_handler.py
- [[.validate()]] - code - backend/file_handling/image_file_handler.py
- [[Determine file type from extension. Returns 'image' or 'pdf'.]] - rationale - backend/file_handling/image_file_handler.py
- [[File upload validation, temp storage, and cleanup — supports images and PDFs.]] - rationale - backend/file_handling/image_file_handler.py
- [[Save file bytes to a temp path with a UUID name. Returns the path.]] - rationale - backend/file_handling/image_file_handler.py
- [[Validate an uploaded file. Raises ValueError on failure.]] - rationale - backend/file_handling/image_file_handler.py
- [[_get_extension()]] - code - backend/file_handling/image_file_handler.py
- [[image_file_handler.py]] - code - backend/file_handling/image_file_handler.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Image_File_Handler
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_App Bootstrap & Services]]

## Top bridge nodes
- [[image_file_handler.py]] - degree 3, connects to 1 community
- [[.get_file_type()]] - degree 3, connects to 1 community
- [[.save_temp()]] - degree 3, connects to 1 community
- [[.validate()]] - degree 3, connects to 1 community