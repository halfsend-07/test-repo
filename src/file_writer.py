"""File writer module with correct UTF-8 buffer handling.

The save routine uses byte-length calculations for buffer management,
ensuring multibyte UTF-8 sequences that straddle the buffer boundary
are handled correctly without overflow.
"""

import os

# Buffer size in bytes — must be used for byte-length arithmetic,
# never for character-count arithmetic.
BUFFER_SIZE = 65536  # 64 KB


def save_file(content: str, path: str) -> None:
    """Save content to a file using chunked writes with correct byte handling.

    Encodes the full content to UTF-8 bytes first, then writes in
    BUFFER_SIZE-byte chunks. This avoids the v2.3.1 regression where
    character-count chunking could split a multibyte UTF-8 sequence
    across buffer boundaries.

    Args:
        content: The text content to save.
        path: The filesystem path to write to.
    """
    encoded = content.encode("utf-8")
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(path, "wb") as f:
        offset = 0
        while offset < len(encoded):
            chunk = encoded[offset : offset + BUFFER_SIZE]
            f.write(chunk)
            offset += len(chunk)
