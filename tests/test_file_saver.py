"""Tests for file_saver module.

Covers boundary conditions around the 64KB buffer size with both
ASCII-only and multibyte UTF-8 content, verifying the fix for the
v2.3.1 regression where files > 64KB with multibyte characters caused
a buffer overflow.
"""

import os
import tempfile

import pytest

from src.file_saver import (
    DEFAULT_BUFFER_SIZE,
    _calculate_byte_length,
    save_file,
)


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory for test output files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestCalculateByteLength:
    """Tests for _calculate_byte_length."""

    def test_ascii_string(self):
        assert _calculate_byte_length("hello") == 5

    def test_empty_string(self):
        assert _calculate_byte_length("") == 0

    def test_emoji_characters(self):
        # Each emoji is 4 bytes in UTF-8
        content = "\U0001f600"  # 😀
        assert _calculate_byte_length(content) == 4

    def test_cjk_characters(self):
        # CJK characters are 3 bytes each in UTF-8
        content = "世界"  # 世界
        assert _calculate_byte_length(content) == 6

    def test_mixed_content(self):
        # 5 ASCII (5 bytes) + 1 emoji (4 bytes) = 9 bytes
        content = "hello\U0001f600"
        assert _calculate_byte_length(content) == 9

    def test_bytes_input(self):
        content = b"hello"
        assert _calculate_byte_length(content) == 5


class TestSaveFileASCII:
    """Tests for save_file with ASCII-only content."""

    def test_small_ascii_file(self, tmp_dir):
        """ASCII file under 64KB saves successfully."""
        filepath = os.path.join(tmp_dir, "small.txt")
        content = "a" * 1000
        bytes_written = save_file(filepath, content)

        assert bytes_written == 1000
        with open(filepath, "rb") as f:
            assert f.read() == content.encode("utf-8")

    def test_ascii_file_under_64kb(self, tmp_dir):
        """ASCII file just under 64KB saves successfully."""
        filepath = os.path.join(tmp_dir, "under_64kb.txt")
        content = "a" * (DEFAULT_BUFFER_SIZE - 1)
        bytes_written = save_file(filepath, content)

        assert bytes_written == DEFAULT_BUFFER_SIZE - 1
        with open(filepath, "rb") as f:
            assert f.read() == content.encode("utf-8")

    def test_ascii_file_over_64kb(self, tmp_dir):
        """ASCII file over 64KB saves successfully."""
        filepath = os.path.join(tmp_dir, "over_64kb.txt")
        content = "a" * (DEFAULT_BUFFER_SIZE + 10000)
        bytes_written = save_file(filepath, content)

        assert bytes_written == DEFAULT_BUFFER_SIZE + 10000
        with open(filepath, "rb") as f:
            assert f.read() == content.encode("utf-8")


