# Writing Agent Blocks 2 & 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the writing agent CLI with Block 2 (one-time format lock) and Block 3 (per-issue draft generation using topic, subject line picker, auto-suggested CTA, and voice-driven draft).

**Architecture:** All changes live in `agents/writing/agent.py`. Block 2 is a single persisted choice. Block 3 is a re-runnable orchestration of four Claude calls (subject lines → CTA suggest → draft → review loop). CTAs come from an operator-maintained `briefs/<slug>/ctas.md`. Drafts are written to `briefs/<slug>/drafts/<date>-<slug>.md` with YAML frontmatter.

**Tech Stack:** Python 3, `anthropic` SDK (already wired), `rich` (console), `pytest` + `unittest.mock`.

**Spec:** [docs/superpowers/specs/2026-04-08-writing-agent-blocks-2-3-design.md](../specs/2026-04-08-writing-agent-blocks-2-3-design.md)

---

## File Structure

- **Modify:** `agents/writing/agent.py` — all new constants and functions go here, wired into existing `main()`.
- **Modify:** `tests/writing/test_agent.py` — append new tests.
- **Create at runtime (operator writes):** `briefs/<slug>/ctas.md`.
- **Create at runtime (agent writes):** `.agent/<slug>/block2.json`, `briefs/<slug>/drafts/*.md`.

No new source files. The writing agent is intentionally kept as a single module to match the existing pattern.

---

## Task 1: Module-level constants — format structures and labels

**Files:**
- Modify: `agents/writing/agent.py` (append constants near top, after existing `JSON_EXTRACTION_PROMPT`)
- Test: `tests/writing/test_agent.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/writing/test_agent.py`:

```python
from agents.writing.agent import (
    FORMAT_STRUCTURES,
    FORMAT_LABELS,
    PERSONAL_LETTER_STRUCTURE,
    ROUNDUP_STRUCTURE,
    CURATION_STRUCTURE,
)


def test_format_structures_has_three_entries():
    assert set(FORMAT_STRUCTURES.keys()) == {"personal_letter", "roundup", "curation"}


def test_format_labels_human_readable():
    assert FORMAT_LABELS["personal_letter"] == "Personal Letter"
    assert FORMAT_LABELS["roundup"] == "Roundup"
    assert FORMAT_LABELS["curation"] == "Curation"


def test_format_structures_are_nonempty_strings():
    for slug, struct in FORMAT_STRUCTURES.items():
        assert isinstance(struct, str)
        assert len(struct) > 200, f"{slug} structure looks too short"


def test_personal_letter_structure_mentions_key_sections():
    assert "The Moment" in PERSONAL_LETTER_STRUCTURE
    assert "How to Apply This" in PERSONAL_LETTER_STRUCTURE


def test_roundup_structure_mentions_key_sections():
    assert "Quick Hits" in ROUNDUP_STRUCTURE
    assert "TL;DR" in ROUNDUP_STRUCTURE


def test_curation_structure_mentions_key_sections():
    assert "3 Ideas" in CURATION_STRUCTURE
    assert "2 Quotes" in CURATION_STRUCTURE
    assert "1 Question" in CURATION_STRUCTURE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/writing/test_agent.py -v -k "format_structures or format_labels or personal_letter_structure or roundup_structure or curation_structure"`
Expected: FAIL with `ImportError` on `FORMAT_STRUCTURES`.

- [ ] **Step 3: Add constants to `agents/writing/agent.py`**

Insert after the existing `JSON_EXTRACTION_PROMPT` constant (around line 274) and before `console = Console()`:

```python
PERSONAL_LETTER_STRUCTURE = """\
## [ISSUE TITLE]

Date: [DATE]

Subject Line: [SUBJECT LINE]

---

## The Moment
[Personal story, observation, or trigger]

---

## The Problem
[Describe the common challenge your reader faces]

---

## Why Most Advice Fails
- [Mistake #1]
- [Mistake #2]

[Explain why these don't work]

---

## A Better Way
[Your core idea, mindset shift, or framework]

---

## How to Apply This
1. [Action step]
2. [Action step]
3. [Action step]

---

## Key Takeaway
[One sharp insight worth remembering]

---

## Optional CTA
[Course / coaching / product / sponsor]

—

[Your Name]

STRUCTURE RULES:
- Open with a personal moment or observation
- Clearly name a problem or challenge the reader relates to
- Explain why common advice or solutions fail
- Introduce a better approach or mindset shift
- Give 3 concrete, actionable steps
- End with a sharp takeaway
- Include a P.S. with a soft secondary touch on the CTA or a related asset
- No hype, no clichés, no generic motivational language
- Write in first person
"""

ROUNDUP_STRUCTURE = """\
## [ISSUE TITLE]

Date: [DATE]

Subject Line: [SUBJECT LINE]

---

## Opening
[2–3 lines setting context, mood, or why today's issue matters]

---

## Main Stories

### Story #1
- **Headline:** [Headline + link]
- **TL;DR:** [1-sentence summary]

**Key takeaways**
- [takeaway]
- [takeaway]
- [takeaway]

**My take**
[Your opinion / why it matters]

---

### Story #2
- **Headline:** [Headline + link]
- **TL;DR:** [1-sentence summary]

**Key takeaways**
- [takeaway]
- [takeaway]
- [takeaway]

**My take**
[Your opinion]

---

### Story #3
- **Headline:** [Headline + link]
- **TL;DR:** [1-sentence summary]

**Key takeaways**
- [takeaway]
- [takeaway]
- [takeaway]

**My take**
[Your opinion]

---

## Sponsor / Promo
[Ad copy or internal CTA]

---

## Quick Hits
- [Link] — [1-line context]
- [Link] — [1-line context]
- [Link] — [1-line context]

---

## Sign-off
[Closing line]

— [Your Name]

P.S. [Secondary CTA touch or related asset]

STRUCTURE RULES:
- Short personal opening (2–3 lines max)
- For each main story: headline, 1-sentence TL;DR, 3 key takeaways, editor's take
- Sponsor / CTA placed immediately after the main stories
- Quick Hits section with 3–5 additional links, one-line context each
- End with a short sign-off and a P.S.
- No emojis, no news-article tone, clarity over cleverness
"""

CURATION_STRUCTURE = """\
## [ISSUE TITLE]

Date: [DATE]

Subject Line: [SUBJECT LINE]

---

## 3 Ideas
1. [Idea]
2. [Idea]
3. [Idea]

---

## 2 Quotes

> "[Quote]"
> — [Source]

> "[Quote]"
> — [Source]

---

## 1 Question
[Reflective question for the reader]

—

[Your Name]

P.S. [Secondary CTA touch or related asset]

STRUCTURE RULES:
- 3 original ideas (1–2 sentences each)
- 2 quotes from others, with attribution, thematically linked to the ideas
- 1 thoughtful question for reflection
- End with a P.S.
- No long explanations
- Ideas must be original, not summaries
"""

FORMAT_STRUCTURES = {
    "personal_letter": PERSONAL_LETTER_STRUCTURE,
    "roundup": ROUNDUP_STRUCTURE,
    "curation": CURATION_STRUCTURE,
}

FORMAT_LABELS = {
    "personal_letter": "Personal Letter",
    "roundup": "Roundup",
    "curation": "Curation",
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/writing/test_agent.py -v -k "format_structures or format_labels or personal_letter_structure or roundup_structure or curation_structure"`
Expected: PASS on all 5 tests.

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat(writing): add format structure constants for Block 2/3"
```

---

## Task 2: `slugify_subject` helper

**Files:**
- Modify: `agents/writing/agent.py`
- Test: `tests/writing/test_agent.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/writing/test_agent.py`:

```python
from agents.writing.agent import slugify_subject


