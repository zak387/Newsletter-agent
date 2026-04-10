# Strategy Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI-based strategy agent that runs once per creator, researches their niche via Claude subagents, asks the operator targeted questions, and produces a locked strategy brief in Markdown and JSON.

**Architecture:** Step-based state machine where each step reads and writes to a session file in `.agent/<creator-slug>/`. Three skills (`public_research`, `newsletter_research`, `trend_research`) run as Claude subagents via the Anthropic SDK. The agent runs as a single Python entry point (`agents/strategy/agent.py`) with all step logic inlined.

**Tech Stack:** Python 3.11+, `anthropic` SDK (claude-sonnet-4-6), `rich` for CLI output, `json` + `pathlib` for state, no database.

---

## File Map

| File | Responsibility |
|---|---|
| `agents/strategy/agent.py` | Entry point + full step orchestration (Steps 0–6) |
| `agents/strategy/skills/public_research.py` | Claude subagent: creator content audit (Steps 0–1) |
| `agents/strategy/skills/newsletter_research.py` | Claude subagent: competitor research (Step 2) |
| `agents/strategy/skills/trend_research.py` | Claude subagent: trend + niche validation (Step 3) |
| `agents/strategy/renderer.py` | Renders strategy brief dict → Markdown string |
| `agents/strategy/session.py` | Read/write session.json and learnings.json |

---

## Task 1: Project bootstrap and dependencies

**Files:**
- Create: `requirements.txt`
- Create: `agents/__init__.py`
- Create: `agents/strategy/__init__.py`
- Create: `agents/strategy/skills/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
anthropic>=0.40.0
rich>=13.0.0
```

- [ ] **Step 2: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: both packages install without error.

- [ ] **Step 3: Create empty `__init__.py` files**

```bash
touch agents/__init__.py agents/strategy/__init__.py agents/strategy/skills/__init__.py
```

- [ ] **Step 4: Verify Python version**

```bash
python --version
```

Expected: Python 3.11 or higher.

- [ ] **Step 5: Commit**

```bash
git init
git add requirements.txt agents/__init__.py agents/strategy/__init__.py agents/strategy/skills/__init__.py
git commit -m "chore: bootstrap project structure and dependencies"
```

---

## Task 2: Session state manager

**Files:**
- Create: `agents/strategy/session.py`
- Create: `tests/strategy/test_session.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/strategy/test_session.py`:

```python
import json
import pytest
from pathlib import Path
from agents.strategy.session import Session

def test_session_creates_files_on_save(tmp_path):
    s = Session(creator_slug="test-creator", base_dir=tmp_path)
    s.set("step", 0)
    s.save()
    assert (tmp_path / ".agent" / "test-creator" / "session.json").exists()

def test_session_loads_existing_state(tmp_path):
    s = Session(creator_slug="test-creator", base_dir=tmp_path)
    s.set("niche", "personal finance")
    s.save()

    s2 = Session(creator_slug="test-creator", base_dir=tmp_path)
    assert s2.get("niche") == "personal finance"

def test_session_get_returns_default_when_missing(tmp_path):
    s = Session(creator_slug="test-creator", base_dir=tmp_path)
    assert s.get("missing_key", default="fallback") == "fallback"

def test_learnings_append_and_load(tmp_path):
    s = Session(creator_slug="test-creator", base_dir=tmp_path)
    s.append_learning({"round": 1, "feedback": "change the name"})
    s.append_learning({"round": 2, "feedback": "sharpen the ICP"})
    s.save()

    s2 = Session(creator_slug="test-creator", base_dir=tmp_path)
    assert len(s2.learnings) == 2
    assert s2.learnings[0]["feedback"] == "change the name"

def test_save_brief_json(tmp_path):
    s = Session(creator_slug="test-creator", base_dir=tmp_path)
    s.save_brief_json({"newsletter_name": ["Option A", "Option B", "Option C"]})
    brief_path = tmp_path / ".agent" / "test-creator" / "strategy-brief.json"
    assert brief_path.exists()
    data = json.loads(brief_path.read_text())
    assert data["newsletter_name"][0] == "Option A"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/strategy/test_session.py -v
```

Expected: ImportError or ModuleNotFoundError — `session.py` does not exist yet.

- [ ] **Step 3: Implement `agents/strategy/session.py`**

