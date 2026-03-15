"""ULID-like ID generation helpers."""

from __future__ import annotations

import os
import time

_ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_base32(value: int, length: int) -> str:
    chars = []
    for _ in range(length):
        chars.append(_ENCODING[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def new_ulid() -> str:
    """Generate a lexically sortable ULID-like identifier."""
    timestamp_ms = int(time.time() * 1000)
    randomness = int.from_bytes(os.urandom(10), "big")
    return f"{_encode_base32(timestamp_ms, 10)}{_encode_base32(randomness, 16)}"


def new_id(prefix: str) -> str:
    """Generate a prefixed immutable identifier."""
    return f"{prefix}_{new_ulid()}"
