"""File writer module with correct UTF-8 buffer handling.

Fixes the v2.3.1 regression where the save routine used character count
instead of byte length for buffer allocation, causing a buffer overflow
(segfault) when saving files larger than 64KB containing multibyte
UTF-8 characters.
"""

import os

# Buffer size in bytes. Buffer arithmetic must use byte length,
# not character count, to avoid overflow with multibyte sequences.
BUFFER_SIZE = 65536  # 64 KB


def save_file(content: str, path: str) -> None:
    """Save content to a file using chunked writes with correct byte handling.

    Encodes the full content to UTF-8 bytes first, then writes in
    BUFFER_SIZE-byte chunks. This avoids the v2.3.1 regression where
    character-count chunking could overflow the buffer when multibyte
    UTF-8 characters caused the encoded size to exceed the character
    count.

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
            chunk = encoded[offset:offset + BUFFER_SIZE]
            f.write(chunk)
            offset += len(chunk)