```python
import json
from pathlib import Path


class Session:
    def __init__(self, creator_slug: str, base_dir: Path = None):
        self.creator_slug = creator_slug
        self.base_dir = Path(base_dir) if base_dir else Path(".")
        self._dir = self.base_dir / ".agent" / creator_slug
        self._session_file = self._dir / "session.json"
        self._learnings_file = self._dir / "learnings.json"
        self._state: dict = {}
        self.learnings: list = []
        self._load()

    def _load(self):
        if self._session_file.exists():
            self._state = json.loads(self._session_file.read_text(encoding="utf-8"))
        if self._learnings_file.exists():
            self.learnings = json.loads(self._learnings_file.read_text(encoding="utf-8"))

    def get(self, key: str, default=None):
        return self._state.get(key, default)

    def set(self, key: str, value):
        self._state[key] = value

    def append_learning(self, entry: dict):
        self.learnings.append(entry)

    def save(self):
        self._dir.mkdir(parents=True, exist_ok=True)
        self._session_file.write_text(
            json.dumps(self._state, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        self._learnings_file.write_text(
            json.dumps(self.learnings, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def save_brief_json(self, brief: dict):
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / "strategy-brief.json"
        path.write_text(json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/strategy/test_session.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/strategy/session.py tests/strategy/test_session.py
git commit -m "feat: session state manager with learnings and brief persistence"
```

---

## Task 3: Markdown renderer

**Files:**
- Create: `agents/strategy/renderer.py`
- Create: `tests/strategy/test_renderer.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/strategy/test_renderer.py`:

```python
from agents.strategy.renderer import render_brief

def test_render_includes_all_sections():
    brief = {
        "newsletter_name": ["The Long Game", "Signal vs Noise", "Compound Weekly"],
        "newsletter_name_rationale": ["Reflects compounding growth", "Cuts through clutter", "Weekly cadence + value"],
        "niche_umbrella": "Personal transformation > mindset + longevity for high-performers",
        "niche_rationale": "Competitor landscape is thin above surface-level productivity content",
        "target_reader": "A 34-year-old operations manager who reads widely but acts rarely.",
        "newsletter_statement": "This newsletter helps high-performers achieve sustainable output by applying systems thinking to personal health.",
        "why_exist": "Search interest in burnout recovery has grown 40% YoY. No newsletter owns this frame for professionals.",
        "why_creator": "Spent 3 years recovering from adrenal fatigue while running a team of 12. Built the system she wished existed.",
        "content_pillars": [
            {"name": "The Protocol", "description": "Evidence-based recovery and performance routines"},
            {"name": "The Mistake", "description": "What high-performers get wrong and the fix"},
            {"name": "The Read", "description": "One curated resource per week with a contrarian take"},
        ],
        "creator_archetype": {"primary": "Experimenter", "secondary": "Expert", "evidence": "Publishes weekly self-experiments with tracked outcomes"},
        "business_model": "Affiliates only (under 5k subscribers)",
        "competitor_insight": "No newsletter in this space pairs recovery science with operational thinking. Most competitors are either too clinical or too motivational.",
        "comparable_newsletter": "Dan Go's High Performance Founder — similar reader but focused on physical performance, not recovery systems.",
    }
    md = render_brief(brief)
    assert "## Newsletter Name" in md
    assert "The Long Game" in md
    assert "## Target Reader" in md
    assert "## Newsletter Statement" in md
    assert "## Content Pillars" in md
    assert "## Creator Archetype" in md
    assert "## Business Model" in md
    assert "## Competitor Insight" in md

def test_render_blank_field_shows_note():
    brief = {
        "newsletter_name": None,
        "newsletter_name_rationale": None,
        "niche_umbrella": None,
        "niche_rationale": None,
        "target_reader": None,
        "newsletter_statement": None,
        "why_exist": None,
        "why_creator": None,
        "content_pillars": None,
        "creator_archetype": None,
        "business_model": None,
        "competitor_insight": None,
        "comparable_newsletter": None,
    }
    md = render_brief(brief)
    assert "_Not yet completed_" in md
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/strategy/test_renderer.py -v
```

Expected: ImportError — `renderer.py` does not exist yet.

- [ ] **Step 3: Implement `agents/strategy/renderer.py`**

