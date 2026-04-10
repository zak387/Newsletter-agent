#!/usr/bin/env python3
"""Writing Agent — produces a voice profile and newsletter draft for a creator."""

import sys
import json
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import re
from dotenv import load_dotenv
load_dotenv(_project_root / ".env")

from agents.writing._claude_cli import ClaudeCLIClient as _ClaudeClient

from agents.strategy.session import Session

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


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

DRAFT_PROMPT = """\
You are writing a newsletter issue as this creator.

<priority_hierarchy>
These three rule sets may conflict. When they do, apply them in this exact order of precedence — higher always overrides lower:

1. **CTA rules** (highest) — non-negotiable. Placement, number of CTAs, and P.S. requirements override everything else.
2. **Format structure** — the skeleton of the issue (Roundup, Curation, Personal Letter, etc.). Section ordering and intent are a HARD CONSTRAINT and override voice tendencies. Never collapse a named format into a different shape because the voice profile prefers prose.
3. **Voice profile** (lowest in precedence, but NEVER optional) — word choice, rhythm, beliefs, signature phrases. Voice operates WITHIN the structure set by the format, not against it.

**CRITICAL:** "Format overrides voice" means the format sets the slots and the section ordering. It does NOT mean you switch registers inside those slots. Every sentence inside every slot — every headline, every TL;DR, every takeaway, every "my take", every quick hit, every sign-off — must still be written in the creator's voice and must still pass the voice profile's Never list and Hard Rules. A Roundup written in generic news-wire or analyst voice is a failure even if the structure is perfect. Do not import the cultural default tone of the format (e.g. Morning Brew / Axios / TechCrunch headline-case, hedged clinical phrasing, "linked to", "associated with", "some experts say"). Write the slots AS the creator.

Before writing any draft, re-read the voice profile's calibration quotes, Never list, and signature phrases. Stress-test every sentence you write against them. If a sentence sounds like it could appear in any newsletter, rewrite it until it could only have been written by this specific creator.

If the topic cannot be written in the chosen format without violating CTA rules or format structure, stop and flag it rather than silently reshaping the format.
</priority_hierarchy>

<voice_profile>
{voice_profile_json}
</voice_profile>

The voice profile above is the source of voice — word choice, rhythm, beliefs, signature phrases. Match them. Do not drift into generic AI voice. Voice is subordinate to the format structure below.

<format_structure>
{format_structure}
</format_structure>

The format structure is the skeleton of the issue and is a HARD CONSTRAINT — it overrides voice rules. Follow its section ordering, intent, and required elements exactly. The section names in the structure (e.g. "The Moment", "The Problem", "A Better Way") are guidance for YOU, not headings for the reader — never output them literally. Instead, add 2 or 3 CONTEXTUAL headers that say something about the content at that point in the email, written as short statement-style headlines a skim-reader can scan. For example: "## Eight out of ten products on the shelf have seed oils" or "## Six words. Ten seconds. That is the whole scan." — not "## The Problem" or "## A Better Way". 2–3 contextual headers total is the target for a Personal Letter; do NOT add a header to every section. Carry the other transitions with blank lines and prose.

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

{welcome_block}CTA rules (HIGHEST PRIORITY — these OVERRIDE both the format structure and the voice profile when they conflict):
- FORMAT PERSONAL LETTER ONLY: The email MUST open with the Welcome block (provided above if present), then a standalone CTA block positioned ABOVE all body copy. The standalone CTA block is 2–3 short sentences pitching the primary CTA, followed by the link on its own line. Do NOT weave the CTA into the narrative in addition — the standalone block above the copy replaces the woven-in CTA.
- FORMAT ROUNDUP or CURATION: Keep the CTA placement defined by the format structure. No standalone top block required.
- The P.S. at the end of the draft must include a SECOND CTA — either reinforcing the primary CTA or pointing to a natural secondary asset. There should ALWAYS be two CTAs in the final email: one at the top (standalone block for Personal Letter, format-defined for Roundup/Curation) and one in the P.S.
- Match the CTA's energy to the issue's emotional weight. Do not bolt a hard sales push onto a vulnerable letter.

{reference_block}
OUTPUT INSTRUCTIONS:
- Line 1: the chosen subject line, exactly as given.
- Line 2: blank.
- Line 3 onwards: the full newsletter body, following the format structure's section order but without the bracketed-concept headers.
- No reasoning. No preamble. No meta-commentary. No structural labels unless the content naturally requires them.
- Write the draft only.
{feedback_block}"""


