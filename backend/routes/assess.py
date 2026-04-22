"""POST /api/assess — Submit student answers for assessment."""

import logging
import uuid
import threading

from flask import Blueprint, current_app, jsonify, request
from models.assessment import AssessmentResponse, MultiAssessmentResponse, TaskStartResponse
from app import auth_required_conditional, get_current_user_id, limiter

assess_bp = Blueprint("assess", __name__)
logger = logging.getLogger(__name__)


def _run_pipeline_async(app, eval_service, progress_service, task_id, **kwargs):
    """Run the evaluation pipeline in a background thread with progress tracking."""
    with app.app_context():
        try:
            logger.info("Started async assessment task %s", task_id)

            def on_progress(stage: str, message: str = ""):
                logger.info("Task %s stage=%s message=%s", task_id, stage, message)
                progress_service.update(task_id, stage, "running", message)

            result = eval_service.evaluate(on_progress=on_progress, **kwargs)
            validated_result = MultiAssessmentResponse.model_validate(result).model_dump(
                mode="json"
            )

            progress_service.store_result(task_id, validated_result)
            progress_service.update(task_id, "completed", "completed", "Assessment complete!")
            logger.info("Completed async assessment task %s", task_id)

        except ValueError as e:
            logger.warning("Async assessment task %s failed validation: %s", task_id, e)
            progress_service.update(task_id, "error", "error", str(e))
        except Exception:
            logger.exception("Async assessment task %s failed", task_id)
            progress_service.update(
                task_id, "error", "error",
                "Assessment could not be completed. Please try again or contact support."
            )
        finally:
            file_handler = app.config["FILE_HANDLER"]
            file_handler.cleanup(kwargs.get("answer_file_path", ""))
            question_path = kwargs.get("question_file_path")
            if question_path:
                file_handler.cleanup(question_path)


@assess_bp.route("/api/assess", methods=["POST"])
@limiter.limit("30/hour")
@auth_required_conditional
def assess():
    """
    Accept an answer file + optional model answer / question paper.

    Backward compatible:
    - If 'image' + 'model_answer' provided → single-question path (synchronous)
    - If 'answer_file' provided → multi-question path (async with progress)
    """
    # Determine which upload field was used
    answer_file = request.files.get("answer_file") or request.files.get("image")
    question_file = request.files.get("question_file")

    if not answer_file or not answer_file.filename:
        return jsonify({"error": "No answer file provided", "code": 400}), 400

    # Optional parameters
    model_answer = request.form.get("model_answer", "").strip()
    question_id = request.form.get("question_id", "Q1")
    student_id = request.form.get("student_id", "anonymous")
    max_marks_raw = request.form.get("max_marks", "10")
    try:
        max_marks = int(max_marks_raw)
    except ValueError:
        return jsonify({"error": "max_marks must be an integer", "code": 400}), 400

    if not 1 <= max_marks <= 100:
        return jsonify({"error": "max_marks must be between 1 and 100", "code": 400}), 400

    # Validate and save answer file
    file_handler = current_app.config["FILE_HANDLER"]
    file_bytes = answer_file.read()
    logger.info(
        "Received assessment upload filename=%s size=%d student_id=%s question_file=%s",
        answer_file.filename,
        len(file_bytes),
        student_id,
        bool(question_file and question_file.filename),
    )

    try:
        file_handler.validate(filename=answer_file.filename, file_bytes=file_bytes)
    except ValueError as e:
        logger.warning("Upload validation failed for %s: %s", answer_file.filename, e)
        return jsonify({"error": str(e), "code": 400}), 400

    temp_path = file_handler.save_temp(
        filename=answer_file.filename, file_bytes=file_bytes
    )
    file_type = file_handler.get_file_type(answer_file.filename)

    if model_answer and file_type != "image":
        file_handler.cleanup(temp_path)
        return jsonify({
            "error": "Manual assessment only supports image uploads. Use document assessment for PDFs.",
            "code": 400,
        }), 400

    if model_answer and question_file and question_file.filename:
        file_handler.cleanup(temp_path)
        return jsonify({
            "error": "Manual assessment cannot include a question paper. "
            "Either remove the question paper or switch to auto/document mode.",
            "code": 400,
        }), 400

    # Handle optional question file
    question_temp_path = None
    question_file_type = None
    if question_file and question_file.filename:
        q_bytes = question_file.read()
        try:
            file_handler.validate(filename=question_file.filename, file_bytes=q_bytes)
        except ValueError as e:
            file_handler.cleanup(temp_path)
            return jsonify({"error": f"Question file error: {e}", "code": 400}), 400

        question_temp_path = file_handler.save_temp(
            filename=question_file.filename, file_bytes=q_bytes
        )
        question_file_type = file_handler.get_file_type(question_file.filename)

    try:
        # Decision: single-question (backward compat) or multi-question path
        if model_answer and file_type == "image" and not question_file:
            # LEGACY: single image + model answer → use existing AssessmentService
            service = current_app.config["ASSESSMENT_SERVICE"]
            result = service.assess(
                image_path=temp_path,
                model_answer=model_answer,
                question_id=question_id,
                student_id=student_id,
                max_marks=max_marks,
            )
            logger.info("Completed synchronous assessment for %s", student_id)
            file_handler.cleanup(temp_path)
            return jsonify(AssessmentResponse.model_validate(result).model_dump(mode="json"))
        else:
            # NEW: multi-question pipeline — async with progress tracking
            task_id = str(uuid.uuid4())
            progress_service = current_app.config["PROGRESS_SERVICE"]
            eval_service = current_app.config["EVALUATION_SERVICE"]
            owner_id = get_current_user_id()

            progress_service.create_task(task_id, owner_id=owner_id)
            progress_service.update(task_id, "upload_received", "running", "Processing upload...")

            # Launch pipeline in background thread
            app = current_app._get_current_object()
            thread = threading.Thread(
                target=_run_pipeline_async,
                args=(app, eval_service, progress_service, task_id),
                kwargs={
                    "answer_file_path": temp_path,
                    "file_type": file_type,
                    "question_file_path": question_temp_path,
                    "question_file_type": question_file_type,
                    "student_id": student_id,
                    "max_marks_per_question": max_marks,
                },
                daemon=True,
            )
            thread.start()
            logger.info("Queued async assessment task %s for %s", task_id, student_id)

            response = TaskStartResponse.model_validate(
                {"task_id": task_id, "status": "processing"}
            )
            return jsonify(response.model_dump(mode="json")), 202

    except ValueError as e:
        logger.warning("Assessment request failed validation: %s", e)
        file_handler.cleanup(temp_path)
        if question_temp_path:
            file_handler.cleanup(question_temp_path)
        return jsonify({"error": str(e), "code": 400}), 400
    except RuntimeError as e:
        logger.exception("Assessment request failed with runtime error")
        file_handler.cleanup(temp_path)
        if question_temp_path:
            file_handler.cleanup(question_temp_path)
        return jsonify({"error": "An internal error occurred during assessment. Please try again.", "code": 500}), 500
