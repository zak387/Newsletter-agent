# Writing Agent Block 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `agents/writing/agent.py` — a CLI that runs the Tastemaker Protocol against a creator's content pack and produces a locked voice profile in both markdown and JSON.

**Architecture:** Single file agent (`agents/writing/agent.py`) following the same step-based state machine pattern as `agents/strategy/agent.py`. Imports `Session` from `agents.strategy.session` directly with a different session filename. Calls Claude API twice per run: once for the Tastemaker extraction (streaming, `claude-opus-4-6`), once for JSON extraction (`claude-sonnet-4-6`).

**Tech Stack:** Python 3, `anthropic` SDK (0.88+), `rich` (console/panels/prompts), `pypdf` (PDF text extraction)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `agents/writing/__init__.py` | Create | Package marker |
| `agents/writing/agent.py` | Create | Full CLI — step orchestration, all block 1 logic |
| `tests/writing/__init__.py` | Create | Package marker |
| `tests/writing/test_agent.py` | Create | Unit tests for pure functions in agent.py |

No other files are created or modified.

---

### Task 1: Install PDF dependency and create package structure

**Files:**
- Create: `agents/writing/__init__.py`
- Create: `tests/writing/__init__.py`

- [ ] **Step 1: Install pypdf**

```bash
pip install pypdf
```

Expected output: `Successfully installed pypdf-...`

- [ ] **Step 2: Verify install**

```bash
python -c "import pypdf; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Create package files**

Create `agents/writing/__init__.py` with empty content:
```python
```

Create `tests/writing/__init__.py` with empty content:
```python
```

- [ ] **Step 4: Commit**

```bash
git add agents/writing/__init__.py tests/writing/__init__.py
git commit -m "feat: scaffold writing agent package"
```

---

### Task 2: Content pack ingestion — pure functions

These are the pure functions that handle content pack loading. They have no side effects and are easy to test.

**Files:**
- Create: `agents/writing/agent.py` (initial version — ingestion functions only)
- Create: `tests/writing/test_agent.py`

- [ ] **Step 1: Write failing tests for `estimate_tokens` and `load_content_pack_from_file`**

Create `tests/writing/test_agent.py`:

```python
import sys
import pytest
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.writing.agent import estimate_tokens, load_content_pack_from_file


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0


def test_estimate_tokens_four_chars():
    # 4 chars = 1 token (chars / 4, floor)
    assert estimate_tokens("abcd") == 1


def test_estimate_tokens_rounds_down():
    assert estimate_tokens("abc") == 0


def test_estimate_tokens_large():
    text = "a" * 400
    assert estimate_tokens(text) == 100


def test_load_content_pack_from_file_txt(tmp_path):
    f = tmp_path / "pack.txt"
    f.write_text("hello world", encoding="utf-8")
    result = load_content_pack_from_file(str(f))
    assert result == "hello world"


def test_load_content_pack_from_file_md(tmp_path):
    f = tmp_path / "pack.md"
    f.write_text("# Title\ncontent", encoding="utf-8")
    result = load_content_pack_from_file(str(f))
    assert result == "# Title\ncontent"


def test_load_content_pack_from_file_missing():
    with pytest.raises(FileNotFoundError):
        load_content_pack_from_file("/nonexistent/path/pack.txt")


def test_load_content_pack_from_file_unsupported(tmp_path):
    f = tmp_path / "pack.docx"
    f.write_bytes(b"binary")
    with pytest.raises(ValueError, match="Unsupported file format"):
        load_content_pack_from_file(str(f))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/writing/test_agent.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'agents.writing.agent'`

- [ ] **Step 3: Create `agents/writing/agent.py` with ingestion functions**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/writing/test_agent.py -v
```

Expected: all 8 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat: writing agent content pack ingestion functions"
```

---

### Task 3: Size guard and content pack truncation

**Files:**
- Modify: `agents/writing/agent.py` — add `apply_size_guard`
- Modify: `tests/writing/test_agent.py` — add size guard tests

- [ ] **Step 1: Write failing tests**

Append to `tests/writing/test_agent.py`:

```python
from agents.writing.agent import apply_size_guard, TOKEN_LIMIT


