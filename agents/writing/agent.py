#!/usr/bin/env python3
"""Writing Agent — produces a voice profile and newsletter draft for a creator."""

import sys
import json
from pathlib import Path

from agents.strategy.session import Session

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


def apply_size_guard(text: str, truncate: bool) -> str:
    """Enforce the 80k token limit.

    If text is within limit, returns it unchanged.
    If over limit and truncate=True, truncates to exactly TOKEN_LIMIT tokens.
    If over limit and truncate=False, raises ValueError.
    """
    token_count = estimate_tokens(text)
    if token_count <= TOKEN_LIMIT:
        return text
    if truncate:
        max_chars = TOKEN_LIMIT * _CHARS_PER_TOKEN
        return text[:max_chars]
    raise ValueError(
        f"Content pack exceeds {TOKEN_LIMIT:,} token limit "
        f"(estimated {token_count:,} tokens). Pass truncate=True to truncate."
    )


class WritingSession(Session):
    """Session subclass that uses writing-specific filenames to avoid
    collision with the strategy agent's session files."""

    def _load(self):
        # Override filenames before calling parent load
        self._session_file = self._dir / "writing-session.json"
        self._learnings_file = self._dir / "writing-learnings.json"
        super()._load()

    def save(self):
        # Ensure correct filenames are set before saving
        self._session_file = self._dir / "writing-session.json"
        self._learnings_file = self._dir / "writing-learnings.json"
        super().save()


def load_positioning_brief(creator_slug: str, base_dir: Path = None) -> dict:
    """Load the positioning brief produced by the strategy agent.

    Exits with a clear error if the file does not exist.
    """
    base = Path(base_dir).resolve() if base_dir else _project_root
    brief_path = base / ".agent" / creator_slug / "positioning-brief.json"
    if not brief_path.exists():
        print(
            f"\nERROR: Positioning brief not found at {brief_path}\n"
            f"Run the strategy agent first:\n"
            f"  python agents/strategy/agent.py --creator {creator_slug}\n"
        )
        sys.exit(1)
    return json.loads(brief_path.read_text(encoding="utf-8"))
