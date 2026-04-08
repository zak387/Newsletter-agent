# Writing Agent — Block 1 Design Spec
*Date: 2026-04-08*

## Purpose

Produce a complete voice profile for a creator by running the Tastemaker Protocol against their content pack. This is Block 1 of the writing agent. Blocks 2 (format and structure selection) and 3 (draft generation) are out of scope for this spec.

---

## Prerequisites

- Strategy agent must have been run for the creator. The writing agent reads `.agent/<creator-slug>/positioning-brief.json` before anything else.
- If the positioning brief is missing, the agent exits with a clear error message naming the missing file and instructing the operator to run the strategy agent first.

---

## Architecture

```
agents/writing/
    agent.py        ← CLI entry point, step orchestration
    session.py      ← not needed; agent.py imports Session from agents.strategy.session directly
```

### Run command
```bash
python agents/writing/agent.py --creator <creator-slug>
```

### Session state
Lives in `.agent/<creator-slug>/writing-session.json` — separate from the strategy agent's `session.json` to avoid key collisions. Block 1 is resumable: if `block1_done` is set in session, the agent skips to Block 2 (stub for now).

### Learnings
Stored in `.agent/<creator-slug>/writing-learnings.json`. Applied on every regeneration pass during the review loop.

---

## Block 1 — Voice Extraction via the Tastemaker Protocol

### Step 0 — Load positioning brief

Reads `.agent/<creator-slug>/positioning-brief.json`. Prints a one-line confirmation to the console (newsletter name candidate, niche, archetype) so the operator can confirm the right creator is loaded before proceeding.

### Step 1 — Content pack ingestion

Two input paths — the operator chooses:

**Path A — File input**
Operator provides a file path. Agent reads from disk. Supported formats: `.md`, `.txt`, `.pdf`. PDF text is extracted as plain text. If the file cannot be read or the format is unsupported, the agent surfaces a clear error and re-prompts.

**Path B — Direct paste**
Operator pastes content directly into the terminal. Agent reads from stdin until a sentinel line (`END` on its own line). A prompt explains the sentinel before input begins.

**Size guard**
After ingestion, the agent estimates token count (characters ÷ 4 as a conservative approximation). If the estimated count exceeds 80,000 tokens:
- Warns the operator with the estimated size
- Offers two options: truncate to 80k tokens (from the start of the content pack) or abort
- Does not proceed silently

### Step 2 — Run Tastemaker prompt

Injects the full content pack into the Tastemaker Protocol prompt (see prompt section below). Sends as a single Claude API call using `claude-opus-4-6` — this is a deep analysis task where quality takes priority over speed. Streams output to the console so the operator can see progress.

The positioning brief context (archetype, niche, ICP) is prepended to the content pack injection so the model has creator context before running the 20-question analysis.

### Step 3 — Human review loop

After the voice profile is generated:
- Displays the full profile in a Rich panel
- Operator types feedback to regenerate, or `"save it"` (or equivalent: `"done"`, `"lock it"`) to finalise
- Each round of feedback is stored to `writing-learnings.json` and included in the next regeneration call
- No round limit

### Step 4 — Write outputs

On lock:

| File | Purpose |
|------|---------|
| `briefs/<creator-slug>/voice-profile.md` | Operator-facing. The full rendered voice profile as produced by the model. No post-processing. |
| `.agent/<creator-slug>/voice-profile.json` | Canonical. Structured fields extracted from the markdown for downstream blocks. |

---

## Tastemaker Protocol Prompt

The full prompt is embedded in the agent (not a separate file). The content pack is injected at the `[INSERT CREATOR CONTENT PACK HERE]` placeholder. The positioning brief summary (archetype, niche, ICP) is injected before the content pack with a short framing sentence.

The prompt text is the Tastemaker Protocol as specified — unchanged. The agent does not modify or summarise the prompt.

---

## Voice Profile JSON Schema

Extracted from the markdown output in a second lightweight Claude call (not a regex parse — the structure is too variable). The extraction prompt asks for a JSON object matching the schema below.

```json
{
  "creator_name": "string",
  "core_identity": "string",
  "beliefs": [
    {"question": "string", "answer": "string"}
  ],
  "writing_mechanics": [
    {"question": "string", "answer": "string"}
  ],
  "aesthetic_crimes": [
    {"question": "string", "answer": "string"}
  ],
  "voice_and_personality": [
    {"question": "string", "answer": "string"}
  ],
  "structural_preferences": [
    {"question": "string", "answer": "string"}
  ],
  "hard_nos": [
    {"question": "string", "answer": "string"}
  ],
  "red_flags": [
    {"question": "string", "answer": "string"}
  ],
  "flagged_gaps": ["string"],
  "quick_reference": {
    "always": ["string"],
    "never": ["string"],
    "signature_phrases": ["string"],
    "voice_calibration_quotes": ["string"]
  },
  "what_matters_most": ["string", "string", "string"]
}
```

`what_matters_most` is always exactly three items: the creator's single most important belief, the one structural/stylistic pattern that most defines their voice, and the one thing they never do that AI writers default to.

---

## File Layout Summary

```
agents/
  writing/
    agent.py            ← imports Session from agents.strategy.session directly

.agent/<creator-slug>/
  positioning-brief.json    ← read-only input (written by strategy agent)
  writing-session.json      ← writing agent step state
  writing-learnings.json    ← feedback from review rounds
  voice-profile.json        ← canonical structured output

briefs/<creator-slug>/
  positioning-brief.md      ← written by strategy agent (not touched here)
  voice-profile.md          ← written by writing agent Block 1
```

---

## Error Handling

- Missing positioning brief → exit with named file path and instruction to run strategy agent
- Unreadable content pack file → clear error, re-prompt for input method
- Unsupported file format → list supported formats, re-prompt
- Content pack over size threshold → warn, offer truncate or abort
- Model returns malformed JSON on extraction pass → surface raw output, ask operator to retry
- All errors surface explicitly — no silent fallbacks

---

## Out of Scope

- Block 2 (format and structure selection) — stub only, not implemented
- Block 3 (draft generation) — not implemented
- Multi-file content packs (multiple uploads in one session) — not implemented; operator combines into one file before running
- PDF with images or scanned pages — text extraction only; image content is not processed
