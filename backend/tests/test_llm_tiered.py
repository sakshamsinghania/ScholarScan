"""Tests for LlmService.generate_tiered_model_answer()."""

import os
import sys
import json

import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.similarity import TieredReference
from services.llm_service import LlmService


VALID_TIERED_JSON = json.dumps({
    "core": ["photosynthesis", "chloroplast", "sunlight energy"],
    "supporting": ["carbon dioxide fixation", "glucose production"],
    "extended": ["Calvin cycle"],
    "flat_answer": "Photosynthesis converts sunlight into glucose in chloroplasts.",
})

VALID_TIERED_FENCED = f"```json\n{VALID_TIERED_JSON}\n```"

MALFORMED_JSON = "This is not JSON at all {{"

MISSING_FLAT_ANSWER = json.dumps({
    "core": ["mitosis", "cell division"],
    "supporting": ["chromosomes"],
    "extended": [],
})

EMPTY_CORE = json.dumps({
    "core": [],
    "supporting": ["bonus concept"],
    "extended": [],
    "flat_answer": "Some answer text.",
})

NON_STRING_ITEMS = json.dumps({
    "core": ["valid", 123, None, "also valid"],
    "supporting": [],
    "extended": [],
    "flat_answer": "Answer.",
})


def _make_service(response_text: str, side_effect=None) -> LlmService:
    openai_client = MagicMock()
    choice = MagicMock()
    choice.message.content = response_text
    response = MagicMock()
    response.choices = [choice]

    if side_effect:
        openai_client.chat.completions.create.side_effect = side_effect
    else:
        openai_client.chat.completions.create.return_value = response

    with patch("services.llm_service.OpenAI", return_value=openai_client):
        svc = LlmService(
            api_key="test-key",
            model="test-model",
            cache_path="/dev/null",
        )

    return svc


class TestTieredParseValidJSON:
    def test_parses_valid_json(self):
        result = LlmService._parse_tiered_json(VALID_TIERED_JSON)
        assert result is not None
        assert isinstance(result, TieredReference)
        assert result.core == ["photosynthesis", "chloroplast", "sunlight energy"]
        assert result.supporting == ["carbon dioxide fixation", "glucose production"]
        assert result.extended == ["Calvin cycle"]
        assert "Photosynthesis" in result.flat_text

    def test_parses_fenced_json(self):
        result = LlmService._parse_tiered_json(VALID_TIERED_FENCED)
        assert result is not None
        assert result.core == ["photosynthesis", "chloroplast", "sunlight energy"]

    def test_malformed_json_returns_none(self):
        result = LlmService._parse_tiered_json(MALFORMED_JSON)
        assert result is None

    def test_missing_flat_answer_synthesizes(self):
        result = LlmService._parse_tiered_json(MISSING_FLAT_ANSWER)
        assert result is not None
        assert "mitosis" in result.flat_text

    def test_empty_core_allowed(self):
        result = LlmService._parse_tiered_json(EMPTY_CORE)
        assert result is not None
        assert result.core == []

    def test_non_string_items_filtered(self):
        result = LlmService._parse_tiered_json(NON_STRING_ITEMS)
        assert result is not None
        assert result.core == ["valid", "also valid"]

    def test_not_a_dict_returns_none(self):
        result = LlmService._parse_tiered_json(json.dumps(["a", "b"]))
        assert result is None

    def test_raw_llm_response_preserved(self):
        result = LlmService._parse_tiered_json(VALID_TIERED_JSON)
        assert result.raw_llm_response == VALID_TIERED_JSON


class TestTieredFallback:
    def test_fallback_returns_empty_core(self):
        result = LlmService._fallback_tiered("q?", "legacy text")
        assert result.core == []
        assert result.supporting == []
        assert result.flat_text == "legacy text"

    def test_empty_question_returns_fallback(self):
        svc = _make_service("")
        result = svc.generate_tiered_model_answer("")
        assert isinstance(result, TieredReference)
        assert result.core == []

    def test_unconfigured_service_returns_fallback(self):
        svc = LlmService(api_key="", model="test")
        result = svc.generate_tiered_model_answer("What is gravity?")
        assert isinstance(result, TieredReference)
        assert result.core == []


class TestGenerateTieredModelAnswer:
    def test_valid_response_returns_tiered(self, tmp_path):
        openai_client = MagicMock()
        choice = MagicMock()
        choice.message.content = VALID_TIERED_JSON
        response = MagicMock()
        response.choices = [choice]
        openai_client.chat.completions.create.return_value = response

        with patch("services.llm_service.OpenAI", return_value=openai_client):
            svc = LlmService(
                api_key="test-key",
                model="test-model",
                cache_path=str(tmp_path / "cache.json"),
            )

        result = svc.generate_tiered_model_answer("What is photosynthesis?")
        assert isinstance(result, TieredReference)
        assert len(result.core) == 3
        svc.close()

    def test_malformed_response_retries_then_falls_back(self, tmp_path):
        malformed_choice = MagicMock()
        malformed_choice.message.content = MALFORMED_JSON
        malformed_response = MagicMock()
        malformed_response.choices = [malformed_choice]

        openai_client = MagicMock()
        openai_client.chat.completions.create.return_value = malformed_response

        with patch("services.llm_service.OpenAI", return_value=openai_client):
            svc = LlmService(
                api_key="test-key",
                model="test-model",
                cache_path=str(tmp_path / "cache.json"),
            )

        result = svc.generate_tiered_model_answer("What is gravity?", max_retries=2)
        assert isinstance(result, TieredReference)
        svc.close()
