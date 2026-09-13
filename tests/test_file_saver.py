"""Tests for file_saver module — UTF-8 buffer handling."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from file_saver import BUFFER_SIZE, save_file


def _make_emoji_content(target_bytes):
    """Build a string of emoji whose UTF-8 encoding is >= target_bytes."""
    # Each emoji (e.g. U+1F600) encodes to 4 bytes in UTF-8
    count = (target_bytes // 4) + 1
    return "\U0001f600" * count


def _make_cjk_content(target_bytes):
    """Build a string of CJK characters whose UTF-8 encoding is >= target_bytes."""
    # Each CJK character (e.g. U+4E16) encodes to 3 bytes in UTF-8
    count = (target_bytes // 3) + 1
    return "世" * count


def test_save_ascii_under_buffer():
    """ASCII content under 64KB saves correctly."""
    content = "a" * (BUFFER_SIZE - 1)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        written = save_file(path, content)
        assert written == BUFFER_SIZE - 1
        with open(path, "rb") as f:
            assert f.read() == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_ascii_over_buffer():
    """ASCII content over 64KB saves correctly."""
    content = "b" * (BUFFER_SIZE * 2)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        written = save_file(path, content)
        assert written == BUFFER_SIZE * 2
        with open(path, "rb") as f:
            assert f.read() == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_emoji_under_buffer():
    """Emoji content whose byte length is under 64KB saves correctly."""
    # 10000 emoji * 4 bytes = 40000 bytes < 64KB
    content = "\U0001f600" * 10000
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        written = save_file(path, content)
        assert written == len(content.encode("utf-8"))
        with open(path, "rb") as f:
            assert f.read() == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_emoji_over_buffer():
    """Emoji content whose byte length exceeds 64KB saves correctly.

    This is the core regression test: 65KB / 4 bytes per emoji =
    ~16384 characters, so len(content) < 64KB but
    len(content.encode('utf-8')) > 64KB. A buffer sized by character
    count would overflow here.
    """
    content = _make_emoji_content(BUFFER_SIZE + 1)
    encoded = content.encode("utf-8")
    assert len(content) < len(encoded), "precondition: chars < bytes"
    assert len(encoded) > BUFFER_SIZE, "precondition: bytes > buffer"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        written = save_file(path, content)
        assert written == len(encoded)
        with open(path, "rb") as f:
            data = f.read()
        assert data == encoded, "round-trip content mismatch"
    finally:
        os.unlink(path)


def test_save_cjk_over_buffer():
    """CJK content whose byte length exceeds 64KB saves correctly."""
    content = _make_cjk_content(BUFFER_SIZE + 1)
    encoded = content.encode("utf-8")
    assert len(encoded) > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        written = save_file(path, content)
        assert written == len(encoded)
        with open(path, "rb") as f:
            assert f.read() == encoded
    finally:
        os.unlink(path)


def test_save_large_emoji_128kb():
    """128KB of dense 4-byte emoji saves correctly."""
    content = _make_emoji_content(BUFFER_SIZE * 2)
    encoded = content.encode("utf-8")
    assert len(encoded) >= BUFFER_SIZE * 2

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        written = save_file(path, content)
        assert written == len(encoded)
        with open(path, "rb") as f:
            assert f.read() == encoded
    finally:
        os.unlink(path)


def test_save_creates_directory():
    """save_file creates intermediate directories if needed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "sub", "dir", "file.txt")
        content = "hello \U0001f600"
        written = save_file(path, content)
        assert written == len(content.encode("utf-8"))
        with open(path, "rb") as f:
            assert f.read() == content.encode("utf-8")


def test_roundtrip_mixed_content():
    """Mixed ASCII and multibyte content round-trips correctly."""
    # Mix of ASCII, 2-byte, 3-byte, and 4-byte characters
    content = "Hello " + "é" * 100 + " 世界 " + "\U0001f600" * 100
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content
    finally:
        os.unlink(path)