```python
def _field(value: str | None) -> str:
    return value if value else "_Not yet completed_"


def render_brief(brief: dict) -> str:
    lines = ["# Strategy Brief", ""]

    # Newsletter name
    lines += ["## Newsletter Name", ""]
    names = brief.get("newsletter_name") or []
    rationales = brief.get("newsletter_name_rationale") or []
    if names:
        for name, rationale in zip(names, rationales):
            lines.append(f"**{name}** — {rationale}")
    else:
        lines.append("_Not yet completed_")
    lines.append("")

    # Niche umbrella
    lines += ["## Niche Umbrella", ""]
    lines.append(_field(brief.get("niche_umbrella")))
    if brief.get("niche_rationale"):
        lines += ["", f"_{brief['niche_rationale']}_"]
    lines.append("")

    # Target reader
    lines += ["## Target Reader", ""]
    lines.append(_field(brief.get("target_reader")))
    lines.append("")

    # Newsletter statement
    lines += ["## Newsletter Statement", ""]
    lines.append(_field(brief.get("newsletter_statement")))
    lines.append("")

    # Why exist
    lines += ["## Why Does This Content Need to Exist?", ""]
    lines.append(_field(brief.get("why_exist")))
    lines.append("")

    # Why creator
    lines += ["## Why This Creator Specifically?", ""]
    lines.append(_field(brief.get("why_creator")))
    lines.append("")

    # Content pillars
    lines += ["## Content Pillars", ""]
    pillars = brief.get("content_pillars") or []
    if pillars:
        for i, pillar in enumerate(pillars, 1):
            lines.append(f"**{i}. {pillar['name']}** — {pillar['description']}")
    else:
        lines.append("_Not yet completed_")
    lines.append("")

    # Creator archetype
    lines += ["## Creator Archetype", ""]
    archetype = brief.get("creator_archetype")
    if archetype:
        label = archetype["primary"]
        if archetype.get("secondary"):
            label += f" (with {archetype['secondary']} as modifier)"
        lines.append(f"**{label}**")
        if archetype.get("evidence"):
            lines.append(f"_{archetype['evidence']}_")
    else:
        lines.append("_Not yet completed_")
    lines.append("")

    # Business model
    lines += ["## Business Model", ""]
    lines.append(_field(brief.get("business_model")))
    lines.append("")

    # Competitor insight
    lines += ["## Competitor Insight", ""]
    lines.append(_field(brief.get("competitor_insight")))
    lines.append("")

    # Comparable newsletter
    lines += ["## Comparable Newsletter", ""]
    lines.append(_field(brief.get("comparable_newsletter")))
    lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/strategy/test_renderer.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/strategy/renderer.py tests/strategy/test_renderer.py
git commit -m "feat: strategy brief markdown renderer"
```

---

## Task 4: Public research skill (subagent)

**Files:**
- Create: `agents/strategy/skills/public_research.py`
- Create: `tests/strategy/skills/test_public_research.py`

- [ ] **Step 1: Write the failing test**

Create `tests/strategy/skills/test_public_research.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from agents.strategy.skills.public_research import run_public_research

def test_run_public_research_returns_dict():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='''{
        "content_summary": "Creator posts about personal finance for millennials",
        "audience_signals": ["25-35 age range", "urban professionals"],
        "gaps_flagged": ["no survey data available"],
        "category_suggestion": "Personal transformation",
        "sub_niches": ["financial independence", "career transitions", "mindset"]
    }''')]

    with patch("agents.strategy.skills.public_research.anthropic.Anthropic") as MockClient:
        mock_client = MockClient.return_value
        mock_client.messages.create.return_value = mock_response
        result = run_public_research(
            urls=["https://twitter.com/example"],
            human_context="Engagement rate around 4%",
        )

    assert "content_summary" in result
    assert "sub_niches" in result
    assert isinstance(result["sub_niches"], list)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/strategy/skills/test_public_research.py -v
```

Expected: ImportError — file does not exist.

- [ ] **Step 3: Implement `agents/strategy/skills/public_research.py`**

```python
import json
import anthropic

SYSTEM_PROMPT = """You are a creator research specialist. Your job is to audit a creator's public content and extract signals about their niche, audience, and positioning.

You will be given URLs to the creator's public content and any human-supplied context. Read what is available and extract:
- A summary of the creator's content focus
- Audience signals (age, profession, interests, purchasing behaviour)
- Gaps you could not confirm from the available data
- A suggested primary category (Jobs / Hobbies / Investments / Personal transformation)
- All plausible sub-niches visible in the content

Return ONLY a JSON object with these exact keys:
{
  "content_summary": "string",
  "audience_signals": ["string"],
  "gaps_flagged": ["string"],
  "category_suggestion": "string",
  "sub_niches": ["string"]
}"""


def run_public_research(urls: list[str], human_context: str = "") -> dict:
    client = anthropic.Anthropic()

    url_list = "\n".join(f"- {u}" for u in urls) if urls else "No URLs provided."
    context_block = f"\nHuman-supplied context:\n{human_context}" if human_context else ""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Creator content URLs:\n{url_list}{context_block}\n\nPlease audit this creator's public content and return the JSON object.",
            }
        ],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/strategy/skills/test_public_research.py -v
```

Expected: 1 test PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/strategy/skills/public_research.py tests/strategy/skills/test_public_research.py
git commit -m "feat: public research subagent skill"
```

---

## Task 5: Newsletter research skill (subagent)

**Files:**
- Create: `agents/strategy/skills/newsletter_research.py`
- Create: `tests/strategy/skills/test_newsletter_research.py`

- [ ] **Step 1: Write the failing test**

Create `tests/strategy/skills/test_newsletter_research.py`:

```python
from unittest.mock import patch, MagicMock
from agents.strategy.skills.newsletter_research import run_newsletter_research

