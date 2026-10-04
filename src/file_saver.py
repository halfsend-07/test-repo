"""File saving module with correct UTF-8 buffer handling.

This module handles saving file content to disk, correctly sizing
buffers based on byte length rather than character count. This
prevents buffer overflows when content contains multibyte UTF-8
characters (e.g., emoji, CJK characters) and exceeds 64KB.

Fixed in response to segfault regression introduced in v2.3.1
where the buffer was allocated using len(content) (character count)
instead of len(content.encode('utf-8')) (byte count).
"""

import os
import tempfile

# Buffer size threshold in bytes (64KB)
BUFFER_SIZE = 65536


def calculate_buffer_size(content: str) -> int:
    """Calculate the required buffer size in bytes for the given content.

    Uses the byte length of the UTF-8 encoded content, not the character
    count. This is critical for multibyte characters where a single
    character can occupy up to 4 bytes in UTF-8.

    Args:
        content: The string content to calculate buffer size for.

    Returns:
        The number of bytes needed to store the UTF-8 encoded content.
    """
    return len(content.encode("utf-8"))


def save_file(filepath: str, content: str) -> int:
    """Save content to a file with correct UTF-8 buffer handling.

    Writes the content to a temporary file first, then atomically
    moves it to the target path. The buffer is sized based on the
    byte length of the UTF-8 encoded content, not the character count.

    Args:
        filepath: The path where the file should be saved.
        content: The string content to save.

    Returns:
        The number of bytes written.

    Raises:
        OSError: If the file cannot be written.
        ValueError: If content is None.
    """
    if content is None:
        raise ValueError("Content cannot be None")

    # Calculate buffer size based on byte length, not character count.
    # This is the fix for the v2.3.1 regression where len(content)
    # was used instead of len(encoded), causing buffer overflow when
    # multibyte UTF-8 characters pushed byte count beyond the
    # character-count-based allocation.
    encoded = content.encode("utf-8")
    byte_count = len(encoded)

    # Use a temporary file for atomic write
    dir_name = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(dir_name, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        os.write(fd, encoded)
        os.close(fd)
        os.replace(tmp_path, filepath)
    except Exception:
        os.close(fd) if not os.get_inheritable(fd) else None
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return byte_count