def test_apply_size_guard_under_limit():
    text = "a" * (TOKEN_LIMIT * _CHARS_PER_TOKEN - 4)
    # Should return text unchanged, no truncation needed
    result = apply_size_guard(text, truncate=False)
    assert result == text


def test_apply_size_guard_over_limit_truncate():
    # 80001 tokens worth of text
    text = "a" * ((TOKEN_LIMIT + 1) * _CHARS_PER_TOKEN)
    result = apply_size_guard(text, truncate=True)
    assert estimate_tokens(result) == TOKEN_LIMIT


def test_apply_size_guard_over_limit_no_truncate():
    text = "a" * ((TOKEN_LIMIT + 1) * _CHARS_PER_TOKEN)
    with pytest.raises(ValueError, match="Content pack exceeds"):
        apply_size_guard(text, truncate=False)


_CHARS_PER_TOKEN = 4  # mirrors agent constant for tests
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/writing/test_agent.py::test_apply_size_guard_under_limit tests/writing/test_agent.py::test_apply_size_guard_over_limit_truncate tests/writing/test_agent.py::test_apply_size_guard_over_limit_no_truncate -v
```

Expected: `FAILED` — `ImportError: cannot import name 'apply_size_guard'`

- [ ] **Step 3: Add `apply_size_guard` to `agents/writing/agent.py`**

Add after the `_extract_pdf_text` function:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/writing/test_agent.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat: writing agent size guard"
```

---

### Task 4: Session setup and positioning brief loading

The `Session` class from `agents.strategy.session` is reused with a custom session filename (`writing-session.json`) and learnings filename (`writing-learnings.json`). This requires checking if `Session` supports custom filenames — it doesn't currently, so we use a thin subclass.

**Files:**
- Modify: `agents/writing/agent.py` — add `WritingSession`, `load_positioning_brief`
- Modify: `tests/writing/test_agent.py` — add tests

- [ ] **Step 1: Check `Session.__init__` signature**

Read `agents/strategy/session.py` lines 1-20. Confirm `Session` uses hardcoded filenames `session.json` and `learnings.json` — it does (from the spec exploration). We need a subclass.

- [ ] **Step 2: Write failing tests**

Append to `tests/writing/test_agent.py`:

```python
import json
from agents.writing.agent import WritingSession, load_positioning_brief


def test_writing_session_uses_different_filenames(tmp_path):
    session = WritingSession(creator_slug="test-creator", base_dir=tmp_path)
    session.set("block1_done", True)
    session.save()
    assert (tmp_path / ".agent" / "test-creator" / "writing-session.json").exists()
    assert (tmp_path / ".agent" / "test-creator" / "writing-learnings.json").exists()
    # Strategy agent files must NOT be created
    assert not (tmp_path / ".agent" / "test-creator" / "session.json").exists()


def test_load_positioning_brief_missing(tmp_path):
    with pytest.raises(SystemExit):
        load_positioning_brief("test-creator", base_dir=tmp_path)


def test_load_positioning_brief_found(tmp_path):
    brief_dir = tmp_path / ".agent" / "test-creator"
    brief_dir.mkdir(parents=True)
    brief = {"newsletter_name": ["The Clean Label"], "niche_umbrella": "Personal transformation > clean eating", "creator_archetype": {"primary": "Experimenter"}}
    (brief_dir / "positioning-brief.json").write_text(json.dumps(brief), encoding="utf-8")
    result = load_positioning_brief("test-creator", base_dir=tmp_path)
    assert result["newsletter_name"] == ["The Clean Label"]
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/writing/test_agent.py::test_writing_session_uses_different_filenames tests/writing/test_agent.py::test_load_positioning_brief_missing tests/writing/test_agent.py::test_load_positioning_brief_found -v
```

Expected: `FAILED` — import errors

- [ ] **Step 4: Add `WritingSession` and `load_positioning_brief` to `agents/writing/agent.py`**

Add these imports at the top of the file (after the existing sys.path block):

```python
import json
import sys
from pathlib import Path

from agents.strategy.session import Session
```

