---
type: community
cohesion: 0.06
members: 89
---

# App Bootstrap & Services

**Cohesion:** 0.06 - loosely connected
**Members:** 89 nodes

## Members
- [[.__init__()_10]] - code - backend/services/assessment_service.py
- [[.__init__()_12]] - code - backend/services/evaluation_service.py
- [[.__init__()]] - code - backend/file_handling/image_file_handler.py
- [[.__init__()_9]] - code - backend/services/llm_service.py
- [[.__init__()_6]] - code - backend/services/pdf_service.py
- [[.__init__()_8]] - code - backend/services/progress_service.py
- [[.__init__()_11]] - code - backend/services/result_storage_service.py
- [[._extract_question_paper()]] - code - backend/services/evaluation_service.py
- [[._extract_raw_text()]] - code - backend/services/evaluation_service.py
- [[._ocr_page()]] - code - backend/services/pdf_service.py
- [[._run_ocr()]] - code - backend/services/assessment_service.py
- [[.assess()]] - code - backend/services/assessment_service.py
- [[.cleanup()]] - code - backend/file_handling/image_file_handler.py
- [[.cleanup()_1]] - code - backend/services/progress_service.py
- [[.close()_1]] - code - backend/services/llm_service.py
- [[.evaluate()]] - code - backend/services/evaluation_service.py
- [[.extract_text()]] - code - backend/services/pdf_service.py
- [[.get_all()]] - code - backend/services/result_storage_service.py
- [[.get_filtered()]] - code - backend/services/result_storage_service.py
- [[.is_scanned_page()]] - code - backend/services/pdf_service.py
- [[.store()]] - code - backend/services/result_storage_service.py
- [[Application configuration loaded from environment variables.]] - rationale - backend/config.py
- [[Application factory. Creates a Flask app with all blueprints registered.      Ar]] - rationale - backend/app.py
- [[Args             extract_text_fn OCR function (from coreocr.py) for scanned p]] - rationale - backend/services/pdf_service.py
- [[AssessmentService]] - code - backend/services/assessment_service.py
- [[Best-effort check for production runtime.]] - rationale - backend/app.py
- [[Build EvaluationService with all mocked dependencies.]] - rationale - backend/tests/test_evaluation_progress.py
- [[Business layer that coordinates core modules to assess a student answer.      Us]] - rationale - backend/services/assessment_service.py
- [[Config]] - code - backend/config.py
- [[Convert a single PDF page to an image and run OCR on it.]] - rationale - backend/services/pdf_service.py
- [[Create mock callables that mimic core module functions.]] - rationale - backend/tests/test_assessment_service.py
- [[Create the shared LLM service with free-tier safeguard settings.]] - rationale - backend/app.py
- [[Detect if a pdfplumber page has no extractable text.         A page is considere]] - rationale - backend/services/pdf_service.py
- [[EvaluationService]] - code - backend/services/evaluation_service.py
- [[Extract all text from a PDF file.          For each page         - If digital t]] - rationale - backend/services/pdf_service.py
- [[Extract questions from a separate question paper.]] - rationale - backend/services/evaluation_service.py
- [[Extract text from PDF files with OCR fallback for scanned pages.]] - rationale - backend/services/pdf_service.py
- [[Extract text from file based on type.]] - rationale - backend/services/evaluation_service.py
- [[Extract text from image with error wrapping.]] - rationale - backend/services/assessment_service.py
- [[Extracts text from PDFs using pdfplumber for digital content.     Falls back to]] - rationale - backend/services/pdf_service.py
- [[Fallback result when assessment fails for a question.]] - rationale - backend/services/evaluation_service.py
- [[FileHandler]] - code - backend/file_handling/image_file_handler.py
- [[Flask application configuration.]] - rationale - backend/config.py
- [[Flask application factory — creates and configures the app.]] - rationale - backend/app.py
- [[Handles file validation, temporary storage, and cleanup for images and PDFs.]] - rationale - backend/file_handling/image_file_handler.py
- [[In-memory storage for assessment results. Swappable to a database later.]] - rationale - backend/services/result_storage_service.py
- [[LlmService]] - code - backend/services/llm_service.py
- [[Map core AssessmentResult to API response dict.]] - rationale - backend/services/assessment_service.py
- [[Multi-question assessment orchestrator.      Pipeline     1. Extract text from]] - rationale - backend/services/evaluation_service.py
- [[Orchestrate multi-question assessment PDF → Questions → LLM → Scoring.]] - rationale - backend/services/evaluation_service.py
- [[Orchestrates the core assessment pipeline OCR → NLP → Similarity → Scoring.]] - rationale - backend/services/assessment_service.py
- [[Parse raw text into structured question-answer segments.]] - rationale - backend/services/question_service.py
- [[PdfService]] - code - backend/services/pdf_service.py
- [[ProgressService]] - code - backend/services/progress_service.py
- [[QuestionService]] - code - backend/services/question_service.py
- [[Read allowed frontend origins from env, with sensible local defaults.]] - rationale - backend/app.py
- [[Record coarse capability flags for health reporting.]] - rationale - backend/app.py
- [[Release background resources owned by the service.]] - rationale - backend/services/llm_service.py
- [[Remove a task from tracking. Silently ignores missing tasks.]] - rationale - backend/services/progress_service.py
- [[Remove a temp file. Silently ignores missing files.]] - rationale - backend/file_handling/image_file_handler.py
- [[ResultStorageService]] - code - backend/services/result_storage_service.py
- [[Return a copy of all stored results.]] - rationale - backend/services/result_storage_service.py
- [[Return results matching the given filters.]] - rationale - backend/services/result_storage_service.py
- [[Return the backend port, with a collision-resistant local default.]] - rationale - backend/app.py
- [[Run the full assessment pipeline for a single student answer.          Args]] - rationale - backend/services/assessment_service.py
- [[Run the full multi-question pipeline.          Args             answer_file_pat]] - rationale - backend/services/evaluation_service.py
- [[Store a result dict, adding a unique ID. Returns the generated ID.]] - rationale - backend/services/result_storage_service.py
- [[Tests for AssessmentService — orchestrates core assessment pipeline.]] - rationale - backend/tests/test_assessment_service.py
- [[Tests for EvaluationService progress callback integration.]] - rationale - backend/tests/test_evaluation_progress.py
- [[Thread-safe in-memory storage for assessment results.]] - rationale - backend/services/result_storage_service.py
- [[Track per-task pipeline progress with thread-safe access.      Uses a Queue per]] - rationale - backend/services/progress_service.py
- [[Wire up mock services for testing — no ML models loaded.]] - rationale - backend/app.py
- [[Wire up real core modules — loads ML models.]] - rationale - backend/app.py
- [[_build_llm_service()]] - code - backend/app.py
- [[_build_response()]] - code - backend/services/assessment_service.py
- [[_configure_runtime_capabilities()]] - code - backend/app.py
- [[_empty_result()]] - code - backend/services/evaluation_service.py
- [[_get_cors_origins()]] - code - backend/app.py
- [[_is_production()]] - code - backend/app.py
- [[_register_mock_services()]] - code - backend/app.py
- [[_register_real_services()]] - code - backend/app.py
- [[app.py]] - code - backend/app.py
- [[assessment_service.py]] - code - backend/services/assessment_service.py
- [[config.py]] - code - backend/config.py
- [[create_app()]] - code - backend/app.py
- [[evaluation_service.py]] - code - backend/services/evaluation_service.py
- [[get_runtime_port()]] - code - backend/app.py
- [[pdf_service.py]] - code - backend/services/pdf_service.py
- [[result_storage_service.py]] - code - backend/services/result_storage_service.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/App_Bootstrap_&_Services
SORT file.name ASC
```

## Connections to other communities
- 20 edges to [[_COMMUNITY_Question Detection & Tests]]
- 9 edges to [[_COMMUNITY_Scoring & Batch Pipeline]]
- 8 edges to [[_COMMUNITY_Progress Service Tests]]
- 8 edges to [[_COMMUNITY_LLM Service Tests]]
- 8 edges to [[_COMMUNITY_Gemini API Coordination]]
- 8 edges to [[_COMMUNITY_Progress Service Core]]
- 7 edges to [[_COMMUNITY_PDF Service Tests]]
- 6 edges to [[_COMMUNITY_Assessment Service Tests]]
- 5 edges to [[_COMMUNITY_File Handler Tests]]
- 4 edges to [[_COMMUNITY_Image File Handler]]
- 4 edges to [[_COMMUNITY_Evaluation Progress Tests]]
- 3 edges to [[_COMMUNITY_App Runtime Tests]]
- 3 edges to [[_COMMUNITY_Result Storage Tests]]

## Top bridge nodes
- [[LlmService]] - degree 39, connects to 3 communities
- [[ResultStorageService]] - degree 35, connects to 2 communities
- [[EvaluationService]] - degree 29, connects to 2 communities
- [[ProgressService]] - degree 28, connects to 2 communities
- [[QuestionService]] - degree 28, connects to 2 communities