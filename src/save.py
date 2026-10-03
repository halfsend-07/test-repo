"""File save module with proper UTF-8 multibyte character handling.

Allocates write buffers based on byte length of the encoded content,
not character count, to prevent buffer overflows when saving files
containing multibyte UTF-8 characters (emoji, CJK, etc.) that exceed
64KB.
"""

import os
from pathlib import Path

# Default buffer size: 64KB
DEFAULT_BUFFER_SIZE = 65536


def save_file(filepath: str, content: str, encoding: str = "utf-8") -> int:
    """Save content to a file, handling multibyte characters correctly.

    Encodes content to bytes first to ensure the buffer is sized by
    byte length rather than character count. This prevents buffer
    overflows when multibyte UTF-8 characters cause the byte
    representation to exceed the character count.

    Args:
        filepath: Path to the file to save.
        content: String content to write.
        encoding: Character encoding to use (default: utf-8).

    Returns:
        Number of bytes written.

    Raises:
        OSError: If the file cannot be written.
        UnicodeEncodeError: If content cannot be encoded.
    """
    encoded = content.encode(encoding)
    byte_length = len(encoded)

    dest = Path(filepath)
    dest.parent.mkdir(parents=True, exist_ok=True)

    bytes_written = 0
    with open(dest, "wb") as f:
        offset = 0
        while offset < byte_length:
            chunk = encoded[offset : offset + DEFAULT_BUFFER_SIZE]
            bytes_written += f.write(chunk)
            offset += len(chunk)

    return bytes_written


def calculate_buffer_size(content: str, encoding: str = "utf-8") -> int:
    """Return the byte length needed to store the encoded content.

    This is the fix for the v2.3.1 regression: the old code used
    ``len(content)`` (character count) instead of encoding first,
    which under-allocated the buffer for multibyte characters.

    Args:
        content: The string to measure.
        encoding: The target encoding (default: utf-8).

    Returns:
        Byte length of the encoded string.
    """
    return len(content.encode(encoding))