def test_slugify_subject_basic():
    assert slugify_subject("Hello World") == "hello-world"


def test_slugify_subject_strips_punctuation():
    assert slugify_subject("I can't believe it!") == "i-cant-believe-it"


def test_slugify_subject_collapses_spaces():
    assert slugify_subject("too    many   spaces") == "too-many-spaces"


def test_slugify_subject_truncates_long():
    long = "word " * 50
    result = slugify_subject(long)
    assert len(result) <= 60


def test_slugify_subject_truncates_on_word_boundary():
    long = "alphabetical " * 20
    result = slugify_subject(long)
    # Should not end with a half-cut word or trailing hyphen
    assert not result.endswith("-")


def test_slugify_subject_empty():
    assert slugify_subject("") == "untitled"


def test_slugify_subject_only_punctuation():
    assert slugify_subject("!!!???") == "untitled"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/writing/test_agent.py -v -k "slugify"`
Expected: FAIL with ImportError on `slugify_subject`.

- [ ] **Step 3: Implement `slugify_subject`**

Add to `agents/writing/agent.py` (after the format constants, before `console = Console()`):

```python
def slugify_subject(subject: str, max_len: int = 60) -> str:
    """Convert a subject line into a filesystem-safe slug.

    Lowercases, strips punctuation (apostrophes removed, other punct → space),
    collapses whitespace to single hyphens, truncates to max_len on a word
    boundary. Returns "untitled" for empty / all-punctuation input.
    """
    if not subject:
        return "untitled"
    # Remove apostrophes entirely so "can't" → "cant"
    s = subject.lower().replace("'", "").replace("\u2019", "")
    # Replace any non-alphanumeric with a space
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = s.strip()
    if not s:
        return "untitled"
    # Truncate on word boundary
    if len(s) > max_len:
        s = s[:max_len].rsplit(" ", 1)[0]
    return s.replace(" ", "-")
```

(`re` is already imported at the top of the file.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/writing/test_agent.py -v -k "slugify"`
Expected: PASS on all 7 tests.

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat(writing): add slugify_subject helper"
```

---

## Task 3: Block 2 storage — `load_block2_data` / `save_block2_data`

**Files:**
- Modify: `agents/writing/agent.py`
- Test: `tests/writing/test_agent.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/writing/test_agent.py`:

```python
from agents.writing.agent import load_block2_data, save_block2_data


def test_load_block2_data_missing_returns_none(tmp_path):
    assert load_block2_data("acme", base_dir=tmp_path) is None


def test_save_and_load_block2_data_roundtrip(tmp_path):
    save_block2_data("acme", {"format": "personal_letter"}, base_dir=tmp_path)
    loaded = load_block2_data("acme", base_dir=tmp_path)
    assert loaded == {"format": "personal_letter"}


def test_save_block2_data_creates_directory(tmp_path):
    save_block2_data("newcreator", {"format": "roundup"}, base_dir=tmp_path)
    assert (tmp_path / ".agent" / "newcreator" / "block2.json").exists()


def test_load_block2_data_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError):
        load_block2_data("../evil", base_dir=tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/writing/test_agent.py -v -k "block2_data"`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement the functions**

Add to `agents/writing/agent.py` (after `load_strategy_brief`):

```python
def _validate_creator_slug(creator_slug: str) -> None:
    if "/" in creator_slug or "\\" in creator_slug or ".." in creator_slug:
        raise ValueError(f"Invalid creator_slug: {creator_slug!r}")


def load_block2_data(creator_slug: str, base_dir: Path = None) -> dict | None:
    """Load the locked Block 2 format selection for a creator.

    Returns None if the file does not exist.
    """
    _validate_creator_slug(creator_slug)
    base = Path(base_dir).resolve() if base_dir else _project_root
    path = base / ".agent" / creator_slug / "block2.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_block2_data(creator_slug: str, data: dict, base_dir: Path = None) -> None:
    """Persist Block 2 data to .agent/<slug>/block2.json."""
    _validate_creator_slug(creator_slug)
    base = Path(base_dir).resolve() if base_dir else _project_root
    agent_dir = base / ".agent" / creator_slug
    agent_dir.mkdir(parents=True, exist_ok=True)
    path = agent_dir / "block2.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/writing/test_agent.py -v -k "block2_data"`
Expected: PASS on all 4 tests.

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat(writing): add block2 data load/save"
```

---

## Task 4: Voice profile JSON loader

**Files:**
- Modify: `agents/writing/agent.py`
- Test: `tests/writing/test_agent.py`

- [ ] **Step 1: Write the failing test**

```python
from agents.writing.agent import load_voice_profile_json


def test_load_voice_profile_json_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="voice-profile.json"):
        load_voice_profile_json("acme", base_dir=tmp_path)


def test_load_voice_profile_json_reads_file(tmp_path):
    agent_dir = tmp_path / ".agent" / "acme"
    agent_dir.mkdir(parents=True)
    (agent_dir / "voice-profile.json").write_text(
        '{"creator_name": "Acme", "core_identity": "test"}',
        encoding="utf-8",
    )
    result = load_voice_profile_json("acme", base_dir=tmp_path)
    assert result["creator_name"] == "Acme"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/writing/test_agent.py -v -k "load_voice_profile_json"`
Expected: FAIL ImportError.

- [ ] **Step 3: Implement**

Add to `agents/writing/agent.py` (after `save_block2_data`):

```python
def load_voice_profile_json(creator_slug: str, base_dir: Path = None) -> dict:
    """Load the locked voice profile JSON from Block 1.

    Raises FileNotFoundError if missing, with a message telling the operator
    to re-run Block 1.
    """
    _validate_creator_slug(creator_slug)
    base = Path(base_dir).resolve() if base_dir else _project_root
    path = base / ".agent" / creator_slug / "voice-profile.json"
    if not path.exists():
        raise FileNotFoundError(
            f"voice-profile.json not found at {path}. "
            f"Run Block 1 first: python agents/writing/agent.py --creator {creator_slug}"
        )
    return json.loads(path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/writing/test_agent.py -v -k "load_voice_profile_json"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat(writing): add voice profile JSON loader"
```

---

## Task 5: CTA file loader and parser

**Files:**
- Modify: `agents/writing/agent.py`
- Test: `tests/writing/test_agent.py`

- [ ] **Step 1: Write the failing test**

```python
from agents.writing.agent import load_ctas_md, parse_ctas_md


CTAS_SAMPLE = """# CTAs — Acme

## Offer
- **Label:** Course launch Q2
- **Copy:** Join 500+ creators in the course.
- **Link:** https://example.com/course

## Community
- **Label:** The Lab membership
- **Copy:** Monthly community for creators.
- **Link:** https://example.com/lab

## Content
- **Label:** Latest podcast
- **Copy:** New episode on audience trust.
- **Link:** https://example.com/podcast
"""


def test_load_ctas_md_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="ctas.md"):
        load_ctas_md("acme", base_dir=tmp_path)


