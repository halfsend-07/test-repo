"""File save module with proper UTF-8 buffer handling.

Saves files using a chunked write strategy. Buffer sizes are calculated
using byte length rather than character count to correctly handle
multibyte UTF-8 sequences.
"""

BUFFER_SIZE = 65536  # 64KB


def save_file(path: str, content: str) -> None:
    """Save content to a file, handling large files with multibyte characters.

    Uses byte length (not character count) for buffer management to avoid
    buffer overflows when content contains multibyte UTF-8 characters
    such as emoji or CJK characters.

    Args:
        path: Destination file path.
        content: Text content to write.
    """
    encoded = content.encode("utf-8")
    with open(path, "wb") as f:
        offset = 0
        while offset < len(encoded):
            chunk = encoded[offset : offset + BUFFER_SIZE]
            f.write(chunk)
            offset += len(chunk)