def test_run_newsletter_research_returns_dict():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='''{
        "competitors": [
            {
                "name": "The Hustle",
                "platform": "Beehiiv",
                "estimated_subscribers": "2M+",
                "positioning": "Business and tech news for entrepreneurs",
                "content_format": "Daily digest",
                "monetisation": "Sponsorships",
                "gaps": "Does not cover personal finance for early-career professionals"
            }
        ],
        "gap_analysis": "No newsletter serves early-career professionals making their first investment decisions with actionable weekly guidance.",
        "niche_depth_recommendation": "Go deeper into first-time investor territory — the broad personal finance space is saturated."
    }''')]

    with patch("agents.strategy.skills.newsletter_research.anthropic.Anthropic") as MockClient:
        mock_client = MockClient.return_value
        mock_client.messages.create.return_value = mock_response
        result = run_newsletter_research(niche_candidate="personal finance for millennials")

    assert "competitors" in result
    assert "gap_analysis" in result
    assert "niche_depth_recommendation" in result
    assert isinstance(result["competitors"], list)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/strategy/skills/test_newsletter_research.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `agents/strategy/skills/newsletter_research.py`**

```python
import json
import anthropic

SYSTEM_PROMPT = """You are a newsletter competitive intelligence specialist. Your scope is newsletters ONLY — this includes individual creator newsletters, company newsletters, media newsletters, and any regular editorial publication.

Do NOT include YouTube channels, podcasts, Reddit communities, or social media accounts.

For a given niche, you will:
1. Research active newsletters in the space
2. For each significant newsletter, map: name, platform, estimated subscribers (if findable), positioning frame, content format, monetisation model, and what they consistently miss
3. Produce a gap analysis: what is not being covered, which reader needs are unmet, what positioning frames are unclaimed
4. Give a niche depth recommendation based purely on what you find — if the space is uncrowded, say so; if dense, recommend going deeper and name specific directions

Return ONLY a JSON object with these exact keys:
{
  "competitors": [
    {
      "name": "string",
      "platform": "string",
      "estimated_subscribers": "string",
      "positioning": "string",
      "content_format": "string",
      "monetisation": "string",
      "gaps": "string"
    }
  ],
  "gap_analysis": "string",
  "niche_depth_recommendation": "string"
}"""


def run_newsletter_research(niche_candidate: str) -> dict:
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Research the newsletter landscape for this niche: {niche_candidate}\n\nReturn the JSON object.",
            }
        ],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/strategy/skills/test_newsletter_research.py -v
```

Expected: 1 test PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/strategy/skills/newsletter_research.py tests/strategy/skills/test_newsletter_research.py
git commit -m "feat: newsletter research subagent skill"
```

---

## Task 6: Trend research skill (subagent)

**Files:**
- Create: `agents/strategy/skills/trend_research.py`
- Create: `tests/strategy/skills/test_trend_research.py`

- [ ] **Step 1: Write the failing test**

Create `tests/strategy/skills/test_trend_research.py`:

```python
from unittest.mock import patch, MagicMock
from agents.strategy.skills.trend_research import run_trend_research

def test_run_trend_research_returns_dict():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='''{
        "search_trajectory": "Growing — 35% increase in search volume over 24 months",
        "tailwinds": ["Rising interest rates making savings accounts attractive again", "Gen Z entering workforce with student debt concerns"],
        "saturation_signals": ["Several well-funded newsletters launched in 2023"],
        "timing_verdict": "Good timing if differentiated — market is growing but filling up fast",
        "purchasing_power_signals": ["Niche implies above-average financial engagement"],
        "purchasing_power_confirmed": true
    }''')]

    with patch("agents.strategy.skills.trend_research.anthropic.Anthropic") as MockClient:
        mock_client = MockClient.return_value
        mock_client.messages.create.return_value = mock_response
        result = run_trend_research(
            niche_candidate="personal finance for millennials",
            creator_context="Has sold a $97 budgeting course to 200 buyers",
        )

    assert "search_trajectory" in result
    assert "purchasing_power_confirmed" in result
    assert isinstance(result["purchasing_power_confirmed"], bool)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/strategy/skills/test_trend_research.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `agents/strategy/skills/trend_research.py`**

