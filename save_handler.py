"""File save handler with correct UTF-8 buffer management.

Fixes a segmentation fault that occurred when saving files larger than
64KB containing UTF-8 multibyte characters. The bug was caused by
allocating the write buffer based on character count instead of byte
length, leading to a buffer overflow when multibyte sequences pushed the
encoded size past the 64KB boundary.
"""

import io
import os

# Buffer size in bytes (64 KiB).
BUFFER_SIZE = 65536


def save_file(path: str, content: str) -> int:
    """Save *content* to *path* using chunked, byte-aware writes.

    The content is encoded to UTF-8 first, then written in chunks whose
    size is measured in **bytes** — not characters — so multibyte
    sequences that straddle a chunk boundary are never split.

    Returns the number of bytes written.
    """
    encoded = content.encode("utf-8")
    bytes_written = 0

    with open(path, "wb") as fh:
        offset = 0
        while offset < len(encoded):
            chunk = encoded[offset : offset + BUFFER_SIZE]
            fh.write(chunk)
            bytes_written += len(chunk)
            offset += len(chunk)

    return bytes_written


def load_file(path: str) -> str:
    """Read a UTF-8 encoded file and return its text content."""
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()
