"""Tests for file_saver module.

Test matrix from triage analysis:
1. >64KB ASCII-only content → should save successfully
2. <64KB with multibyte UTF-8 (emoji/CJK) → should save successfully
3. >64KB with multibyte UTF-8 → should save successfully (was segfault)
4. Character count <64K but byte count >64KB (dense multibyte) → should save
5. Edge: 65536 bytes exactly, with multibyte char spanning boundary → should save
"""

import os
import tempfile

import pytest

from src.file_saver import BUFFER_SIZE, calculate_buffer_size, save_file


class TestCalculateBufferSize:
    """Tests for calculate_buffer_size function."""

    def test_ascii_only(self):
        """ASCII characters are 1 byte each."""
        content = "hello"
        assert calculate_buffer_size(content) == 5

    def test_multibyte_emoji(self):
        """Emoji characters are 4 bytes each in UTF-8."""
        content = "\U0001f600"  # 😀
        assert calculate_buffer_size(content) == 4

    def test_multibyte_cjk(self):
        """CJK characters are 3 bytes each in UTF-8."""
        content = "世"  # 世
        assert calculate_buffer_size(content) == 3

    def test_mixed_content(self):
        """Mixed ASCII and multibyte characters."""
        # 'a' = 1 byte, '😀' = 4 bytes
        content = "a\U0001f600"
        assert calculate_buffer_size(content) == 5

    def test_empty_string(self):
        """Empty string has zero byte length."""
        assert calculate_buffer_size("") == 0

    def test_byte_count_exceeds_char_count(self):
        """Byte count should exceed character count for multibyte content.

        This is the core of the v2.3.1 regression: using len(content)
        instead of len(content.encode('utf-8')) underestimates the
        buffer needed for multibyte characters.
        """
        # 20000 emoji characters = 20000 chars but 80000 bytes
        content = "\U0001f600" * 20000
        char_count = len(content)
        byte_count = calculate_buffer_size(content)
        assert char_count == 20000
        assert byte_count == 80000
        assert byte_count > BUFFER_SIZE
        assert char_count < BUFFER_SIZE


class TestSaveFile:
    """Tests for save_file function."""

    def test_save_ascii_over_64kb(self):
        """Test 1: >64KB ASCII-only content saves successfully."""
        content = "A" * (BUFFER_SIZE + 1024)
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            bytes_written = save_file(filepath, content)
            assert bytes_written == BUFFER_SIZE + 1024
            with open(filepath, "r", encoding="utf-8") as f:
                assert f.read() == content

    def test_save_multibyte_under_64kb(self):
        """Test 2: <64KB with multibyte UTF-8 saves successfully."""
        # 1000 emoji = 4000 bytes, well under 64KB
        content = "\U0001f600" * 1000
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            bytes_written = save_file(filepath, content)
            assert bytes_written == 4000
            with open(filepath, "r", encoding="utf-8") as f:
                assert f.read() == content

    def test_save_multibyte_over_64kb(self):
        """Test 3: >64KB with multibyte UTF-8 saves successfully.

        This is the exact scenario that caused the v2.3.1 segfault.
        The character count (20000) is below 64KB but the byte count
        (80000) exceeds it. With the old code, the buffer was sized
        to 20000 bytes, causing overflow when writing 80000 bytes.
        """
        # 20000 emoji chars = 20000 chars, 80000 bytes (>64KB)
        content = "\U0001f600" * 20000
        assert len(content) < BUFFER_SIZE  # char count under threshold
        assert len(content.encode("utf-8")) > BUFFER_SIZE  # byte count over

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            bytes_written = save_file(filepath, content)
            assert bytes_written == 80000
            with open(filepath, "r", encoding="utf-8") as f:
                assert f.read() == content

    def test_save_dense_multibyte_over_64kb_bytes(self):
        """Test 4: Char count <64K but byte count >64KB saves successfully."""
        # CJK characters: 3 bytes each
        # 25000 CJK chars = 25000 chars, 75000 bytes (>64KB)
        content = "世" * 25000
        assert len(content) < BUFFER_SIZE
        assert len(content.encode("utf-8")) > BUFFER_SIZE

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            bytes_written = save_file(filepath, content)
            assert bytes_written == 75000
            with open(filepath, "r", encoding="utf-8") as f:
                assert f.read() == content

    def test_save_boundary_with_multibyte_spanning(self):
        """Test 5: 65536 bytes exactly, with multibyte char at boundary."""
        # Fill with ASCII up to near boundary, then add a multibyte char
        # that pushes past or lands exactly at 65536 bytes
        ascii_part = "A" * (BUFFER_SIZE - 4)  # 65532 ASCII bytes
        emoji = "\U0001f600"  # 4 bytes
        content = ascii_part + emoji  # 65536 bytes total

        assert calculate_buffer_size(content) == BUFFER_SIZE

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            bytes_written = save_file(filepath, content)
            assert bytes_written == BUFFER_SIZE
            with open(filepath, "r", encoding="utf-8") as f:
                assert f.read() == content

    def test_save_empty_content(self):
        """Empty content saves as empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            bytes_written = save_file(filepath, "")
            assert bytes_written == 0
            with open(filepath, "r", encoding="utf-8") as f:
                assert f.read() == ""

    def test_save_none_content_raises(self):
        """None content raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            with pytest.raises(ValueError, match="Content cannot be None"):
                save_file(filepath, None)

    def test_save_creates_parent_directories(self):
        """Save creates parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "sub", "dir", "test.txt")
            save_file(filepath, "hello")
            with open(filepath, "r", encoding="utf-8") as f:
                assert f.read() == "hello"

    def test_save_returns_byte_count(self):
        """Return value is byte count, not character count."""
        content = "\U0001f600" * 10  # 10 chars, 40 bytes
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            result = save_file(filepath, content)
            assert result == 40
            assert result != len(content)