```python
import json
import anthropic

SYSTEM_PROMPT = """You are a niche timing and trend analyst. You assess whether a newsletter niche is well-timed, growing, or saturating.

For a given niche you will:
1. Assess search volume trajectory (growing / flat / declining)
2. Identify cultural, regulatory, or consumer behaviour tailwinds
3. Flag saturation signals or declining interest where present
4. Give a plain-language timing verdict
5. Assess purchasing power signals for the audience

Purchasing power is CONFIRMED if at least two of these signals are present:
- Creator has successfully affiliated with or sponsored products above a meaningful price point
- Creator's audience has responded to paid offers
- Survey data indicates disposable income or premium purchase behaviour
- The niche itself implies above-average spend

Return ONLY a JSON object with these exact keys:
{
  "search_trajectory": "string",
  "tailwinds": ["string"],
  "saturation_signals": ["string"],
  "timing_verdict": "string",
  "purchasing_power_signals": ["string"],
  "purchasing_power_confirmed": true or false
}"""


def run_trend_research(niche_candidate: str, creator_context: str = "") -> dict:
    client = anthropic.Anthropic()

    context_block = f"\nCreator context for purchasing power assessment:\n{creator_context}" if creator_context else ""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Assess niche timing and purchasing power for: {niche_candidate}{context_block}\n\nReturn the JSON object.",
            }
        ],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/strategy/skills/test_trend_research.py -v
```

Expected: 1 test PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/strategy/skills/trend_research.py tests/strategy/skills/test_trend_research.py
git commit -m "feat: trend research subagent skill"
```

---

## Task 7: Main agent — Steps 0, 1 (ingest + niche classification)

**Files:**
- Create: `agents/strategy/agent.py`

- [ ] **Step 1: Create the agent entry point with Steps 0 and 1**

Create `agents/strategy/agent.py`:

```python
#!/usr/bin/env python3
"""Strategy Agent — runs once per creator, produces a strategy brief."""

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from agents.strategy.session import Session
from agents.strategy.skills.public_research import run_public_research
from agents.strategy.skills.newsletter_research import run_newsletter_research
from agents.strategy.skills.trend_research import run_trend_research
from agents.strategy.renderer import render_brief

console = Console()

CATEGORIES = ["Jobs", "Hobbies", "Investments", "Personal transformation"]


def ask(prompt: str) -> str:
    """Pause and collect operator input."""
    return Prompt.ask(f"\n[bold cyan]{prompt}[/bold cyan]")


def step0_ingest(session: Session) -> dict:
    console.print(Panel("[bold]Step 0 — Data Ingestion[/bold]", style="blue"))

    if session.get("step0_done"):
        console.print("[dim]Step 0 already complete — loading from session.[/dim]")
        return session.get("step0_result")

    console.print("Enter the creator's public content URLs (one per line). Empty line to finish:")
    urls = []
    while True:
        url = input("> ").strip()
        if not url:
            break
        urls.append(url)

    human_context = ask("Any additional context? (engagement rate, products sold, audience signals — or press Enter to skip)")

    console.print("\n[dim]Running public research subagent...[/dim]")
    result = run_public_research(urls=urls, human_context=human_context)

    if result.get("gaps_flagged"):
        console.print("\n[yellow]Gaps flagged (research could not confirm these):[/yellow]")
        for gap in result["gaps_flagged"]:
            console.print(f"  • {gap}")

    session.set("step0_result", result)
    session.set("step0_done", True)
    session.save()
    return result


def step1_niche(session: Session, ingest_result: dict) -> str:
    console.print(Panel("[bold]Step 1 — Niche Classification[/bold]", style="blue"))

    if session.get("step1_done"):
        console.print("[dim]Step 1 already complete — loading from session.[/dim]")
        return session.get("niche_candidate")

    # Stage 1a — Category
    suggested_category = ingest_result.get("category_suggestion", "")
    console.print(f"\nSuggested primary category: [bold]{suggested_category}[/bold]")
    console.print(f"Available categories: {', '.join(CATEGORIES)}")
    category = ask("Confirm category or type a different one")

    # Stage 1b — Sub-niches
    sub_niches = ingest_result.get("sub_niches", [])
    console.print(f"\nSub-niches found in creator content:")
    for i, s in enumerate(sub_niches, 1):
        console.print(f"  {i}. {s}")

    selected = ask("Which sub-niches should we combine or prioritise? (type them, comma-separated)")

    # Stage 1c — Niche candidate
    niche_candidate = f"{category} > {selected}"
    console.print(f"\nNiche candidate: [bold]{niche_candidate}[/bold]")
    confirm = ask("Confirm this niche candidate? (yes / edit)")

    if confirm.lower() not in ("yes", "y"):
        niche_candidate = ask("Enter your preferred niche candidate")

    session.set("niche_candidate", niche_candidate)
    session.set("step1_done", True)
    session.save()
    return niche_candidate


