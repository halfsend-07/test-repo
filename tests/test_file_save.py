"""Tests for file_save module.

Covers the UTF-8 multibyte buffer overflow regression (issue #1870):
- ASCII-only files above 64KB save correctly
- Multibyte UTF-8 files below 64KB save correctly
- Multibyte UTF-8 files above 64KB save correctly (the crash case)
- Files at the 64KB boundary with trailing multibyte characters save correctly
- Round-trip: saved content matches original byte-for-byte
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from file_save import save_file


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


class TestSaveFileUTF8:
    """Test save_file with various UTF-8 content sizes."""

    def test_ascii_only_above_64kb(self, tmp_dir):
        """ASCII-only file at 70KB should save successfully."""
        path = str(tmp_dir / "ascii_large.txt")
        content = "A" * (70 * 1024)
        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            result = f.read()
        assert result == content

    def test_multibyte_utf8_below_64kb(self, tmp_dir):
        """Multibyte UTF-8 file at 30KB should save successfully."""
        path = str(tmp_dir / "utf8_small.txt")
        # Each emoji is 4 bytes in UTF-8; 30KB / 4 = 7680 emoji characters
        content = "\U0001F600" * 7680
        assert len(content.encode("utf-8")) < 65536
        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            result = f.read()
        assert result == content

    def test_multibyte_utf8_above_64kb(self, tmp_dir):
        """Multibyte UTF-8 file at 70KB should save successfully.

        This is the crash case from issue #1870: files over 64KB with
        multibyte characters caused a segfault because the buffer was
        allocated using character count instead of byte length.
        """
        path = str(tmp_dir / "utf8_large.txt")
        # Each emoji is 4 bytes; 70KB / 4 = 17920 emoji characters
        content = "\U0001F600" * 17920
        byte_len = len(content.encode("utf-8"))
        assert byte_len > 65536
        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            result = f.read()
        assert result == content

    def test_boundary_with_trailing_multibyte(self, tmp_dir):
        """File exactly at 64KB boundary with trailing 4-byte emoji."""
        path = str(tmp_dir / "boundary.txt")
        # Fill to just under 64KB with ASCII, then add a 4-byte emoji
        ascii_part = "X" * (65536 - 1)
        content = ascii_part + "\U0001F60E"  # sunglasses emoji (4 bytes)
        byte_len = len(content.encode("utf-8"))
        # 65535 ASCII bytes + 4 emoji bytes = 65539 total bytes (just over 64KB)
        assert byte_len > 65536
        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            result = f.read()
        assert result == content

    def test_roundtrip_byte_exact(self, tmp_dir):
        """Saved content must match original byte-for-byte."""
        path = str(tmp_dir / "roundtrip.txt")
        # Mix of ASCII, 2-byte (é), 3-byte (中), and 4-byte (emoji)
        content = "Hello é 中文 \U0001F680\U0001F30D end" * 5000
        save_file(path, content)

        with open(path, "rb") as f:
            saved_bytes = f.read()
        assert saved_bytes == content.encode("utf-8")

    def test_cjk_characters_above_64kb(self, tmp_dir):
        """CJK characters (3 bytes each) above 64KB save correctly."""
        path = str(tmp_dir / "cjk_large.txt")
        # Each CJK character is 3 bytes; need > 21846 chars to exceed 64KB
        content = "中" * 22000
        assert len(content.encode("utf-8")) > 65536
        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            result = f.read()
        assert result == content

    def test_empty_file(self, tmp_dir):
        """Empty content should save as an empty file."""
        path = str(tmp_dir / "empty.txt")
        save_file(path, "")

        with open(path, "r", encoding="utf-8") as f:
            result = f.read()
        assert result == ""

    def test_type_error_on_non_string(self, tmp_dir):
        """Non-string content should raise TypeError."""
        path = str(tmp_dir / "bad.txt")
        with pytest.raises(TypeError, match="content must be str"):
            save_file(path, b"bytes are not strings")