class TestSaveFileUTF8:
    """Tests for save_file with multibyte UTF-8 content.

    These tests cover the regression case: files > 64KB in byte length
    that contain multibyte UTF-8 characters.
    """

    def test_multibyte_file_under_64kb_bytes(self, tmp_dir):
        """Multibyte UTF-8 file under 64KB (by bytes) saves successfully."""
        filepath = os.path.join(tmp_dir, "utf8_under.txt")
        # Each emoji is 4 bytes; 1000 emojis = 4000 bytes (well under 64KB)
        content = "\U0001f600" * 1000
        bytes_written = save_file(filepath, content)

        assert bytes_written == 4000
        with open(filepath, "rb") as f:
            saved = f.read()
        assert saved.decode("utf-8") == content

    def test_multibyte_file_over_64kb_bytes(self, tmp_dir):
        """Multibyte UTF-8 file over 64KB (by bytes) saves successfully.

        This is the primary regression test. In v2.3.1, this case caused
        a buffer overflow because the buffer was allocated based on
        character count (which would be ~17K characters for 70KB of emoji)
        rather than byte count (~70KB).
        """
        filepath = os.path.join(tmp_dir, "utf8_over.txt")
        # 70KB of text with emoji: each emoji is 4 bytes
        # 18000 emojis = 72000 bytes > 64KB
        num_emojis = 18000
        content = "\U0001f600" * num_emojis
        expected_bytes = num_emojis * 4

        bytes_written = save_file(filepath, content)

        assert bytes_written == expected_bytes
        with open(filepath, "rb") as f:
            saved = f.read()
        assert len(saved) == expected_bytes
        assert saved.decode("utf-8") == content

    def test_mixed_content_over_64kb(self, tmp_dir):
        """Mixed ASCII + multibyte content over 64KB saves successfully."""
        filepath = os.path.join(tmp_dir, "mixed_over.txt")
        # Mix of ASCII and emoji to exceed 64KB
        # 10000 ASCII chars (10000 bytes) + 15000 emoji (60000 bytes) = 70000 bytes
        content = "a" * 10000 + "\U0001f600" * 15000
        expected_bytes = 10000 + 15000 * 4

        bytes_written = save_file(filepath, content)

        assert bytes_written == expected_bytes
        with open(filepath, "rb") as f:
            saved = f.read()
        assert saved.decode("utf-8") == content

    def test_cjk_content_over_64kb(self, tmp_dir):
        """CJK content over 64KB saves successfully."""
        filepath = os.path.join(tmp_dir, "cjk_over.txt")
        # CJK characters are 3 bytes each
        # 22000 CJK chars = 66000 bytes > 64KB
        content = "世" * 22000
        expected_bytes = 22000 * 3

        bytes_written = save_file(filepath, content)

        assert bytes_written == expected_bytes
        with open(filepath, "rb") as f:
            saved = f.read()
        assert saved.decode("utf-8") == content

    def test_content_roundtrip_preserves_encoding(self, tmp_dir):
        """Saved content matches original after roundtrip."""
        filepath = os.path.join(tmp_dir, "roundtrip.txt")
        # Realistic mixed content with various UTF-8 character widths
        content = (
            "Hello World! "
            "éèê "  # 2-byte: accented chars
            "世界 "  # 3-byte: CJK
            "\U0001f600\U0001f389 "  # 4-byte: emoji
        ) * 5000  # Repeat to exceed 64KB

        bytes_written = save_file(filepath, content)
        with open(filepath, "rb") as f:
            saved = f.read()

        assert len(saved) == bytes_written
        assert saved.decode("utf-8") == content


class TestSaveFileEdgeCases:
    """Edge case tests for save_file."""

    def test_empty_content(self, tmp_dir):
        filepath = os.path.join(tmp_dir, "empty.txt")
        bytes_written = save_file(filepath, "")
        assert bytes_written == 0

    def test_bytes_content(self, tmp_dir):
        filepath = os.path.join(tmp_dir, "bytes.txt")
        content = b"binary content \xff"
        bytes_written = save_file(filepath, content)
        assert bytes_written == len(content)

    def test_creates_parent_directories(self, tmp_dir):
        filepath = os.path.join(tmp_dir, "sub", "dir", "file.txt")
        save_file(filepath, "content")
        assert os.path.exists(filepath)

    def test_invalid_content_type(self, tmp_dir):
        filepath = os.path.join(tmp_dir, "invalid.txt")
        with pytest.raises(TypeError):
            save_file(filepath, 12345)

    def test_exactly_64kb_boundary_multibyte(self, tmp_dir):
        """File exactly at 64KB boundary with multibyte chars."""
        filepath = os.path.join(tmp_dir, "exact_64kb.txt")
        # 16384 emoji * 4 bytes = 65536 bytes = exactly 64KB
        content = "\U0001f600" * (DEFAULT_BUFFER_SIZE // 4)
        bytes_written = save_file(filepath, content)

        assert bytes_written == DEFAULT_BUFFER_SIZE
        with open(filepath, "rb") as f:
            saved = f.read()
        assert saved.decode("utf-8") == content