def main():
    parser = argparse.ArgumentParser(description="Strategy Agent")
    parser.add_argument("--creator", required=True, help="Creator slug (e.g. jane-doe)")
    args = parser.parse_args()

    creator_slug = args.creator
    session = Session(creator_slug=creator_slug)

    console.print(Panel(f"[bold green]Strategy Agent[/bold green]\nCreator: {creator_slug}", style="green"))

    # Steps 0 and 1
    ingest_result = step0_ingest(session)
    niche_candidate = step1_niche(session, ingest_result)

    console.print(f"\n[green]Steps 0–1 complete. Niche candidate: {niche_candidate}[/green]")
    console.print("[dim]Steps 2–6 coming in next tasks.[/dim]")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the entry point runs without error**

```bash
python agents/strategy/agent.py --help
```

Expected: usage help printed, no import errors.

- [ ] **Step 3: Commit**

```bash
git add agents/strategy/agent.py
git commit -m "feat: strategy agent entry point with steps 0 and 1"
```

---

## Task 8: Main agent — Steps 2, 3 (competitor research + validation)

**Files:**
- Modify: `agents/strategy/agent.py`

- [ ] **Step 1: Add `step2_competitors` function to `agent.py`**

Add after the `step1_niche` function:

```python
def step2_competitors(session: Session, niche_candidate: str) -> dict:
    console.print(Panel("[bold]Step 2 — Newsletter Competitor Research[/bold]", style="blue"))

    if session.get("step2_done"):
        console.print("[dim]Step 2 already complete — loading from session.[/dim]")
        return session.get("step2_result")

    console.print("\n[dim]Running newsletter research subagent (this may take a minute)...[/dim]")
    result = run_newsletter_research(niche_candidate=niche_candidate)

    console.print("\n[bold]Competitors found:[/bold]")
    for c in result.get("competitors", []):
        console.print(f"\n  [bold]{c['name']}[/bold] ({c.get('platform', 'unknown')})")
        console.print(f"  {c.get('positioning', '')}")
        console.print(f"  Gap: {c.get('gaps', '')}")

    console.print(f"\n[bold]Gap analysis:[/bold]\n{result.get('gap_analysis', '')}")
    console.print(f"\n[bold]Niche depth recommendation:[/bold]\n{result.get('niche_depth_recommendation', '')}")

    session.set("step2_result", result)
    session.set("step2_done", True)
    session.save()
    return result
```

- [ ] **Step 2: Add `step3_validate` function to `agent.py`**

Add after `step2_competitors`:

```python
def step3_validate(session: Session, niche_candidate: str, ingest_result: dict) -> dict:
    console.print(Panel("[bold]Step 3 — Niche Validation[/bold]", style="blue"))

    if session.get("step3_done"):
        console.print("[dim]Step 3 already complete — loading from session.[/dim]")
        return session.get("step3_result")

    creator_context = ingest_result.get("content_summary", "") + " " + " ".join(ingest_result.get("audience_signals", []))

    console.print("\n[dim]Running trend research subagent...[/dim]")
    result = run_trend_research(niche_candidate=niche_candidate, creator_context=creator_context)

    console.print(f"\n[bold]Search trajectory:[/bold] {result.get('search_trajectory', '')}")
    console.print(f"\n[bold]Timing verdict:[/bold] {result.get('timing_verdict', '')}")

    if result.get("saturation_signals"):
        console.print("\n[yellow]Saturation signals:[/yellow]")
        for s in result["saturation_signals"]:
            console.print(f"  • {s}")

    # Purchasing power gate
    if not result.get("purchasing_power_confirmed", False):
        console.print("\n[bold red]GATE: Purchasing power cannot be confirmed from available data.[/bold red]")
        console.print("Signals found:")
        for s in result.get("purchasing_power_signals", []):
            console.print(f"  • {s}")
        console.print("\nPlease supply additional context (products sold, price points, audience responses).")
        additional = ask("Supply purchasing power context (or type 'proceed' to continue without confirmation)")
        if additional.lower() != "proceed":
            result["purchasing_power_additional_context"] = additional
            result["purchasing_power_confirmed"] = True

    session.set("step3_result", result)
    session.set("step3_done", True)
    session.save()
    return result
```

- [ ] **Step 3: Wire steps 2 and 3 into `main()`**

Replace the last 3 lines of `main()`:

```python
    # Steps 2 and 3
    competitor_result = step2_competitors(session, niche_candidate)
    validation_result = step3_validate(session, niche_candidate, ingest_result)

    console.print(f"\n[green]Steps 0–3 complete.[/green]")
    console.print("[dim]Steps 4–6 coming in next tasks.[/dim]")
```

- [ ] **Step 4: Commit**

```bash
git add agents/strategy/agent.py
git commit -m "feat: strategy agent steps 2 and 3 (competitor research and niche validation)"
```

---

## Task 9: Main agent — Step 4 (intake questions)

**Files:**
- Modify: `agents/strategy/agent.py`

