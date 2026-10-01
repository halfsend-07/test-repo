"""Tests for the file writer module.

Verifies that saving files with multibyte UTF-8 characters works
correctly at and above the 64KB buffer boundary.
"""

import os
import tempfile

from src.file_writer import BUFFER_SIZE, save_file


def test_save_large_file_with_emoji():
    """Save a >64KB file with 4-byte emoji characters past the boundary."""
    emoji = "\U0001F600"  # U+1F600 GRINNING FACE - 4 bytes in UTF-8
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
    """Save a file just over 64KB with 3-byte CJK characters."""
    cjk_char = "世"  # 世 - 3 bytes in UTF-8
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


def test_save_128kb_mixed_content():
    """Save a 128KB file mixing ASCII and multibyte characters."""
    ascii_block = "A" * (BUFFER_SIZE - 2)
    emoji = "\U0001F680"  # U+1F680 ROCKET - 4 bytes in UTF-8
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
    """Saved content matches original byte-for-byte across encodings."""
    content = (
        "Hello, World! "
        "éñü "
        "世界 "
        "\U0001F600\U0001F680 "
    ) * 5000

    assert len(content.encode("utf-8")) > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        with open(path, "rb") as f:
            saved_bytes = f.read()
        assert saved_bytes == content.encode("utf-8")
        assert saved_bytes.decode("utf-8") == content
    finally:
        os.unlink(path)


def test_save_exact_buffer_size():
    """Save a file whose encoded size is exactly BUFFER_SIZE bytes."""
    content = "A" * BUFFER_SIZE  # ASCII: 1 byte per char = exactly 65536 bytes

    assert len(content.encode("utf-8")) == BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        with open(path, "rb") as f:
            saved_bytes = f.read()
        assert saved_bytes == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_small_ascii_file():
    """Small ASCII files save correctly (regression guard)."""
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
