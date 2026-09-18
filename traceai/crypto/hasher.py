from __future__ import annotations

"""Cryptographic hashing utilities for byte verification."""

import hashlib
from pathlib import Path


def compute_sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 digest of raw bytes, returning prefixed string 'sha256:<hex>'."""
    digest = hashlib.sha256(data).hexdigest()
    return f"sha256:{digest}"


def compute_sha256_file(path: Path | str, chunk_size: int = 65536) -> str:
    """Stream file bytes and compute SHA-256 digest."""
    p = Path(path).resolve()
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"
