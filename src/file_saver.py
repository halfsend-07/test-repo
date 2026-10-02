"""File saving module with proper UTF-8 buffer handling.

This module provides file saving functionality that correctly handles
UTF-8 multibyte characters by allocating write buffers based on byte
length rather than character count.

Fixed in response to a regression in v2.3.1 where files larger than
64KB containing multibyte UTF-8 characters (emoji, CJK, etc.) caused
a buffer overflow and segmentation fault.
"""

import os

# Default buffer size: 64KB
DEFAULT_BUFFER_SIZE = 65536


def _calculate_byte_length(content):
    """Return the byte length of content when encoded as UTF-8.

    This is the correct way to determine buffer size for UTF-8 content.
    Multibyte characters (emoji, CJK, accented characters, etc.) require
    2-4 bytes each, so byte length can exceed character count.

    Args:
        content: String content to measure.

    Returns:
        The number of bytes needed to represent the content in UTF-8.
    """
    if isinstance(content, bytes):
        return len(content)
    return len(content.encode("utf-8"))


def save_file(filepath, content):
    """Save content to a file with proper UTF-8 encoding.

    Uses byte length (not character count) to allocate the write buffer,
    preventing buffer overflow when content contains multibyte UTF-8
    characters.

    The previous implementation (v2.3.1 regression) used len(content)
    which returns the character count. For multibyte UTF-8 characters,
    the actual byte length can be 2-4x the character count, causing a
    buffer overflow when the byte length exceeds 64KB even though the
    character count is within the limit.

    Args:
        filepath: Path to the output file.
        content: String content to save.

    Returns:
        The number of bytes written.

    Raises:
        OSError: If the file cannot be written.
        TypeError: If content is not a string or bytes.
    """
    if not isinstance(content, (str, bytes)):
        raise TypeError(
            f"content must be str or bytes, not {type(content).__name__}"
        )

    if isinstance(content, str):
        encoded = content.encode("utf-8")
    else:
        encoded = content

    # Use byte length for buffer size calculation, not character count.
    # This is the fix for the v2.3.1 regression: the old code used
    # len(content) which gives character count, not byte count.
    byte_length = len(encoded)
    buffer_size = max(DEFAULT_BUFFER_SIZE, byte_length)

    parent_dir = os.path.dirname(filepath)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    # Write using a buffer sized to the actual byte length
    with open(filepath, "wb", buffering=buffer_size) as f:
        bytes_written = f.write(encoded)

    return bytes_written
