# Niche Surfacing Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface five niche options (3 content-derived, 2 AI-inferred) in Step 1 for operator selection before Step 2 competitor research runs.

**Architecture:** Add `ai_inferred_niches` to the `public_research` subagent output, then rewrite `step1_niche()` in `agent.py` to display all five options and collect an operator selection instead of constructing a single candidate.

**Tech Stack:** Python, anthropic SDK, rich (console/prompt), pytest, unittest.mock

---

## File Map

| File | Change |
|---|---|
| `agents/strategy/skills/public_research.py` | Add `ai_inferred_niches` to system prompt and output validation |
| `agents/strategy/agent.py` | Rewrite `step1_niche()` to display 5 options and collect selection |
| `tests/strategy/skills/test_public_research.py` | Add test for `ai_inferred_niches` field |
| `tests/strategy/test_agent_step1.py` | New file — tests for the rewritten `step1_niche()` |

---

## Task 1: Add `ai_inferred_niches` to public_research subagent

**Files:**
- Modify: `agents/strategy/skills/public_research.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/strategy/skills/test_public_research.py`:

```python
def test_run_public_research_returns_ai_inferred_niches():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='''{
        "content_summary": "Creator posts about personal finance for millennials",
        "audience_signals": ["25-35 age range", "urban professionals"],
        "gaps_flagged": ["no survey data available"],
        "category_suggestion": "Personal transformation",
        "sub_niches": ["financial independence", "career transitions", "mindset"],
        "ai_inferred_niches": [
            {"niche": "debt-free living for millennials", "rationale": "High engagement on debt payoff content suggests an underserved core pain point"},
            {"niche": "financial identity for career changers", "rationale": "Credibility signals around career transitions overlap with financial anxiety content"}
        ]
    }''')]

    with patch("agents.strategy.skills.public_research.anthropic.Anthropic") as MockClient:
        mock_client = MockClient.return_value
        mock_client.messages.create.return_value = mock_response
        result = run_public_research(
            urls=["https://twitter.com/example"],
            human_context="Engagement rate around 4%",
        )

    assert "ai_inferred_niches" in result
    assert isinstance(result["ai_inferred_niches"], list)
    assert len(result["ai_inferred_niches"]) == 2
    assert "niche" in result["ai_inferred_niches"][0]
    assert "rationale" in result["ai_inferred_niches"][0]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "c:\Users\zakar\Newsletter agent v1" && python -m pytest tests/strategy/skills/test_public_research.py::test_run_public_research_returns_ai_inferred_niches -v
```

Expected: FAIL — `ai_inferred_niches` not in result (key missing from validation)

- [ ] **Step 3: Update the system prompt in `public_research.py`**

Replace the `SYSTEM_PROMPT` string in `agents/strategy/skills/public_research.py`:

```python
SYSTEM_PROMPT = """You are a creator research specialist. Your job is to audit a creator's public content and extract signals about their niche, audience, and positioning.

You will be given URLs to the creator's public content and any human-supplied context. Read what is available and extract:
- A summary of the creator's content focus
- Audience signals (age, profession, interests, purchasing behaviour)
- Gaps you could not confirm from the available data
- A suggested primary category (Jobs / Hobbies / Investments / Personal transformation)
- All plausible sub-niches visible in the content (list up to 5, drawn directly from what the creator publishes)
- Two AI-inferred niches: angles this creator could credibly own based on their credibility signals, audience response patterns, and content depth — not just what they currently publish. Each must include a one-line rationale explaining what in the data supports it.

Return ONLY a JSON object with these exact keys:
{
  "content_summary": "string",
  "audience_signals": ["string"],
  "gaps_flagged": ["string"],
  "category_suggestion": "string",
  "sub_niches": ["string"],
  "ai_inferred_niches": [
    {"niche": "string", "rationale": "string"},
    {"niche": "string", "rationale": "string"}
  ]
}"""
```

