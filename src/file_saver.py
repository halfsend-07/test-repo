"""File save module with correct UTF-8 buffer sizing.

Allocates write buffers based on byte length rather than character count
to prevent buffer overflows when content contains multibyte UTF-8 characters
(e.g., emoji, CJK characters).

Fixed in response to issue #1123: segfault when saving files >64KB
containing multibyte UTF-8 characters.
"""

import os
import tempfile

# Default buffer size: 64KB
DEFAULT_BUFFER_SIZE = 65536


def _byte_length(content):
    """Return the byte length of content when encoded as UTF-8.

    This replaces the previous logic that used len(content) (character
    count) for buffer sizing. For ASCII-only text, byte length equals
    character count. For multibyte UTF-8 characters, byte length can
    be 2-4x the character count, which caused buffer overflows when the
    character count fit within the buffer but the byte count did not.
    """
    if isinstance(content, bytes):
        return len(content)
    return len(content.encode("utf-8"))


def _allocate_buffer(content):
    """Allocate a buffer large enough for the UTF-8 byte representation.

    Uses byte length (not character count) to determine the required
    buffer size. Returns the buffer size, which is the larger of
    DEFAULT_BUFFER_SIZE and the actual byte length of the content.
    """
    byte_len = _byte_length(content)
    return max(DEFAULT_BUFFER_SIZE, byte_len)


def save_file(filepath, content):
    """Save content to a file, handling UTF-8 multibyte characters correctly.

    Uses atomic write (write to temp file, then rename) to prevent
    partial writes on failure. Buffer is sized based on byte length
    of the UTF-8 encoded content, not character count.

    Args:
        filepath: Path to the destination file.
        content: String content to write.

    Returns:
        Number of bytes written.

    Raises:
        OSError: If the file cannot be written.
        TypeError: If content is not a string or bytes.
    """
    if not isinstance(content, (str, bytes)):
        raise TypeError(f"content must be str or bytes, got {type(content).__name__}")

    # Allocate buffer based on byte length, not character count.
    # This is the fix for issue #1123: the previous implementation
    # used len(content) which returns character count for str objects.
    # For multibyte UTF-8 content, byte count > character count,
    # causing a buffer overflow when content exceeded 64KB in bytes
    # but not in characters.
    buffer_size = _allocate_buffer(content)

    if isinstance(content, str):
        encoded = content.encode("utf-8")
    else:
        encoded = content

    # Use atomic write to prevent data corruption on crash
    dir_name = os.path.dirname(os.path.abspath(filepath))
    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        # Write in chunks matching the allocated buffer size
        offset = 0
        total_written = 0
        while offset < len(encoded):
            chunk = encoded[offset : offset + buffer_size]
            written = os.write(fd, chunk)
            total_written += written
            offset += written
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.rename(tmp_path, filepath)
    except Exception:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return total_written
