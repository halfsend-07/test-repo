"""Tests for the file_handler module.

Verifies that save_file correctly handles UTF-8 multibyte characters
at various file sizes, including the previously-crashing case of files
larger than 64KB containing multibyte characters.
"""

import os
import tempfile
from unittest import mock

import pytest

from src.file_handler import BUFFER_SIZE, load_file, save_file


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


def _make_multibyte_content(target_bytes: int) -> str:
    """Generate a string of emoji characters whose UTF-8 encoding is
    approximately ``target_bytes`` bytes long.

    Each emoji (e.g. U+1F600) encodes to 4 bytes in UTF-8.
    """
    emoji = "\U0001F600"  # 😀 — 4 bytes in UTF-8
    count = target_bytes // len(emoji.encode("utf-8"))
    return emoji * count


def _make_mixed_content(target_bytes: int) -> str:
    """Generate mixed ASCII and multibyte content of approximately
    ``target_bytes`` bytes."""
    # Alternate between ASCII and emoji to create mixed content.
    ascii_part = "Hello, world! "  # 14 bytes
    emoji_part = "\U0001F600\U0001F601\U0001F602"  # 12 bytes (3 × 4)
    unit = ascii_part + emoji_part  # 26 bytes per unit
    unit_bytes = len(unit.encode("utf-8"))
    count = target_bytes // unit_bytes
    return unit * count


class TestSaveFileUnderBufferSize:
    """Files under 64KB with multibyte UTF-8 chars should save correctly."""

    def test_small_multibyte_file(self, tmp_dir):
        content = _make_multibyte_content(BUFFER_SIZE - 1024)
        filepath = os.path.join(tmp_dir, "small.txt")

        save_file(content, filepath)
        result = load_file(filepath)

        assert result == content

    def test_just_under_boundary(self, tmp_dir):
        # File just under 64KB with multibyte characters
        content = _make_multibyte_content(BUFFER_SIZE - 4)
        filepath = os.path.join(tmp_dir, "just_under.txt")

        save_file(content, filepath)
        result = load_file(filepath)

        assert result == content


class TestSaveFileOverBufferSize:
    """Files over 64KB with multibyte UTF-8 chars — the crash scenario."""

    def test_just_over_boundary(self, tmp_dir):
        """This is the exact scenario that previously caused a segfault:
        a file just over 64KB with multibyte characters."""
        content = _make_multibyte_content(BUFFER_SIZE + 1024)
        filepath = os.path.join(tmp_dir, "just_over.txt")

        save_file(content, filepath)
        result = load_file(filepath)

        assert result == content

    def test_large_multibyte_file(self, tmp_dir):
        """256KB file with multibyte characters."""
        content = _make_multibyte_content(256 * 1024)
        filepath = os.path.join(tmp_dir, "large.txt")

        save_file(content, filepath)
        result = load_file(filepath)

        assert result == content

    def test_large_mixed_content(self, tmp_dir):
        """256KB file with mixed ASCII and multibyte characters."""
        content = _make_mixed_content(256 * 1024)
        filepath = os.path.join(tmp_dir, "mixed.txt")

        save_file(content, filepath)
        result = load_file(filepath)

        assert result == content


class TestRoundTripIntegrity:
    """Verify saved content matches original exactly after round-trip."""

    def test_roundtrip_emoji(self, tmp_dir):
        content = "Hello 🌍🌎🌏 World! " * 5000
        filepath = os.path.join(tmp_dir, "emoji.txt")

        save_file(content, filepath)
        assert load_file(filepath) == content

    def test_roundtrip_cjk(self, tmp_dir):
        content = "漢字テスト文字列 " * 10000
        filepath = os.path.join(tmp_dir, "cjk.txt")

        save_file(content, filepath)
        assert load_file(filepath) == content

    def test_roundtrip_mixed_scripts(self, tmp_dir):
        content = "ASCII Ñoño 日本語 🎉 Ελληνικά العربية " * 3000
        filepath = os.path.join(tmp_dir, "mixed_scripts.txt")

        save_file(content, filepath)
        assert load_file(filepath) == content


class TestEdgeCases:
    """Edge cases for save_file."""

    def test_empty_content(self, tmp_dir):
        filepath = os.path.join(tmp_dir, "empty.txt")
        save_file("", filepath)
        assert load_file(filepath) == ""

    def test_ascii_only_large(self, tmp_dir):
        content = "a" * (BUFFER_SIZE + 1024)
        filepath = os.path.join(tmp_dir, "ascii_large.txt")
        save_file(content, filepath)
        assert load_file(filepath) == content

    def test_none_content_raises(self, tmp_dir):
        filepath = os.path.join(tmp_dir, "none.txt")
        with pytest.raises(ValueError, match="content must not be None"):
            save_file(None, filepath)

    def test_creates_parent_directories(self, tmp_dir):
        filepath = os.path.join(tmp_dir, "sub", "dir", "file.txt")
        save_file("test content", filepath)
        assert load_file(filepath) == "test content"

    def test_exact_buffer_boundary(self, tmp_dir):
        """Content whose byte length is exactly BUFFER_SIZE."""
        emoji = "\U0001F600"
        count = BUFFER_SIZE // len(emoji.encode("utf-8"))
        content = emoji * count
        assert len(content.encode("utf-8")) == BUFFER_SIZE

        filepath = os.path.join(tmp_dir, "exact.txt")
        save_file(content, filepath)
        assert load_file(filepath) == content


class TestErrorCleanup:
    """Verify error paths clean up temp files and propagate exceptions."""

    def test_write_failure_cleans_up_temp_file(self, tmp_dir):
        """When os.write fails, the temp file should be removed."""
        filepath = os.path.join(tmp_dir, "fail.txt")
        with mock.patch("src.file_handler.os.write", side_effect=OSError("disk full")):
            with pytest.raises(OSError, match="disk full"):
                save_file("some content", filepath)
        # No temp files should remain in the directory
        remaining = os.listdir(tmp_dir)
        assert remaining == [], f"Temp files leaked: {remaining}"

    def test_replace_failure_cleans_up_temp_file(self, tmp_dir):
        """When os.replace fails after a successful write, the temp file
        should still be cleaned up and the fd should not be double-closed."""
        filepath = os.path.join(tmp_dir, "fail.txt")
        with mock.patch("src.file_handler.os.replace", side_effect=OSError("permission denied")):
            with pytest.raises(OSError, match="permission denied"):
                save_file("some content", filepath)
        # No temp files should remain
        remaining = os.listdir(tmp_dir)
        assert remaining == [], f"Temp files leaked: {remaining}"

    def test_replace_failure_does_not_double_close(self, tmp_dir):
        """Regression test: os.replace failure must not attempt to close
        an already-closed file descriptor (the double-close bug)."""
        filepath = os.path.join(tmp_dir, "fail.txt")
        original_close = os.close
        close_calls = []

        def tracking_close(fd):
            close_calls.append(fd)
            return original_close(fd)

        with mock.patch("src.file_handler.os.close", side_effect=tracking_close):
            with mock.patch("src.file_handler.os.replace", side_effect=OSError("perm")):
                with pytest.raises(OSError, match="perm"):
                    save_file("test", filepath)

        # The fd should be closed exactly once, not twice
        assert len(close_calls) == 1, (
            f"Expected fd to be closed once, but os.close was called "
            f"{len(close_calls)} times"
        )
