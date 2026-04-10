# Writing Agent — Blocks 2 & 3 Design

Date: 2026-04-08
Status: Draft for review

## Context

Block 1 of the writing agent (Tastemaker voice extraction) is complete and shipped. This spec covers Blocks 2 and 3, which turn the locked voice profile into actual newsletter drafts.

The agent is operated via CLI: `python agents/writing/agent.py --creator <slug>`. Block 1 already runs on first invocation and is skipped on subsequent runs via `session.block1_done`. This spec extends that flow.

## Scope

In scope:
- Block 2: one-time format selection per creator.
- Block 3: per-issue draft generation, re-runnable indefinitely.
- Per-creator CTA library stored as markdown.
- Draft output files dated and slugged.

Out of scope:
- Deep Dive and Trends Report formats (not in operator's format menu).
- Topic research or selection — operator brings the topic.
- Multi-issue batch drafting.
- Automatic sending or scheduling.

## Block 2 — Format Selection (one-time)

### Purpose
Lock a single newsletter format for the creator. Run once. Never re-prompted unless the operator manually clears `block2.json`.

### Flow
1. If `.agent/<slug>/block2.json` exists, load it and skip to Block 3.
2. Otherwise, prompt the operator:
   ```
   Select the newsletter format for this creator:
     1 — Personal Letter
     2 — Roundup
     3 — Curation
   ```
3. Write `.agent/<slug>/block2.json`:
   ```json
   { "format": "personal_letter" }
   ```
   (values: `personal_letter` | `roundup` | `curation`)
4. Set `session.block2_done = True` and save.

### No review loop
Format selection is a single choice. No Claude call, no regeneration. The operator picks once.

## Block 3 — Draft Generation (per-issue, re-runnable)

### Inputs loaded from disk
- `.agent/<slug>/voice-profile.json` — locked voice profile from Block 1.
- `.agent/<slug>/block2.json` — locked format.
- `briefs/<slug>/ctas.md` — operator-maintained CTA library. **Required.** If missing, error out with a clear message telling the operator to create it.
- `newsletter-reference.md` (project root) — craft reference for inspiration only. Loaded as raw markdown and passed in the draft prompt with an explicit "do not copy" instruction.

### Flow

**Step 1 — Format confirmation**
Display a single-line confirmation so the operator can catch a wrong creator slug:
```
Format locked for <slug>: Personal Letter — proceed? (y/n)
```
If `n`, exit. No automatic format re-selection.

**Step 2 — Topic prompt**
```
What is this issue about? (1–3 sentences)
```
Free-text input. Stored in memory for the session; not persisted until the draft is saved.

**Step 3 — Subject line generation**
Single Claude call. Prompt inputs: voice profile JSON, topic, format.

Returns JSON:
```json
{
  "subject_lines": [
    {"option": "string", "framework": "confession | curiosity gap | quoted insight | direct promise | named mechanism | question | contrarian take | other"},
    ...
  ]
}
```
Must return **between 10 and 15** options. The prompt will specify this range explicitly.

Display to operator as a numbered list with the framework tag shown inline:
```
 1. [confession] I can't believe I almost bailed on this...
 2. [curiosity gap] Your mission, if you choose to accept...
 ...
15. [contrarian take] Why most creator advice is backwards
```
Prompt: `Pick a subject line (1–15), or type "regenerate" for a new batch:`

Regenerate loops back to the same Claude call with a note to produce different options. Picking a number locks that subject line.

**Step 4 — CTA auto-suggestion**
Single Claude call. Prompt inputs: the full `ctas.md` contents, topic, chosen subject line, voice profile core identity.

Returns JSON:
```json
{
  "suggested_cta_type": "intro | offer | assessment | community | content",
  "suggested_cta_label": "string — must match a label from ctas.md exactly",
  "rationale": "one-line string"
}
```

Display to operator:
```
Suggested CTA: [offer] Course launch — Q2
Reason: Topic directly aligns with the course's core promise.
Accept? (y / or enter label to override):
```
- `y` → accept.
- Any other text → treated as a label. Validated against `ctas.md`; re-prompts if no match.

The selected CTA's full entry (label + copy + link) is extracted from `ctas.md` and passed into the draft prompt.

**Step 5 — Draft generation**
Single streaming Claude call. Prompt inputs:
- Voice profile JSON (serialized)
- Format structure constant (the exact template for the locked format, held as a module-level string)
- Topic
- Chosen subject line + its framework
- Selected CTA (full entry)
- `newsletter-reference.md` contents, with a header: *"REFERENCE ONLY — study patterns and moves. Do not copy phrasing, tone, sentences, or structures from these examples. Voice comes exclusively from the voice profile above."*

The prompt must include explicit instructions:
- Write the full newsletter body following the format structure exactly.
- The P.S. is part of the draft — use the chosen CTA as the primary, and write a natural P.S. that complements it (may reference the CTA a second time or gesture to a related creator asset).
- Do not include any reasoning, preamble, or labels beyond what the format structure requires.
- Output format: subject line on the first line, then a blank line, then the full body.

Stream output to console so the operator can watch.

**Step 6 — Review loop**
After streaming completes, prompt:
```
Review the draft above. Type feedback to regenerate, or "save it" to finalise:
```
- `save it` / `save` / `done` / `lock it` / `lock` → lock the draft.
- Any other text → append to session learnings under a `block3_draft` key and regenerate. Feedback is injected into the draft prompt on the next round (same pattern as Block 1's `step_review_loop`).

**Step 7 — Write output**
- Directory: `briefs/<slug>/drafts/` (created if missing).
- Filename: `<YYYY-MM-DD>-<subject-slug>.md` where `<subject-slug>` is a lowercased, hyphenated, truncated (~60 char) slug of the chosen subject line.
- Contents: the draft exactly as produced, with a small YAML frontmatter header:
  ```yaml
  ---
  date: 2026-04-08
  format: personal_letter
  subject: "I can't believe I almost bailed on this..."
  cta: "Course launch — Q2"
  topic: "<topic as entered by operator>"
  ---
  ```
- If a file with the same date+slug already exists, append `-2`, `-3`, etc.

**Session state**
Block 3 does NOT set a `done` flag. It is intentionally re-runnable. Each invocation after Block 1 and Block 2 are done jumps straight to the Block 3 flow. Session learnings from Block 3 feedback are scoped per draft and cleared at the start of each new Block 3 run.

## Module layout

All changes in `agents/writing/agent.py`:

### New module-level constants
- `PERSONAL_LETTER_STRUCTURE` — the personal letter template from the spec brief, verbatim.
- `ROUNDUP_STRUCTURE` — the roundup template, verbatim.
- `CURATION_STRUCTURE` — the curation template, verbatim.
- `FORMAT_STRUCTURES` — dict mapping `{"personal_letter": ..., "roundup": ..., "curation": ...}`.
- `FORMAT_LABELS` — dict mapping slugs to human labels (`"personal_letter" → "Personal Letter"`).
- `SUBJECT_LINE_PROMPT` — prompt template for Step 3.
- `CTA_SUGGESTION_PROMPT` — prompt template for Step 4.
- `DRAFT_PROMPT` — prompt template for Step 5.

### New functions
- `load_voice_profile_json(creator_slug, base_dir=None) -> dict`
- `load_block2_data(creator_slug, base_dir=None) -> dict | None`
- `save_block2_data(creator_slug, data, base_dir=None) -> None`
- `load_ctas_md(creator_slug, base_dir=None) -> str` — raises `FileNotFoundError` with a clear operator-facing message if missing.
- `parse_ctas_md(ctas_md: str) -> list[dict]` — parses the markdown into `[{type, label, copy, link}, ...]` so we can look up by label after the auto-suggest call. Uses a simple heading + bullet parser; tolerant of minor formatting variations.
- `load_newsletter_reference(base_dir=None) -> str` — reads `newsletter-reference.md` from project root. Returns empty string with a warning if missing (not fatal — reference is inspiration, not required).
- `slugify_subject(subject: str) -> str` — lowercase, hyphenate, strip punctuation, truncate to ~60 chars.
- `step_block2(creator_slug, session) -> dict` — interactive format selection.
- `generate_subject_lines(topic, format_slug, voice_profile_json, client) -> list[dict]` — returns 10–15 options with frameworks.
- `suggest_cta(topic, subject_line, ctas_md, voice_profile_json, client) -> dict` — returns suggested CTA type + label + rationale.
- `run_draft(topic, subject_line, cta_entry, format_slug, voice_profile_json, newsletter_reference_md, learnings, client) -> str` — streams and returns the draft.
- `step_block3(creator_slug, session, brief, voice_profile_json, block2_data) -> None` — orchestrates Steps 1–7.
- `write_draft_file(creator_slug, subject_line, draft_body, topic, format_slug, cta_label, base_dir=None) -> Path` — writes the draft with frontmatter; handles collision suffixes.

### `main()` changes
Replace the `# Block 2 stub` section with:
```python
block2_data = load_block2_data(creator_slug)
if block2_data is None:
    block2_data = step_block2(creator_slug, session)
    session.set("block2_done", True)
    session.save()
else:
    console.print(f"[dim]Block 2 already complete — format: {FORMAT_LABELS[block2_data['format']]}.[/dim]")

voice_profile_json = load_voice_profile_json(creator_slug)
step_block3(creator_slug, session, brief, voice_profile_json, block2_data)
```

## Prompt design notes

### Subject line prompt
- Must explicitly require 10–15 options (model has historically drifted to exactly 10 without a range instruction — the range instruction should say "you MUST return between 10 and 15 options inclusive").
- Voice profile passed as-is.
- Framework tag must come from a closed list; any other value is accepted but normalized to `"other"`.
- Return JSON only, no markdown fences (same pattern as `extract_voice_profile_json`).

### CTA suggestion prompt
- The full `ctas.md` is passed as the canonical CTA source — the model must pick a label that exists in it verbatim.
- Rationale field is a single line, used only for operator display.
- If the operator overrides, we do NOT re-call the model — we just look up the override label in the parsed CTAs.

### Draft prompt
- Voice profile at the top, marked as "sole source of voice."
- Format structure next, marked as "follow exactly."
- Topic, subject line, CTA next.
- `newsletter-reference.md` LAST, with a clear "inspiration only, do not copy" guard so the model doesn't treat it as voice input.
- Previous-round feedback (from the review loop) is appended to the prompt as "operator feedback from previous round" — same pattern as Block 1's tastemaker.
- Output instructions: subject line first, blank line, body. No preamble, no reasoning, no structural labels beyond what the format requires.

## Error handling

- Missing `voice-profile.json` → error exit, instruct operator to re-run Block 1.
- Missing `ctas.md` → error exit with instructions to create the file, including the expected schema.
- Malformed `ctas.md` (no parseable entries) → error exit.
- Subject line JSON parse failure → retry once with a stricter instruction; then error.
- CTA suggestion JSON parse failure → retry once; then fall back to asking the operator to pick a CTA type and label manually.
- Draft streaming API error → error exit; no partial file written.
- File collision on draft output → append `-2`, `-3`, etc.

## Testing

Unit tests in `tests/writing/test_agent.py` (additions, not replacements):

- `test_load_block2_data_missing_returns_none`
- `test_save_and_load_block2_data_roundtrip`
- `test_load_ctas_md_missing_raises_with_instructions`
- `test_parse_ctas_md_basic` — happy path with 3 CTA types.
- `test_parse_ctas_md_tolerates_extra_whitespace`
- `test_slugify_subject_basic`
- `test_slugify_subject_truncates_long`
- `test_slugify_subject_strips_punctuation`
- `test_generate_subject_lines_parses_valid_json` — mocked client.
- `test_generate_subject_lines_rejects_fewer_than_10` — validates count; retries or errors.
- `test_generate_subject_lines_accepts_15_max`
- `test_suggest_cta_returns_valid_label` — mocked client, validates label exists in parsed CTAs.
- `test_suggest_cta_rejects_invalid_label` — model returns a label not in ctas.md → retry/fallback.
- `test_run_draft_injects_voice_profile_and_structure` — intercept prompt, assert both present.
- `test_run_draft_marks_newsletter_reference_as_inspiration_only` — intercept prompt, assert guard string present.
- `test_write_draft_file_writes_frontmatter`
- `test_write_draft_file_handles_collision`

No live API calls. All Anthropic client calls mocked.

## File structure after this work

```
agents/writing/agent.py                 (extended)
briefs/<slug>/
  voice-profile.md                      (Block 1 output, existing)
  ctas.md                               (operator-created, new)
  drafts/
    2026-04-08-i-cant-believe-i-almost-bailed.md   (Block 3 output)
.agent/<slug>/
  voice-profile.json                    (Block 1 output, existing)
  block2.json                           (Block 2 output, new)
  writing-session.json                  (existing, extended)
  writing-learnings.json                (existing, extended)
newsletter-reference.md                 (project root, existing)
```

## Non-goals reiterated

- No automatic format switching per issue.
- No topic generation.
- No copying from `newsletter-reference.md` — it is prompt-level inspiration only, explicitly guarded.
- No separate P.S. CTA selection — the P.S. is written as part of the draft using the single chosen CTA.
- No Deep Dive / Trends formats.
