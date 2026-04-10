import sys
import pytest
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.writing.agent import estimate_tokens, load_content_pack_from_file


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0


def test_estimate_tokens_four_chars():
    # 4 chars = 1 token (chars / 4, floor)
    assert estimate_tokens("abcd") == 1


def test_estimate_tokens_rounds_down():
    assert estimate_tokens("abc") == 0


def test_estimate_tokens_large():
    text = "a" * 400
    assert estimate_tokens(text) == 100


def test_load_content_pack_from_file_txt(tmp_path):
    f = tmp_path / "pack.txt"
    f.write_text("hello world", encoding="utf-8")
    result = load_content_pack_from_file(str(f))
    assert result == "hello world"


def test_load_content_pack_from_file_md(tmp_path):
    f = tmp_path / "pack.md"
    f.write_text("# Title\ncontent", encoding="utf-8")
    result = load_content_pack_from_file(str(f))
    assert result == "# Title\ncontent"


def test_load_content_pack_from_file_missing():
    with pytest.raises(FileNotFoundError):
        load_content_pack_from_file("/nonexistent/path/pack.txt")


def test_load_content_pack_from_file_unsupported(tmp_path):
    f = tmp_path / "pack.docx"
    f.write_bytes(b"binary")
    with pytest.raises(ValueError, match="Unsupported file format"):
        load_content_pack_from_file(str(f))


from unittest.mock import MagicMock, patch
from agents.writing.agent import _extract_pdf_text


def test_extract_pdf_text_joins_pages_and_handles_none(tmp_path):
    """_extract_pdf_text joins pages with newline and treats None extract_text() as empty string."""
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Page one text"
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = None  # simulate page with no extractable text
    mock_page3 = MagicMock()
    mock_page3.extract_text.return_value = "Page three text"

    mock_reader = MagicMock()
    mock_reader.pages = [mock_page1, mock_page2, mock_page3]

    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_bytes(b"%PDF-fake")

    with patch("pypdf.PdfReader", return_value=mock_reader):
        result = _extract_pdf_text(fake_pdf)

    assert result == "Page one text\n\nPage three text"


from agents.writing.agent import apply_size_guard, TOKEN_LIMIT

_CHARS_PER_TOKEN = 4  # mirrors agent constant for tests


def test_apply_size_guard_under_limit():
    text = "a" * (TOKEN_LIMIT * _CHARS_PER_TOKEN - 4)
    # Should return text unchanged, no truncation needed
    result = apply_size_guard(text, truncate=False)
    assert result == text


def test_apply_size_guard_over_limit_truncate():
    # 80001 tokens worth of text
    text = "a" * ((TOKEN_LIMIT + 1) * _CHARS_PER_TOKEN)
    result = apply_size_guard(text, truncate=True)
    assert estimate_tokens(result) == TOKEN_LIMIT


def test_apply_size_guard_over_limit_no_truncate():
    text = "a" * ((TOKEN_LIMIT + 1) * _CHARS_PER_TOKEN)
    with pytest.raises(ValueError, match="Content pack exceeds"):
        apply_size_guard(text, truncate=False)


import json
from agents.writing.agent import WritingSession, load_strategy_brief


def test_writing_session_uses_different_filenames(tmp_path):
    session = WritingSession(creator_slug="test-creator", base_dir=tmp_path)
    session.set("block1_done", True)
    session.save()
    assert (tmp_path / ".agent" / "test-creator" / "writing-session.json").exists()
    assert (tmp_path / ".agent" / "test-creator" / "writing-learnings.json").exists()
    # Strategy agent files must NOT be created
    assert not (tmp_path / ".agent" / "test-creator" / "session.json").exists()