- [ ] **Step 4: Update the validation in `run_public_research()`**

Replace the `required` set and add a check for `ai_inferred_niches` structure:

```python
    required = {"content_summary", "audience_signals", "gaps_flagged", "category_suggestion", "sub_niches", "ai_inferred_niches"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Model response missing required keys: {missing}")
    if not isinstance(data["ai_inferred_niches"], list) or len(data["ai_inferred_niches"]) != 2:
        raise ValueError("ai_inferred_niches must be a list of exactly 2 objects")
    for item in data["ai_inferred_niches"]:
        if "niche" not in item or "rationale" not in item:
            raise ValueError("Each ai_inferred_niche must have 'niche' and 'rationale' keys")
    return data
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd "c:\Users\zakar\Newsletter agent v1" && python -m pytest tests/strategy/skills/test_public_research.py -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add agents/strategy/skills/public_research.py tests/strategy/skills/test_public_research.py
git commit -m "feat: add ai_inferred_niches to public_research subagent output"
```

---

## Task 2: Rewrite `step1_niche()` in agent.py

**Files:**
- Modify: `agents/strategy/agent.py:71-106`
- Create: `tests/strategy/test_agent_step1.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/strategy/test_agent_step1.py`:

```python
import pytest
from unittest.mock import patch, MagicMock, call
from agents.strategy.agent import step1_niche
from agents.strategy.session import Session


def _make_session(tmp_path, overrides=None):
    """Create a real Session instance backed by a temp directory."""
    with patch("agents.strategy.session.Session._session_dir", new_callable=lambda: property(lambda self: tmp_path)):
        session = Session.__new__(Session)
        session._data = overrides or {}
        session._learnings = []
        session._slug = "test-creator"
        session._path = tmp_path / "session.json"
        return session


def _make_ingest_result(sub_niches=None, ai_inferred_niches=None, category_suggestion="Personal transformation"):
    return {
        "content_summary": "Creator posts about gut health",
        "audience_signals": ["health-conscious adults"],
        "gaps_flagged": [],
        "category_suggestion": category_suggestion,
        "sub_niches": sub_niches or ["gut health", "clean eating", "label reading"],
        "ai_inferred_niches": ai_inferred_niches or [
            {"niche": "chronic illness recovery through food", "rationale": "High engagement on Crohn's content"},
            {"niche": "grocery education for families", "rationale": "Audience skews parents with young children"},
        ],
    }


def test_step1_displays_five_niches_and_returns_selection(tmp_path):
    session = _make_session(tmp_path)
    ingest_result = _make_ingest_result()

    # Operator selects option 2
    with patch("agents.strategy.agent.ask", return_value="Personal transformation") as mock_ask_category, \
         patch("builtins.input", return_value="2") as mock_input, \
         patch.object(session, "set") as mock_set, \
         patch.object(session, "save"):

        result = step1_niche(session, ingest_result)

    assert result == "clean eating"


def test_step1_operator_can_type_custom_niche(tmp_path):
    session = _make_session(tmp_path)
    ingest_result = _make_ingest_result()

    with patch("agents.strategy.agent.ask", return_value="Personal transformation"), \
         patch("builtins.input", side_effect=["0", "my custom niche"]), \
         patch.object(session, "set"), \
         patch.object(session, "save"):

        result = step1_niche(session, ingest_result)

    assert result == "my custom niche"


def test_step1_resumes_from_session(tmp_path):
    session = _make_session(tmp_path, overrides={
        "step1_done": True,
        "niche_candidate": "gut health",
    })

    result = step1_niche(session, _make_ingest_result())
    assert result == "gut health"


def test_step1_raises_if_session_corrupt(tmp_path):
    session = _make_session(tmp_path, overrides={
        "step1_done": True,
        "niche_candidate": None,
    })

    with pytest.raises(RuntimeError, match="niche_candidate is missing"):
        step1_niche(session, _make_ingest_result())
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "c:\Users\zakar\Newsletter agent v1" && python -m pytest tests/strategy/test_agent_step1.py -v
```

