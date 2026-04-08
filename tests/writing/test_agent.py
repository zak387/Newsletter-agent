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