Then add after the existing functions:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/writing/test_agent.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat: writing agent session and positioning brief loading"
```

---

### Task 5: Tastemaker prompt and JSON extraction prompt constants

These are string constants embedded in the agent. No logic — just the prompts. No tests needed (strings are not logic).

**Files:**
- Modify: `agents/writing/agent.py` — add `TASTEMAKER_PROMPT` and `JSON_EXTRACTION_PROMPT`

- [ ] **Step 1: Add prompt constants to `agents/writing/agent.py`**

Add after the imports section, before the functions:

```python
TASTEMAKER_PROMPT = """\
You are a Voice Analyst. Your job is to study the creator's content pack and answer 20 targeted questions about how this creator thinks, writes, and sees the world — on their behalf. You are not interviewing anyone. You are reading the evidence and drawing conclusions from it.

<your_role>
You are not generating opinions. You are extracting documented patterns from the content provided. Every answer must be grounded in specific evidence from the content pack — direct quotes, observed patterns, or documented behaviours. If the content pack does not give you enough signal to answer a question reliably, say so explicitly and flag it as a gap. Do not guess. Do not invent.
</your_role>

<creator_context>
{creator_context}
</creator_context>

<content_pack>
{content_pack}
</content_pack>

<question_selection_logic>
You will answer exactly 20 questions drawn from the seven categories below. Select the 20 questions you can answer most reliably given the available content. Prioritise writing mechanics, voice and personality, and aesthetic crimes — these are the most directly useful for writing as this creator. Skip any question where the content pack provides insufficient evidence and flag the skip with a one-line note explaining what additional content would be needed to answer it.

The categories and their question pools are:

BELIEFS AND CONTRARIAN TAKES (select 3)
- What does this creator believe that others in their niche clearly do not?
- What conventional wisdom do they openly reject or push back against?
- What is a position they hold that would be considered a hot take in their space?

WRITING MECHANICS (select 5)
- How does this creator actually open a piece of writing — what is their default first move?
- What is their default sentence length and rhythm? Short and punchy, or longer and more complex?
- How do they close a piece? What is their sign-off pattern?
- What words or phrases do they return to repeatedly across their content?
- What words or phrases are completely absent from their writing that you would expect to find?

AESTHETIC CRIMES (select 3)
- Based on their writing choices, what stylistic patterns do they appear to actively avoid?
- What types of content or writing do they seem to find lazy or low-effort based on how they position their own work?
- What phrases or constructions are conspicuously absent from their vocabulary?

VOICE AND PERSONALITY (select 4)
- How do they use humour — and how often?
- What is their tone when they are being direct or making a strong claim?
- How do they handle complexity — do they simplify, embrace nuance, or both?
- What does their writing sound like when they are most energised or excited about a topic?

STRUCTURAL PREFERENCES (select 3)
- How do they organise ideas within a piece — linear argument, story-first, problem-solution, or something else?
- What is their relationship with lists, headers, and bullets — do they use them freely or avoid them?
- How long are their typical content pieces and how do they signal transitions between sections?

HARD NOS (select 1)
- Based on their content, what topics, tones, or approaches do they appear to never use?

RED FLAGS (select 1)
- Based on how they write and position themselves, what signals in other people's writing would likely make them distrust the content immediately?
</question_selection_logic>

<output_requirements>
Produce a complete voice profile document in the following structure. This is a reference document, not a summary. Preserve full depth in every answer.

---

# VOICE PROFILE: [Creator Name]

## Core Identity
[2-3 sentences capturing the essence of how this creator thinks and writes. The only summary in this document.]

---

## SECTION 1: BELIEFS AND CONTRARIAN TAKES

### Q1: [State the question]
[Full answer with specific evidence from the content pack. Quote directly where possible.]

### Q2: [State the question]
[Full answer with evidence]

### Q3: [State the question]
[Full answer with evidence]

---

## SECTION 2: WRITING MECHANICS

### Q4: [State the question]
[Full answer with evidence]

[Continue for all 5 questions in this category]

---

## SECTION 3: AESTHETIC CRIMES

### Q9: [State the question]
[Full answer with evidence]

[Continue for all 3 questions in this category]

---

## SECTION 4: VOICE AND PERSONALITY

### Q12: [State the question]
[Full answer with evidence]

[Continue for all 4 questions in this category]

---

## SECTION 5: STRUCTURAL PREFERENCES

### Q16: [State the question]
[Full answer with evidence]

[Continue for all 3 questions in this category]

---

## SECTION 6: HARD NOS

### Q19: [State the question]
[Full answer with evidence]

---

## SECTION 7: RED FLAGS

### Q20: [State the question]
[Full answer with evidence]

---

## FLAGGED GAPS
[List any questions skipped due to insufficient content pack evidence, with a one-line note on what additional content would close the gap]

---

## QUICK REFERENCE CARD

### Always:
[Specific patterns to follow — extracted directly from the answers above]

### Never:
[Specific things to avoid — extracted directly from the answers above]

### Signature Phrases and Structures:
[Actual examples pulled from the content pack — direct quotes or documented patterns]

### Voice Calibration:
[3-5 key quotes from the creator's own writing that best capture their tone. These are the sentences to hold in mind when writing as them.]

---

## HOW TO USE THIS DOCUMENT — ANTI-OVERFITTING GUIDE

This document captures this creator's voice patterns. It is not a checklist to follow rigidly.

### Spirit over letter
The goal is to inhabit this creator's sensibility, not to mechanically apply every pattern. A draft that uses three tendencies naturally will always beat a draft that forces in ten of them awkwardly.

### Frequency guidance
Each tendency is one of three types:
- HARD RULE — never violate. Rare. Usually found in the Never section.
- STRONG TENDENCY — do this 70-80% of the time. Breaking it occasionally is fine.
- LIGHT PREFERENCE — nice to have. Context determines when to apply.

When no label is attached, assume LIGHT PREFERENCE.

### Natural variation
Real writers are not perfectly consistent. Introduce natural variation:
- Do not start every draft the same way just because this creator has a signature opener
- Do not avoid a word forever just because they rarely use it — sometimes it is the right word
- Let the content dictate the structure, not the template

### The litmus test
Before finalising anything written as this creator, ask:

> "Does this sound like something they would actually write — or does it sound like an AI trying very hard to imitate them?"

If it feels forced, pull back. Less imitation, more inhabitation.

### What matters most
[To be filled by the agent after completing the 20 questions — the three most important things extracted from this specific creator's profile]

1. Their single most important belief about their subject matter
2. The one structural or stylistic pattern that most defines their voice
3. The one thing they never do that AI writers typically default to

---

## INSTRUCTIONS FOR CLAUDE — WRITING AS THIS CREATOR

When writing as [Creator Name], reference this document. Pay attention to:

1. The specific examples and quotes in the Signature Phrases section — use similar structures, not identical ones
2. The Never list — treat these as hard constraints
3. The beliefs documented — let them inform the angle and opinion in every draft
4. The sentence rhythm and length patterns — match these before anything else

This document is a source of truth, not a suggestion. Apply it with judgment, not mechanically.
</output_requirements>

Begin by reading the content pack and producing the complete voice profile.\
"""

