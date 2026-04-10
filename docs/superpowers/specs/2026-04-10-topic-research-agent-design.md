# Topic Research Agent — Design Spec

Date: 2026-04-10
Status: Draft for review

## Context

The writing agent currently has three blocks: Block 1 (voice profile extraction), Block 2 (format selection), Block 3 (draft generation). Topic selection in Block 3 is a free-text prompt — the operator types a topic with no research, sourcing, or qualification.

This spec adds a new Block 2 (Topic Research) that sources, qualifies, and confirms a topic before format selection. Current Block 2 becomes Block 3, current Block 3 becomes Block 4.

## Scope

In scope:
- New `agents/writing/topic_research.py` module with all topic research logic.
- Three source scans: content pack + external long-form (Source A), social media via LunarCrush/fallback (Source B), Reddit trending (Source C).
- Topic bank: dual storage (JSON canonical + MD human-readable). Append-only. Status tracking.
- Two operator gates: raw candidates → qualification → selection.
- Integration into writing agent `main()` as Block 2.
- Block renumbering: Block 1 (voice), Block 2 (topic), Block 3 (format), Block 4 (draft).

Out of scope:
- Copy writing. The topic agent produces a topic and format, nothing else.
- Automatic topic selection. The operator always selects.
- Google Scholar or additional research sources beyond Reddit.
- Multi-issue batch topic selection.

## New block ordering

```
Block 1: Voice Profile (unchanged, runs once per creator)
    ↓
Block 2: Topic Research (NEW — this spec)
    ↓ returns {creator, topic, format, source}
Block 3: Format Selection (currently Block 2 — receives format as default, operator confirms/overrides)
    ↓
Block 4: Draft Generation (currently Block 3 — receives topic from Block 2, no free-text prompt)
```

## Session state additions

New keys in `writing-session.json`:
- `block2_topic_done: bool` — guards re-running topic research within a session
- `selected_topic: string` — the confirmed topic text
- `selected_format: string` — the format declared by qualification (personal_letter / roundup / curation)
- `selected_source: string` — which source the topic came from (A / B / C)

## File locations

| File | Purpose | Format |
|---|---|---|
| `.agent/<slug>/topic_bank.json` | Canonical topic bank | JSON array |
| `briefs/<slug>/topics/topic_bank.md` | Human-readable topic bank | Markdown list |

Both files are always written together. The JSON is the source of truth. The MD is a render for the operator.

### Topic bank entry schema (JSON)

```json
{
  "topic": "string — one sentence",
  "date": "string — date if available, 'undated' if not",
  "source": "A | B | C",
  "status": "UNUSED | SELECTED",
  "selected_date": "string — date when selected, null if UNUSED"
}
```

### Topic bank entry format (MD)

```
- [Topic] · [Date] · Source: [A / B / C] · Status: UNUSED
```

When status changes to SELECTED:
```
- [Topic] · [Date] · Source: [A / B / C] · Status: SELECTED · [selected_date]
```

## Module: `agents/writing/topic_research.py`

### Layer 1 — Data functions (pure Python, no Claude)

#### `load_strategy_brief_fields(creator_slug, base_dir)`
Reads the strategy brief from `.agent/<slug>/strategy-brief.json`. Extracts and returns:
- `niche` — niche umbrella statement
- `sub_niche` — sub-niche description
- `niche_adjacency` — topics the creator can credibly cover beyond core niche
- `icp` — target reader description
- `instagram_handle` — extracted from brief, or None
- `tiktok_handle` — extracted from brief, or None
- `youtube_handle` — extracted from brief, or None
- `creator_name` — full name
- `podcast_name` — if mentioned, or None

If the strategy brief does not exist, print error and exit:
> "No strategy brief found for [slug]. Run the Strategy Agent first before running topic research."

#### `load_topic_bank(creator_slug, base_dir)`
Reads `.agent/<slug>/topic_bank.json`. Returns list of candidate dicts. Returns empty list if file does not exist.

