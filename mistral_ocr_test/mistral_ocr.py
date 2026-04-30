"""
Mistral OCR - PDF Processing Script
Uses mistral-ocr-latest model to extract text from PDFs.

Supports three upload methods:
  1. Local PDF file (uploads to Mistral cloud, then OCRs)
  2. Base64 encoded PDF
  3. Public PDF URL

Usage:
  pip install mistralai

  # Set your API key
  export MISTRAL_API_KEY="your_api_key_here"

  # Run the script
  python mistral_ocr.py --file your_document.pdf
  python mistral_ocr.py --url https://arxiv.org/pdf/2201.04234
  python mistral_ocr.py --file your_document.pdf --output result.md
"""

import os
import sys
import json
import base64
import argparse
from pathlib import Path


def get_client():
    """Initialize and return the Mistral client."""
    try:
        from mistralai.client import Mistral
    except ImportError:
        print("Error: mistralai package not installed.")
        print("Run: pip install mistralai")
        sys.exit(1)

    api_key = 'vWjcY1lnFMSwoIOe7Dr7d4RDB3BYCCCA'
    if not api_key:
        print("Error: MISTRAL_API_KEY environment variable not set.")
        print("Set it with: export MISTRAL_API_KEY='your_key_here'")
        sys.exit(1)

    return Mistral(api_key=api_key)


# ─────────────────────────────────────────────
# Method 1: Upload PDF to Mistral Cloud (recommended for local files)
# ─────────────────────────────────────────────
def ocr_via_file_upload(client, pdf_path: str, **ocr_kwargs) -> dict:
    """
    Upload a local PDF to Mistral's file storage, then run OCR on it.
    Best for large files or repeated processing of the same document.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"Uploading '{pdf_path.name}' to Mistral cloud...")
    with open(pdf_path, "rb") as f:
        uploaded_file = client.files.upload(
            file={"file_name": pdf_path.name, "content": f},
            purpose="ocr",
        )

    print(f"File uploaded. ID: {uploaded_file.id}")
    print("Getting signed URL...")

    # Get a temporary signed URL for the uploaded file
    signed_url = client.files.get_signed_url(file_id=uploaded_file.id)

    print("Running OCR...")
    response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": signed_url.url,
        },
        **ocr_kwargs,
    )

    # Optional: delete the file after processing to save storage
    client.files.delete(file_id=uploaded_file.id)
    print(f"Cleaned up uploaded file (ID: {uploaded_file.id})")

    return response


# ─────────────────────────────────────────────
# Method 2: Base64 Encoded PDF (no upload needed)
# ─────────────────────────────────────────────
def ocr_via_base64(client, pdf_path: str, **ocr_kwargs) -> dict:
    """
    Encode a local PDF as base64 and send it directly in the API request.
    Simpler than uploading, but only suitable for smaller files.
    """
    with open(pdf_path, "rb") as f:
        pdf_base64 = base64.standard_b64encode(f.read()).decode("utf-8")

    response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_base64",
            "document_base64": pdf_base64,
        },
        **ocr_kwargs,
    )
    return response
    

# ─────────────────────────────────────────────
# Method 3: Public URL
# ─────────────────────────────────────────────
def ocr_via_url(client, url: str, **ocr_kwargs) -> dict:
    """
    Run OCR on a publicly accessible PDF URL.
    The URL must be reachable by Mistral's servers.
    """
    print(f"Running OCR on URL: {url}")
    response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": url,
        },
        **ocr_kwargs,
    )
    return response


# ─────────────────────────────────────────────
# Result Processing
# ─────────────────────────────────────────────
def extract_full_text(ocr_response) -> str:
    """Combine markdown text from all pages into a single string."""
    pages = ocr_response.pages
    parts = []
    for page in pages:
        parts.append(f"\n\n--- Page {page.index + 1} ---\n")
        parts.append(page.markdown or "")
    return "".join(parts).strip()


def print_summary(ocr_response):
    """Print a summary of the OCR results to the console."""
    pages = ocr_response.pages
    model = ocr_response.model
    usage = ocr_response.usage_info

    print("\n" + "=" * 60)
    print(f"  Model  : {model}")
    print(f"  Pages  : {len(pages)}")
    if usage:
        print(f"  Usage  : {usage}")
    print("=" * 60)

    for page in pages:
        print(f"\n[Page {page.index + 1}]")

        # Show confidence scores if available
        if page.confidence_scores:
            cs = page.confidence_scores
            avg = getattr(cs, "average_page_confidence_score", None)
            mn = getattr(cs, "minimum_page_confidence_score", None)
            if avg is not None:
                print(f"  Confidence  avg={avg:.3f}  min={mn:.3f}")

        # Show a preview of extracted text
        text = page.markdown or ""
        preview = text[:300].replace("\n", " ")
        print(f"  Text preview: {preview}{'...' if len(text) > 300 else ''}")

        if page.images:
            print(f"  Images found: {len(page.images)}")
        if page.tables:
            print(f"  Tables found: {len(page.tables)}")
        if page.hyperlinks:
            print(f"  Hyperlinks  : {len(page.hyperlinks)}")


def save_results(ocr_response, output_path: str, save_json: bool = False):
    """Save extracted text (and optionally full JSON) to disk."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save markdown text
    full_text = extract_full_text(ocr_response)
    output_path.write_text(full_text, encoding="utf-8")
    print(f"\nMarkdown saved → {output_path}")

    # Optionally save the raw JSON response
    if save_json:
        json_path = output_path.with_suffix(".json")
        raw = {
            "model": ocr_response.model,
            "pages": [
                {
                    "index": p.index,
                    "markdown": p.markdown,
                    "images": [vars(img) for img in (p.images or [])],
                    "tables": [vars(tbl) for tbl in (p.tables or [])],
                    "hyperlinks": p.hyperlinks or [],
                    "header": p.header,
                    "footer": p.footer,
                }
                for p in ocr_response.pages
            ],
        }
        json_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"JSON saved     → {json_path}")


