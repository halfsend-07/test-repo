"""File save module with proper UTF-8 buffer handling.

Fixed in v2.3.2: The save_file function now allocates buffers based on
the actual byte length of UTF-8 encoded content rather than character
count, preventing buffer overflows when multibyte characters cause the
encoded size to exceed 64KB.
"""

import os
import tempfile

# Prior to the fix, BUFFER_SIZE was used as a character-count limit,
# which under-allocated when multibyte UTF-8 characters were present.
BUFFER_SIZE = 65536  # 64KB


def save_file(path, content):
    """Save content to a file with proper UTF-8 encoding.

    Uses atomic write (write to temp file, then rename) to prevent
    data loss on crash. Allocates the write buffer based on the byte
    length of the encoded content, not the character count.

    Args:
        path: Destination file path.
        content: String content to save.

    Raises:
        OSError: If the file cannot be written.
        TypeError: If content is not a string.
    """
    if not isinstance(content, str):
        raise TypeError(f"content must be str, got {type(content).__name__}")

    # Encode to UTF-8 to get the actual byte representation.
    # This is the fix: previously, the code used len(content) (character
    # count) to size the buffer. For multibyte characters, the byte
    # length can be up to 4x the character count, causing overflow when
    # the encoded output exceeded BUFFER_SIZE.
    encoded = content.encode("utf-8")

    dir_name = os.path.dirname(os.path.abspath(path))
    os.makedirs(dir_name, exist_ok=True)

    # Atomic write: write to a temp file in the same directory, then
    # rename. This prevents partial writes if the process is interrupted.
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".save_")
    try:
        offset = 0
        while offset < len(encoded):
            chunk = encoded[offset : offset + BUFFER_SIZE]
            os.write(fd, chunk)
            offset += len(chunk)
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.replace(tmp_path, path)
    except BaseException:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
