"""File handler module for saving documents.

Handles file I/O with proper UTF-8 encoding support, including
correct buffer sizing based on byte length rather than character count.
"""

import os
import tempfile

# Buffer size threshold for chunked writes (64KB)
BUFFER_SIZE = 65536


def save_file(content: str | None, filepath: str) -> None:
    """Save content to a file with proper UTF-8 encoding.

    Uses byte-length-aware buffering to correctly handle multibyte
    UTF-8 characters (emoji, CJK, accented characters, etc.) at any
    file size.

    The content is first encoded to UTF-8 bytes, then written in
    chunks sized by byte length. This avoids the bug where using
    character count to size buffers causes a buffer overflow when
    multibyte characters make the byte length exceed the character
    count.

    Args:
        content: The text content to save.
        filepath: The destination file path.

    Raises:
        OSError: If the file cannot be written.
        ValueError: If content is None.
    """
    if content is None:
        raise ValueError("content must not be None")

    # Encode to UTF-8 bytes — this is the actual data size that matters
    # for buffer allocation, not len(content) which counts characters.
    data = content.encode("utf-8")

    # Write atomically via a temporary file to avoid partial writes on
    # crash.  The temp file is created in the same directory so the
    # final rename is an atomic filesystem operation.
    dir_path = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(dir_path, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dir_path)
    fd_closed = False
    try:
        offset = 0
        while offset < len(data):
            chunk = data[offset : offset + BUFFER_SIZE]
            os.write(fd, chunk)
            offset += len(chunk)
        os.close(fd)
        fd_closed = True
        os.replace(tmp_path, filepath)
    except BaseException:
        if not fd_closed:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_file(filepath: str) -> str:
    """Load a UTF-8 encoded file and return its content as a string.

    Args:
        filepath: The file path to read.

    Returns:
        The file content as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        OSError: If the file cannot be read.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()
