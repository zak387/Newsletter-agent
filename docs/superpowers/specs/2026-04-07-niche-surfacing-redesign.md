# Niche Surfacing Redesign — Spec

**Date:** 2026-04-07
**Scope:** Strategy agent Step 1 and Step 2

---

## Problem

Step 1 currently produces a single niche candidate locked before any competitor research runs. This limits the operator to niches already visible in the creator's public content and bypasses hidden angles that credibility signals or audience responses might reveal.

---

## Solution

Split niche selection from competitor research. Step 1 surfaces five niche options for operator selection. Step 2 runs deep competitor research on the chosen niche only.

---

## Step 1 — Niche Surfacing (redesigned)

### What it produces

Five niche options presented to the operator before anything else runs:

| # | Source | Description |
|---|---|---|
| 1–3 | Content-derived | Sub-niches the creator demonstrably operates in, drawn from Step 0 public research data |
| 4–5 | AI-inferred | Niches surfaced from credibility signals, audience response patterns, and content depth — angles the creator hasn't fully leaned into but the data suggests they could own |

Each option is labelled with its source so the operator always knows where it came from.

### Operator interaction

The agent displays all five options and pauses. The operator picks one. No competitor research, no trend research, no synthesis runs until a niche is chosen.

### Changes to `public_research.py`

A new output field is added to the subagent response:

```json
"ai_inferred_niches": [
  {
    "niche": "string",
    "rationale": "string — why the data suggests this creator could own this angle"
  },
  {
    "niche": "string",
    "rationale": "string"
  }
]
```

The existing `sub_niches` field (list of strings) continues to supply the 3 content-derived options. The new `ai_inferred_niches` field supplies the 2 AI-inferred options.

### Stage 1a — Category classification

Unchanged. The operator confirms or corrects the primary category before niches are displayed.

### Stage 1b — Niche display (replaces sub-niche selection)

The agent displays all five options in a numbered list:

```
Content-derived niches (from your existing content):
  1. [niche]
  2. [niche]
  3. [niche]

AI-inferred niches (from credibility signals and audience data):
  4. [niche] — [rationale]
  5. [niche] — [rationale]
```

### Stage 1c — Operator selection (replaces niche candidate confirmation)

Operator types a number (1–5) or types their own niche if none fit. The selected niche is stored as `niche_candidate` in the session and passed to Step 2.

**Gate:** Pauses and waits for operator input before proceeding.

---

## Step 2 — Competitor Research (unchanged internally)

Step 2 receives `niche_candidate` as before and runs one focused `newsletter_research` subagent call. No changes to the subagent prompt or output schema.

The only change: `niche_candidate` now arrives as an operator-selected choice from five options rather than a constructed string from Stage 1c.

---

## Operator flow

```
Step 1a — category confirmed
Step 1b — 5 niches displayed (3 content-derived, 2 AI-inferred)
Step 1c — operator picks one → niche_candidate locked
Step 2  — full competitor research on chosen niche
Steps 3–6 — unchanged
```

---

## Files changed

| File | Change |
|---|---|
| `agents/strategy/skills/public_research.py` | Add `ai_inferred_niches` to system prompt and output schema |
| `agents/strategy/agent.py` | Rewrite `step1_niche()` to display 5 options and collect selection |

---

## Out of scope

- Steps 3–6 are unchanged
- No changes to `newsletter_research.py` or `trend_research.py`
- No changes to the brief output schema or renderer