_REFERENCE_GUARD = """\
<newsletter_reference>
REFERENCE ONLY — the examples below show craft patterns and transferable moves from other newsletters. Do not copy phrasing, tone, sentences, or structures from these examples. Voice comes exclusively from the voice_profile above. Use the reference only to understand what good newsletters do, not to imitate them.

{reference}
</newsletter_reference>

"""


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

<subject_line_rules>
{subject_line_rules}
</subject_line_rules>

TASK: Produce subject line options for this issue. You MUST return between 10 and 15 options (inclusive). Ten is the minimum, fifteen is the maximum — do not return fewer, do not return more.

HARD CONSTRAINTS (non-negotiable — these override voice profile preferences):
- TARGET is 20 characters per subject line. HARD CEILING is 30 characters. Aim for 20 or fewer; never exceed 30. Count every character including spaces and punctuation before you return. Reject any option above 30 characters and replace it before returning. Prefer options under 20 when possible — 20+ should be used sparingly.
- Every subject line MUST fit exactly one of these five frameworks: Curiosity, Pain, Dream Outcome, Proof, Mistake. No other tags are allowed.
- Aim for a spread across frameworks — do not return 15 Curiosity options. At minimum, use at least 3 different frameworks across the set.
- No emojis. No em-dashes. No generic AI patterns.
- Subject lines should sound like this creator's voice (word choice, register) within the character limit — but the character limit wins if they conflict.

Return ONLY a JSON object in this exact shape, no markdown fences, no explanation:

{{
  "subject_lines": [
    {{"option": "string (target ≤20 chars, hard ceiling ≤30 chars)", "framework": "Curiosity | Pain | Dream Outcome | Proof | Mistake"}}
  ]
}}
"""

PERSONAL_LETTER_STRUCTURE = """\
SECTION ORDER (guidance only — do NOT output these labels):

1. Opener — creator's signature sign-in (e.g. "Kyle here.")
2. Welcome block — fixed per-creator intro, provided by the operator. Render it exactly as given, on its own, followed by a visual separator.
3. Standalone CTA block — a short 2-3 sentence pitch of the primary CTA followed by the link on its own line. This sits ABOVE all body copy. No woven-in CTA inside the body — the standalone block above replaces it.
4. The Moment — personal story, observation, or trigger
5. The Problem — the common challenge the reader faces
6. Why Most Advice Fails — 2–4 common pieces of advice, each dismissed in one line
7. A Better Way — the core idea, mindset shift, or framework
8. How to Apply This — three numbered action steps
9. Closing aphorism — one sharp closing insight or signature phrase from the creator's voice
10. Sign-off — creator's closing pattern
11. P.S. — emotional payoff plus SECOND CTA (reinforces the primary CTA or points to a natural secondary asset)

NO KEY TAKEAWAYS SECTION in Personal Letter format. That is a Roundup convention.

CONTEXTUAL HEADERS (required for skimmability):

The final draft must include 2 or 3 contextual headers in the body — short, concrete, statement-style headlines that say something about the content. Use them as navigation for a skim-reader. They are NOT concept labels.

- Bad (concept label): ## The Problem
- Good (contextual): ## Eight out of ten products on the shelf have seed oils

- Bad: ## A Better Way
- Good: ## Six words. Ten seconds. That is the whole scan.

Recommended placement of the 2–3 contextual headers:
- Header 1 above The Moment (frames the opening scene)
- Header 2 above either The Problem or Why Most Advice Fails
- Header 3 above A Better Way or How to Apply This

Do NOT add a header to every section. 2–3 total is the target. The rest of the transitions should be carried by blank lines and prose. Do NOT put a header on the Welcome block or the standalone CTA block — those sit above all headers.