def test_load_ctas_md_reads_file(tmp_path):
    briefs = tmp_path / "briefs" / "acme"
    briefs.mkdir(parents=True)
    (briefs / "ctas.md").write_text(CTAS_SAMPLE, encoding="utf-8")
    result = load_ctas_md("acme", base_dir=tmp_path)
    assert "Course launch Q2" in result


def test_parse_ctas_md_extracts_three_entries():
    entries = parse_ctas_md(CTAS_SAMPLE)
    assert len(entries) == 3
    labels = [e["label"] for e in entries]
    assert "Course launch Q2" in labels
    assert "The Lab membership" in labels
    assert "Latest podcast" in labels


def test_parse_ctas_md_attaches_type_from_heading():
    entries = parse_ctas_md(CTAS_SAMPLE)
    by_label = {e["label"]: e for e in entries}
    assert by_label["Course launch Q2"]["type"] == "offer"
    assert by_label["The Lab membership"]["type"] == "community"
    assert by_label["Latest podcast"]["type"] == "content"


def test_parse_ctas_md_extracts_copy_and_link():
    entries = parse_ctas_md(CTAS_SAMPLE)
    offer = [e for e in entries if e["label"] == "Course launch Q2"][0]
    assert offer["copy"] == "Join 500+ creators in the course."
    assert offer["link"] == "https://example.com/course"


def test_parse_ctas_md_empty_raises():
    with pytest.raises(ValueError, match="No CTAs parsed"):
        parse_ctas_md("# CTAs\n\nNothing here.")


def test_parse_ctas_md_tolerates_extra_whitespace():
    messy = """# CTAs

##   Offer

-   **Label:**   Messy Label
-   **Copy:**   Some copy here
-   **Link:**   https://example.com
"""
    entries = parse_ctas_md(messy)
    assert len(entries) == 1
    assert entries[0]["label"] == "Messy Label"
    assert entries[0]["type"] == "offer"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/writing/test_agent.py -v -k "ctas_md"`
Expected: FAIL ImportError.

- [ ] **Step 3: Implement loader and parser**

Add to `agents/writing/agent.py` (after `load_voice_profile_json`):

```python
_VALID_CTA_TYPES = {"intro", "offer", "assessment", "community", "content"}


def load_ctas_md(creator_slug: str, base_dir: Path = None) -> str:
    """Load the creator's ctas.md file.

    Raises FileNotFoundError with setup instructions if missing.
    """
    _validate_creator_slug(creator_slug)
    base = Path(base_dir).resolve() if base_dir else _project_root
    path = base / "briefs" / creator_slug / "ctas.md"
    if not path.exists():
        raise FileNotFoundError(
            f"ctas.md not found at {path}.\n\n"
            f"Create this file with CTA entries grouped by type. Example:\n\n"
            f"# CTAs — {creator_slug}\n\n"
            f"## Offer\n"
            f"- **Label:** My course\n"
            f"- **Copy:** Short pitch text.\n"
            f"- **Link:** https://example.com\n"
        )
    return path.read_text(encoding="utf-8")


def parse_ctas_md(ctas_md: str) -> list[dict]:
    """Parse a ctas.md file into a list of CTA dicts.

    Each dict has keys: type, label, copy, link.
    Headings (## Offer, ## Community, ...) set the type for the entries that
    follow. Each entry is a bullet block with Label / Copy / Link lines.
    Raises ValueError if no entries are parsed.
    """
    entries: list[dict] = []
    current_type: str | None = None
    current_entry: dict | None = None

    heading_re = re.compile(r"^\s*##\s+(\w+)\s*$")
    field_re = re.compile(r"^\s*-?\s*\*\*(Label|Copy|Link):\*\*\s*(.+?)\s*$")

    def flush():
        nonlocal current_entry
        if current_entry and current_entry.get("label"):
            # Ensure all fields present, default missing to ""
            current_entry.setdefault("copy", "")
            current_entry.setdefault("link", "")
            entries.append(current_entry)
        current_entry = None

    for line in ctas_md.splitlines():
        heading_match = heading_re.match(line)
        if heading_match:
            flush()
            candidate = heading_match.group(1).lower()
            current_type = candidate if candidate in _VALID_CTA_TYPES else None
            continue

        field_match = field_re.match(line)
        if field_match and current_type:
            field_name = field_match.group(1).lower()
            value = field_match.group(2).strip()
            if field_name == "label":
                # New entry starts on a Label line
                flush()
                current_entry = {"type": current_type, "label": value}
            elif current_entry is not None:
                current_entry[field_name] = value

    flush()

    if not entries:
        raise ValueError(
            "No CTAs parsed from ctas.md. "
            "Expected '## <Type>' headings followed by bullet entries with "
            "**Label:**, **Copy:**, and **Link:** fields."
        )
    return entries
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/writing/test_agent.py -v -k "ctas_md"`
Expected: PASS on all 7 tests.

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat(writing): add ctas.md loader and parser"
```

---

## Task 6: Newsletter reference loader

**Files:**
- Modify: `agents/writing/agent.py`
- Test: `tests/writing/test_agent.py`

- [ ] **Step 1: Write the failing test**

```python
from agents.writing.agent import load_newsletter_reference


def test_load_newsletter_reference_returns_contents(tmp_path):
    (tmp_path / "newsletter-reference.md").write_text(
        "# Reference\nSome content.", encoding="utf-8"
    )
    result = load_newsletter_reference(base_dir=tmp_path)
    assert "Some content." in result


def test_load_newsletter_reference_missing_returns_empty(tmp_path):
    # Missing file should return empty string (non-fatal)
    result = load_newsletter_reference(base_dir=tmp_path)
    assert result == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/writing/test_agent.py -v -k "newsletter_reference"`
Expected: FAIL ImportError.

- [ ] **Step 3: Implement**

Add to `agents/writing/agent.py` (after `parse_ctas_md`):

```python
def load_newsletter_reference(base_dir: Path = None) -> str:
    """Load newsletter-reference.md from project root.

    Returns empty string if missing — the reference is inspiration only,
    not required for drafting.
    """
    base = Path(base_dir).resolve() if base_dir else _project_root
    path = base / "newsletter-reference.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/writing/test_agent.py -v -k "newsletter_reference"`
Expected: PASS on both tests.

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat(writing): add newsletter reference loader"
```

---

## Task 7: `step_block2` interactive format selection

**Files:**
- Modify: `agents/writing/agent.py`
- Test: `tests/writing/test_agent.py`

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import patch
from agents.writing.agent import step_block2


def test_step_block2_saves_personal_letter(tmp_path):
    with patch("agents.writing.agent.ask", return_value="1"):
        result = step_block2("acme", base_dir=tmp_path)
    assert result == {"format": "personal_letter"}
    saved = json.loads(
        (tmp_path / ".agent" / "acme" / "block2.json").read_text(encoding="utf-8")
    )
    assert saved == {"format": "personal_letter"}


def test_step_block2_saves_roundup(tmp_path):
    with patch("agents.writing.agent.ask", return_value="2"):
        result = step_block2("acme", base_dir=tmp_path)
    assert result == {"format": "roundup"}


def test_step_block2_saves_curation(tmp_path):
    with patch("agents.writing.agent.ask", return_value="3"):
        result = step_block2("acme", base_dir=tmp_path)
    assert result == {"format": "curation"}


def test_step_block2_rejects_invalid_then_accepts(tmp_path):
    # First call returns invalid, second returns valid
    with patch("agents.writing.agent.ask", side_effect=["9", "bad", "1"]):
        result = step_block2("acme", base_dir=tmp_path)
    assert result == {"format": "personal_letter"}
```

