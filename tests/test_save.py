"""Tests for the save module's UTF-8 multibyte character handling.

Covers the regression introduced in v2.3.1 where files larger than
64KB containing multibyte UTF-8 characters (emoji, CJK) caused a
segmentation fault due to buffer allocation based on character count
rather than byte length.
"""

import os
import tempfile

import pytest

from src.save import DEFAULT_BUFFER_SIZE, calculate_buffer_size, save_file


class TestCalculateBufferSize:
    """Test byte-length calculation for various character types."""

    def test_ascii_only(self):
        content = "a" * 1000
        assert calculate_buffer_size(content) == 1000

    def test_emoji_characters(self):
        # Each emoji is 4 bytes in UTF-8
        content = "😀" * 100
        assert calculate_buffer_size(content) == 400

    def test_cjk_characters(self):
        # Each CJK character is 3 bytes in UTF-8
        content = "漢" * 100
        assert calculate_buffer_size(content) == 300

    def test_mixed_ascii_and_multibyte(self):
        content = "hello 😀 world 漢字"
        char_count = len(content)
        byte_count = calculate_buffer_size(content)
        assert byte_count > char_count

    def test_char_count_under_64k_but_byte_count_over(self):
        """Edge case: character count fits in 64KB but byte count does not."""
        # 20000 emoji = 20000 chars but 80000 bytes (> 64KB)
        content = "😀" * 20000
        assert len(content) < DEFAULT_BUFFER_SIZE
        assert calculate_buffer_size(content) > DEFAULT_BUFFER_SIZE


class TestSaveFile:
    """Test file saving with various sizes and character encodings."""

    def test_save_small_ascii_file(self, tmp_path):
        filepath = str(tmp_path / "small.txt")
        content = "Hello, world!"
        bytes_written = save_file(filepath, content)
        assert bytes_written == len(content)
        with open(filepath, "rb") as f:
            assert f.read() == content.encode("utf-8")

    def test_save_70kb_emoji_text(self, tmp_path):
        """Reproduces the reported crash: 70KB of emoji text."""
        filepath = str(tmp_path / "emoji_large.txt")
        # Generate ~70KB of emoji text (each emoji = 4 bytes)
        emoji_count = (70 * 1024) // 4
        content = "😀" * emoji_count
        bytes_written = save_file(filepath, content)
        expected_bytes = emoji_count * 4
        assert bytes_written == expected_bytes
        with open(filepath, "rb") as f:
            saved = f.read()
        assert saved.decode("utf-8") == content

    def test_save_64kb_emoji_boundary(self, tmp_path):
        """Boundary test at exactly 64KB of emoji content."""
        filepath = str(tmp_path / "emoji_boundary.txt")
        emoji_count = DEFAULT_BUFFER_SIZE // 4
        content = "😀" * emoji_count
        bytes_written = save_file(filepath, content)
        assert bytes_written == emoji_count * 4
        with open(filepath, "rb") as f:
            assert f.read().decode("utf-8") == content

    def test_save_70kb_ascii_text(self, tmp_path):
        """Control test: 70KB ASCII text should save fine."""
        filepath = str(tmp_path / "ascii_large.txt")
        content = "A" * (70 * 1024)
        bytes_written = save_file(filepath, content)
        assert bytes_written == 70 * 1024
        with open(filepath, "rb") as f:
            assert f.read().decode("utf-8") == content

    def test_save_mixed_ascii_multibyte_over_64kb(self, tmp_path):
        """Mixed ASCII and multibyte content exceeding 64KB."""
        filepath = str(tmp_path / "mixed_large.txt")
        # Build content with mix of ASCII and emoji
        chunk = "Hello 😀 World 漢字 " * 5000
        # Ensure byte count exceeds 64KB
        while calculate_buffer_size(chunk) <= DEFAULT_BUFFER_SIZE:
            chunk += "Hello 😀 World 漢字 "
        bytes_written = save_file(filepath, chunk)
        assert bytes_written == calculate_buffer_size(chunk)
        with open(filepath, "rb") as f:
            assert f.read().decode("utf-8") == chunk

    def test_save_creates_parent_directories(self, tmp_path):
        filepath = str(tmp_path / "nested" / "dir" / "file.txt")
        content = "test content"
        save_file(filepath, content)
        assert os.path.exists(filepath)

    def test_save_empty_file(self, tmp_path):
        filepath = str(tmp_path / "empty.txt")
        bytes_written = save_file(filepath, "")
        assert bytes_written == 0
        assert os.path.getsize(filepath) == 0