JSON_EXTRACTION_PROMPT = """\
You are extracting structured data from a voice profile document.

Read the voice profile below and return ONLY a JSON object matching this exact schema. No explanation, no markdown fences.

Voice profile:
{voice_profile_md}

Return this JSON structure:
{{
  "creator_name": "string — from the VOICE PROFILE header",
  "core_identity": "string — from the Core Identity section",
  "beliefs": [
    {{"question": "string", "answer": "string"}}
  ],
  "writing_mechanics": [
    {{"question": "string", "answer": "string"}}
  ],
  "aesthetic_crimes": [
    {{"question": "string", "answer": "string"}}
  ],
  "voice_and_personality": [
    {{"question": "string", "answer": "string"}}
  ],
  "structural_preferences": [
    {{"question": "string", "answer": "string"}}
  ],
  "hard_nos": [
    {{"question": "string", "answer": "string"}}
  ],
  "red_flags": [
    {{"question": "string", "answer": "string"}}
  ],
  "flagged_gaps": ["string — one per flagged gap"],
  "quick_reference": {{
    "always": ["string"],
    "never": ["string"],
    "signature_phrases": ["string"],
    "voice_calibration_quotes": ["string"]
  }},
  "what_matters_most": ["belief string", "style pattern string", "never-do string"]
}}

what_matters_most must have exactly 3 items in this order:
1. The creator's single most important belief about their subject matter
2. The one structural or stylistic pattern that most defines their voice
3. The one thing they never do that AI writers typically default to
"""
```

- [ ] **Step 2: Verify file is syntactically valid**

```bash
python -c "import agents.writing.agent; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add agents/writing/agent.py
git commit -m "feat: writing agent Tastemaker and JSON extraction prompts"
```

---

### Task 6: Tastemaker extraction and JSON extraction functions

**Files:**
- Modify: `agents/writing/agent.py` — add `run_tastemaker`, `extract_voice_profile_json`
- Modify: `tests/writing/test_agent.py` — add tests for JSON parse error path

These functions call the Claude API. The happy-path API calls are not unit-tested (they make real network calls). Only the error-handling branch (malformed JSON) is tested via a mock.

- [ ] **Step 1: Write failing test for malformed JSON handling**

Append to `tests/writing/test_agent.py`:

```python
from unittest.mock import patch, MagicMock
from agents.writing.agent import extract_voice_profile_json