Write in first person. No hype, no clichés, no generic motivational language.
"""

ROUNDUP_STRUCTURE = """\
SECTION ORDER (guidance only — do NOT output these labels as headings):

1. Opener — creator's signature sign-in (e.g. "Kyle here.")
2. Framed opener — 4–6 lines. NOT a summary. Plant a clear opinion or verdict about the trend/topic the issue is covering. Frame the reader into the creator's angle before the stories begin. End by teeing up that the rest of the email is the evidence.
3. Rundown — a short 3-bullet scan block, one bullet per main story. Each bullet is one punchy line in the creator's voice (not the article's headline). Lets a skim-reader get the whole issue in ten seconds.
4. Main Stories — exactly three. For EACH story:
   - A contextual `###` header that IS the headline (statement-style, in the creator's voice — NOT the article's original headline, and NOT a concept label). Do NOT repeat the headline as a bullet underneath.
   - **TL;DR:** one-sentence factual summary of what the article says, with the source link inline (e.g. "according to [Consumer Reports](https://...)").
   - **Three things to know** — exactly three bullets, each a concrete fact or implication pulled from the source, translated into the creator's voice.
   - **{verdict_label}** — the creator's opinion. Must be in the creator's voice: verdict-first, concrete, second-person where natural, specific products/ingredients/numbers. Never drift into explainer / news-wire / analyst tone. No "some experts say", no "linked to", no "associated with".
5. CTA block — primary CTA, placed immediately after the three main stories. 2–3 sentences pitching it in the creator's voice, followed by the link on its own line.
6. Quick Hits — 3–5 bullets on the rest of the category. Each bullet is one punchy line in the creator's voice. Links optional; if included they must be real.
7. Sign-off line — one short closing action / aphorism in the creator's voice.
8. Creator's closing pattern (e.g. "Kyle")
9. P.S. — emotional or reflective payoff PLUS a SECOND CTA (reinforcing the primary or pointing to a natural secondary asset), followed by the second CTA's link on its own line.

SOURCING RULES (NON-NEGOTIABLE):

Every Roundup must combine two sources of material:
- **Web-searched real articles** — each of the three main stories MUST be anchored to a real, verifiable article found via web search. The URL in the TL;DR must be a real URL from the search results, not a placeholder, not invented, not a guess. If web search is unavailable or returns nothing usable, STOP and flag it to the operator rather than writing the draft.
- **The creator's own prior takes / observations / voice profile** — the `{verdict_label}` section for each story, and the framed opener, must be grounded in the creator's documented beliefs, signature phrases, and prior positions from the voice profile and brief. The articles supply the news; the creator supplies the angle.

Never invent a source. Never write "[link]" as a placeholder. Never fabricate a publication, study, or statistic. If you cannot find a real article for a story, drop the story or replace the topic.

CONTEXTUAL HEADERS:

The three `###` story headers are the skim layer. Each one must be a short statement-style headline in the creator's voice — what the creator would say about the story, not what the original outlet said. Example:
- Bad (outlet voice): ### Consumer Reports Finds Elevated Lead in 23 Protein Powders
- Good (creator voice): ### Two out of three protein powders tested high for lead

Do NOT output `## Opening`, `## Main Stories`, `## Quick Hits`, or any other concept label as a heading. The only headings in the final draft are the three story headers and the CTA block header.

VOICE INSIDE EVERY SLOT:

The format sets the slots. The voice profile owns the sentences inside them. Every TL;DR, every bullet, every verdict, every quick hit, every sign-off must sound like the creator — not like an analyst, not like a news wire, not like a generic newsletter. Stress-test every sentence against the voice profile's Never list and calibration quotes before returning the draft.

No emojis. No em-dashes. No news-article tone. Clarity over cleverness.
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