def test_load_strategy_brief_missing(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        load_strategy_brief("test-creator", base_dir=tmp_path)
    assert exc_info.value.code == 1


def test_load_strategy_brief_found(tmp_path):
    brief_dir = tmp_path / ".agent" / "test-creator"
    brief_dir.mkdir(parents=True)
    brief = {"newsletter_name": ["The Clean Label"], "niche_umbrella": "Personal transformation > clean eating", "creator_archetype": {"primary": "Experimenter"}}
    (brief_dir / "strategy-brief.json").write_text(json.dumps(brief), encoding="utf-8")
    result = load_strategy_brief("test-creator", base_dir=tmp_path)
    assert result["newsletter_name"] == ["The Clean Label"]


from unittest.mock import MagicMock
from agents.writing.agent import extract_voice_profile_json


def test_extract_voice_profile_json_malformed_raises():
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(text="not valid json {{{{")]

    with pytest.raises(RuntimeError, match="JSON parse error"):
        extract_voice_profile_json("some profile text", client=mock_client)


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
    assert not result.endswith("-")


def test_slugify_subject_empty():
    assert slugify_subject("") == "untitled"


def test_slugify_subject_only_punctuation():
    assert slugify_subject("!!!???") == "untitled"


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


from agents.writing.agent import load_newsletter_reference


def test_load_newsletter_reference_returns_contents(tmp_path):
    (tmp_path / "newsletter-reference.md").write_text(
        "# Reference\nSome content.", encoding="utf-8"
    )
    result = load_newsletter_reference(base_dir=tmp_path)
    assert "Some content." in result


def test_load_newsletter_reference_missing_returns_empty(tmp_path):
    result = load_newsletter_reference(base_dir=tmp_path)
    assert result == ""


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
    with patch("agents.writing.agent.ask", side_effect=["9", "bad", "1"]):
        result = step_block2("acme", base_dir=tmp_path)
    assert result == {"format": "personal_letter"}


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
            {"option": f"Opt {i}", "framework": "Curiosity"} for i in range(12)
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
    assert result[0]["option"] == "Opt 0"
    assert result[0]["framework"] == "Curiosity"


def test_generate_subject_lines_accepts_15():
    payload = json.dumps({
        "subject_lines": [
            {"option": f"Opt {i}", "framework": "Pain"} for i in range(15)
        ]
    })
    client = _mock_client_returning(payload)
    result = generate_subject_lines(
        topic="x", format_slug="roundup",
        voice_profile_json={}, client=client,
    )
    assert len(result) == 15


def test_generate_subject_lines_rejects_fewer_than_10_then_retries():
    short_payload = json.dumps({
        "subject_lines": [
            {"option": f"x{i}", "framework": "Curiosity"} for i in range(5)
        ]
    })
    good_payload = json.dumps({
        "subject_lines": [
            {"option": f"y{i}", "framework": "Proof"} for i in range(11)
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
            {"option": f"o{i}", "framework": "Mistake"} for i in range(10)
        ]
    }) + "\n```"
    client = _mock_client_returning(payload)
    result = generate_subject_lines(
        topic="x", format_slug="roundup",
        voice_profile_json={}, client=client,
    )
    assert len(result) == 10


def test_generate_subject_lines_raises_after_two_bad_responses():
    bad = json.dumps({"subject_lines": [{"option": "x", "framework": "bogus"}]})
    client = MagicMock()
    msg = MagicMock()
    block = MagicMock(); block.text = bad
    msg.content = [block]
    client.messages.create.side_effect = [msg, msg]

    with pytest.raises(RuntimeError, match="post-filter"):
        generate_subject_lines(
            topic="x", format_slug="roundup",
            voice_profile_json={}, client=client,
        )


def test_generate_subject_lines_filters_over_30_chars():
    # 41-char line violates the 30-char hard ceiling and must be dropped.
    payload = json.dumps({
        "subject_lines": (
            [{"option": "This is way too long for a mobile preview", "framework": "Curiosity"}]
            + [{"option": f"Opt {i}", "framework": "Curiosity"} for i in range(11)]
        )
    })
    client = _mock_client_returning(payload)
    result = generate_subject_lines(
        topic="x", format_slug="personal_letter",
        voice_profile_json={}, client=client,
    )
    assert len(result) == 11  # the 41-char line was filtered out
    assert all(len(r["option"]) <= 30 for r in result)