def test_extract_voice_profile_json_malformed_raises(capsys):
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(text="not valid json {{{{")]

    with pytest.raises(RuntimeError, match="JSON parse error"):
        extract_voice_profile_json("some profile text", client=mock_client)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/writing/test_agent.py::test_extract_voice_profile_json_malformed_raises -v
```

Expected: `FAILED` — `ImportError: cannot import name 'extract_voice_profile_json'`

- [ ] **Step 3: Add `run_tastemaker` and `extract_voice_profile_json` to `agents/writing/agent.py`**

Add these imports at the top (after existing imports):

```python
import re
import anthropic as _anthropic
```

Add these functions after the prompt constants:

```python
def run_tastemaker(content_pack: str, brief: dict, client=None) -> str:
    """Run the Tastemaker Protocol prompt and return the full voice profile markdown.

    Streams output to console so the operator can watch progress.
    Returns the complete accumulated text.
    """
    if client is None:
        client = _anthropic.Anthropic()

    creator_context = (
        f"Archetype: {brief.get('creator_archetype', {}).get('primary', 'Unknown')}\n"
        f"Niche: {brief.get('niche_umbrella', 'Unknown')}\n"
        f"Target reader: {brief.get('target_reader', 'Unknown')}"
    )

    prompt = TASTEMAKER_PROMPT.format(
        creator_context=creator_context,
        content_pack=content_pack,
    )

    accumulated = []
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            accumulated.append(text)

    print()  # newline after streaming completes
    return "".join(accumulated)


def extract_voice_profile_json(voice_profile_md: str, client=None) -> dict:
    """Extract structured JSON from the voice profile markdown.

    Uses a lightweight claude-sonnet-4-6 call. Raises RuntimeError if
    the model returns malformed JSON.
    """
    if client is None:
        client = _anthropic.Anthropic()

    prompt = JSON_EXTRACTION_PROMPT.format(voice_profile_md=voice_profile_md)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"JSON parse error extracting voice profile structure: {e}\n\nRaw output:\n{raw[:500]}"
        ) from e
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/writing/test_agent.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat: writing agent Tastemaker and JSON extraction functions"
```

---

### Task 7: Interactive CLI steps (ingestion, review loop, output writing)

These are the interactive orchestration functions. They use `rich` for console output and `Prompt.ask` for operator input — not unit-testable without heavy mocking. They are tested by running the agent manually at the end of this task.

**Files:**
- Modify: `agents/writing/agent.py` — add `step_ingest_content_pack`, `step_review_loop`, `step_write_outputs`, `main`

- [ ] **Step 1: Add interactive steps and `main` to `agents/writing/agent.py`**

Add this import at the top:

```python
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()


def ask(prompt: str) -> str:
    """Pause and collect operator input."""
    return Prompt.ask(f"\n[bold cyan]{prompt}[/bold cyan]")
