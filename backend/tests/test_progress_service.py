"""Tests for ProgressService — thread-safe pipeline progress tracking."""

import os
import sys
import time
import pytest
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.progress_service import ProgressService, PIPELINE_STAGES


@pytest.fixture
def service():
    return ProgressService()


class TestCreateTask:
    def test_creates_task(self, service):
        service.create_task("task-1")
        progress = service.get_current("task-1")
        assert progress is not None
        assert progress["task_id"] == "task-1"

    def test_initial_stage_is_none(self, service):
        service.create_task("task-1")
        progress = service.get_current("task-1")
        assert progress["stage"] is None
        assert progress["status"] == "pending"

    def test_unknown_task_returns_none(self, service):
        assert service.get_current("nonexistent") is None


class TestUpdateStage:
    def test_updates_stage(self, service):
        service.create_task("task-1")
        service.update("task-1", "text_extraction", "running", "Extracting text...")
        progress = service.get_current("task-1")
        assert progress["stage"] == "text_extraction"
        assert progress["status"] == "running"
        assert progress["message"] == "Extracting text..."

    def test_tracks_completed_stages(self, service):
        service.create_task("task-1")
        service.update("task-1", "upload_received", "completed")
        service.update("task-1", "file_type_detection", "completed")
        service.update("task-1", "text_extraction", "running")
        progress = service.get_current("task-1")
        assert "upload_received" in progress["completed_stages"]
        assert "file_type_detection" in progress["completed_stages"]
        assert "text_extraction" not in progress["completed_stages"]

    def test_step_number_increments(self, service):
        service.create_task("task-1")
        service.update("task-1", "upload_received", "completed")
        service.update("task-1", "file_type_detection", "running")
        progress = service.get_current("task-1")
        assert progress["step"] == 2
        assert progress["total_steps"] == len(PIPELINE_STAGES)

    def test_update_nonexistent_task_is_noop(self, service):
        # Should not raise
        service.update("nonexistent", "text_extraction", "running")

    def test_completed_marks_stage(self, service):
        service.create_task("task-1")
        service.update("task-1", "text_extraction", "completed")
        progress = service.get_current("task-1")
        assert "text_extraction" in progress["completed_stages"]


class TestErrorStage:
    def test_error_status(self, service):
        service.create_task("task-1")
        service.update("task-1", "text_extraction", "error", "OCR failed")
        progress = service.get_current("task-1")
        assert progress["status"] == "error"
        assert progress["message"] == "OCR failed"


class TestStream:
    def test_stream_yields_events(self, service):
        service.create_task("task-1")

        events = []

        def produce():
            time.sleep(0.05)
            service.update("task-1", "upload_received", "completed")
            time.sleep(0.05)
            service.update("task-1", "completed", "completed", "Done!")

        producer = threading.Thread(target=produce)
        producer.start()

        for event in service.stream("task-1", timeout=2):
            events.append(event)
            if event.get("stage") == "completed":
                break

        producer.join()
        assert len(events) >= 2
        assert events[-1]["stage"] == "completed"

    def test_stream_nonexistent_returns_empty(self, service):
        events = list(service.stream("nonexistent", timeout=0.1))
        assert events == []


class TestCleanup:
    def test_cleanup_removes_task(self, service):
        service.create_task("task-1")
        service.cleanup("task-1")
        assert service.get_current("task-1") is None

    def test_cleanup_nonexistent_is_noop(self, service):
        service.cleanup("nonexistent")  # Should not raise

    def test_expired_tasks_are_evicted_automatically(self):
        service = ProgressService(task_ttl_seconds=0.01)
        service.create_task("task-1")
        time.sleep(0.02)

        assert service.get_current("task-1") is None


class TestThreadSafety:
    def test_concurrent_updates(self, service):
        service.create_task("task-1")
        errors = []

        def writer(stage_idx):
            try:
                stage_key = PIPELINE_STAGES[stage_idx][0]
                service.update("task-1", stage_key, "completed")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(len(PIPELINE_STAGES))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        progress = service.get_current("task-1")
        assert progress is not None


class TestStoreResult:
    def test_stores_final_result(self, service):
        service.create_task("task-1")
        service.store_result("task-1", {"total_score": 14})
        assert service.get_result("task-1") == {"total_score": 14}

    def test_result_not_found(self, service):
        assert service.get_result("nonexistent") is None