def slugify_subject(subject: str, max_len: int = 60) -> str:
    """Convert a subject line into a filesystem-safe slug.

    Lowercases, strips apostrophes entirely, replaces other non-alphanumeric
    characters with spaces, collapses whitespace, and truncates to max_len on
    a word boundary. Returns "untitled" for empty or all-punctuation input.
    """
    if not subject:
        return "untitled"
    s = subject.lower().replace("'", "").replace("\u2019", "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = s.strip()
    if not s:
        return "untitled"
    if len(s) > max_len:
        s = s[:max_len].rsplit(" ", 1)[0]
    return s.replace(" ", "-")


console = Console()


def ask(prompt: str) -> str:
    """Pause and collect operator input."""
    return Prompt.ask(f"\n[bold cyan]{prompt}[/bold cyan]")


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


def load_strategy_brief(creator_slug: str, base_dir: Path = None) -> dict:
    """Load the strategy brief produced by the strategy agent.

    Exits with a clear error if the file does not exist.
    """
    _validate_creator_slug(creator_slug)
    base = Path(base_dir).resolve() if base_dir else _project_root
    brief_path = base / ".agent" / creator_slug / "strategy-brief.json"
    if not brief_path.exists():
        print(
            f"\nERROR: Positioning brief not found at {brief_path}\n"
            f"Run the strategy agent first:\n"
            f"  python agents/strategy/agent.py --creator {creator_slug}\n"
        )
        sys.exit(1)
    return json.loads(brief_path.read_text(encoding="utf-8"))


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


SUBJECT_LINE_TARGET_CHARS = 20
SUBJECT_LINE_MAX_CHARS = 30
_VALID_SUBJECT_FRAMEWORKS = {"Curiosity", "Pain", "Dream Outcome", "Proof", "Mistake"}


def load_subject_line_rules(base_dir: Path = None) -> str:
    """Load docs/subject-line-rules.md from project root.

    Returns a built-in fallback if missing so the agent never runs without rules.
    """
    base = Path(base_dir).resolve() if base_dir else _project_root
    path = base / "docs" / "subject-line-rules.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return (
        "Maximum 20 characters per subject line (including spaces and punctuation). "
        "Every subject line must fit one of these five frameworks: Curiosity, Pain, "
        "Dream Outcome, Proof, Mistake."
    )


def load_welcome_block(creator_slug: str, base_dir: Path = None) -> str:
    """Load the per-creator welcome block from briefs/<slug>/welcome.md.

    Returns empty string if missing — the welcome block is required by the
    Personal Letter format, but missing files are handled gracefully so the
    agent can still run for creators who have not set one up.
    """
    _validate_creator_slug(creator_slug)
    base = Path(base_dir).resolve() if base_dir else _project_root
    path = base / "briefs" / creator_slug / "welcome.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _filter_subject_lines(options: list[dict]) -> list[dict]:
    """Drop options that violate the hard constraints.

    Keeps only options where:
    - option is a non-empty string ≤ SUBJECT_LINE_MAX_CHARS
    - framework is one of the five valid frameworks
    """
    kept: list[dict] = []
    for opt in options:
        if not isinstance(opt, dict):
            continue
        line = opt.get("option", "")
        framework = opt.get("framework", "")
        if not isinstance(line, str) or not line.strip():
            continue
        if len(line) > SUBJECT_LINE_MAX_CHARS:
            continue
        if framework not in _VALID_SUBJECT_FRAMEWORKS:
            continue
        kept.append({"option": line, "framework": framework})
    return kept


def generate_subject_lines(
    topic: str,
    format_slug: str,
    voice_profile_json: dict,
    client=None,
    base_dir: Path = None,
) -> list[dict]:
    """Generate 10–15 subject line options, enforcing hard rules.

    Applies post-filter to drop any option that exceeds SUBJECT_LINE_MAX_CHARS
    or uses an invalid framework. Retries once if the filtered set is too small.
    Returns the list of {option, framework} dicts.
    """
    if client is None:
        client = _ClaudeClient()

    rules = load_subject_line_rules(base_dir=base_dir)
    prompt = SUBJECT_LINE_PROMPT.format(
        voice_profile_json=json.dumps(voice_profile_json, indent=2),
        format_label=FORMAT_LABELS.get(format_slug, format_slug),
        topic=topic,
        subject_line_rules=rules,
    )

    filtered: list[dict] = []
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
            raw_options = data.get("subject_lines", [])
        except json.JSONDecodeError:
            raw_options = []

        filtered = _filter_subject_lines(raw_options)
        if 10 <= len(filtered) <= 15:
            return filtered

    raise RuntimeError(
        f"Subject line generation failed: after post-filter (≤{SUBJECT_LINE_MAX_CHARS} "
        f"chars, valid framework), got {len(filtered)} options — need 10–15."
    )


