"""File saving module with proper UTF-8 buffer handling."""

import os

# Buffer size threshold in bytes
BUFFER_SIZE = 65536  # 64KB


def save_file(filepath, content):
    """Save content to a file, handling UTF-8 multibyte characters correctly.

    The buffer is sized by byte count of the encoded content, not by
    character count. This ensures that multibyte UTF-8 characters
    (emoji, CJK, accented characters) do not cause a buffer overrun
    when the encoded byte length exceeds the character count.

    Args:
        filepath: Path to the destination file.
        content: String content to save.

    Returns:
        The number of bytes written.
    """
    encoded = content.encode("utf-8")
    byte_length = len(encoded)

    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(filepath, "wb") as f:
        offset = 0
        while offset < byte_length:
            chunk = encoded[offset : offset + BUFFER_SIZE]
            f.write(chunk)
            offset += len(chunk)

    return byte_length
