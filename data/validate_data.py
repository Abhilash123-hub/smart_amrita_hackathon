#!/usr/bin/env python3
"""
TRACEAI Data Layer Validation Script
-------------------------------------
Validates the TRACEAI Synthetic Demo Dataset for:
  1. Unique record IDs
  2. Duplicate IDs
  3. Required metadata fields presence
  4. All referenced files exist
  5. record_type matches actual file extension
  6. dataset_version present
  7. licence information present
  8. source information present
  9. parent_record references a valid record when present
  10. Manifest record count matches actual metadata records
  11. Text/image counts match actual dataset
  12. JSON files are valid

Returns exit code 0 on PASS, exit code 1 on FAIL.
"""

import json
import sys
from pathlib import Path

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SOURCES_FILE = SCRIPT_DIR / "sample" / "sample_sources.json"
MANIFEST_FILE = SCRIPT_DIR / "dataset_manifest.json"
SCHEMA_FILE = SCRIPT_DIR / "schema.json"

REQUIRED_FIELDS = [
    "record_id", "file_name", "file_path", "record_type",
    "source", "source_type", "license", "license_verified",
    "dataset", "dataset_version", "transformation", "created_at"
]

RECORD_TYPE_EXTENSIONS = {
    "text":  {".txt", ".md", ".csv", ".json", ".text"},
    "image": {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"},
    "audio": {".mp3", ".wav", ".flac", ".ogg"},
    "video": {".mp4", ".mkv", ".avi", ".webm", ".mov"},
    "code":  {".py", ".js", ".ts", ".go", ".rs", ".cpp", ".java"},
}


def load_json(path: Path, label: str):
    """Load and parse a JSON file. Returns (data, error_msg)."""
    if not path.exists():
        return None, f"{label} not found at {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data, None
    except json.JSONDecodeError as e:
        return None, f"{label} is not valid JSON: {e}"


def validate():
    errors = []
    warnings = []

    print()
    print("DATA VALIDATION")
    print("-" * 60)

    # ------------------------------------------------------------------
    # 1. Validate JSON files
    # ------------------------------------------------------------------
    sources, err = load_json(SOURCES_FILE, "sample_sources.json")
    if err:
        errors.append(err)
        sources = []

    manifest, err = load_json(MANIFEST_FILE, "dataset_manifest.json")
    if err:
        errors.append(err)
        manifest = {}

    schema, err = load_json(SCHEMA_FILE, "schema.json")
    if err:
        errors.append(err)

    # ------------------------------------------------------------------
    # 2. Record-level checks
    # ------------------------------------------------------------------
    record_ids = []
    duplicate_ids = []
    missing_files = []
    missing_fields = []
    type_mismatch = []
    missing_dataset_version = []
    missing_license = []
    missing_source = []
    invalid_parent_refs = []

    valid_record_id_set = set()

    for rec in sources:
        rid = rec.get("record_id", "<UNKNOWN>")
        record_ids.append(rid)

        # Check for duplicates
        if rid in valid_record_id_set:
            duplicate_ids.append(rid)
        valid_record_id_set.add(rid)

        # Required fields
        for field in REQUIRED_FIELDS:
            if field not in rec or rec[field] is None or rec[field] == "":
                missing_fields.append(f"{rid}.{field}")

        # File existence
        file_path_str = rec.get("file_path")
        if file_path_str:
            abs_path = REPO_ROOT / file_path_str
            if not abs_path.exists():
                missing_files.append(f"{rid}: {file_path_str}")
        else:
            missing_files.append(f"{rid}: file_path is null/missing")

        # record_type vs file extension
        rt = rec.get("record_type", "")
        fname = rec.get("file_name", "")
        ext = Path(fname).suffix.lower() if fname else ""
        if rt in RECORD_TYPE_EXTENSIONS:
            if ext not in RECORD_TYPE_EXTENSIONS[rt]:
                type_mismatch.append(
                    f"{rid}: record_type={rt!r} but file extension={ext!r}"
                )

        # dataset_version
        if not rec.get("dataset_version"):
            missing_dataset_version.append(rid)

        # license
        if not rec.get("license"):
            missing_license.append(rid)

        # source
        if not rec.get("source"):
            missing_source.append(rid)

    # Parent record references (second pass after building valid_record_id_set)
    for rec in sources:
        parent = rec.get("parent_record")
        if parent is not None:
            if parent not in valid_record_id_set:
                invalid_parent_refs.append(
                    f"{rec.get('record_id')}: parent_record={parent!r} does not exist"
                )

    # ------------------------------------------------------------------
    # 3. Manifest count validation
    # ------------------------------------------------------------------
    manifest_ok = True
    manifest_issues = []

    if manifest:
        m_total = manifest.get("record_count", -1)
        m_text = manifest.get("text_record_count", -1)
        m_img = manifest.get("image_record_count", -1)
        m_records = manifest.get("records", [])

        actual_total = len(sources)
        actual_text = sum(1 for r in sources if r.get("record_type") == "text")
        actual_img = sum(1 for r in sources if r.get("record_type") == "image")
        actual_ids = sorted([r.get("record_id") for r in sources])

        if m_total != actual_total:
            manifest_ok = False
            manifest_issues.append(
                f"record_count: manifest={m_total}, actual={actual_total}"
            )
        if m_text != actual_text:
            manifest_ok = False
            manifest_issues.append(
                f"text_record_count: manifest={m_text}, actual={actual_text}"
            )
        if m_img != actual_img:
            manifest_ok = False
            manifest_issues.append(
                f"image_record_count: manifest={m_img}, actual={actual_img}"
            )
        sorted_manifest_ids = sorted(m_records)
        if sorted_manifest_ids != actual_ids:
            manifest_ok = False
            manifest_issues.append(
                f"records list mismatch: manifest={sorted_manifest_ids}, actual={actual_ids}"
            )
    else:
        manifest_ok = False
        manifest_issues.append("manifest file could not be loaded")

    # ------------------------------------------------------------------
    # 4. Collect final error list
    # ------------------------------------------------------------------
    if duplicate_ids:
        for d in duplicate_ids:
            errors.append(f"Duplicate record_id: {d}")
    if missing_files:
        for m in missing_files:
            errors.append(f"Missing file: {m}")
    if missing_fields:
        for m in missing_fields:
            errors.append(f"Missing required field: {m}")
    if type_mismatch:
        for t in type_mismatch:
            errors.append(f"Type mismatch: {t}")
    if missing_dataset_version:
        for m in missing_dataset_version:
            errors.append(f"Missing dataset_version: {m}")
    if missing_license:
        for m in missing_license:
            errors.append(f"Missing license: {m}")
    if missing_source:
        for m in missing_source:
            errors.append(f"Missing source: {m}")
    if invalid_parent_refs:
        for i in invalid_parent_refs:
            errors.append(f"Invalid parent_record: {i}")
    if not manifest_ok:
        for i in manifest_issues:
            errors.append(f"Manifest count error: {i}")

    # ------------------------------------------------------------------
    # 5. Print results
    # ------------------------------------------------------------------
    print(f"Records found          : {len(sources)}")
    files_found = len(sources) - len(missing_files)
    print(f"Files found on disk    : {files_found}")
    print(f"Duplicate IDs          : {len(duplicate_ids)}")
    print(f"Missing files          : {len(missing_files)}")
    print(f"Missing required fields: {len(missing_fields)}")
    print(f"Type mismatches        : {len(type_mismatch)}")
    print(f"Missing dataset_version: {len(missing_dataset_version)}")
    print(f"Missing license info   : {len(missing_license)}")
    print(f"Missing source info    : {len(missing_source)}")
    print(f"Invalid parent refs    : {len(invalid_parent_refs)}")
    manifest_status = "OK" if manifest_ok else "FAIL -- " + "; ".join(manifest_issues)
    print(f"Manifest count         : {manifest_status}")

    if errors:
        print()
        print("ERRORS:")
        for e in errors:
            print(f"  [ERROR] {e}")
    if warnings:
        print()
        print("WARNINGS:")
        for w in warnings:
            print(f"  [WARN] {w}")

    print()
    if errors:
        print("RESULT: FAIL")
        print(f"  {len(errors)} error(s) found. See above.")
        return 1
    else:
        print("RESULT: PASS")
        return 0


if __name__ == "__main__":
    sys.exit(validate())