def suggest_cta(
    topic: str,
    subject_line: str,
    ctas_md: str,
    voice_profile_json: dict,
    client=None,
) -> dict:
    """Call Claude to suggest a CTA. Retries once on parse or schema failure."""
    if client is None:
        client = _ClaudeClient()

    prompt = CTA_SUGGESTION_PROMPT.format(
        core_identity=voice_profile_json.get("core_identity", ""),
        topic=topic,
        subject_line=subject_line,
        ctas_md=ctas_md,
    )

    last_error: str = ""
    for attempt in range(2):
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
            last_error = f"malformed JSON: {e}"
            continue

        missing = [k for k in ("suggested_cta_type", "suggested_cta_label", "rationale") if k not in data]
        if missing:
            last_error = f"missing required keys: {missing}"
            continue

        return data

    raise RuntimeError(
        f"CTA suggestion failed after retry: {last_error}"
    )


def run_draft(
    topic: str,
    subject_line: str,
    cta_entry: dict,
    format_slug: str,
    voice_profile_json: dict,
    newsletter_reference_md: str,
    learnings: list | None,
    client=None,
    welcome_block_text: str = "",
) -> str:
    """Stream a newsletter draft. Returns the accumulated text."""
    if client is None:
        client = _ClaudeClient()

    format_structure = FORMAT_STRUCTURES[format_slug]

    if format_slug == "roundup":
        verdict_label = voice_profile_json.get("roundup_verdict_label", "My take")
        format_structure = format_structure.replace("{verdict_label}", verdict_label)

    if newsletter_reference_md:
        reference_block = _REFERENCE_GUARD.format(reference=newsletter_reference_md)
    else:
        reference_block = ""

    if learnings:
        feedback_block = "\n\nOperator feedback from previous round to incorporate:\n" + \
            "\n".join(f"- {entry.get('feedback', '')}" for entry in learnings)
    else:
        feedback_block = ""

    if welcome_block_text and format_slug == "personal_letter":
        welcome_block = (
            "<welcome_block>\n"
            f"{welcome_block_text}\n"
            "</welcome_block>\n\n"
            "The welcome_block above is a fixed per-creator intro. Render it EXACTLY as given, "
            "in its own paragraph right after the opener, followed by a visual separator before "
            "the standalone CTA block. Do not rewrite, paraphrase, or decorate it.\n\n"
        )
    else:
        welcome_block = ""

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
        welcome_block=welcome_block,
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