#### `save_topic_bank(creator_slug, candidates, base_dir)`
Writes both `.agent/<slug>/topic_bank.json` and `briefs/<slug>/topics/topic_bank.md`.
- Reads existing bank first.
- Appends new candidates. Never overwrites existing entries.
- Deduplication: if a new candidate's topic text is substantially similar to an existing entry, skip it. Use simple string similarity, not Claude.
- Creates directories if they do not exist.

#### `update_topic_status(creator_slug, topic_text, status, date, base_dir)`
Finds the matching entry in both JSON and MD files. Updates status and selected_date. Does not remove any entries.

#### `scan_content_pack(creator_slug, base_dir)`
Reads the content pack from `briefs/<slug>/` or project root (check both locations).
- Parses section headers (## and ###) and content blocks.
- For each distinct topic/section, extracts a one-sentence topic summary and date if available.
- Returns list of `{topic, date, source: "A"}`.
- This is a Python-only parse. No Claude call.

#### `format_raw_candidates(candidates)`
Prints candidates grouped by source (A, B, C). For each candidate, shows only topic and date.
- If a source has no candidates, prints: `"[Source name] — no candidates found"`
- No filtering, ranking, sorting within sources, commentary, or recommendations.

#### `format_qualified_shortlist(qualified)`
Prints candidates grouped by format (Personal Letter, Roundup, Curation), not by source.
- FLAGGED candidates show the one-line flag note.
- Discarded candidates are not shown.
- No ranking within groups. No explanation of qualification logic.

### Layer 2 — Research functions (Claude CLI calls)

Each function shells out to the `claude` CLI with a research-specific prompt. The CLI has access to MCP (LunarCrush) and web search tools. Each function returns a list of candidate dicts.

#### `scan_external_longform(brief_fields, base_dir)`
Sends a Claude CLI prompt containing the creator's name, YouTube handle, podcast name, and any known website/blog URL from the brief.

Claude CLI prompt instructions:
- Search the creator's YouTube channel — scan video titles and descriptions.
- Search the creator's podcast — scan episode titles and descriptions on whatever platform they publish to.
- Search the creator's website or blog — scan post titles and available summaries.
- For each candidate, return JSON: `{"topic": "one sentence", "date": "date if available"}`.
- Return up to 15 candidates.

Returns list of `{topic, date, source: "A"}`.

#### `scan_social_media(brief_fields, base_dir)`
Sends a Claude CLI prompt containing the creator's social handles.

Claude CLI prompt instructions:
- Confirm LunarCrush MCP is available by attempting a call. If tools are not available, fall back to Method 2.
- **Method 1 — LunarCrush (primary):**
  - Call Creator_Posts with Instagram handle first: `network: instagram, screenName: [handle], interval: 1m, limit: 20`.
  - If Instagram returns limited or no results, try TikTok: `network: tiktok, screenName: [handle], interval: 1m, limit: 20`.
  - If both return limited results, extend interval to 3m.
  - If no Instagram or TikTok, try YouTube: `network: youtube, screenName: [handle], interval: 1m, limit: 20`.
  - Sort results by engagements descending. Keep top 10.
- **Method 2 — TikTok via Google search (fallback):**
  - Run two searches: `"[tiktok handle]" tiktok site:tiktok.com` and `"[tiktok handle]" tiktok [current year] site:tiktok.com`.
  - Only record posts where caption content is visible in the search snippet.
- If the creator has no surfaceable social presence through either method, return empty list.
- For each candidate, return JSON: `{"topic": "one sentence", "date": "date if available"}`.

Returns list of `{topic, date, source: "B"}`.

#### `scan_trending(brief_fields, base_dir)`
Sends a Claude CLI prompt containing niche, sub-niche, niche adjacency, and ICP.

Claude CLI prompt instructions:
- Derive 3 to 5 subreddits where the creator's ICP is likely active. Derive from the strategy brief, never hardcode.
- State which subreddits you are scanning before running searches.
- Run 2 to 3 targeted web searches scoped to the last 30 days using niche keywords combined with the identified subreddits.
- Look for: questions or confusion the ICP is actively expressing, debates or disagreements with significant comment volume, a trend/product/study/news item generating discussion, a topic the audience would immediately recognize as relevant.
- Posts from the last 30 days only. Do not surface threads older than 30 days unless actively receiving new comments.
- Surface up to 5 candidates. Quality over quantity.
- For each candidate, return JSON: `{"topic": "one sentence", "date": "date if available"}`.

Returns list of `{topic, date, source: "C"}`.

#### `qualify_candidates(candidates, brief_fields, base_dir)`
Sends a Claude CLI prompt containing all candidates and the full niche adjacency statement from the brief.

Claude CLI prompt instructions:

**Test 1 — Niche fit:**
Read the niche adjacency statement. For each candidate ask: "Can this creator credibly cover this topic, and does it connect, even loosely, to their core niche?"
- PASS — clear connection. Keep.
- FLAGGED — loose or indirect connection. Keep, with a one-sentence note explaining the connection so the operator can decide.
- DISCARD — no meaningful connection. Remove silently.

**Test 2 — Format fit (only on PASS/FLAGGED candidates):**
For each remaining candidate ask: "What format does this topic naturally want to be?"
- PERSONAL LETTER — topic came from Source A or B, creator has lived experience or strong POV, creator is the protagonist, goes deeper on a single idea.
- ROUNDUP — topic involves multiple recent items/stories/angles that work better aggregated than explored individually, creator is the curator, topic is the container.
- CURATION — topic is best served by gathered links/findings/resources around a theme, creator's voice is lighter, more pointing less analyzing, most likely from Source C.
- If a topic could work in more than one format, declare the primary format and note the alternative.

Return JSON array: `[{"topic": "...", "date": "...", "source": "A|B|C", "status": "PASS|FLAGGED", "flag_note": "one sentence or null", "format": "personal_letter|roundup|curation", "alt_format": "format or null"}]`.

Do not return discarded candidates.

### Layer 3 — Orchestration

#### `step_block2_topic(creator_slug, session, base_dir)`

This is the main entry point called by `main()` in `agent.py`.

**Flow:**

```
1. LOAD BEFORE STARTING
   - Call load_strategy_brief_fields(). If missing, exit with error.
   - Extract all required fields.
   - If no social handles found, print:
     "I need the creator's social media handles to run Step 2.
      Please provide their Instagram and/or TikTok handle."
     Then prompt for input. If none provided, Source B will return empty.

2. CHECK TOPIC BANK
   - Call load_topic_bank().
   - If bank has unused candidates:
     - Print: "There are [N] unused topic candidates already in the bank
       for [creator name]. Want to use those before running a new scan?"
     - Wait for operator input.
     - If operator says YES: skip to step 6 (present raw) using bank candidates only.
     - If operator says NO: continue to step 3.
   - If bank is empty or does not exist: continue to step 3.

3. SOURCE SCAN A — LONG-FORM ARCHIVE
   - Call scan_content_pack() — Python, local file parse.
   - Call scan_external_longform() — Claude CLI, searches YouTube/podcast/blog.
   - Combine results into source_a candidates.

4. SOURCE SCAN B — RECENT BEST POSTS
   - Call scan_social_media() — Claude CLI, LunarCrush/fallback.

5. SOURCE SCAN C — WHAT PEOPLE ARE TALKING ABOUT NOW
   - Call scan_trending() — Claude CLI, Reddit via web search.

6. MERGE AND SAVE
   - Combine all fresh candidates (steps 3-5) with any unused bank candidates.
   - Call save_topic_bank() — appends new, preserves existing.
   - Print: "All [N] candidates have been saved to the topic bank."

7. GATE 1 — PRESENT RAW CANDIDATES
   - Call format_raw_candidates() — grouped by source.
   - Print: "Ready to qualify when you are."
   - Wait for operator input (Enter to proceed).

8. QUALIFY
   - Call qualify_candidates() — Claude CLI, niche fit + format fit.

9. GATE 2 — PRESENT QUALIFIED SHORTLIST
   - Call format_qualified_shortlist() — grouped by format.
   - Print: "Which topic do you want to run with?"
   - Operator enters a number.

10. HANDLE SELECTION
    - If selected topic was FLAGGED:
      Print: "[Topic] was flagged — [flag note]. Confirmed you want to proceed?"
      Wait for confirmation. If operator picks different topic, use that.
    - If operator enters a topic NOT on the shortlist:
      Print: "That one wasn't in the qualified shortlist. Want me to add it
      and proceed, or pick from the list?"
      Handle accordingly.

11. CONFIRM AND UPDATE
    - Print confirmation:
      CONFIRMED
      Creator: [name]
      Topic: [selected topic]
      Format: [format]
      Source: [A / B / C]
    - Call update_topic_status() — UNUSED → SELECTED with today's date.

12. HANDOFF
    - Print: "Handing off to the Writer. Topic: [topic]. Format: [format]."
    - Return dict:
      {
        "creator": creator_name,
        "topic": selected topic text,
        "format": declared format (personal_letter / roundup / curation),
        "source": "A" / "B" / "C",
        "tone_profile_path": "briefs/<slug>/voice-profile.md",
        "strategy_brief_path": "briefs/<slug>/strategy-brief.md"
      }
```

## Changes to `agents/writing/agent.py`

### Block renumbering

| Current | New | Function |
|---|---|---|
| Block 1: Voice Profile | Block 1: Voice Profile (unchanged) | `step_ingest_content_pack()`, `step_review_loop()`, `step_write_outputs()` |
| — | Block 2: Topic Research (NEW) | `step_block2_topic()` from `topic_research.py` |
| Block 2: Format Selection | Block 3: Format Selection | `step_block3_format()` (renamed from `step_block2()`) |
| Block 3: Draft Generation | Block 4: Draft Generation | `step_block4_draft()` (renamed from `step_block3()`) |

### Changes to `main()`

```python
def main():
    # ... argparse, creator_slug ...
    session = WritingSession(creator_slug=creator_slug)

    # Block 1 — Voice Profile (unchanged, skip if done)
    if not session.get("block1_done"):
        # ... existing Block 1 flow ...
        session.set("block1_done", True)
        session.save()

    # Block 2 — Topic Research (NEW)
    from agents.writing.topic_research import step_block2_topic
    topic_result = step_block2_topic(creator_slug, session, base_dir=_project_root)
    # topic_result = {creator, topic, format, source, tone_profile_path, strategy_brief_path}

    # Block 3 — Format Selection (receives format as default)
    block3_data = step_block3_format(creator_slug, base_dir=_project_root,
                                      default_format=topic_result["format"])
    session.set("block3_done", True)
    session.save()

    # Block 4 — Draft Generation (receives topic from Block 2, no free-text prompt)
    voice_profile_json = load_voice_profile_json(creator_slug, base_dir=_project_root)
    step_block4_draft(creator_slug, session, voice_profile_json, block3_data,
                      topic=topic_result["topic"])
```

### Changes to format selection (`step_block3_format`)

Currently `step_block2()`. Rename to `step_block3_format()`. Add a `default_format` parameter:
- If `default_format` is provided, show it as the pre-selected option:
  ```
  Topic research suggests: Personal Letter
  Select the newsletter format for this creator:
    1 — Personal Letter (suggested)
    2 — Roundup
    3 — Curation
  ```
- Operator can accept the suggestion (Enter) or override with a different choice.
- Rest of the logic stays the same.

### Changes to draft generation (`step_block4_draft`)

Currently `step_block3()`. Rename to `step_block4_draft()`. Add a `topic` parameter:
- Remove the free-text topic prompt (`ask("What is this issue about?")`).
- Use the `topic` parameter passed from Block 2 instead.
- Rest of the flow (subject lines, CTA, draft, review loop) stays the same.

## Claude CLI prompt templates

Each research function sends a prompt to the `claude` CLI. The prompts are stored as string constants in `topic_research.py` (following the pattern in `agent.py` where `TASTEMAKER_PROMPT`, `DRAFT_PROMPT`, etc. are module-level constants).

Each prompt:
- Includes all spec instructions for that step verbatim.
- Specifies the exact JSON output format expected.
- Includes the creator context (brief fields) injected via `.format()`.
- Ends with: "Return ONLY the JSON array. No commentary, no explanation."

### Prompt constants

| Constant | Used by | Purpose |
|---|---|---|
| `EXTERNAL_LONGFORM_PROMPT` | `scan_external_longform()` | YouTube, podcast, blog scan |
| `SOCIAL_MEDIA_PROMPT` | `scan_social_media()` | LunarCrush + fallback |
| `TRENDING_PROMPT` | `scan_trending()` | Reddit via web search |
| `QUALIFICATION_PROMPT` | `qualify_candidates()` | Niche fit + format fit |

## Immutable rules enforcement

| Rule | How enforced |
|---|---|
| 1. All three scans run before candidates presented (unless bank reuse) | Orchestration flow: steps 3-5 always run before step 7, unless operator chose bank reuse at step 2 |
| 2. Raw candidates always presented before qualification | Step 7 (Gate 1) always precedes step 8 (qualify) |
| 3. All candidates saved to bank before selection | Step 6 (save) precedes step 7 (present) which precedes step 9 (select) |
| 4. Agent never selects the topic | Step 9: operator always picks. Python waits for input. |
| 5. Niche fit derived from strategy brief | `qualify_candidates()` prompt includes niche adjacency from brief |
| 6. Format declared by agent based on properties | `qualify_candidates()` prompt includes format fit criteria |
| 7. Topic bank never overwritten, only appended/updated | `save_topic_bank()` reads existing, appends new. `update_topic_status()` modifies in place. |
| 8. Flagged candidates surfaced with note | Step 10 handles FLAGGED acknowledgment |
| 9. Agent never writes copy | Module returns topic + format only. No draft text. |
| 10. No step skipped, sequence every time | Python orchestration enforces step order |

## Testing

### Unit tests (`tests/writing/test_topic_research.py`)

| Test | What it covers |
|---|---|
| `test_load_topic_bank_empty` | Returns empty list when no file exists |
| `test_load_topic_bank_existing` | Parses existing JSON correctly |
| `test_save_topic_bank_append` | New candidates appended, existing preserved |
| `test_save_topic_bank_dedup` | Duplicate topics not appended |
| `test_save_topic_bank_creates_dirs` | Creates briefs/<slug>/topics/ if missing |
| `test_save_topic_bank_dual_write` | Both JSON and MD files written |
| `test_update_topic_status` | Status changes from UNUSED to SELECTED with date |
| `test_update_topic_status_preserves_others` | Other entries unchanged |
| `test_scan_content_pack_parses_sections` | Extracts topics from content pack headers |
| `test_scan_content_pack_missing_file` | Returns empty list, does not crash |
| `test_format_raw_candidates_groups_by_source` | Output grouped A, B, C |
| `test_format_raw_candidates_empty_source` | Prints "[Source] — no candidates found" |
| `test_format_qualified_shortlist_groups_by_format` | Output grouped by format |
| `test_format_qualified_shortlist_shows_flags` | FLAGGED entries show note |
| `test_format_qualified_shortlist_hides_discarded` | DISCARD entries not shown |
| `test_load_strategy_brief_fields_extracts_all` | All required fields returned |
| `test_load_strategy_brief_fields_missing` | Prints error, calls sys.exit |
| `test_md_format_matches_spec` | MD output matches `- [Topic] · [Date] · Source: [X] · Status: UNUSED` |

Research and qualification functions (`scan_external_longform`, `scan_social_media`, `scan_trending`, `qualify_candidates`) are integration tests — they require Claude CLI. These are tested manually or via a dedicated integration test suite that is not part of the unit test run.