Expected: FAIL — `step1_niche` still has old implementation

- [ ] **Step 3: Rewrite `step1_niche()` in `agent.py`**

Replace the existing `step1_niche` function (lines 71–106) with:

```python
def step1_niche(session: Session, ingest_result: dict) -> str:
    console.print(Panel("[bold]Step 1 — Niche Selection[/bold]", style="blue"))

    if session.get("step1_done"):
        console.print("[dim]Step 1 already complete — loading from session.[/dim]")
        niche = session.get("niche_candidate")
        if niche is None:
            raise RuntimeError("Session claims step1 is done but niche_candidate is missing. Delete the session file and re-run.")
        return niche

    # Stage 1a — Category
    suggested_category = ingest_result.get("category_suggestion", "")
    console.print(f"\nSuggested primary category: [bold]{suggested_category}[/bold]")
    console.print(f"Available categories: {', '.join(CATEGORIES)}")
    ask("Confirm category or type a different one")

    # Stage 1b — Display five niche options
    sub_niches = ingest_result.get("sub_niches", [])[:3]
    ai_niches = ingest_result.get("ai_inferred_niches", [])[:2]

    console.print("\n[bold]Content-derived niches[/bold] (from your existing content):")
    for i, niche in enumerate(sub_niches, 1):
        console.print(f"  {i}. {niche}")

    console.print("\n[bold]AI-inferred niches[/bold] (from credibility signals and audience data):")
    for j, item in enumerate(ai_niches, len(sub_niches) + 1):
        console.print(f"  {j}. {item['niche']} [dim]— {item['rationale']}[/dim]")

    # Build ordered list for selection
    all_niches = list(sub_niches) + [item["niche"] for item in ai_niches]

    console.print("\nEnter a number (1–5) to select a niche, or 0 to type your own:")
    while True:
        choice = input("> ").strip()
        if choice == "0":
            niche_candidate = input("Enter your niche: ").strip()
            break
        if choice.isdigit() and 1 <= int(choice) <= len(all_niches):
            niche_candidate = all_niches[int(choice) - 1]
            break
        console.print(f"[yellow]Please enter a number between 0 and {len(all_niches)}.[/yellow]")

    console.print(f"\nSelected niche: [bold]{niche_candidate}[/bold]")

    session.set("niche_candidate", niche_candidate)
    session.set("step1_done", True)
    session.save()
    return niche_candidate
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd "c:\Users\zakar\Newsletter agent v1" && python -m pytest tests/strategy/test_agent_step1.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
cd "c:\Users\zakar\Newsletter agent v1" && python -m pytest -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add agents/strategy/agent.py tests/strategy/test_agent_step1.py
git commit -m "feat: rewrite step1_niche to surface 5 niche options before selection"
```

---

## Self-Review

**Spec coverage:**
- ✅ 3 content-derived niches from `sub_niches` — Task 2, Step 3 (`[:3]` slice)
- ✅ 2 AI-inferred niches from `ai_inferred_niches` — Task 1 (new field) + Task 2 (display)
- ✅ Each option labelled with source — Task 2, Step 3 (separate headed sections)
- ✅ Operator picks one before Step 2 runs — Task 2, Step 3 (selection gate)
- ✅ Operator can type custom niche — Task 2, Step 3 (choice == "0" branch)
- ✅ Session resume unchanged — Task 2, Step 3 (early return if `step1_done`)
- ✅ Steps 3–6 unchanged — no other files modified

**Placeholder scan:** None found.

**Type consistency:**
- `ai_inferred_niches` is a `list[dict]` with keys `niche` and `rationale` — consistent across Task 1 prompt, Task 1 validation, Task 2 display, and Task 2 tests.
- `sub_niches` remains a `list[str]` — no change to downstream consumers (Step 2 only receives `niche_candidate` string).