def test_generate_subject_lines_allows_21_to_30_chars():
    # 21–30 char lines are allowed (above target, within ceiling).
    payload = json.dumps({
        "subject_lines": (
            # 21 chars: "Can't dodge seed oil?"
            [{"option": "Can't dodge seed oil?", "framework": "Pain"}]
            # 30 chars: "123456789012345678901234567890"
            + [{"option": "123456789012345678901234567890", "framework": "Curiosity"}]
            + [{"option": f"Opt {i}", "framework": "Mistake"} for i in range(10)]
        )
    })
    client = _mock_client_returning(payload)
    result = generate_subject_lines(
        topic="x", format_slug="personal_letter",
        voice_profile_json={}, client=client,
    )
    assert len(result) == 12
    assert any(r["option"] == "Can't dodge seed oil?" for r in result)
    assert any(len(r["option"]) == 30 for r in result)


def test_generate_subject_lines_filters_31_chars():
    # 31 chars exactly is over the ceiling — must be dropped.
    payload = json.dumps({
        "subject_lines": (
            [{"option": "1234567890123456789012345678901", "framework": "Curiosity"}]
            + [{"option": f"Opt {i}", "framework": "Pain"} for i in range(11)]
        )
    })
    client = _mock_client_returning(payload)
    result = generate_subject_lines(
        topic="x", format_slug="personal_letter",
        voice_profile_json={}, client=client,
    )
    assert len(result) == 11  # the 31-char line dropped
    assert all(len(r["option"]) <= 30 for r in result)


def test_generate_subject_lines_filters_invalid_framework():
    payload = json.dumps({
        "subject_lines": (
            [{"option": "Short one", "framework": "bogus"}]
            + [{"option": f"Opt {i}", "framework": "Dream Outcome"} for i in range(12)]
        )
    })
    client = _mock_client_returning(payload)
    result = generate_subject_lines(
        topic="x", format_slug="personal_letter",
        voice_profile_json={}, client=client,
    )
    assert len(result) == 12  # the bogus-framework entry was filtered out
    assert all(r["framework"] in {"Curiosity", "Pain", "Dream Outcome", "Proof", "Mistake"} for r in result)


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


def test_suggest_cta_retries_once_on_malformed_json():
    good_payload = json.dumps({
        "suggested_cta_type": "offer",
        "suggested_cta_label": "Course launch Q2",
        "rationale": "retry succeeded",
    })
    client = MagicMock()
    bad_msg = MagicMock()
    bad_block = MagicMock(); bad_block.text = "not json"
    bad_msg.content = [bad_block]
    good_msg = MagicMock()
    good_block = MagicMock(); good_block.text = good_payload
    good_msg.content = [good_block]
    client.messages.create.side_effect = [bad_msg, good_msg]

    result = suggest_cta(
        topic="x", subject_line="y",
        ctas_md=CTAS_SAMPLE, voice_profile_json={}, client=client,
    )
    assert result["suggested_cta_label"] == "Course launch Q2"
    assert client.messages.create.call_count == 2


def test_suggest_cta_raises_after_two_bad_responses():
    client = MagicMock()
    msg1 = MagicMock()
    block1 = MagicMock(); block1.text = "not json"
    msg1.content = [block1]
    msg2 = MagicMock()
    block2 = MagicMock(); block2.text = "still not json"
    msg2.content = [block2]
    client.messages.create.side_effect = [msg1, msg2]

    with pytest.raises(RuntimeError, match="CTA suggestion"):
        suggest_cta(
            topic="x", subject_line="y",
            ctas_md=CTAS_SAMPLE, voice_profile_json={}, client=client,
        )
    assert client.messages.create.call_count == 2


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
    assert "Quick Hits" in prompt
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
    assert "REFERENCE ONLY" not in prompt


from agents.writing.agent import load_welcome_block


def test_load_welcome_block_missing_returns_empty(tmp_path):
    assert load_welcome_block("acme", base_dir=tmp_path) == ""


