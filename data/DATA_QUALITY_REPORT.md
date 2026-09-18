# TRACEAI Data Quality Report

> **Dataset**: TRACEAI Synthetic Demo Dataset
> **Version**: 1.0
> **Report Generated**: 2026-09-18
> **Validation Script**: `python data/validate_data.py`
> **Hash Script**: `python data/check_hashes.py`

---

## Dataset Summary

| Field | Value |
|---|---|
| Dataset Name | TRACEAI Synthetic Demo Dataset |
| Dataset Version | 1.0 |
| Total Records | 6 |
| Text Records | 3 |
| Image Records | 3 |
| Metadata Records (in sample_sources.json) | 6 |
| Source Type | SYNTHETIC |
| Licence | Project-created demo data |
| Created Date | 2026-09-18 |

---

## Validation Results (`python data/validate_data.py`)

```
DATA VALIDATION
------------------------------------------------------------
Records found          : 6
Files found on disk    : 6
Duplicate IDs          : 0
Missing files          : 0
Missing required fields: 0
Type mismatches        : 0
Missing dataset_version: 0
Missing license info   : 0
Missing source info    : 0
Invalid parent refs    : 0
Manifest count         : OK

RESULT: PASS
```

**Overall Validation Result: PASS**

---

## SHA-256 Hash Verification (`python data/check_hashes.py`)

```
SHA-256 HASH VERIFICATION
------------------------------------------------------------
  [DOC-001] sample_document_1.txt
          SHA-256  : sha256:8005447d518ac3463c514afbf98c56f04e405c4e3a1145c3cf1a9c44dbbc0ad6
          Size     : 2,000 bytes

  [DOC-002] sample_document_2.txt
          SHA-256  : sha256:5aa7eba5f187832dfabdc996110918e9c9a1ef7bb946c97a403d86ea77aa80cf
          Size     : 2,198 bytes

  [DOC-003] sample_document_3.txt
          SHA-256  : sha256:10e1616a22d9abeec6945d675c1410457cea5b5156944436a3f6978e3a907310
          Size     : 2,424 bytes

  [IMG-001] sample_image_1.png
          SHA-256  : sha256:2729680b9427a00e6af56843331e909e0e7dbf21b300f527aeb406626aac0f79
          Size     : 399,229 bytes

  [IMG-002] sample_image_2.png
          SHA-256  : sha256:c5e7a44fac747b9cd00959da41dec0d6af8db784478ac55e4ffc621c1da5c342
          Size     : 1,144,533 bytes

  [IMG-003] sample_image_3.png
          SHA-256  : sha256:03b7c28701a9d705d3877558b33152118b535f5f9bf76ea1e0079ee0eb6afbd6
          Size     : 1,019,338 bytes

Verified hashes written to: data/verified_hashes.json

RESULT: PASS (6 file(s) hashed successfully)
```

> **IMPORTANT**: SHA-256 is exact file identity/integrity verification.
> SHA-256 is **NOT** pHash. pHash (perceptual hashing) is for visual similarity and is implemented downstream by the AI image track.

**Hash Verification Result: PASS**

---

## Field-Level Quality Checks

| Check | Status | Count |
|---|---|---|
| Records with unique record_id | PASS | 6 / 6 |
| Records with file on disk | PASS | 6 / 6 |
| Records with no duplicate ID | PASS | 0 duplicates |
| Records with all required fields | PASS | 6 / 6 |
| Records with correct record_type vs file extension | PASS | 6 / 6 |
| Records with dataset_version | PASS | 6 / 6 |
| Records with license field | PASS | 6 / 6 |
| Records with source field | PASS | 6 / 6 |
| Records with valid parent_record references | PASS | 4 / 4 with parents |
| Manifest record count matches metadata | PASS | 6 = 6 |
| Manifest text count matches metadata | PASS | 3 = 3 |
| Manifest image count matches metadata | PASS | 3 = 3 |
| JSON files parseable (sample_sources.json) | PASS | OK |
| JSON files parseable (dataset_manifest.json) | PASS | OK |
| JSON files parseable (schema.json) | PASS | OK |

---

## Lineage Check

