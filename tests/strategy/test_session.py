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
    brief_path = tmp_path / ".agent" / "test-creator" / "positioning-brief.json"
    assert brief_path.exists()
    data = json.loads(brief_path.read_text())
    assert data["newsletter_name"][0] == "Option A"
