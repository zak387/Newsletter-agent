#!/usr/bin/env python3
"""Writing Agent — produces a voice profile and newsletter draft for a creator."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


TOKEN_LIMIT = 80_000
_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Estimate token count from character count (chars / 4, floor)."""
    return len(text) // _CHARS_PER_TOKEN


def load_content_pack_from_file(path: str) -> str:
    """Load content pack text from a file on disk.

    Supports .md, .txt, .pdf. Raises FileNotFoundError if missing,
    ValueError for unsupported formats.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    suffix = p.suffix.lower()
    if suffix in (".md", ".txt"):
        return p.read_text(encoding="utf-8")
    if suffix == ".pdf":
        return _extract_pdf_text(p)
    raise ValueError(
        f"Unsupported file format: '{suffix}'. Supported formats: .md, .txt, .pdf"
    )


def _extract_pdf_text(path: Path) -> str:
    """Extract plain text from a PDF file using pypdf."""
    import pypdf  # local import — optional dependency

    reader = pypdf.PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)
