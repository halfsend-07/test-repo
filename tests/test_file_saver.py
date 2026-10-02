"""Tests for file_saver module.

Covers the UTF-8 buffer allocation fix for issue #1866: saving files
larger than 64KB with multibyte characters must not crash.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from file_saver import BUFFER_SIZE, calculate_buffer_size, save_file


class TestCalculateBufferSize:
    """Tests for calculate_buffer_size."""

    def test_ascii_within_one_buffer(self):
        content = "a" * 100
        assert calculate_buffer_size(content) == BUFFER_SIZE

    def test_ascii_over_64kb(self):
        content = "a" * (BUFFER_SIZE + 1)
        assert calculate_buffer_size(content) == BUFFER_SIZE * 2

    def test_emoji_4byte_sequences_over_64kb(self):
        """65KB of emoji (4 bytes each) requires a buffer sized by bytes."""
        # Each emoji is 4 bytes in UTF-8; 16385 emoji = 65540 bytes > 64KB
        emoji_count = (BUFFER_SIZE // 4) + 1
        content = "\U0001f600" * emoji_count  # 😀
        byte_length = len(content.encode("utf-8"))
        assert byte_length > BUFFER_SIZE
        buf = calculate_buffer_size(content)
        assert buf >= byte_length

    def test_cjk_3byte_sequences_over_64kb(self):
        """CJK characters are 3 bytes each in UTF-8."""
        char_count = (BUFFER_SIZE // 3) + 1
        content = "世" * char_count  # 世
        byte_length = len(content.encode("utf-8"))
        assert byte_length > BUFFER_SIZE
        buf = calculate_buffer_size(content)
        assert buf >= byte_length

    def test_mixed_ascii_and_multibyte(self):
        """Mixed content must use byte length, not character count."""
        ascii_part = "a" * 60000
        emoji_part = "\U0001f600" * 2000  # 8000 bytes
        content = ascii_part + emoji_part
        byte_length = len(content.encode("utf-8"))
        assert byte_length > BUFFER_SIZE
        buf = calculate_buffer_size(content)
        assert buf >= byte_length

    def test_content_under_64kb_multibyte(self):
        """Content under 64KB should still allocate correctly."""
        content = "\U0001f600" * 100  # 400 bytes
        buf = calculate_buffer_size(content)
        assert buf == BUFFER_SIZE


class TestSaveFile:
    """Tests for save_file."""

    def test_save_65kb_emoji_content(self):
        """Saving 65KB of emoji must succeed without crashing."""
        emoji_count = (BUFFER_SIZE // 4) + 1
        content = "\U0001f600" * emoji_count
        byte_length = len(content.encode("utf-8"))

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name

        try:
            bytes_written = save_file(path, content)
            assert bytes_written == byte_length

            with open(path, "rb") as f:
                saved = f.read()
            assert saved.decode("utf-8") == content
        finally:
            os.unlink(path)

    def test_save_70kb_mixed_content(self):
        """Saving 70KB of mixed ASCII and CJK must succeed."""
        ascii_part = "Hello world! " * 4000  # ~52KB
        cjk_part = "世界" * 10000  # ~60KB
        content = ascii_part + cjk_part

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name

        try:
            bytes_written = save_file(path, content)
            assert bytes_written == len(content.encode("utf-8"))

            with open(path, "rb") as f:
                saved = f.read()
            assert saved.decode("utf-8") == content
        finally:
            os.unlink(path)

    def test_save_under_64kb_multibyte(self):
        """Control case: under 64KB with multibyte must succeed."""
        content = "\U0001f600" * 1000  # 4000 bytes
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name

        try:
            bytes_written = save_file(path, content)
            assert bytes_written == len(content.encode("utf-8"))
        finally:
            os.unlink(path)

    def test_save_over_64kb_ascii_only(self):
        """Control case: over 64KB ASCII-only must succeed."""
        content = "x" * (BUFFER_SIZE + 5000)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name

        try:
            bytes_written = save_file(path, content)
            assert bytes_written == len(content.encode("utf-8"))
        finally:
            os.unlink(path)

    def test_roundtrip_preserves_content(self):
        """Saved content must round-trip intact through UTF-8."""
        content = "ASCII世\U0001f600Mixedé" * 5000
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name

        try:
            save_file(path, content)
            with open(path, "rb") as f:
                saved = f.read()
            assert saved.decode("utf-8") == content
        finally:
            os.unlink(path)