| Record | Parent | Lineage Valid |
|---|---|---|
| DOC-001 | null (root) | YES |
| DOC-002 | DOC-001 | YES — DOC-001 exists |
| DOC-003 | DOC-001 | YES — DOC-001 exists |
| IMG-001 | null (root) | YES |
| IMG-002 | IMG-001 | YES — IMG-001 exists |
| IMG-003 | IMG-001 | YES — IMG-001 exists |

All lineage references are internally consistent.

---

## Licence Metadata Completeness

| Record | Licence Field | licence_verified | Status |
|---|---|---|---|
| DOC-001 | Project-created demo data | true | COMPLETE |
| DOC-002 | Project-created demo data | true | COMPLETE |
| DOC-003 | Project-created demo data | true | COMPLETE |
| IMG-001 | Project-created demo data | true | COMPLETE |
| IMG-002 | Project-created demo data | true | COMPLETE |
| IMG-003 | Project-created demo data | true | COMPLETE |

All records have complete licence metadata.
`license_verified = true` is correct for synthetic project-created records.
No external licences are claimed.

---

## Source Metadata Completeness

| Record | Source | source_type | source_url | Status |
|---|---|---|---|---|
| DOC-001 | TRACEAI Synthetic Demo Dataset | synthetic | null | COMPLETE |
| DOC-002 | TRACEAI Synthetic Demo Dataset | synthetic | null | COMPLETE |
| DOC-003 | TRACEAI Synthetic Demo Dataset | synthetic | null | COMPLETE |
| IMG-001 | TRACEAI Synthetic Demo Dataset | synthetic | null | COMPLETE |
| IMG-002 | TRACEAI Synthetic Demo Dataset | synthetic | null | COMPLETE |
| IMG-003 | TRACEAI Synthetic Demo Dataset | synthetic | null | COMPLETE |

All records have complete source metadata.

---

## Missing / Incomplete Data

| Check | Count | Detail |
|---|---|---|
| Missing files | 0 | None |
| Duplicate IDs | 0 | None |
| Missing required fields | 0 | None |
| Invalid lineage references | 0 | None |
| Records with source_url | 0 | All null (correct for synthetic) |
| pHash values | N/A | Downstream field — not in data layer |
| embedding_id values | N/A | Downstream field — not in data layer |

---

## Known Limitations

1. **Small dataset**: 6 records total. Not representative of enterprise-scale AI datasets.
2. **Synthetic data only**: All records are project-created. No external data sources.
3. **Demonstration only**: Intended for hackathon demo, not production deployment.
4. **No pHash values**: pHash is a downstream field generated by the AI image track, not the data layer.
5. **No embedding_id values**: FAISS embedding IDs are generated by the AI text track at indexing time.
6. **No sha256 in metadata**: SHA-256 is computed at ingestion time by `AssetInput.from_file()`. The `verified_hashes.json` file provides pre-computed hashes for reference, but the gateway recomputes them live.
7. **Similarity categories are indicative**: LOW/MEDIUM/HIGH in `similarity_demo_category` are demo review categories, not legal determinations.
8. **External source verification not performed**: `license_verified = true` applies only because these are synthetic project-created records, not because any external licence has been checked.
9. **No real-world copyright index overlap**: The sample documents were written to have controlled textual overlap for demonstration. They are not based on the copyright index in `mock_data/copyright_index/`.

---

## Compatibility Note (Backend Integration)

The TRACEAI ingestion gateway (`traceai/gateway.py`) expects:
- **Input**: A directory path or single file path passed to `discover_assets()`
- **Format**: The gateway reads raw file bytes and computes SHA-256 and MIME type automatically
- **No pre-computed metadata required**: The gateway does not read `sample_sources.json` at ingestion time

**To use the data layer sample files with the gateway:**

```bash
# Scan text documents
python main.py scan --input-dir ./data/sample/documents --index-dir ./mock_data/copyright_index

# Scan images
python main.py scan --input-dir ./data/sample/images --index-dir ./mock_data/copyright_index

# Scan all sample data
python main.py scan --input-dir ./data/sample --index-dir ./mock_data/copyright_index
```

The `sample_sources.json` metadata is for:
- Data layer documentation and lineage tracking
- Test case documentation (expected demo categories)
- Audit and evidence trail purposes
- Future integration with a metadata database

---

*Report generated by: TRACEAI Data Engineer*
*Validation performed: 2026-09-18*
*All values in this report are obtained from actual script output, not manually invented.*