Ensure `import json` is present at the top of the test file (it already is via previous tasks; add if not).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/writing/test_agent.py -v -k "step_block2"`
Expected: FAIL ImportError.

- [ ] **Step 3: Implement `step_block2`**

Add to `agents/writing/agent.py` (before `step_ingest_content_pack` or grouped with other `step_` functions):

```python
def step_block2(creator_slug: str, base_dir: Path = None) -> dict:
    """Interactive format selection. Persists and returns block2 data."""
    console.print(Panel("[bold]Block 2 — Format Selection[/bold]", style="blue"))
    console.print("Select the newsletter format for this creator:")
    console.print("  [bold]1[/bold] — Personal Letter")
    console.print("  [bold]2[/bold] — Roundup")
    console.print("  [bold]3[/bold] — Curation")

    choice_to_format = {
        "1": "personal_letter",
        "2": "roundup",
        "3": "curation",
    }

    while True:
        choice = ask("Enter 1, 2, or 3").strip()
        if choice in choice_to_format:
            format_slug = choice_to_format[choice]
            break
        console.print("[red]Please enter 1, 2, or 3.[/red]")

    data = {"format": format_slug}
    save_block2_data(creator_slug, data, base_dir=base_dir)
    console.print(
        f"\n[bold green]Format locked:[/bold green] {FORMAT_LABELS[format_slug]}"
    )
    return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/writing/test_agent.py -v -k "step_block2"`
Expected: PASS on all 4 tests.

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat(writing): add Block 2 format selection step"
```

---

## Task 8: `generate_subject_lines` — subject line Claude call

**Files:**
- Modify: `agents/writing/agent.py`
- Test: `tests/writing/test_agent.py`

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import MagicMock
from agents.writing.agent import generate_subject_lines, SUBJECT_LINE_PROMPT


def _mock_client_returning(text: str):
    client = MagicMock()
    message = MagicMock()
    block = MagicMock()
    block.text = text
    message.content = [block]
    client.messages.create.return_value = message
    return client


def test_generate_subject_lines_parses_valid_json():
    payload = json.dumps({
        "subject_lines": [
            {"option": f"Option {i}", "framework": "confession"} for i in range(12)
        ]
    })
    client = _mock_client_returning(payload)
    result = generate_subject_lines(
        topic="test topic",
        format_slug="personal_letter",
        voice_profile_json={"creator_name": "Acme"},
        client=client,
    )
    assert len(result) == 12
    assert result[0]["option"] == "Option 0"
    assert result[0]["framework"] == "confession"


def test_generate_subject_lines_accepts_15():
    payload = json.dumps({
        "subject_lines": [
            {"option": f"Opt {i}", "framework": "question"} for i in range(15)
        ]
    })
    client = _mock_client_returning(payload)
    result = generate_subject_lines(
        topic="x", format_slug="roundup",
        voice_profile_json={}, client=client,
    )
    assert len(result) == 15


def test_generate_subject_lines_rejects_fewer_than_10_then_retries():
    # First response has 5, second has 11 — should succeed on retry
    short_payload = json.dumps({
        "subject_lines": [
            {"option": f"x{i}", "framework": "confession"} for i in range(5)
        ]
    })
    good_payload = json.dumps({
        "subject_lines": [
            {"option": f"y{i}", "framework": "confession"} for i in range(11)
        ]
    })
    client = MagicMock()
    short_msg = MagicMock()
    short_block = MagicMock(); short_block.text = short_payload
    short_msg.content = [short_block]
    good_msg = MagicMock()
    good_block = MagicMock(); good_block.text = good_payload
    good_msg.content = [good_block]
    client.messages.create.side_effect = [short_msg, good_msg]

    result = generate_subject_lines(
        topic="x", format_slug="curation",
        voice_profile_json={}, client=client,
    )
    assert len(result) == 11
    assert client.messages.create.call_count == 2


def test_generate_subject_lines_strips_markdown_fences():
    payload = "```json\n" + json.dumps({
        "subject_lines": [
            {"option": f"o{i}", "framework": "question"} for i in range(10)
        ]
    }) + "\n```"
    client = _mock_client_returning(payload)
    result = generate_subject_lines(
        topic="x", format_slug="roundup",
        voice_profile_json={}, client=client,
    )
    assert len(result) == 10


def test_generate_subject_lines_raises_after_two_bad_responses():
    bad = json.dumps({"subject_lines": [{"option": "x", "framework": "q"}]})
    client = _mock_client_returning(bad)
    # Set side_effect so the same bad payload is returned twice
    msg = MagicMock()
    block = MagicMock(); block.text = bad
    msg.content = [block]
    client.messages.create.side_effect = [msg, msg]

    with pytest.raises(RuntimeError, match="between 10 and 15"):
        generate_subject_lines(
            topic="x", format_slug="roundup",
            voice_profile_json={}, client=client,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/writing/test_agent.py -v -k "generate_subject_lines"`
Expected: FAIL ImportError.

- [ ] **Step 3: Implement prompt and function**

Add to `agents/writing/agent.py`:

```python
SUBJECT_LINE_PROMPT = """\
You are generating subject line options for a newsletter issue.

<voice_profile>
{voice_profile_json}
</voice_profile>

<format>
{format_label}
</format>

<topic>
{topic}
</topic>

TASK: Produce subject line options for this issue. You MUST return between 10 and 15 options (inclusive). Ten is the minimum, fifteen is the maximum — do not return fewer, do not return more.

Each option must come with a framework tag from this closed list:
- confession
- curiosity gap
- quoted insight
- direct promise
- named mechanism
- question
- contrarian take
- other

Rules:
- Subject lines must sound like this creator's voice (see voice profile).
- No generic AI patterns ("ultimate guide to...", "unlock the secrets of...").
- No emojis unless the voice profile explicitly uses them.
- Each option should be distinct in angle — not minor rewordings of each other.

Return ONLY a JSON object in this exact shape, no markdown fences, no explanation:

{{
  "subject_lines": [
    {{"option": "string", "framework": "one of the tags above"}}
  ]
}}
"""


def generate_subject_lines(
    topic: str,
    format_slug: str,
    voice_profile_json: dict,
    client=None,
) -> list[dict]:
    """Generate 10–15 subject line options. Retries once on count violation.

    Returns the list of {option, framework} dicts.
    """
    if client is None:
        client = _anthropic.Anthropic()

    prompt = SUBJECT_LINE_PROMPT.format(
        voice_profile_json=json.dumps(voice_profile_json, indent=2),
        format_label=FORMAT_LABELS.get(format_slug, format_slug),
        topic=topic,
    )

    for attempt in range(2):
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
        try:
            data = json.loads(raw)
            options = data.get("subject_lines", [])
        except json.JSONDecodeError:
            options = []

        if 10 <= len(options) <= 15:
            return options

    raise RuntimeError(
        f"Subject line generation failed: expected between 10 and 15 options, "
        f"got {len(options)} after retry."
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/writing/test_agent.py -v -k "generate_subject_lines"`
Expected: PASS on all 5 tests.

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat(writing): add subject line generator"
```

---

## Task 9: `suggest_cta` — CTA auto-suggestion Claude call

**Files:**
- Modify: `agents/writing/agent.py`
- Test: `tests/writing/test_agent.py`

- [ ] **Step 1: Write the failing test**

```python
from agents.writing.agent import suggest_cta


def test_suggest_cta_returns_valid_suggestion():
    payload = json.dumps({
        "suggested_cta_type": "offer",
        "suggested_cta_label": "Course launch Q2",
        "rationale": "Topic aligns with course promise."
    })
    client = _mock_client_returning(payload)
    result = suggest_cta(
        topic="course marketing",
        subject_line="How I built my course",
        ctas_md=CTAS_SAMPLE,
        voice_profile_json={"creator_name": "Acme"},
        client=client,
    )
    assert result["suggested_cta_type"] == "offer"
    assert result["suggested_cta_label"] == "Course launch Q2"
    assert "rationale" in result


def test_suggest_cta_strips_fences():
    payload = "```json\n" + json.dumps({
        "suggested_cta_type": "community",
        "suggested_cta_label": "The Lab membership",
        "rationale": "Community-focused topic."
    }) + "\n```"
    client = _mock_client_returning(payload)
    result = suggest_cta(
        topic="x", subject_line="y",
        ctas_md=CTAS_SAMPLE, voice_profile_json={}, client=client,
    )
    assert result["suggested_cta_label"] == "The Lab membership"


