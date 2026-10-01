"""Tests for the file writer module.

Verifies that saving files with multibyte UTF-8 characters works
correctly at and above the 64KB buffer boundary.
"""

import os
import tempfile

from src.file_writer import BUFFER_SIZE, save_file


def test_save_large_file_with_emoji():
    """Save a >64KB file with 4-byte emoji characters straddling the boundary."""
    # Each emoji is 4 bytes in UTF-8. Build content so that a multibyte
    # sequence straddles the exact 64KB byte boundary.
    emoji = "\U0001F600"  # 😀 — 4 bytes in UTF-8
    # Fill just past the buffer boundary with emoji characters
    count = (BUFFER_SIZE // 4) + 100  # comfortably past 64KB
    content = emoji * count

    assert len(content.encode("utf-8")) > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        with open(path, "rb") as f:
            saved_bytes = f.read()
        assert saved_bytes == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_64kb_file_with_cjk():
    """Save a 64KB file with multibyte CJK characters."""
    # CJK characters are 3 bytes each in UTF-8
    cjk_char = "世"  # 世 — 3 bytes in UTF-8
    count = BUFFER_SIZE // 3 + 1  # just over 64KB in bytes
    content = cjk_char * count

    assert len(content.encode("utf-8")) > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        with open(path, "rb") as f:
            saved_bytes = f.read()
        assert saved_bytes == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_128kb_mixed_ascii_and_multibyte():
    """Save a 128KB file mixing ASCII and multibyte characters."""
    ascii_block = "A" * (BUFFER_SIZE - 2)
    # Place a 4-byte emoji right at the 64KB byte boundary
    emoji = "\U0001F680"  # 🚀 — 4 bytes
    tail = "B" * BUFFER_SIZE
    content = ascii_block + emoji + tail

    assert len(content.encode("utf-8")) > 2 * BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        with open(path, "rb") as f:
            saved_bytes = f.read()
        assert saved_bytes == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_roundtrip_preserves_content():
    """Saved content matches original byte-for-byte."""
    # Mix of ASCII, 2-byte, 3-byte, and 4-byte UTF-8 characters
    content = (
        "Hello, World! "
        "éñü "      # 2-byte: é ñ ü
        "世界 "             # 3-byte: 世界
        "\U0001F600\U0001F680 "     # 4-byte: 😀🚀
    ) * 5000  # repeat to exceed 64KB

    assert len(content.encode("utf-8")) > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        with open(path, "rb") as f:
            saved_bytes = f.read()
        assert saved_bytes == content.encode("utf-8")
        # Also verify string round-trip
        assert saved_bytes.decode("utf-8") == content
    finally:
        os.unlink(path)


def test_save_small_ascii_file():
    """Small ASCII files still save correctly (regression guard)."""
    content = "Hello, World!\n" * 100

    assert len(content.encode("utf-8")) < BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        with open(path, "rb") as f:
            saved_bytes = f.read()
        assert saved_bytes == content.encode("utf-8")
    finally:
        os.unlink(path)