def test_load_welcome_block_reads_file(tmp_path):
    briefs = tmp_path / "briefs" / "acme"
    briefs.mkdir(parents=True)
    (briefs / "welcome.md").write_text(
        "Welcome to Acme, the newsletter for acme fans.\n", encoding="utf-8"
    )
    result = load_welcome_block("acme", base_dir=tmp_path)
    assert "Welcome to Acme" in result
    assert not result.endswith("\n")  # stripped


def test_load_welcome_block_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError):
        load_welcome_block("../evil", base_dir=tmp_path)


def test_run_draft_injects_welcome_block_for_personal_letter():
    client = _mock_streaming_client("out")
    run_draft(
        topic="t", subject_line="s",
        cta_entry={"type": "offer", "label": "l", "copy": "c", "link": "u"},
        format_slug="personal_letter",
        voice_profile_json={},
        newsletter_reference_md="",
        learnings=None, client=client,
        welcome_block_text="Welcome to Acme, the newsletter for fans.",
    )
    prompt = client.messages.stream.call_args.kwargs["messages"][0]["content"]
    assert "Welcome to Acme, the newsletter for fans." in prompt
    assert "<welcome_block>" in prompt
    assert "Render it EXACTLY" in prompt


def test_run_draft_omits_welcome_block_for_roundup():
    client = _mock_streaming_client("out")
    run_draft(
        topic="t", subject_line="s",
        cta_entry={"type": "offer", "label": "l", "copy": "c", "link": "u"},
        format_slug="roundup",
        voice_profile_json={},
        newsletter_reference_md="",
        learnings=None, client=client,
        welcome_block_text="Welcome to Acme.",
    )
    prompt = client.messages.stream.call_args.kwargs["messages"][0]["content"]
    # Welcome block should NOT be injected for non-personal-letter formats
    assert "<welcome_block>" not in prompt


def test_run_draft_omits_welcome_block_when_text_empty():
    client = _mock_streaming_client("out")
    run_draft(
        topic="t", subject_line="s",
        cta_entry={"type": "offer", "label": "l", "copy": "c", "link": "u"},
        format_slug="personal_letter",
        voice_profile_json={},
        newsletter_reference_md="",
        learnings=None, client=client,
        welcome_block_text="",
    )
    prompt = client.messages.stream.call_args.kwargs["messages"][0]["content"]
    assert "<welcome_block>" not in prompt


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
    write_draft_file(
        creator_slug="acme", subject_line="Same",
        draft_body="first", topic="x", format_slug="personal_letter",
        cta_label="c", base_dir=tmp_path, today="2026-04-08",
    )
    path2 = write_draft_file(
        creator_slug="acme", subject_line="Same",
        draft_body="second", topic="x", format_slug="personal_letter",
        cta_label="c", base_dir=tmp_path, today="2026-04-08",
    )
    assert path2.name == "2026-04-08-same-2.md"
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

    subject_payload = json.dumps({
        "subject_lines": [
            {"option": f"Opt {i}", "framework": "Curiosity"} for i in range(10)
        ]
    })
    cta_payload = json.dumps({
        "suggested_cta_type": "offer",
        "suggested_cta_label": "Course launch Q2",
        "rationale": "fits",
    })

    client = MagicMock()

    def _create(**kwargs):
        msg = MagicMock()
        block = MagicMock()
        prompt = kwargs["messages"][0]["content"]
        if "subject_lines" in prompt or "subject line options" in prompt:
            block.text = subject_payload
        else:
            block.text = cta_payload
        msg.content = [block]
        return msg

    client.messages.create.side_effect = _create

    stream_cm = MagicMock()
    stream_cm.__enter__ = MagicMock(return_value=stream_cm)
    stream_cm.__exit__ = MagicMock(return_value=False)
    stream_cm.text_stream = iter(["Option 1\n\nBody of the draft."])
    client.messages.stream.return_value = stream_cm

    monkeypatch.setattr("agents.writing.agent._ClaudeClient", lambda: client)

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