- [ ] **Step 1: Add `step4_intake` function to `agent.py`**

Add after `step3_validate`:

```python
def step4_intake(session: Session, validation_result: dict, ingest_result: dict) -> dict:
    console.print(Panel("[bold]Step 4 — Creator Intake Questions[/bold]", style="blue"))

    if session.get("step4_done"):
        console.print("[dim]Step 4 already complete — loading from session.[/dim]")
        return session.get("step4_result")

    console.print("\nThese questions must be answered before synthesis. Answer on behalf of the creator or pass them along.\n")

    answers = {}

    answers["origin_story"] = ask(
        "1. What is the specific moment or experience that led this creator to this topic? (Not the polished version — the real one)"
    )
    answers["contrarian_belief"] = ask(
        "2. What does this creator believe that most people in this space get wrong?"
    )
    answers["hidden_credibility"] = ask(
        "3. What has this creator done, experienced, or built that gives them credibility here that is NOT obvious from their public content?"
    )
    answers["ideal_reader"] = ask(
        "4. Who is the single most specific reader this newsletter is for? Picture one person — who are they and what are they struggling with right now?"
    )

    # Gap-specific questions
    if not validation_result.get("purchasing_power_confirmed"):
        answers["purchasing_power_detail"] = ask(
            "What products has this creator's audience bought, at what price point, and how did they respond? (or press Enter to skip)"
        )

    archetype_ambiguous = not ingest_result.get("category_suggestion")
    if archetype_ambiguous:
        answers["self_archetype"] = ask(
            "How does this creator think of themselves: practitioner, learner, experimenter, or curator? (or press Enter to skip)"
        )

    session.set("step4_result", answers)
    session.set("step4_done", True)
    session.save()
    return answers
```

- [ ] **Step 2: Wire step 4 into `main()`**

Replace the last 3 lines of `main()`:

```python
    # Step 4
    intake_answers = step4_intake(session, validation_result, ingest_result)

    console.print(f"\n[green]Steps 0–4 complete.[/green]")
    console.print("[dim]Steps 5–6 coming in next tasks.[/dim]")
```

- [ ] **Step 3: Commit**

```bash
git add agents/strategy/agent.py
git commit -m "feat: strategy agent step 4 (creator intake questions)"
```

---

## Task 10: Main agent — Step 5 (synthesis pass)

**Files:**
- Modify: `agents/strategy/agent.py`

- [ ] **Step 1: Add `step5_synthesise` function to `agent.py`**

Add after `step4_intake`:

```python
def step5_synthesise(
    session: Session,
    niche_candidate: str,
    ingest_result: dict,
    competitor_result: dict,
    validation_result: dict,
    intake_answers: dict,
    learnings: list,
) -> dict:
    console.print(Panel("[bold]Step 5 — Synthesis Pass[/bold]", style="blue"))

    import anthropic as _anthropic

    client = _anthropic.Anthropic()

    learnings_block = ""
    if learnings:
        learnings_block = "\n\nPrevious revision learnings to apply:\n" + json.dumps(learnings, indent=2)

    prompt = f"""You are synthesising a strategy brief for a newsletter creator. Use ALL of the research and intake data below to fill every field. Where you cannot confirm a field from the data, leave the value as null.

Niche candidate: {niche_candidate}

Public research findings:
{json.dumps(ingest_result, indent=2)}

Competitor research:
{json.dumps(competitor_result, indent=2)}

Trend and validation data:
{json.dumps(validation_result, indent=2)}

Creator intake answers:
{json.dumps(intake_answers, indent=2)}
{learnings_block}

Return ONLY a JSON object with these exact keys:
{{
  "newsletter_name": ["name1", "name2", "name3"],
  "newsletter_name_rationale": ["rationale1", "rationale2", "rationale3"],
  "niche_umbrella": "string or null",
  "niche_rationale": "string or null",
  "target_reader": "string or null",
  "newsletter_statement": "string or null",
  "why_exist": "string or null",
  "why_creator": "string or null",
  "content_pillars": [
    {{"name": "string", "description": "string"}},
    {{"name": "string", "description": "string"}},
    {{"name": "string", "description": "string"}}
  ],
  "creator_archetype": {{
    "primary": "Expert | Student | Experimenter | Tastemaker",
    "secondary": "string or null",
    "evidence": "string"
  }},
  "business_model": "string",
  "competitor_insight": "string or null",
  "comparable_newsletter": "string or null"
}}"""

    console.print("\n[dim]Running synthesis subagent...[/dim]")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    brief = json.loads(raw.strip())

    session.set("brief", brief)
    session.set("step5_done", True)
    session.save()
    return brief
```

- [ ] **Step 2: Wire step 5 into `main()`**

Replace the last 3 lines of `main()`:

