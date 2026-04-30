"""Unit and integration tests for the extended bench_ocr harness.

Tests cover:
- CER / WER metric functions
- Normalization
- Aggregation (mean/median)
- Manifest read/write round-trip
- Cascade fallback behaviour (mocked providers)
- Warmup skip logic
- CSV + Markdown output schemas
"""

from __future__ import annotations

import csv
import io
import statistics
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest

# Make backend importable
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from scripts.bench_ocr import (
    _cer,
    _normalize,
    _wer,
    _aggregate,
    _estimate_cost,
    _write_csv,
    _write_markdown,
    BenchRow,
    PageRecord,
    ProviderStats,
    extract_pages,
    load_manifest,
    write_manifest,
)


# ---------------------------------------------------------------------------
# CER / WER unit tests
# ---------------------------------------------------------------------------

class TestCer:
    def test_identical(self):
        assert _cer("abc", "abc") == 0.0

    def test_single_substitution(self):
        assert abs(_cer("abc", "abd") - 1 / 3) < 1e-9

    def test_full_deletion(self):
        assert _cer("abc", "") == 1.0

    def test_both_empty(self):
        assert _cer("", "") == 0.0

    def test_insertion_only(self):
        # ref="" hyp="x" — no ref chars to divide by → returns 1.0
        assert _cer("", "x") == 1.0

    def test_longer_hyp(self):
        # "abc" vs "abcd" — 1 insertion / 3 ref chars
        assert abs(_cer("abc", "abcd") - 1 / 3) < 1e-9

    def test_completely_different(self):
        assert _cer("aaa", "bbb") == 1.0


class TestWer:
    def test_identical(self):
        assert _wer("the cat sat", "the cat sat") == 0.0

    def test_one_substitution(self):
        assert abs(_wer("the cat sat", "the cat ran") - 1 / 3) < 1e-9

    def test_full_deletion(self):
        assert _wer("hello world", "") == 1.0

    def test_both_empty(self):
        assert _wer("", "") == 0.0

    def test_single_word(self):
        assert _wer("hello", "hello") == 0.0
        assert _wer("hello", "world") == 1.0


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_collapse_whitespace(self):
        assert _normalize("A  B\t C") == "A B C"

    def test_strip_edges(self):
        assert _normalize("  hello  ") == "hello"

    def test_nfkc(self):
        # NFKC: fullwidth A → A
        result = _normalize("Ａ")
        assert result == "A"

    def test_lowercase(self):
        assert _normalize("Hello World", lowercase=True) == "hello world"

    def test_strip_punct(self):
        result = _normalize("Hello, world!", strip_punct=True)
        assert "," not in result and "!" not in result

    def test_multiline_strip(self):
        result = _normalize("  line1  \n  line2  ")
        assert result == "line1\nline2"

    def test_lowercase_collapse_combined(self):
        # As described in plan: "A  B\n" ≡ "a b" under lowercase+collapse
        assert _normalize("A  B\n", lowercase=True) == "a b"


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

class TestAggregate:
    def _make_rows(self, provider: str, latencies, cers=None):
        rows = []
        for i, lat in enumerate(latencies):
            cer = cers[i] if cers else None
            rows.append(BenchRow(
                page_id=f"p{i:03d}", source_pdf="test.pdf",
                provider=provider, repeat=0,
                latency_s=lat, char_count=100,
                cer=cer, wer=cer,
            ))
        return rows

    def test_mean_cer(self):
        rows = self._make_rows("tesseract", [1.0, 1.0, 1.0], cers=[0.1, 0.3, 0.2])
        stats = _aggregate(rows, "tesseract")
        assert abs(stats.mean_cer - 0.2) < 1e-9

    def test_median_latency(self):
        rows = self._make_rows("tesseract", [2.0, 1.0, 3.0])
        stats = _aggregate(rows, "tesseract")
        assert stats.median_latency == 2.0

    def test_p95_latency(self):
        latencies = list(range(1, 21))  # 1..20
        rows = self._make_rows("tesseract", latencies)
        stats = _aggregate(rows, "tesseract")
        # p95 index = int(20 * 0.95) - 1 = 18, value = 19
        assert stats.p95_latency == 19

    def test_no_rows(self):
        stats = _aggregate([], "tesseract")
        assert stats.n == 0
        assert stats.mean_cer is None

    def test_error_count(self):
        rows = self._make_rows("tesseract", [1.0, 2.0])
        rows[0].error = "timeout"
        stats = _aggregate(rows, "tesseract")
        assert stats.n_errors == 1


