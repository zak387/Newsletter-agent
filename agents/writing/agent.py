#!/usr/bin/env python3
"""Writing Agent — produces a voice profile and newsletter draft for a creator."""

import sys
import json
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import re
import anthropic as _anthropic

from agents.strategy.session import Session


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
    if "/" in creator_slug or "\\" in creator_slug or ".." in creator_slug:
        raise ValueError(f"Invalid creator_slug: {creator_slug!r}")
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


def run_tastemaker(content_pack: str, brief: dict, client=None) -> str:
    """Run the Tastemaker Protocol prompt and return the full voice profile markdown.

    Streams output to console so the operator can watch progress.
    Returns the complete accumulated text.
    """
    if client is None:
        client = _anthropic.Anthropic()

    archetype_obj = brief.get('creator_archetype') or {}
    creator_context = (
        f"Archetype: {archetype_obj.get('primary', 'Unknown')}\n"
        f"Niche: {brief.get('niche_umbrella') or 'Unknown'}\n"
        f"Target reader: {brief.get('target_reader') or 'Unknown'}"
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

    if not message.content:
        raise RuntimeError("JSON extraction call returned no content blocks")
    raw = message.content[0].text.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"JSON parse error extracting voice profile structure: {e}\n\nRaw output:\n{raw[:500]}"
        ) from e
