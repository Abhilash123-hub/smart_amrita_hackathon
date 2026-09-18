#!/usr/bin/env python3
"""
TRACEAI SHA-256 Hash Verification Script
-----------------------------------------
Computes SHA-256 for every sample file in the TRACEAI Synthetic Demo Dataset.

IMPORTANT:
  - SHA-256 is exact file identity / integrity verification.
  - SHA-256 is NOT pHash. pHash is perceptual image hashing for similarity.
  - pHash is implemented downstream by the AI image track.
  - This script only computes SHA-256 (byte-level identity).

Usage:
  python data/check_hashes.py

Output:
  Prints SHA-256 for each file.
  Optionally writes verified hashes to data/verified_hashes.json.

Exit code: 0 on success, 1 if any file is missing.
"""

import hashlib
import json
import sys
from pathlib import Path

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SOURCES_FILE = SCRIPT_DIR / "sample" / "sample_sources.json"
HASHES_OUTPUT = SCRIPT_DIR / "verified_hashes.json"


def sha256_of_file(path: Path) -> str:
    """Compute SHA-256 digest of a file. Returns prefixed hex string."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def main():
    print()
    print("SHA-256 HASH VERIFICATION")
    print("-" * 60)

    if not SOURCES_FILE.exists():
        print(f"[ERROR] sample_sources.json not found at {SOURCES_FILE}")
        return 1

    sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))

    results = []
    errors = []

    for rec in sources:
        rid = rec.get("record_id", "<UNKNOWN>")
        file_path_str = rec.get("file_path")

        if not file_path_str:
            print(f"  [{rid}] SKIP — file_path is null")
            errors.append(rid)
            continue

        abs_path = REPO_ROOT / file_path_str
        if not abs_path.exists():
            print(f"  [{rid}] ERROR — file not found: {abs_path}")
            errors.append(rid)
            continue

        digest = sha256_of_file(abs_path)
        size_bytes = abs_path.stat().st_size
        print(f"  [{rid}] {abs_path.name}")
        print(f"          SHA-256  : {digest}")
        print(f"          Size     : {size_bytes:,} bytes")
        print()

        results.append({
            "record_id": rid,
            "file_name": rec.get("file_name"),
            "file_path": file_path_str,
            "sha256": digest,
            "size_bytes": size_bytes,
            "verified_at": "2026-09-18",
            "note": (
                "SHA-256 computed by data/check_hashes.py. "
                "This is file identity/integrity — NOT a perceptual hash. "
                "pHash is computed downstream by the AI image track."
            )
        })

    # Write verified hashes to JSON
    HASHES_OUTPUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Verified hashes written to: {HASHES_OUTPUT.relative_to(REPO_ROOT)}")
    print()

    if errors:
        print(f"RESULT: FAIL ({len(errors)} file(s) missing or unreadable)")
        return 1
    else:
        print(f"RESULT: PASS ({len(results)} file(s) hashed successfully)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