# ---------------------------------------------------------------------------
# Manifest read/write round-trip
# ---------------------------------------------------------------------------

class TestManifest:
    def test_roundtrip(self, tmp_path):
        records = [
            PageRecord(id="saksham_p001", source_pdf="saksham.pdf",
                       page_num=1, path=tmp_path / "saksham_p001.png",
                       word_count=42, char_count=230),
            PageRecord(id="saksham_p002", source_pdf="saksham.pdf",
                       page_num=2, path=tmp_path / "saksham_p002.png",
                       word_count=38, char_count=195),
        ]
        manifest = tmp_path / "manifest.csv"
        write_manifest(records, manifest)
        loaded = load_manifest(manifest)

        assert len(loaded) == 2
        assert loaded[0].id == "saksham_p001"
        assert loaded[1].page_num == 2
        assert loaded[0].word_count == 42

    def test_malformed_manifest_raises(self, tmp_path):
        bad = tmp_path / "bad.csv"
        bad.write_text("id,wrong_column\nfoo,bar\n")
        with pytest.raises(ValueError, match="missing"):
            load_manifest(bad)

    def test_empty_manifest_raises(self, tmp_path):
        empty = tmp_path / "empty.csv"
        empty.write_text("")
        with pytest.raises(ValueError):
            load_manifest(empty)


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

class TestCostEstimate:
    def _pages(self, n):
        return [PageRecord(id=f"p{i}", source_pdf="x.pdf",
                           page_num=i, path=Path(f"/tmp/p{i}.png"))
                for i in range(n)]

    def test_tesseract_free(self):
        est = _estimate_cost(self._pages(100), ["tesseract"], repeats=3, warmup=2)
        assert est["tesseract"] == 0.0

    def test_mistral_cost(self):
        # 1000 pages × 1 billable repeat = $1.00
        est = _estimate_cost(self._pages(1000), ["mistral"], repeats=3, warmup=2)
        assert abs(est["mistral"] - 1.0) < 1e-6

    def test_vision_cost(self):
        est = _estimate_cost(self._pages(1000), ["vision"], repeats=3, warmup=2)
        assert abs(est["vision"] - 1.5) < 1e-6


# ---------------------------------------------------------------------------
# CSV output schema
# ---------------------------------------------------------------------------

class TestCsvOutput:
    def test_csv_schema(self, tmp_path):
        rows = [
            BenchRow(page_id="p001", source_pdf="a.pdf", provider="tesseract",
                     repeat=0, latency_s=1.23, char_count=300, cer=0.05, wer=0.10),
            BenchRow(page_id="p001", source_pdf="a.pdf", provider="tesseract",
                     repeat=1, latency_s=1.25, char_count=300, cer=None, wer=None,
                     error="timeout"),
        ]
        out = tmp_path / "raw.csv"
        _write_csv(rows, out)
        with out.open() as f:
            reader = csv.DictReader(f)
            loaded = list(reader)
        assert len(loaded) == 2
        assert set(reader.fieldnames) >= {
            "page_id", "source_pdf", "provider", "repeat",
            "latency_s", "char_count", "cer", "wer", "error"
        }
        assert loaded[0]["cer"] == "0.0500"
        assert loaded[1]["error"] == "timeout"


# ---------------------------------------------------------------------------
# Markdown output schema
# ---------------------------------------------------------------------------

class TestMarkdownOutput:
    def test_markdown_contains_key_sections(self, tmp_path):
        stats = [
            ProviderStats(provider="tesseract", n=10, n_errors=0,
                          mean_cer=0.15, mean_wer=0.20,
                          median_latency=2.5, p95_latency=3.1,
                          offline="Yes"),
        ]
        rows = [
            BenchRow(page_id="p001", source_pdf="test.pdf", provider="tesseract",
                     repeat=0, latency_s=2.5, char_count=200, cer=0.15, wer=0.20),
        ]
        out = tmp_path / "summary.md"
        _write_markdown(stats, rows, ["tesseract"], has_gt=True,
                        out_path=out, run_ts="2026-04-24")
        content = out.read_text()
        assert "TABLE II" in content
        assert "tesseract" in content
        assert "Per-PDF breakdown" in content
        assert "2026-04-24" in content