# ─────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Run Mistral OCR on a PDF and extract text.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # OCR a local PDF (uploads to Mistral cloud)
  python mistral_ocr.py --file document.pdf

  # OCR a local PDF using base64 (no upload, good for small files)
  python mistral_ocr.py --file document.pdf --method base64

  # OCR a public PDF URL
  python mistral_ocr.py --url https://arxiv.org/pdf/2201.04234

  # Save result to a specific file
  python mistral_ocr.py --file document.pdf --output extracted.md

  # Also save raw JSON output
  python mistral_ocr.py --file document.pdf --json

  # Extract tables as HTML and include headers/footers
  python mistral_ocr.py --file document.pdf --table-format html --extract-header --extract-footer

  # Include confidence scores
  python mistral_ocr.py --file document.pdf --confidence word
        """,
    )

    # Input source (mutually exclusive)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", metavar="PATH", help="Path to a local PDF file")
    source.add_argument("--url", metavar="URL", help="Public URL of a PDF")

    # Upload method (only relevant for --file)
    parser.add_argument(
        "--method",
        choices=["upload", "base64"],
        default="upload",
        help="How to send the PDF: 'upload' (default) or 'base64'",
    )

    # OCR options
    parser.add_argument(
        "--table-format",
        choices=["markdown", "html"],
        default=None,
        help="Format for extracted tables (default: inline markdown)",
    )
    parser.add_argument(
        "--extract-header",
        action="store_true",
        help="Extract headers separately from main content",
    )
    parser.add_argument(
        "--extract-footer",
        action="store_true",
        help="Extract footers separately from main content",
    )
    parser.add_argument(
        "--confidence",
        choices=["page", "word"],
        default=None,
        metavar="GRANULARITY",
        help="Include confidence scores: 'page' or 'word'",
    )
    parser.add_argument(
        "--include-images",
        action="store_true",
        default=True,
        help="Include base64 image data in response (default: True)",
    )

    # Output options
    parser.add_argument(
        "--output",
        metavar="PATH",
        default=None,
        help="Output file path for extracted text (default: <input_name>.md or ocr_output.md)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also save the full JSON response alongside the markdown",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        dest="print_text",
        help="Print the full extracted text to stdout",
    )

    args = parser.parse_args()

    # Build OCR kwargs
    ocr_kwargs = {
        "include_image_base64": args.include_images,
    }
    if args.table_format:
        ocr_kwargs["table_format"] = args.table_format
    if args.extract_header:
        ocr_kwargs["extract_header"] = True
    if args.extract_footer:
        ocr_kwargs["extract_footer"] = True
    if args.confidence:
        ocr_kwargs["confidence_scores_granularity"] = args.confidence

    # Determine output path
    if args.output:
        output_path = args.output
    elif args.file:
        output_path = Path(args.file).stem + "_ocr.md"
    else:
        output_path = "ocr_output.md"

    # Run OCR
    client = get_client()

    try:
        if args.url:
            response = ocr_via_url(client, args.url, **ocr_kwargs)
        elif args.method == "base64":
            response = ocr_via_base64(client, args.file, **ocr_kwargs)
        else:
            response = ocr_via_file_upload(client, args.file, **ocr_kwargs)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"OCR failed: {e}")
        sys.exit(1)

    # Show summary
    print_summary(response)

    # Save output
    save_results(response, output_path, save_json=args.json)

    # Optionally print full text
    if args.print_text:
        print("\n" + "=" * 60 + " EXTRACTED TEXT " + "=" * 60)
        print(extract_full_text(response))


if __name__ == "__main__":
    main()