"""Tests for file_saver module.

Verifies the fix for issue #1123: buffer overflow when saving files
containing multibyte UTF-8 characters exceeding 64KB.
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from file_saver import DEFAULT_BUFFER_SIZE, _allocate_buffer, _byte_length, save_file


class TestByteLength:
    """Tests for _byte_length helper."""

    def test_ascii_string(self):
        assert _byte_length("hello") == 5

    def test_empty_string(self):
        assert _byte_length("") == 0

    def test_emoji_characters(self):
        # Each emoji is 4 bytes in UTF-8
        content = "\U0001f600" * 10
        assert _byte_length(content) == 40

    def test_cjk_characters(self):
        # CJK characters are 3 bytes each in UTF-8
        content = "世界" * 10  # "world" in Chinese, repeated
        assert _byte_length(content) == 60

    def test_mixed_content(self):
        content = "hello \U0001f600 世界"
        # "hello " = 6 bytes, emoji = 4 bytes, " " = 1 byte, 2 CJK = 6 bytes
        assert _byte_length(content) == 17

    def test_bytes_input(self):
        content = b"hello"
        assert _byte_length(content) == 5


class TestAllocateBuffer:
    """Tests for _allocate_buffer helper."""

    def test_small_content_uses_default(self):
        assert _allocate_buffer("hello") == DEFAULT_BUFFER_SIZE

    def test_content_at_boundary(self):
        # ASCII content exactly at 64KB
        content = "a" * DEFAULT_BUFFER_SIZE
        assert _allocate_buffer(content) == DEFAULT_BUFFER_SIZE

    def test_content_exceeds_default_by_chars(self):
        # 70KB of ASCII
        content = "a" * (DEFAULT_BUFFER_SIZE + 6144)
        assert _allocate_buffer(content) == DEFAULT_BUFFER_SIZE + 6144

    def test_char_count_under_but_byte_count_over(self):
        """Key regression test for issue #1123.

        Character count is under 64KB but byte count exceeds it.
        The old code used len(content) which returns character count,
        causing a buffer overflow.
        """
        # 20000 emoji = 20000 characters but 80000 bytes (>64KB)
        content = "\U0001f600" * 20000
        assert len(content) == 20000  # char count < 64KB
        assert _byte_length(content) == 80000  # byte count > 64KB
        buffer_size = _allocate_buffer(content)
        assert buffer_size == 80000  # buffer must fit all bytes


class TestSaveFile:
    """Tests for save_file function."""

    def test_save_ascii_content(self, tmp_path):
        filepath = str(tmp_path / "test.txt")
        content = "Hello, world!"
        written = save_file(filepath, content)
        assert written == 13
        with open(filepath, "rb") as f:
            assert f.read() == b"Hello, world!"

    def test_save_utf8_content(self, tmp_path):
        filepath = str(tmp_path / "test.txt")
        content = "Hello \U0001f600 世界"
        written = save_file(filepath, content)
        with open(filepath, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
        assert written == len(content.encode("utf-8"))

    def test_save_large_ascii_file(self, tmp_path):
        """Files over 64KB with ASCII should save fine."""
        filepath = str(tmp_path / "large_ascii.txt")
        content = "a" * (DEFAULT_BUFFER_SIZE + 10000)
        written = save_file(filepath, content)
        assert written == len(content)
        with open(filepath, "r") as f:
            assert f.read() == content

    def test_save_large_utf8_file(self, tmp_path):
        """Regression test for issue #1123.

        Files over 64KB in byte length with multibyte UTF-8 characters
        must save without crashing.
        """
        filepath = str(tmp_path / "large_utf8.txt")
        # Create content: 20000 emoji chars = 80000 bytes (>64KB)
        content = "\U0001f600" * 20000
        written = save_file(filepath, content)
        assert written == 80000
        with open(filepath, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")

    def test_save_at_exact_boundary(self, tmp_path):
        """Edge case: content exactly at 64KB boundary."""
        filepath = str(tmp_path / "boundary.txt")
        content = "a" * DEFAULT_BUFFER_SIZE
        written = save_file(filepath, content)
        assert written == DEFAULT_BUFFER_SIZE
        with open(filepath, "r") as f:
            assert f.read() == content

    def test_save_cjk_over_boundary(self, tmp_path):
        """CJK characters (3 bytes each) exceeding 64KB in bytes."""
        filepath = str(tmp_path / "cjk.txt")
        # 22000 CJK chars = 66000 bytes (just over 64KB)
        content = "世" * 22000
        assert len(content) == 22000  # chars under 64KB
        assert _byte_length(content) == 66000  # bytes over 64KB
        written = save_file(filepath, content)
        assert written == 66000
        with open(filepath, "rb") as f:
            assert f.read() == content.encode("utf-8")

    def test_roundtrip_preserves_content(self, tmp_path):
        """Saved content must match original when re-read."""
        filepath = str(tmp_path / "roundtrip.txt")
        content = "ASCII + emoji \U0001f680\U0001f31f + CJK 世界你好" * 5000
        save_file(filepath, content)
        with open(filepath, "r", encoding="utf-8") as f:
            loaded = f.read()
        assert loaded == content

    def test_save_bytes_content(self, tmp_path):
        filepath = str(tmp_path / "bytes.txt")
        content = b"raw bytes \x80\x81"
        written = save_file(filepath, content)
        assert written == len(content)
        with open(filepath, "rb") as f:
            assert f.read() == content

    def test_save_empty_content(self, tmp_path):
        filepath = str(tmp_path / "empty.txt")
        written = save_file(filepath, "")
        assert written == 0
        with open(filepath, "r") as f:
            assert f.read() == ""

    def test_save_rejects_invalid_type(self, tmp_path):
        filepath = str(tmp_path / "bad.txt")
        with pytest.raises(TypeError):
            save_file(filepath, 12345)

    def test_atomic_write_no_partial_on_error(self, tmp_path):
        """If save fails, the original file should not be corrupted."""
        filepath = str(tmp_path / "atomic.txt")
        # Write initial content
        with open(filepath, "w") as f:
            f.write("original")
        # Try to save to a read-only directory (should fail)
        bad_path = "/proc/nonexistent/test.txt"
        with pytest.raises(OSError):
            save_file(bad_path, "new content")
        # Original file should be untouched
        with open(filepath, "r") as f:
            assert f.read() == "original"