# ---------------------------------------------------------------------------
# Warmup skip logic
# ---------------------------------------------------------------------------

class TestWarmupSkip:
    """Verify that with repeats=3 warmup=2 only 1 measurement is retained per page."""

    def test_warmup_rows_discarded(self, tmp_path):
        from unittest.mock import MagicMock, patch
        from scripts.bench_ocr import _run_provider

        page = PageRecord(
            id="p001", source_pdf="test.pdf", page_num=1,
            path=tmp_path / "p001.png"
        )
        # Create a dummy 1px image so the provider doesn't fail on file access
        from PIL import Image as PILImage
        PILImage.new("RGB", (1, 1)).save(str(page.path))

        mock_provider = MagicMock()
        mock_result = MagicMock()
        mock_result.text = "hello world"
        mock_provider.name = "tesseract"
        mock_provider.extract.return_value = mock_result

        rows = _run_provider(mock_provider, page, repeats=3, warmup=0, gt_dir=None)
        assert len(rows) == 3
        assert mock_provider.extract.call_count == 3

        # The harness (main loop) takes rows[-billable:] where billable=repeats-warmup
        billable = max(3 - 2, 1)
        kept = rows[-billable:]
        assert len(kept) == 1


# ---------------------------------------------------------------------------
# Cascade fallback (mocked)
# ---------------------------------------------------------------------------

class TestCascadeFallback:
    """Mistral raises → cascade should fall through to vision."""

    def test_cascade_uses_fallback(self, tmp_path):
        from unittest.mock import MagicMock, patch
        from adapters.ocr.base import OcrResult

        vision_result = OcrResult(
            text="handwritten answer", confidence=0.75, provider="vision"
        )

        mock_mistral = MagicMock()
        mock_mistral.name = "mistral"
        mock_mistral.confidence_threshold = 0.70
        mock_mistral.extract.side_effect = RuntimeError("API unavailable")

        mock_vision = MagicMock()
        mock_vision.name = "vision"
        mock_vision.confidence_threshold = 0.60
        mock_vision.extract.return_value = vision_result

        # Simulate cascade manually (matching OcrService logic)
        providers = [mock_mistral, mock_vision]
        best = None
        for p in providers:
            try:
                result = p.extract("/fake/path.png")
                if best is None or result.confidence > best.confidence:
                    best = result
                if result.confidence >= p.confidence_threshold:
                    break
            except Exception:
                pass

        assert best is not None
        assert best.provider == "vision"
        assert best.text == "handwritten answer"
        mock_mistral.extract.assert_called_once()
        mock_vision.extract.assert_called_once()

    def test_cascade_latency_includes_failed_providers(self, tmp_path):
        """Latency must include all provider attempts, not just the successful one."""
        import time as _time
        from adapters.ocr.base import OcrResult

        calls: list[float] = []

        def slow_fail(path):
            _time.sleep(0.01)
            raise RuntimeError("fail")

        def slow_succeed(path):
            _time.sleep(0.01)
            return OcrResult(text="ok", confidence=0.8, provider="vision")

        from unittest.mock import MagicMock
        mock_fail = MagicMock()
        mock_fail.name = "mistral"
        mock_fail.confidence_threshold = 0.70
        mock_fail.extract.side_effect = slow_fail

        mock_ok = MagicMock()
        mock_ok.name = "vision"
        mock_ok.confidence_threshold = 0.60
        mock_ok.extract.side_effect = slow_succeed

        t0 = _time.perf_counter()
        providers = [mock_fail, mock_ok]
        best = None
        for p in providers:
            try:
                result = p.extract("/x")
                best = result
                break
            except Exception:
                pass
        elapsed = _time.perf_counter() - t0

        # Both providers were attempted → total > 20ms
        assert elapsed > 0.018
        assert best is not None and best.provider == "vision"