```python
    # Step 5
    brief = step5_synthesise(
        session=session,
        niche_candidate=niche_candidate,
        ingest_result=ingest_result,
        competitor_result=competitor_result,
        validation_result=validation_result,
        intake_answers=intake_answers,
        learnings=session.learnings,
    )

    console.print(f"\n[green]Steps 0–5 complete.[/green]")
    console.print("[dim]Step 6 coming in next task.[/dim]")
```

- [ ] **Step 3: Commit**

```bash
git add agents/strategy/agent.py
git commit -m "feat: strategy agent step 5 (synthesis pass)"
```

---

## Task 11: Main agent — Step 6 (human review loop) + brief output

**Files:**
- Modify: `agents/strategy/agent.py`

- [ ] **Step 1: Add `step6_review` function to `agent.py`**

Add after `step5_synthesise`:

```python
def step6_review(
    session: Session,
    brief: dict,
    niche_candidate: str,
    ingest_result: dict,
    competitor_result: dict,
    validation_result: dict,
    intake_answers: dict,
    creator_slug: str,
) -> dict:
    console.print(Panel("[bold]Step 6 — Human Review[/bold]", style="blue"))

    round_number = 0

    while True:
        round_number += 1
        md = render_brief(brief)
        console.print(Panel(md, title=f"Strategy Brief (Round {round_number})", style="white"))

        feedback = ask('Review the brief above. Type feedback to revise, or "lock it" to finalise')

        if feedback.strip().lower() in ("lock it", "lock", "done", "approve", "confirmed"):
            break

        # Store learning
        session.append_learning({"round": round_number, "feedback": feedback})
        session.save()

        console.print("\n[dim]Applying feedback and regenerating brief...[/dim]")
        brief = step5_synthesise(
            session=session,
            niche_candidate=niche_candidate,
            ingest_result=ingest_result,
            competitor_result=competitor_result,
            validation_result=validation_result,
            intake_answers=intake_answers,
            learnings=session.learnings,
        )

    # Write outputs
    briefs_dir = Path("briefs") / creator_slug
    briefs_dir.mkdir(parents=True, exist_ok=True)
    md_path = briefs_dir / "strategy-brief.md"
    md_path.write_text(render_brief(brief), encoding="utf-8")

    session.save_brief_json(brief)
    session.set("locked", True)
    session.save()

    console.print(f"\n[bold green]Brief locked.[/bold green]")
    console.print(f"Markdown: {md_path}")
    return brief
```

- [ ] **Step 2: Wire step 6 into `main()` and complete the flow**

Replace the last 3 lines of `main()`:

```python
    # Step 6
    step6_review(
        session=session,
        brief=brief,
        niche_candidate=niche_candidate,
        ingest_result=ingest_result,
        competitor_result=competitor_result,
        validation_result=validation_result,
        intake_answers=intake_answers,
        creator_slug=creator_slug,
    )
```

- [ ] **Step 3: Run full agent smoke test (dry run)**

```bash
python agents/strategy/agent.py --help
```

Expected: help printed, no import errors.

- [ ] **Step 4: Commit**

```bash
git add agents/strategy/agent.py
git commit -m "feat: strategy agent step 6 (review loop) and brief output — agent complete"
```

---

## Task 12: Create tests directory init files and run full test suite

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/strategy/__init__.py`
- Create: `tests/strategy/skills/__init__.py`

- [ ] **Step 1: Create init files**

```bash
touch tests/__init__.py tests/strategy/__init__.py tests/strategy/skills/__init__.py
```

- [ ] **Step 2: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all 8 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/__init__.py tests/strategy/__init__.py tests/strategy/skills/__init__.py
git commit -m "chore: add test package init files, all tests passing"
```

---

## Self-Review

**Spec coverage check:**
- Step 0 (data ingestion, gap flagging) → Task 7 ✓
- Step 1 (niche classification, operator gate) → Task 7 ✓
- Step 2 (competitor research, gap analysis, niche depth recommendation) → Tasks 5, 8 ✓
- Step 3 (three filters, purchasing power gate) → Tasks 6, 8 ✓
- Step 4 (always-ask questions, gap-specific questions) → Task 9 ✓
- Step 5 (synthesis, all brief fields) → Task 10 ✓
- Step 6 (unlimited review loop, learnings persistence, lock trigger) → Task 11 ✓
- Brief outputs (MD operator-facing, JSON canonical) → Task 11 ✓
- Session persistence and resume → Task 2 ✓
- Renderer with blank field notes → Task 3 ✓

**Placeholder scan:** No TBDs, TODOs, or vague steps found.

**Type consistency:** `Session`, `render_brief`, `run_public_research`, `run_newsletter_research`, `run_trend_research` — all function signatures consistent across tasks that reference them.
