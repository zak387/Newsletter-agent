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