```

Then add the step functions:

```python
def step_ingest_content_pack() -> str:
    """Interactive step: operator chooses file or paste, returns content pack text."""
    console.print(Panel("[bold]Content Pack Ingestion[/bold]", style="blue"))
    console.print("How would you like to provide the content pack?")
    console.print("  [bold]1[/bold] — File path (.md, .txt, or .pdf)")
    console.print("  [bold]2[/bold] — Paste directly into the terminal")

    while True:
        choice = ask("Enter 1 or 2").strip()

        if choice == "1":
            file_path = ask("Enter the full file path").strip()
            try:
                raw = load_content_pack_from_file(file_path)
                break
            except FileNotFoundError as e:
                console.print(f"[red]{e}[/red] — try again.")
            except ValueError as e:
                console.print(f"[red]{e}[/red] — try again.")

        elif choice == "2":
            console.print(
                "\nPaste your content pack below. "
                "When done, type [bold]END[/bold] on its own line and press Enter:"
            )
            lines = []
            while True:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            raw = "\n".join(lines)
            break

        else:
            console.print("[red]Please enter 1 or 2.[/red]")

    estimated = estimate_tokens(raw)
    console.print(f"\n[dim]Content pack loaded — estimated {estimated:,} tokens.[/dim]")

    if estimated > TOKEN_LIMIT:
        console.print(
            f"\n[yellow]WARNING: Content pack is ~{estimated:,} tokens, "
            f"which exceeds the {TOKEN_LIMIT:,} token limit.[/yellow]"
        )
        console.print("Options:")
        console.print("  [bold]t[/bold] — Truncate to 80,000 tokens (from the start)")
        console.print("  [bold]a[/bold] — Abort")
        while True:
            action = ask("Enter t or a").strip().lower()
            if action == "t":
                raw = apply_size_guard(raw, truncate=True)
                console.print(f"[dim]Truncated to {estimate_tokens(raw):,} tokens.[/dim]")
                break
            elif action == "a":
                console.print("Aborted.")
                sys.exit(0)
            else:
                console.print("[red]Please enter t or a.[/red]")

    return raw


def step_review_loop(
    session: WritingSession,
    content_pack: str,
    brief: dict,
) -> str:
    """Run the Tastemaker prompt and present a review loop. Returns the locked voice profile markdown."""
    client = _anthropic.Anthropic()
    round_number = 0

    while True:
        round_number += 1
        console.print(f"\n[dim]Running Tastemaker Protocol (round {round_number})...[/dim]\n")

        learnings_block = ""
        if session.learnings:
            learnings_block = (
                "\n\nPrevious feedback to incorporate:\n"
                + "\n".join(f"- {l.get('feedback', '')}" for l in session.learnings)
            )

        pack_with_learnings = content_pack + learnings_block
        voice_profile_md = run_tastemaker(pack_with_learnings, brief, client=client)

        console.print(Panel(voice_profile_md, title=f"Voice Profile (Round {round_number})", style="white"))

        feedback = ask('Review the voice profile above. Type feedback to regenerate, or "save it" to finalise')

        if feedback.strip().lower() in ("save it", "save", "done", "lock it", "lock"):
            return voice_profile_md

        session.append_learning({"round": round_number, "feedback": feedback})
        session.save()