def test_suggest_cta_raises_on_malformed_json():
    client = _mock_client_returning("not json at all")
    with pytest.raises(RuntimeError, match="CTA suggestion"):
        suggest_cta(
            topic="x", subject_line="y",
            ctas_md=CTAS_SAMPLE, voice_profile_json={}, client=client,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/writing/test_agent.py -v -k "suggest_cta"`
Expected: FAIL ImportError.

- [ ] **Step 3: Implement**

Add to `agents/writing/agent.py`:

```python
CTA_SUGGESTION_PROMPT = """\
You are selecting the most appropriate CTA for a newsletter issue.

<voice_profile_core_identity>
{core_identity}
</voice_profile_core_identity>

<topic>
{topic}
</topic>

<chosen_subject_line>
{subject_line}
</chosen_subject_line>

<available_ctas>
{ctas_md}
</available_ctas>

TASK: Pick the single CTA from the available_ctas file that best fits this issue.

Rules:
- The suggested_cta_label MUST match a Label from the available_ctas file exactly, character-for-character.
- suggested_cta_type must be one of: intro, offer, assessment, community, content.
- Match the CTA energy to the issue energy. A vulnerable, personal issue should not end with a hard sales push — prefer a softer community or content CTA in that case.
- Prefer offer CTAs when the topic is directly about the thing being sold.

Return ONLY a JSON object in this exact shape, no markdown fences, no explanation:

{{
  "suggested_cta_type": "one of the five types",
  "suggested_cta_label": "exact label from ctas file",
  "rationale": "one-line reason"
}}
"""


def suggest_cta(
    topic: str,
    subject_line: str,
    ctas_md: str,
    voice_profile_json: dict,
    client=None,
) -> dict:
    """Call Claude to suggest a CTA based on topic, subject line, and the CTA library."""
    if client is None:
        client = _anthropic.Anthropic()

    prompt = CTA_SUGGESTION_PROMPT.format(
        core_identity=voice_profile_json.get("core_identity", ""),
        topic=topic,
        subject_line=subject_line,
        ctas_md=ctas_md,
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"CTA suggestion returned malformed JSON: {e}\n\nRaw output:\n{raw[:500]}"
        ) from e

    for key in ("suggested_cta_type", "suggested_cta_label", "rationale"):
        if key not in data:
            raise RuntimeError(f"CTA suggestion missing required key: {key}")
    return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/writing/test_agent.py -v -k "suggest_cta"`
Expected: PASS on all 3 tests.

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat(writing): add CTA auto-suggestion"
```

---

## Task 10: `run_draft` — streaming draft generation

**Files:**
- Modify: `agents/writing/agent.py`
- Test: `tests/writing/test_agent.py`

- [ ] **Step 1: Write the failing test**

```python
from agents.writing.agent import run_draft, DRAFT_PROMPT


def _mock_streaming_client(output_text: str):
    """Build a mock anthropic client whose messages.stream yields output_text."""
    client = MagicMock()
    stream_cm = MagicMock()
    stream_cm.__enter__ = MagicMock(return_value=stream_cm)
    stream_cm.__exit__ = MagicMock(return_value=False)
    stream_cm.text_stream = iter([output_text])
    client.messages.stream.return_value = stream_cm
    return client


def test_run_draft_returns_accumulated_text(capsys):
    client = _mock_streaming_client("Subject line here\n\nBody text.")
    result = run_draft(
        topic="test topic",
        subject_line="Subject line here",
        cta_entry={
            "type": "offer", "label": "Course", "copy": "Join", "link": "https://x",
        },
        format_slug="personal_letter",
        voice_profile_json={"creator_name": "Acme", "core_identity": "x"},
        newsletter_reference_md="# Ref\nexample",
        learnings=None,
        client=client,
    )
    assert result == "Subject line here\n\nBody text."


def test_run_draft_injects_voice_profile_and_format_structure():
    client = _mock_streaming_client("out")
    run_draft(
        topic="t", subject_line="s",
        cta_entry={"type": "offer", "label": "l", "copy": "c", "link": "u"},
        format_slug="roundup",
        voice_profile_json={"creator_name": "Acme"},
        newsletter_reference_md="ref text",
        learnings=None, client=client,
    )
    call_args = client.messages.stream.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert "Acme" in prompt
    assert "Quick Hits" in prompt  # from ROUNDUP_STRUCTURE
    assert "ref text" in prompt


def test_run_draft_marks_reference_as_inspiration_only():
    client = _mock_streaming_client("out")
    run_draft(
        topic="t", subject_line="s",
        cta_entry={"type": "offer", "label": "l", "copy": "c", "link": "u"},
        format_slug="personal_letter",
        voice_profile_json={},
        newsletter_reference_md="ref text",
        learnings=None, client=client,
    )
    prompt = client.messages.stream.call_args.kwargs["messages"][0]["content"]
    assert "REFERENCE ONLY" in prompt
    assert "Do not copy" in prompt


def test_run_draft_injects_cta_entry():
    client = _mock_streaming_client("out")
    run_draft(
        topic="t", subject_line="s",
        cta_entry={
            "type": "community", "label": "The Lab",
            "copy": "Join the lab.", "link": "https://lab.example",
        },
        format_slug="personal_letter",
        voice_profile_json={},
        newsletter_reference_md="",
        learnings=None, client=client,
    )
    prompt = client.messages.stream.call_args.kwargs["messages"][0]["content"]
    assert "The Lab" in prompt
    assert "Join the lab." in prompt
    assert "https://lab.example" in prompt


def test_run_draft_appends_learnings():
    client = _mock_streaming_client("out")
    run_draft(
        topic="t", subject_line="s",
        cta_entry={"type": "offer", "label": "l", "copy": "c", "link": "u"},
        format_slug="personal_letter",
        voice_profile_json={},
        newsletter_reference_md="",
        learnings=[{"round": 1, "feedback": "make it shorter"}],
        client=client,
    )
    prompt = client.messages.stream.call_args.kwargs["messages"][0]["content"]
    assert "make it shorter" in prompt
    assert "previous round" in prompt.lower()


def test_run_draft_omits_reference_section_when_empty():
    client = _mock_streaming_client("out")
    run_draft(
        topic="t", subject_line="s",
        cta_entry={"type": "offer", "label": "l", "copy": "c", "link": "u"},
        format_slug="personal_letter",
        voice_profile_json={},
        newsletter_reference_md="",
        learnings=None, client=client,
    )
    prompt = client.messages.stream.call_args.kwargs["messages"][0]["content"]
    # The REFERENCE ONLY guard should be absent when there is no reference
    assert "REFERENCE ONLY" not in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/writing/test_agent.py -v -k "run_draft"`
Expected: FAIL ImportError.

- [ ] **Step 3: Implement**

Add to `agents/writing/agent.py`:

```python
DRAFT_PROMPT = """\
You are writing a newsletter issue as this creator.

<voice_profile>
{voice_profile_json}
</voice_profile>

The voice profile above is the SOLE source of voice. Match its patterns, beliefs, sentence rhythm, and signature phrases. Do not drift into generic AI voice.

<format_structure>
{format_structure}
</format_structure>

Follow the format structure exactly. The structure dictates sections and ordering; voice comes from the voice profile.

<topic>
{topic}
</topic>

<chosen_subject_line>
{subject_line}
</chosen_subject_line>

<cta>
Type: {cta_type}
Label: {cta_label}
Copy: {cta_copy}
Link: {cta_link}
</cta>

CTA rules:
- Place the primary CTA at top of fold — the reader should not have to scroll to find it.
- Include a P.S. at the end of the draft. The P.S. may reinforce the same CTA or gesture to a natural secondary asset, but it must be part of the draft.
- Match the CTA's energy to the issue's emotional weight. Do not bolt a hard sales push onto a vulnerable personal letter.

{reference_block}
OUTPUT INSTRUCTIONS:
- Line 1: the chosen subject line, exactly as given.
- Line 2: blank.
- Line 3 onwards: the full newsletter body, following the format structure.
- No reasoning. No preamble. No meta-commentary. No structural labels beyond what the format structure itself requires.
- Write the draft only.
{feedback_block}"""


_REFERENCE_GUARD = """\
<newsletter_reference>
REFERENCE ONLY — the examples below show craft patterns and transferable moves from other newsletters. Do not copy phrasing, tone, sentences, or structures from these examples. Voice comes exclusively from the voice_profile above. Use the reference only to understand what good newsletters do, not to imitate them.

{reference}
</newsletter_reference>

"""


def run_draft(
    topic: str,
    subject_line: str,
    cta_entry: dict,
    format_slug: str,
    voice_profile_json: dict,
    newsletter_reference_md: str,
    learnings: list | None,
    client=None,
) -> str:
    """Stream a newsletter draft. Returns the accumulated text."""
    if client is None:
        client = _anthropic.Anthropic()

    format_structure = FORMAT_STRUCTURES[format_slug]

    if newsletter_reference_md:
        reference_block = _REFERENCE_GUARD.format(reference=newsletter_reference_md)
    else:
        reference_block = ""

    if learnings:
        feedback_block = "\n\nOperator feedback from previous round to incorporate:\n" + \
            "\n".join(f"- {entry.get('feedback', '')}" for entry in learnings)
    else:
        feedback_block = ""

    prompt = DRAFT_PROMPT.format(
        voice_profile_json=json.dumps(voice_profile_json, indent=2),
        format_structure=format_structure,
        topic=topic,
        subject_line=subject_line,
        cta_type=cta_entry.get("type", ""),
        cta_label=cta_entry.get("label", ""),
        cta_copy=cta_entry.get("copy", ""),
        cta_link=cta_entry.get("link", ""),
        reference_block=reference_block,
        feedback_block=feedback_block,
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

    print()
    return "".join(accumulated)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/writing/test_agent.py -v -k "run_draft"`
Expected: PASS on all 6 tests.

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat(writing): add streaming draft generator"
```

---

## Task 11: `write_draft_file` — persist draft with frontmatter

**Files:**
- Modify: `agents/writing/agent.py`
- Test: `tests/writing/test_agent.py`

- [ ] **Step 1: Write the failing test**

```python
from agents.writing.agent import write_draft_file


def test_write_draft_file_writes_frontmatter(tmp_path):
    path = write_draft_file(
        creator_slug="acme",
        subject_line="Hello World",
        draft_body="Hello World\n\nBody text here.",
        topic="greeting",
        format_slug="personal_letter",
        cta_label="Course",
        base_dir=tmp_path,
        today="2026-04-08",
    )
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "date: 2026-04-08" in content
    assert "format: personal_letter" in content
    assert 'subject: "Hello World"' in content
    assert 'cta: "Course"' in content
    assert 'topic: "greeting"' in content
    assert "Body text here." in content


def test_write_draft_file_slug_in_filename(tmp_path):
    path = write_draft_file(
        creator_slug="acme",
        subject_line="I can't believe it!",
        draft_body="body",
        topic="x",
        format_slug="personal_letter",
        cta_label="c",
        base_dir=tmp_path,
        today="2026-04-08",
    )
    assert path.name == "2026-04-08-i-cant-believe-it.md"


def test_write_draft_file_handles_collision(tmp_path):
    # First write
    write_draft_file(
        creator_slug="acme", subject_line="Same",
        draft_body="first", topic="x", format_slug="personal_letter",
        cta_label="c", base_dir=tmp_path, today="2026-04-08",
    )
    # Second write same day, same subject
    path2 = write_draft_file(
        creator_slug="acme", subject_line="Same",
        draft_body="second", topic="x", format_slug="personal_letter",
        cta_label="c", base_dir=tmp_path, today="2026-04-08",
    )
    assert path2.name == "2026-04-08-same-2.md"
    # Third write
    path3 = write_draft_file(
        creator_slug="acme", subject_line="Same",
        draft_body="third", topic="x", format_slug="personal_letter",
        cta_label="c", base_dir=tmp_path, today="2026-04-08",
    )
    assert path3.name == "2026-04-08-same-3.md"


def test_write_draft_file_escapes_quotes_in_subject(tmp_path):
    path = write_draft_file(
        creator_slug="acme",
        subject_line='He said "hi"',
        draft_body="body", topic="x", format_slug="personal_letter",
        cta_label="c", base_dir=tmp_path, today="2026-04-08",
    )
    content = path.read_text(encoding="utf-8")
    assert 'subject: "He said \\"hi\\""' in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/writing/test_agent.py -v -k "write_draft_file"`
Expected: FAIL ImportError.

- [ ] **Step 3: Implement**

Add to `agents/writing/agent.py`:

```python
def _yaml_escape(value: str) -> str:
    """Escape a string value for a double-quoted YAML scalar."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_draft_file(
    creator_slug: str,
    subject_line: str,
    draft_body: str,
    topic: str,
    format_slug: str,
    cta_label: str,
    base_dir: Path = None,
    today: str | None = None,
) -> Path:
    """Write a draft file under briefs/<slug>/drafts/ with YAML frontmatter.

    On filename collision (same date + slug), appends -2, -3, etc.
    Returns the path written.
    """
    _validate_creator_slug(creator_slug)
    base = Path(base_dir).resolve() if base_dir else _project_root
    drafts_dir = base / "briefs" / creator_slug / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)

    if today is None:
        from datetime import date
        today = date.today().isoformat()

    slug = slugify_subject(subject_line)
    candidate = drafts_dir / f"{today}-{slug}.md"
    if candidate.exists():
        n = 2
        while True:
            candidate = drafts_dir / f"{today}-{slug}-{n}.md"
            if not candidate.exists():
                break
            n += 1

    frontmatter = (
        "---\n"
        f"date: {today}\n"
        f"format: {format_slug}\n"
        f'subject: "{_yaml_escape(subject_line)}"\n'
        f'cta: "{_yaml_escape(cta_label)}"\n'
        f'topic: "{_yaml_escape(topic)}"\n'
        "---\n\n"
    )
    candidate.write_text(frontmatter + draft_body, encoding="utf-8")
    return candidate
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/writing/test_agent.py -v -k "write_draft_file"`
Expected: PASS on all 4 tests.

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat(writing): add draft file writer with frontmatter"
```

---

## Task 12: `step_block3` orchestration

**Files:**
- Modify: `agents/writing/agent.py`

This task wires Tasks 4–11 into the interactive Block 3 flow. It is primarily integration code; unit tests are light because most logic is already covered. One smoke test covers the happy path end-to-end with mocks.

- [ ] **Step 1: Write the failing smoke test**

```python
from agents.writing.agent import step_block3


def test_step_block3_happy_path(tmp_path, monkeypatch):
    # Seed voice profile
    agent_dir = tmp_path / ".agent" / "acme"
    agent_dir.mkdir(parents=True)
    (agent_dir / "voice-profile.json").write_text(
        '{"creator_name": "Acme", "core_identity": "clear"}', encoding="utf-8"
    )
    # Seed ctas.md
    briefs = tmp_path / "briefs" / "acme"
    briefs.mkdir(parents=True)
    (briefs / "ctas.md").write_text(CTAS_SAMPLE, encoding="utf-8")

    # Mock Anthropic client behaviour
    subject_payload = json.dumps({
        "subject_lines": [
            {"option": f"Option {i}", "framework": "confession"} for i in range(10)
        ]
    })
    cta_payload = json.dumps({
        "suggested_cta_type": "offer",
        "suggested_cta_label": "Course launch Q2",
        "rationale": "fits",
    })

    # messages.create returns different payloads on each call
    client = MagicMock()
    def _create(**kwargs):
        msg = MagicMock()
        block = MagicMock()
        # Decide by prompt content
        prompt = kwargs["messages"][0]["content"]
        if "subject line options" in prompt or "subject_lines" in prompt:
            block.text = subject_payload
        else:
            block.text = cta_payload
        msg.content = [block]
        return msg
    client.messages.create.side_effect = _create

    # messages.stream returns a draft
    stream_cm = MagicMock()
    stream_cm.__enter__ = MagicMock(return_value=stream_cm)
    stream_cm.__exit__ = MagicMock(return_value=False)
    stream_cm.text_stream = iter(["Option 1\n\nBody of the draft."])
    client.messages.stream.return_value = stream_cm

    monkeypatch.setattr("agents.writing.agent._anthropic.Anthropic", lambda: client)

    # Simulate operator input:
    # 1. format confirmation: y
    # 2. topic
    # 3. subject line pick: 1
    # 4. cta confirmation: y
    # 5. draft review: save it
    inputs = iter(["y", "my topic here", "1", "y", "save it"])
    monkeypatch.setattr("agents.writing.agent.ask", lambda prompt: next(inputs))

    session = WritingSession(creator_slug="acme", base_dir=tmp_path)
    block2_data = {"format": "personal_letter"}

    step_block3(
        creator_slug="acme",
        session=session,
        voice_profile_json={"creator_name": "Acme", "core_identity": "clear"},
        block2_data=block2_data,
        base_dir=tmp_path,
    )

    # Verify a draft file was written
    drafts = list((tmp_path / "briefs" / "acme" / "drafts").glob("*.md"))
    assert len(drafts) == 1
    content = drafts[0].read_text(encoding="utf-8")
    assert "Option 1" in content
    assert "Body of the draft." in content
    assert 'cta: "Course launch Q2"' in content


def test_step_block3_exits_if_format_not_confirmed(tmp_path, monkeypatch):
    agent_dir = tmp_path / ".agent" / "acme"
    agent_dir.mkdir(parents=True)
    (agent_dir / "voice-profile.json").write_text('{}', encoding="utf-8")
    briefs = tmp_path / "briefs" / "acme"
    briefs.mkdir(parents=True)
    (briefs / "ctas.md").write_text(CTAS_SAMPLE, encoding="utf-8")

    monkeypatch.setattr("agents.writing.agent.ask", lambda prompt: "n")

    session = WritingSession(creator_slug="acme", base_dir=tmp_path)
    with pytest.raises(SystemExit):
        step_block3(
            creator_slug="acme", session=session,
            voice_profile_json={},
            block2_data={"format": "personal_letter"},
            base_dir=tmp_path,
        )
```

Add `from agents.writing.agent import WritingSession` to the imports at the top of the test additions (or import at the top of the file alongside the other imports).

Also update `WritingSession` to accept a `base_dir` parameter. Check `agents/strategy/session.py` to confirm the Session signature — if it doesn't already accept base_dir, add a small shim in the test file using `monkeypatch.setattr` on `_project_root` instead. **Before writing the test, run**:

```
grep -n "def __init__" agents/strategy/session.py
```

and adjust the test to match. If `Session.__init__` does not accept `base_dir`, use this test setup instead:

```python
monkeypatch.setattr("agents.writing.agent._project_root", tmp_path)
session = WritingSession(creator_slug="acme")
```

and remove the `base_dir=tmp_path` arg from the `step_block3` call (use `_project_root` patching instead).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/writing/test_agent.py -v -k "step_block3"`
Expected: FAIL ImportError on `step_block3`.

- [ ] **Step 3: Implement `step_block3`**

Add to `agents/writing/agent.py` (after `write_draft_file`):

```python
def _pick_subject_line(options: list[dict]) -> dict | str:
    """Display subject line options and prompt for a pick.

    Returns the chosen option dict, or the string "regenerate" to request a new batch.
    """
    console.print("\n[bold]Subject line options:[/bold]")
    for i, opt in enumerate(options, start=1):
        framework = opt.get("framework", "other")
        console.print(f"  [bold]{i:>2}[/bold]. [dim][{framework}][/dim] {opt.get('option', '')}")
    while True:
        raw = ask(f'Pick 1-{len(options)}, or type "regenerate" for a new batch').strip().lower()
        if raw in ("regenerate", "regen", "r"):
            return "regenerate"
        if raw.isdigit():
            n = int(raw)
            if 1 <= n <= len(options):
                return options[n - 1]
        console.print(f"[red]Enter a number 1-{len(options)} or 'regenerate'.[/red]")


def _pick_cta(
    suggestion: dict,
    parsed_ctas: list[dict],
) -> dict:
    """Display CTA suggestion and let operator accept or override.

    Returns the full CTA entry dict from parsed_ctas.
    """
    ctype = suggestion["suggested_cta_type"]
    clabel = suggestion["suggested_cta_label"]
    rationale = suggestion.get("rationale", "")
    console.print(f"\n[bold]Suggested CTA:[/bold] [{ctype}] {clabel}")
    console.print(f"[dim]Reason: {rationale}[/dim]")

    by_label = {e["label"]: e for e in parsed_ctas}

    while True:
        raw = ask('Accept? (y / or type a label from ctas.md to override)').strip()
        if raw.lower() in ("y", "yes"):
            if clabel not in by_label:
                console.print(
                    f"[red]Suggested label '{clabel}' not found in ctas.md. "
                    f"Pick one manually.[/red]"
                )
                continue
            return by_label[clabel]
        if raw in by_label:
            return by_label[raw]
        # Also allow case-insensitive label match
        matches = [e for e in parsed_ctas if e["label"].lower() == raw.lower()]
        if matches:
            return matches[0]
        console.print(
            f"[red]No CTA with label '{raw}'. Available labels: "
            f"{', '.join(by_label.keys())}[/red]"
        )


def step_block3(
    creator_slug: str,
    session: "WritingSession",
    voice_profile_json: dict,
    block2_data: dict,
    base_dir: Path = None,
) -> None:
    """Orchestrate Block 3: topic → subject → CTA → draft → review → save."""
    format_slug = block2_data["format"]
    format_label = FORMAT_LABELS[format_slug]

    console.print(Panel("[bold]Block 3 — Draft[/bold]", style="blue"))

    # Step 1 — format confirmation
    confirm = ask(f"Format locked for {creator_slug}: {format_label} — proceed? (y/n)").strip().lower()
    if confirm not in ("y", "yes"):
        console.print("[yellow]Aborted.[/yellow]")
        sys.exit(0)

    # Step 2 — topic
    topic = ask("What is this issue about? (1–3 sentences)").strip()
    if not topic:
        console.print("[red]Topic is required.[/red]")
        sys.exit(1)

    # Load CTA library
    ctas_md = load_ctas_md(creator_slug, base_dir=base_dir)
    parsed_ctas = parse_ctas_md(ctas_md)

    # Load newsletter reference (non-fatal)
    newsletter_reference_md = load_newsletter_reference(base_dir=base_dir)
    if not newsletter_reference_md:
        console.print("[dim]newsletter-reference.md not found — proceeding without reference.[/dim]")

    client = _anthropic.Anthropic()

    # Step 3 — subject line generation + pick
    while True:
        console.print("\n[dim]Generating subject line options...[/dim]")
        options = generate_subject_lines(
            topic=topic,
            format_slug=format_slug,
            voice_profile_json=voice_profile_json,
            client=client,
        )
        choice = _pick_subject_line(options)
        if choice != "regenerate":
            chosen_subject = choice["option"]
            break

    # Step 4 — CTA auto-suggest + confirm
    console.print("\n[dim]Suggesting CTA...[/dim]")
    suggestion = suggest_cta(
        topic=topic,
        subject_line=chosen_subject,
        ctas_md=ctas_md,
        voice_profile_json=voice_profile_json,
        client=client,
    )
    cta_entry = _pick_cta(suggestion, parsed_ctas)

    # Step 5 + 6 — draft + review loop
    # Clear any prior block3 learnings from a previous draft run
    draft_learnings: list = []
    round_number = 0
    while True:
        round_number += 1
        console.print(f"\n[dim]Generating draft (round {round_number})...[/dim]\n")
        draft_body = run_draft(
            topic=topic,
            subject_line=chosen_subject,
            cta_entry=cta_entry,
            format_slug=format_slug,
            voice_profile_json=voice_profile_json,
            newsletter_reference_md=newsletter_reference_md,
            learnings=draft_learnings or None,
            client=client,
        )
        console.print(Panel(draft_body, title=f"Draft (Round {round_number})", style="white"))
        feedback = ask('Review the draft above. Type feedback to regenerate, or "save it" to finalise').strip()
        if feedback.lower() in ("save it", "save", "done", "lock it", "lock"):
            break
        draft_learnings.append({"round": round_number, "feedback": feedback})

    # Step 7 — write output
    path = write_draft_file(
        creator_slug=creator_slug,
        subject_line=chosen_subject,
        draft_body=draft_body,
        topic=topic,
        format_slug=format_slug,
        cta_label=cta_entry["label"],
        base_dir=base_dir,
    )
    console.print(f"\n[bold green]Draft saved:[/bold green] {path}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/writing/test_agent.py -v -k "step_block3"`
Expected: PASS on both tests.

If the `WritingSession` test setup fails, use the `_project_root` monkeypatch approach noted in Step 1 and re-run.

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py tests/writing/test_agent.py
git commit -m "feat(writing): add Block 3 orchestration"
```

---

## Task 13: Wire Block 2 and Block 3 into `main()`

**Files:**
- Modify: `agents/writing/agent.py` (replace the `# Block 2 stub` section in `main()`)

This task has no new unit tests — it is pure wiring. Verified by running the full test suite and a dry smoke run.

- [ ] **Step 1: Read current `main()`**

Read [agents/writing/agent.py](agents/writing/agent.py) lines 576–618 to confirm current shape before editing.

- [ ] **Step 2: Replace the Block 2 stub**

Replace this block in `main()`:

```python
    # Block 2 stub
    console.print("\n[dim]Block 2 (format selection) — coming soon.[/dim]")
```

with:

```python
    # Block 2 — Format selection (one-time)
    block2_data = load_block2_data(creator_slug)
    if block2_data is None:
        block2_data = step_block2(creator_slug)
        session.set("block2_done", True)
        session.save()
    else:
        console.print(
            f"[dim]Block 2 already complete — format: "
            f"{FORMAT_LABELS[block2_data['format']]}.[/dim]"
        )

    # Block 3 — Draft generation (re-runnable)
    voice_profile_json = load_voice_profile_json(creator_slug)
    step_block3(
        creator_slug=creator_slug,
        session=session,
        voice_profile_json=voice_profile_json,
        block2_data=block2_data,
    )
```

- [ ] **Step 3: Run the full test suite**

Run: `pytest tests/writing/test_agent.py -v`
Expected: ALL tests pass (Task 1 through Task 12).

- [ ] **Step 4: Static sanity check**

Run: `python -c "import agents.writing.agent as a; print('OK', hasattr(a, 'step_block3'), hasattr(a, 'step_block2'))"`
Expected: `OK True True`

- [ ] **Step 5: Commit**

```bash
git add agents/writing/agent.py
git commit -m "feat(writing): wire Block 2 and Block 3 into main CLI flow"
```

---

## Self-Review

**Spec coverage:**
- Block 2 one-time format lock → Task 3, 7, 13
- Block 3 format confirmation → Task 12 (`step_block3` Step 1)
- Topic prompt → Task 12 (Step 2)
- 10–15 subject lines, framework-tagged → Task 8
- Pick by number or regenerate → Task 12 (`_pick_subject_line`)
- CTA library `ctas.md` + parser → Task 5
- CTA auto-suggestion → Task 9
- Operator accept/override CTA → Task 12 (`_pick_cta`)
- Draft generation with voice profile + format structure + reference guard → Task 10
- Newsletter reference as inspiration only (guarded) → Task 10
- P.S. as part of draft → Task 10 (`DRAFT_PROMPT` CTA rules)
- Review loop with learnings → Task 12
- Draft file with frontmatter + collision handling → Task 11
- Main wiring → Task 13

**Placeholder scan:** No "TBD", no "similar to", no "handle edge cases" — all code inlined.

**Type consistency:** `block2_data["format"]` is always a slug from `FORMAT_STRUCTURES` keys. `cta_entry` has keys `{type, label, copy, link}` consistently across Task 5 parser, Task 9 suggestion lookup, Task 10 draft injection, Task 11 file write. `voice_profile_json` is a plain dict throughout. `learnings` is `list[dict]` or `None` in both review loops.

All spec sections mapped. Plan is ready to execute.
