#!/usr/bin/env python3
"""OCR cascade benchmark harness — extended version.

Supports:
  - Per-page PNG extraction from PDFs (300 DPI via pdf2image)
  - Four providers: mistral, vision, tesseract, cascade
  - CER / WER vs ground-truth .txt files
  - Repeats + warmup, median + p95 latency aggregation
  - CSV output (one row per page × provider × repeat)
  - Markdown summary table (reproduces Table II from the plan)
  - Per-PDF breakdown subtable
  - Dry-run mode with API cost estimate and hard cap
  - Manifest CSV (id, source_pdf, page_num, path, word_count, char_count)

Usage:
    python -m scripts.bench_ocr \\
      --pdf-dir sample_handwritten_assgn \\
      --manifest sample_handwritten_assgn/manifest.csv \\
      --providers mistral,vision,tesseract,cascade \\
      --repeats 3 --warmup 2 \\
      --out-dir bench_results/
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import statistics
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure backend/ is importable when invoked as `python -m scripts.bench_ocr`
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(_BACKEND_DIR / ".env", override=False)

from adapters.ocr.base import OcrProvider, OcrResult
from adapters.ocr.tesseract import TesseractProvider

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

# Cost estimates (USD per 1000 pages)
_COST_PER_1K: dict[str, float] = {
    "mistral": 1.00,
    "vision": 1.50,
    "tesseract": 0.0,
    "cascade": 2.50,  # worst-case: mistral + vision both called
}
_COST_HARD_CAP_USD = 5.0

_OFFLINE_MAP: dict[str, str] = {
    "mistral": "No",
    "vision": "No",
    "tesseract": "Yes",
    "cascade": "Partial",
}


# ---------------------------------------------------------------------------
# CER / WER
# ---------------------------------------------------------------------------

def _normalize(text: str, lowercase: bool = False, strip_punct: bool = False) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    text = text.strip()
    if lowercase:
        text = text.lower()
    if strip_punct:
        text = re.sub(r"[^\w\s]", "", text)
    return text


def _cer(ref: str, hyp: str) -> float:
    r, h = list(ref), list(hyp)
    if not r:
        return 0.0 if not h else 1.0
    d = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        d[i][0] = i
    for j in range(len(h) + 1):
        d[0][j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            cost = 0 if r[i - 1] == h[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    return d[len(r)][len(h)] / len(r)


def _wer(ref: str, hyp: str) -> float:
    r, h = ref.split(), hyp.split()
    if not r:
        return 0.0 if not h else 1.0
    d = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        d[i][0] = i
    for j in range(len(h) + 1):
        d[0][j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            cost = 0 if r[i - 1] == h[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    return d[len(r)][len(h)] / len(r)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PageRecord:
    id: str
    source_pdf: str
    page_num: int
    path: Path
    word_count: int = 0
    char_count: int = 0


@dataclass
class BenchRow:
    page_id: str
    source_pdf: str
    provider: str
    repeat: int
    latency_s: float
    char_count: int
    cer: Optional[float]
    wer: Optional[float]
    error: str = ""


@dataclass
class ProviderStats:
    provider: str
    n: int
    n_errors: int
    mean_cer: Optional[float]
    mean_wer: Optional[float]
    median_latency: float
    p95_latency: float
    offline: str


# ---------------------------------------------------------------------------
# PDF → page extraction + manifest
# ---------------------------------------------------------------------------

def extract_pages(pdf_dir: Path, pages_dir: Path, dpi: int = 300) -> list[PageRecord]:
    """Convert each PDF in pdf_dir to per-page PNG images in pages_dir."""
    try:
        from pdf2image import convert_from_path
    except ImportError as exc:
        raise ImportError("pdf2image required — pip install pdf2image") from exc

    pages_dir.mkdir(parents=True, exist_ok=True)
    records: list[PageRecord] = []
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"  No PDFs found in {pdf_dir}")
        return records

    for pdf in pdfs:
        print(f"  Extracting {pdf.name} …", end=" ", flush=True)
        try:
            images = convert_from_path(str(pdf), dpi=dpi)
        except Exception as exc:
            print(f"FAILED ({exc})")
            continue

        for page_num, pil_img in enumerate(images, start=1):
            stem = f"{pdf.stem}_p{page_num:03d}"
            out_path = pages_dir / f"{stem}.png"
            if not out_path.exists():
                pil_img.save(str(out_path), format="PNG")
            records.append(PageRecord(
                id=stem,
                source_pdf=pdf.name,
                page_num=page_num,
                path=out_path,
            ))
        print(f"{len(images)} pages")

    return records


def write_manifest(records: list[PageRecord], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "source_pdf", "page_num", "path", "word_count", "char_count"
        ])
        writer.writeheader()
        for r in records:
            writer.writerow({
                "id": r.id,
                "source_pdf": r.source_pdf,
                "page_num": r.page_num,
                "path": str(r.path),
                "word_count": r.word_count,
                "char_count": r.char_count,
            })


def load_manifest(manifest_path: Path) -> list[PageRecord]:
    records: list[PageRecord] = []
    with manifest_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Empty or malformed manifest: {manifest_path}")
        required = {"id", "source_pdf", "page_num", "path"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Manifest missing columns: {missing}")
        for row in reader:
            records.append(PageRecord(
                id=row["id"],
                source_pdf=row["source_pdf"],
                page_num=int(row["page_num"]),
                path=Path(row["path"]),
                word_count=int(row.get("word_count") or 0),
                char_count=int(row.get("char_count") or 0),
            ))
    return records


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def _build_providers(names: list[str], mistral_key: str,
                     credentials_path: Optional[str],
                     vision_api_key: Optional[str] = None) -> dict[str, OcrProvider]:
    available: dict[str, OcrProvider] = {}

    def _try(name: str, factory):
        try:
            available[name] = factory()
            print(f"  [ok]    {name}")
        except Exception as exc:
            print(f"  [skip]  {name} — {exc}")

    if "mistral" in names:
        from adapters.ocr.mistral_ocr import MistralOcrProvider
        _try("mistral", lambda: MistralOcrProvider(api_key=mistral_key))

    if "vision" in names:
        from adapters.ocr.google_vision import GoogleVisionProvider
        _try("vision", lambda: GoogleVisionProvider(
            credentials_path=credentials_path,
            api_key=vision_api_key,
        ))

    if "tesseract" in names:
        _try("tesseract", TesseractProvider)

    if "cascade" in names:
        from adapters.ocr.cascade import CascadeProvider
        config = {}
        if mistral_key:
            config["MISTRAL_API_KEY"] = mistral_key
        if credentials_path:
            config["GOOGLE_CREDENTIALS_PATH"] = credentials_path
        _try("cascade", lambda: CascadeProvider(config))

    return available


# ---------------------------------------------------------------------------
# Dry-run / cost estimation
# ---------------------------------------------------------------------------

def _estimate_cost(pages: list[PageRecord], provider_names: list[str],
                   repeats: int, warmup: int) -> dict[str, float]:
    billable = max(repeats - warmup, 1)
    estimates = {}
    for name in provider_names:
        rate = _COST_PER_1K.get(name, 0.0)
        cost = rate * len(pages) * billable / 1000.0
        estimates[name] = cost
    return estimates


def _dry_run_report(pages: list[PageRecord], provider_names: list[str],
                    repeats: int, warmup: int) -> None:
    estimates = _estimate_cost(pages, provider_names, repeats, warmup)
    total_calls = len(pages) * repeats
    billable = max(repeats - warmup, 1)
    total_cost = sum(estimates.values())

    print("\n=== DRY RUN — cost estimate ===")
    print(f"  Pages:     {len(pages)}")
    print(f"  Repeats:   {repeats}  (warmup: {warmup}, billable: {billable})")
    print(f"  Total API calls per provider: {len(pages) * billable:,}")
    print()
    for name, cost in estimates.items():
        print(f"  {name:<12} ${cost:.4f}")
    print(f"  {'TOTAL':<12} ${total_cost:.4f}")

    if total_cost > _COST_HARD_CAP_USD:
        print(f"\n  ABORT: estimated cost ${total_cost:.2f} exceeds hard cap ${_COST_HARD_CAP_USD}")
        sys.exit(1)
    else:
        print(f"\n  Cost within hard cap (${_COST_HARD_CAP_USD}). Exiting dry run.")


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def _run_provider(provider: OcrProvider, page: PageRecord,
                  repeats: int, warmup: int,
                  gt_dir: Optional[Path]) -> list[BenchRow]:
    gt_text: Optional[str] = None
    if gt_dir:
        gt_file = gt_dir / f"{page.id}.txt"
        if gt_file.exists():
            raw = gt_file.read_text(encoding="utf-8")
            gt_text = _normalize(raw)

    rows: list[BenchRow] = []
    for rep in range(repeats):
        t0 = time.perf_counter()
        try:
            result: OcrResult = provider.extract(str(page.path))
            latency = time.perf_counter() - t0
            hyp = _normalize(result.text)
            cer_val = _cer(gt_text, hyp) if gt_text is not None else None
            wer_val = _wer(gt_text, hyp) if gt_text is not None else None
            rows.append(BenchRow(
                page_id=page.id,
                source_pdf=page.source_pdf,
                provider=provider.name,
                repeat=rep,
                latency_s=latency,
                char_count=len(result.text),
                cer=cer_val,
                wer=wer_val,
            ))
        except Exception as exc:
            latency = time.perf_counter() - t0
            rows.append(BenchRow(
                page_id=page.id,
                source_pdf=page.source_pdf,
                provider=provider.name,
                repeat=rep,
                latency_s=latency,
                char_count=0,
                cer=None,
                wer=None,
                error=str(exc),
            ))
    return rows


def _aggregate(rows: list[BenchRow], provider_name: str) -> ProviderStats:
    provider_rows = [r for r in rows if r.provider == provider_name]
    if not provider_rows:
        return ProviderStats(
            provider=provider_name, n=0, n_errors=0,
            mean_cer=None, mean_wer=None,
            median_latency=0.0, p95_latency=0.0,
            offline=_OFFLINE_MAP.get(provider_name, "?"),
        )

    n_errors = sum(1 for r in provider_rows if r.error)
    latencies = [r.latency_s for r in provider_rows]
    cer_vals = [r.cer for r in provider_rows if r.cer is not None]
    wer_vals = [r.wer for r in provider_rows if r.wer is not None]

    latencies_sorted = sorted(latencies)
    p95_idx = max(0, int(len(latencies_sorted) * 0.95) - 1)

    return ProviderStats(
        provider=provider_name,
        n=len(provider_rows),
        n_errors=n_errors,
        mean_cer=(sum(cer_vals) / len(cer_vals)) if cer_vals else None,
        mean_wer=(sum(wer_vals) / len(wer_vals)) if wer_vals else None,
        median_latency=statistics.median(latencies) if latencies else 0.0,
        p95_latency=latencies_sorted[p95_idx] if latencies_sorted else 0.0,
        offline=_OFFLINE_MAP.get(provider_name, "?"),
    )


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def _write_csv(rows: list[BenchRow], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "page_id", "source_pdf", "provider", "repeat",
            "latency_s", "char_count", "cer", "wer", "error"
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "page_id": r.page_id,
                "source_pdf": r.source_pdf,
                "provider": r.provider,
                "repeat": r.repeat,
                "latency_s": f"{r.latency_s:.4f}",
                "char_count": r.char_count,
                "cer": f"{r.cer:.4f}" if r.cer is not None else "",
                "wer": f"{r.wer:.4f}" if r.wer is not None else "",
                "error": r.error,
            })


def _fmt_pct(val: Optional[float]) -> str:
    return f"{val * 100:.1f}" if val is not None else "n/a"


def _fmt_s(val: float) -> str:
    return f"{val:.2f}"


def _summary_table(stats: list[ProviderStats], has_gt: bool) -> str:
    lines: list[str] = []
    if has_gt:
        header = f"{'Provider':<32} | {'CER (%)':>7} | {'WER (%)':>7} | {'Latency(s)':>10} | {'p95(s)':>7} | {'Offline':>8} | {'N':>5} | {'Errors':>6}"
        sep = "-" * len(header)
        lines += [header, sep]
        for s in stats:
            lines.append(
                f"{s.provider:<32} | {_fmt_pct(s.mean_cer):>7} | {_fmt_pct(s.mean_wer):>7} | "
                f"{_fmt_s(s.median_latency):>10} | {_fmt_s(s.p95_latency):>7} | "
                f"{s.offline:>8} | {s.n:>5} | {s.n_errors:>6}"
            )
    else:
        header = f"{'Provider':<32} | {'Latency(s)':>10} | {'p95(s)':>7} | {'Offline':>8} | {'N':>5} | {'Errors':>6}"
        sep = "-" * len(header)
        lines += [header, sep]
        for s in stats:
            lines.append(
                f"{s.provider:<32} | {_fmt_s(s.median_latency):>10} | {_fmt_s(s.p95_latency):>7} | "
                f"{s.offline:>8} | {s.n:>5} | {s.n_errors:>6}"
            )
    return "\n".join(lines)


def _per_pdf_table(rows: list[BenchRow], provider_names: list[str], has_gt: bool) -> str:
    pdfs = sorted({r.source_pdf for r in rows})
    sections: list[str] = []
    for pdf in pdfs:
        pdf_rows = [r for r in rows if r.source_pdf == pdf]
        stats = [_aggregate(pdf_rows, p) for p in provider_names]
        sections.append(f"\n### {pdf}\n")
        sections.append(_summary_table(stats, has_gt))
    return "\n".join(sections)


def _write_markdown(stats: list[ProviderStats], rows: list[BenchRow],
                    provider_names: list[str], has_gt: bool,
                    out_path: Path, run_ts: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        f"# OCR Benchmark Summary — {run_ts}",
        "",
        "## TABLE II: OCR provider comparison",
        "",
        "```",
        _summary_table(stats, has_gt),
        "```",
        "",
        "## Per-PDF breakdown",
        "",
        _per_pdf_table(rows, provider_names, has_gt),
        "",
        f"*Generated: {run_ts}*",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OCR benchmark harness (extended)")
    p.add_argument("--pdf-dir", default="sample_handwritten_assgn",
                   help="Directory of source PDFs (default: sample_handwritten_assgn)")
    p.add_argument("--manifest",
                   help="Path to manifest.csv; auto-generated if missing")
    p.add_argument("--providers", default="tesseract",
                   help="Comma-separated provider list (default: tesseract). "
                        "Cloud providers (mistral, vision, cascade) require API keys.")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--warmup", type=int, default=2,
                   help="Number of repeats to discard as warmup (default: 2)")
    p.add_argument("--out-dir", default="bench_results",
                   help="Output directory for CSV + markdown (default: bench_results)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print cost estimate and exit without running OCR")
    p.add_argument("--fixtures-dir",
                   help="Use fixture images directly (skip PDF extraction)")
    p.add_argument("--gt-dir",
                   help="Directory of ground-truth .txt files named <page_id>.txt")
    p.add_argument("--dpi", type=int, default=300)
    p.add_argument("--no-extract", action="store_true",
                   help="Skip PDF→page extraction (pages must already exist)")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    run_ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = Path(args.out_dir) / run_ts

    provider_names = [n.strip() for n in args.providers.split(",") if n.strip()]
    mistral_key = os.getenv("MISTRAL_API_KEY", "")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or None
    vision_api_key = os.getenv("GOOGLE_VISION_API_KEY") or None

    # -----------------------------------------------------------------------
    # Step 1 — collect page records
    # -----------------------------------------------------------------------
    if args.fixtures_dir:
        # Legacy mode: use pre-extracted images directly
        fixtures_dir = Path(args.fixtures_dir)
        images = sorted(p for p in fixtures_dir.iterdir()
                        if p.suffix.lower() in _IMAGE_EXTENSIONS)
        records = [
            PageRecord(id=img.stem, source_pdf=img.parent.name,
                       page_num=0, path=img)
            for img in images
        ]
        gt_dir = Path(args.gt_dir) if args.gt_dir else fixtures_dir
    else:
        pdf_dir = Path(args.pdf_dir)
        pages_dir = pdf_dir / "pages"
        gt_dir_path = Path(args.gt_dir) if args.gt_dir else pdf_dir / "gt"
        gt_dir = gt_dir_path if gt_dir_path.exists() else None

        manifest_path = Path(args.manifest) if args.manifest \
            else pdf_dir / "manifest.csv"

        if manifest_path.exists() and args.no_extract:
            print(f"Loading manifest from {manifest_path}")
            records = load_manifest(manifest_path)
        else:
            print(f"\n[Phase 1] Extracting PDF pages → {pages_dir}")
            records = extract_pages(pdf_dir, pages_dir, dpi=args.dpi)
            if records:
                write_manifest(records, manifest_path)
                print(f"  Manifest written → {manifest_path}")
            else:
                print("  No pages extracted — aborting.")
                sys.exit(1)

    if not records:
        print("No pages to benchmark.")
        sys.exit(1)

    print(f"\n  Total pages: {len(records)}")

    # -----------------------------------------------------------------------
    # Step 2 — dry run / cost check
    # -----------------------------------------------------------------------
    if args.dry_run:
        _dry_run_report(records, provider_names, args.repeats, args.warmup)
        return

    # -----------------------------------------------------------------------
    # Step 3 — init providers
    # -----------------------------------------------------------------------
    print(f"\n[Phase 2] Initialising providers: {', '.join(provider_names)}")
    providers = _build_providers(provider_names, mistral_key, credentials_path, vision_api_key)

    active_names = [n for n in provider_names if n in providers]
    if not active_names:
        print("No providers available — aborting.")
        sys.exit(1)

    has_gt = gt_dir is not None and any(
        (gt_dir / f"{r.id}.txt").exists() for r in records
    )
    print(f"  Ground truth: {'present' if has_gt else 'absent (latency-only mode)'}")

    # -----------------------------------------------------------------------
    # Step 4 — run benchmark
    # -----------------------------------------------------------------------
    print(f"\n[Phase 3] Running benchmark "
          f"({len(records)} pages × {len(active_names)} providers "
          f"× {args.repeats} repeats, warmup={args.warmup})")

    all_rows: list[BenchRow] = []

    for page in records:
        for pname in active_names:
            provider = providers[pname]
            print(f"  {page.id}  ×  {pname} …", end=" ", flush=True)
            page_rows = _run_provider(provider, page, args.repeats, args.warmup, gt_dir)
            # Discard warmup repeats from metrics (keep last repeats-warmup rows)
            billable = max(args.repeats - args.warmup, 1)
            kept = page_rows[-billable:]
            all_rows.extend(kept)
            errs = sum(1 for r in kept if r.error)
            med_lat = statistics.median(r.latency_s for r in kept)
            print(f"lat={med_lat:.2f}s  errs={errs}")

    # -----------------------------------------------------------------------
    # Step 5 — aggregate + output
    # -----------------------------------------------------------------------
    stats = [_aggregate(all_rows, n) for n in active_names]

    print("\n\n=== BENCHMARK RESULTS ===\n")
    print(_summary_table(stats, has_gt))

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "raw.csv"
    md_path = out_dir / "summary.md"
    by_pdf_path = out_dir / "by_pdf.md"

    _write_csv(all_rows, csv_path)

    _write_markdown(stats, all_rows, active_names, has_gt, md_path, run_ts)

    # per-PDF breakdown in separate file
    by_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    by_pdf_md = (
        f"# Per-PDF OCR Breakdown — {run_ts}\n"
        + _per_pdf_table(all_rows, active_names, has_gt)
    )
    by_pdf_path.write_text(by_pdf_md, encoding="utf-8")

    print(f"\nOutputs written to {out_dir}/")
    print(f"  {csv_path.name}  — raw per-page results")
    print(f"  {md_path.name}   — summary table (Table II)")
    print(f"  {by_pdf_path.name}  — per-PDF breakdown")


if __name__ == "__main__":
    main()