def step_write_outputs(
    creator_slug: str,
    voice_profile_md: str,
    base_dir: Path = None,
) -> None:
    """Write voice-profile.md and voice-profile.json to their canonical locations."""
    base = Path(base_dir).resolve() if base_dir else _project_root
    client = _anthropic.Anthropic()

    # Operator-facing markdown
    briefs_dir = base / "briefs" / creator_slug
    briefs_dir.mkdir(parents=True, exist_ok=True)
    md_path = briefs_dir / "voice-profile.md"
    md_path.write_text(voice_profile_md, encoding="utf-8")
    console.print(f"\n[dim]Markdown written: {md_path}[/dim]")

    # Canonical JSON
    console.print("[dim]Extracting structured JSON...[/dim]")
    try:
        profile_json = extract_voice_profile_json(voice_profile_md, client=client)
    except RuntimeError as e:
        console.print(f"\n[bold red]JSON extraction failed:[/bold red]\n{e}")
        console.print("The markdown voice profile has been saved. Re-run to retry JSON extraction.")
        return

    agent_dir = base / ".agent" / creator_slug
    agent_dir.mkdir(parents=True, exist_ok=True)
    json_path = agent_dir / "voice-profile.json"
    json_path.write_text(json.dumps(profile_json, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"[dim]JSON written: {json_path}[/dim]")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Writing Agent")
    parser.add_argument("--creator", required=True, help="Creator slug (e.g. kyle-cleankitchennutrition)")
    args = parser.parse_args()

    creator_slug = args.creator
    session = WritingSession(creator_slug=creator_slug)

    console.print(Panel(f"[bold green]Writing Agent[/bold green]\nCreator: {creator_slug}", style="green"))

    # Load positioning brief — exits with error if missing
    brief = load_positioning_brief(creator_slug)
    names = brief.get("newsletter_name") or ["—"]
    niche = brief.get("niche_umbrella") or "—"
    archetype = (brief.get("creator_archetype") or {}).get("primary") or "—"
    console.print(f"[dim]Brief loaded — Name: {names[0]} | Niche: {niche} | Archetype: {archetype}[/dim]")

    # Block 1 — Voice extraction
    if session.get("block1_done"):
        console.print("[dim]Block 1 already complete — voice profile already locked.[/dim]")
    else:
        content_pack = step_ingest_content_pack()
        voice_profile_md = step_review_loop(session, content_pack, brief)
        step_write_outputs(creator_slug, voice_profile_md)

        session.set("block1_done", True)
        session.save()

        console.print(f"\n[bold green]Block 1 complete. Voice profile locked.[/bold green]")
        console.print(f"  briefs/{creator_slug}/voice-profile.md")
        console.print(f"  .agent/{creator_slug}/voice-profile.json")

    # Block 2 stub
    console.print("\n[dim]Block 2 (format selection) — coming soon.[/dim]")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run existing tests to confirm nothing broke**

```bash
pytest tests/writing/test_agent.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 3: Smoke test the agent CLI (dry run — check it starts and shows the brief)**

First ensure a creator with a positioning brief exists (the `kyle-cleankitchennutrition` brief is already present from the strategy agent run):

```bash
python agents/writing/agent.py --creator kyle-cleankitchennutrition
```

Expected: Agent starts, prints the green header panel, prints the brief summary line, then asks for content pack input. Press Ctrl+C to exit — this is just confirming startup works.

- [ ] **Step 4: Smoke test missing brief error**

```bash
python agents/writing/agent.py --creator nonexistent-creator
```

Expected: prints `ERROR: Positioning brief not found at ...` and exits without a traceback.

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat: writing agent Block 1 complete — Tastemaker Protocol CLI"
```

---

### Task 8: Run full test suite

**Files:** None modified

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v
```

Expected: all tests `PASSED`. No failures in strategy agent tests either.

- [ ] **Step 2: If any strategy agent tests fail, investigate before proceeding**

Strategy agent tests live in `tests/strategy/`. They should be unaffected by the writing agent additions. If they fail, read the error — do not proceed until they pass.

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Separate CLI (`agents/writing/agent.py`) | Task 7 |
| Read positioning brief, exit if missing | Task 4 |
| File input (.md, .txt, .pdf) | Task 2 |
| Direct paste input with END sentinel | Task 7 |
| Size guard — warn, truncate or abort | Tasks 3 + 7 |
| Run Tastemaker prompt with claude-opus-4-6, streaming | Task 6 |
| Positioning brief context injected into prompt | Task 6 |
| Review loop with feedback stored to writing-learnings.json | Task 7 |
| Write `briefs/<slug>/voice-profile.md` | Task 7 |
| Write `.agent/<slug>/voice-profile.json` | Task 7 |
| JSON extracted via second Claude call, not regex | Task 6 |
| Session state in `writing-session.json` | Task 4 |
| Block 1 resumable (skip if `block1_done`) | Task 7 |
| Block 2 stub | Task 7 |
| Malformed JSON error surfaces to operator | Task 6 |

All requirements covered.
