"""Tests for filesaver module.

Covers UTF-8 multibyte handling for files around and above the 64KB
buffer boundary, verifying byte-accurate round-trip fidelity.
"""

import os
import tempfile

from filesaver import save_file


def _round_trip(content: str) -> str:
    """Save content to a temp file and read it back."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    finally:
        os.unlink(path)


def test_small_ascii_file():
    content = "hello world"
    assert _round_trip(content) == content


def test_small_multibyte_file():
    content = "こんにちは世界 🌍🌎🌏"
    assert _round_trip(content) == content


def test_under_64kb_with_multibyte():
    """File just under 64KB containing multibyte characters."""
    # Each emoji is 4 bytes in UTF-8; fill just under 64KB
    unit = "🎉"  # 4 bytes
    count = (65536 // 4) - 10  # safely under 64KB
    content = unit * count
    result = _round_trip(content)
    assert result == content


def test_over_64kb_with_multibyte():
    """File over 64KB containing multibyte characters — the crash case."""
    unit = "🎉"  # 4 bytes per emoji
    count = (65536 // 4) + 1000  # well over 64KB
    content = unit * count
    result = _round_trip(content)
    assert result == content


def test_over_64kb_mixed_ascii_and_multibyte():
    """Mixed ASCII and multibyte content exceeding 64KB."""
    ascii_part = "A" * 40000
    emoji_part = "🚀" * 8000  # 32000 bytes
    content = ascii_part + emoji_part
    assert len(content.encode("utf-8")) > 65536
    result = _round_trip(content)
    assert result == content


def test_byte_exact_round_trip():
    """Saved file content matches input byte-for-byte."""
    content = "Hello 🌍 世界 café naïve"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        with open(path, "rb") as f:
            raw = f.read()
        assert raw == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_large_cjk_file():
    """Large file with CJK characters (3 bytes each in UTF-8)."""
    # CJK characters are 3 bytes each
    content = "漢" * 30000  # 90000 bytes, well over 64KB
    result = _round_trip(content)
    assert result == content
