"""File saving module with proper UTF-8 buffer handling.

Fixes a regression introduced in v2.3.1 where the save buffer was
allocated based on character count instead of byte length, causing
a segmentation fault when saving files larger than 64KB containing
multibyte UTF-8 characters (e.g., emoji or CJK characters).
"""

BUFFER_SIZE = 65536  # 64KB


def calculate_buffer_size(content: str) -> int:
    """Calculate the required buffer size in bytes for the given content.

    Uses the byte length of the UTF-8 encoded content rather than the
    character count. Multibyte UTF-8 characters (emoji, CJK, etc.) use
    2-4 bytes per codepoint, so the byte length can be significantly
    larger than the character count.

    Args:
        content: The string content to calculate buffer size for.

    Returns:
        The required buffer size in bytes, rounded up to the next
        multiple of BUFFER_SIZE.
    """
    byte_length = len(content.encode("utf-8"))
    # Round up to the next buffer-size boundary
    return ((byte_length // BUFFER_SIZE) + 1) * BUFFER_SIZE


def save_file(path: str, content: str) -> int:
    """Save content to a file with proper UTF-8 handling.

    Allocates the write buffer based on the byte length of the UTF-8
    encoded content, not the character count.

    Args:
        path: The file path to write to.
        content: The string content to save.

    Returns:
        The number of bytes written.
    """
    encoded = content.encode("utf-8")
    buffer_size = calculate_buffer_size(content)

    if buffer_size < len(encoded):
        raise ValueError(
            f"Buffer size {buffer_size} is smaller than content size "
            f"{len(encoded)}"
        )

    with open(path, "wb") as f:
        bytes_written = f.write(encoded)

    return bytes_written
