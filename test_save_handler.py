"""Tests for save_handler — UTF-8 file save/load round-trip.

Covers the regression described in issue #1254: saving files larger than
64KB that contain multibyte UTF-8 characters caused a segmentation fault
due to byte-length vs character-count confusion in buffer allocation.
"""

import os
import tempfile

from save_handler import BUFFER_SIZE, load_file, save_file


def _round_trip(content: str) -> str:
    """Save *content* to a temp file, read it back, and return the text."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        save_file(path, content)
        return load_file(path)
    finally:
        os.unlink(path)


def test_ascii_under_64kb():
    """ASCII content under 64KB saves and loads correctly."""
    content = "a" * (BUFFER_SIZE - 1)
    assert _round_trip(content) == content


def test_ascii_over_64kb():
    """ASCII content over 64KB saves and loads correctly."""
    content = "a" * (BUFFER_SIZE + 1024)
    assert _round_trip(content) == content


def test_multibyte_under_64kb():
    """Multibyte UTF-8 content under 64KB saves correctly."""
    # Each emoji is 4 bytes in UTF-8; 10000 emojis = 40KB.
    content = "\U0001f600" * 10000
    assert _round_trip(content) == content


def test_multibyte_over_64kb():
    """Multibyte UTF-8 content over 64KB saves correctly (regression)."""
    # 20000 emojis * 4 bytes = 80KB > 64KB.
    content = "\U0001f600" * 20000
    assert _round_trip(content) == content


def test_multibyte_at_boundary():
    """A multibyte character straddling the 64KB boundary is handled."""
    # Fill up to one byte before the boundary with ASCII, then add a
    # 4-byte emoji so the encoded bytes cross the 64KB mark.
    ascii_prefix = "x" * (BUFFER_SIZE - 1)
    content = ascii_prefix + "\U0001f600"
    assert _round_trip(content) == content


def test_mixed_content_70kb():
    """70KB of mixed ASCII + emoji round-trips correctly."""
    # Simulate the reproduction steps: ~70KB of text with emoji mixed in.
    block = "Hello world \U0001f30d — some CJK: 世界\n"
    repetitions = (70 * 1024) // len(block.encode("utf-8")) + 1
    content = block * repetitions
    assert len(content.encode("utf-8")) > 70 * 1024
    assert _round_trip(content) == content


def test_returns_byte_count():
    """save_file returns the number of bytes written."""
    content = "\U0001f600" * 100  # 400 bytes
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        written = save_file(path, content)
        assert written == len(content.encode("utf-8"))
    finally:
        os.unlink(path)


def test_empty_file():
    """Saving an empty string produces an empty file."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        written = save_file(path, "")
        assert written == 0
        assert load_file(path) == ""
    finally:
        os.unlink(path)