def run_tastemaker(content_pack: str, brief: dict, client=None, learnings: list = None) -> str:
    """Run the Tastemaker Protocol prompt and return the full voice profile markdown.

    Streams output to console so the operator can watch progress.
    Returns the complete accumulated text.

    learnings: list of dicts from previous review rounds. Injected at the prompt level
    (not inside <content_pack>) so the model treats them as instructions, not creator content.
    """
    if client is None:
        client = _ClaudeClient()

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

    if learnings:
        feedback_block = "\n\nOperator feedback from previous round to incorporate:\n" + \
            "\n".join(f"- {entry.get('feedback', '')}" for entry in learnings)
        prompt = prompt + feedback_block

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
        client = _ClaudeClient()

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
        f"\n[bold green]Format selected:[/bold green] {FORMAT_LABELS[format_slug]}"
    )
    return data


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
    client = _ClaudeClient()
    round_number = 0

    while True:
        round_number += 1
        console.print(f"\n[dim]Running Tastemaker Protocol (round {round_number})...[/dim]\n")

        voice_profile_md = run_tastemaker(
            content_pack, brief, client=client, learnings=session.learnings or None
        )

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
    client=None,
) -> None:
    """Write voice-profile.md and voice-profile.json to their canonical locations."""
    base = Path(base_dir).resolve() if base_dir else _project_root
    if client is None:
        client = _ClaudeClient()

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
    except (RuntimeError, Exception) as e:
        console.print(f"\n[bold red]JSON extraction failed:[/bold red]\n{e}")
        console.print("The markdown voice profile has been saved. Re-run to retry JSON extraction.")
        return

    agent_dir = base / ".agent" / creator_slug
    agent_dir.mkdir(parents=True, exist_ok=True)
    json_path = agent_dir / "voice-profile.json"
    json_path.write_text(json.dumps(profile_json, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"[dim]JSON written: {json_path}[/dim]")


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
    """Display CTA suggestion and let operator accept or override."""
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

    confirm = ask(f"Format locked for {creator_slug}: {format_label} — proceed? (y/n)").strip().lower()
    if confirm not in ("y", "yes"):
        console.print("[yellow]Aborted.[/yellow]")
        sys.exit(0)

    topic = ask("What is this issue about? (1–3 sentences)").strip()
    if not topic:
        console.print("[red]Topic is required.[/red]")
        sys.exit(1)

    ctas_md = load_ctas_md(creator_slug, base_dir=base_dir)
    parsed_ctas = parse_ctas_md(ctas_md)

    newsletter_reference_md = load_newsletter_reference(base_dir=base_dir)
    if not newsletter_reference_md:
        console.print("[dim]newsletter-reference.md not found — proceeding without reference.[/dim]")

    welcome_block_text = load_welcome_block(creator_slug, base_dir=base_dir)
    if format_slug == "personal_letter" and not welcome_block_text:
        console.print(
            f"[yellow]WARNING: briefs/{creator_slug}/welcome.md not found — "
            f"Personal Letter format expects a welcome block. Proceeding without it.[/yellow]"
        )

    client = _ClaudeClient()

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

    console.print("\n[dim]Suggesting CTA...[/dim]")
    suggestion = suggest_cta(
        topic=topic,
        subject_line=chosen_subject,
        ctas_md=ctas_md,
        voice_profile_json=voice_profile_json,
        client=client,
    )
    cta_entry = _pick_cta(suggestion, parsed_ctas)

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
            welcome_block_text=welcome_block_text,
        )
        console.print(Panel(draft_body, title=f"Draft (Round {round_number})", style="white"))
        feedback = ask('Review the draft above. Type feedback to regenerate, or "save it" to finalise').strip()
        if feedback.lower() in ("save it", "save", "done", "lock it", "lock"):
            break
        draft_learnings.append({"round": round_number, "feedback": feedback})

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


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Writing Agent")
    parser.add_argument("--creator", required=True, help="Creator slug (e.g. kyle-cleankitchennutrition)")
    args = parser.parse_args()

    creator_slug = args.creator
    session = WritingSession(creator_slug=creator_slug)

    console.print(Panel(f"[bold green]Writing Agent[/bold green]\nCreator: {creator_slug}", style="green"))

    # Load positioning brief — exits with error if missing
    brief = load_strategy_brief(creator_slug)
    names = brief.get("newsletter_name") or ["—"]
    niche = brief.get("niche_umbrella") or "—"
    archetype = (brief.get("creator_archetype") or {}).get("primary") or "—"
    console.print(f"[dim]Brief loaded — Name: {names[0]} | Niche: {niche} | Archetype: {archetype}[/dim]")

    # Block 1 — Voice extraction
    if session.get("block1_done"):
        json_path = _project_root / ".agent" / creator_slug / "voice-profile.json"
        if not json_path.exists():
            console.print("[yellow]WARNING: Block 1 was marked complete but voice-profile.json is missing. JSON extraction may have failed on the previous run.[/yellow]")
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

    # Block 2 — Format selection (per-run, never locked)
    block2_data = step_block2(creator_slug)
    session.set("block2_done", True)
    session.save()

    # Block 3 — Draft generation (re-runnable)
    voice_profile_json = load_voice_profile_json(creator_slug)
    step_block3(
        creator_slug=creator_slug,
        session=session,
        voice_profile_json=voice_profile_json,
        block2_data=block2_data,
    )


if __name__ == "__main__":
    main()
