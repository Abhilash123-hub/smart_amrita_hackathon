# TRACEAI Dataset

## Dataset Name

**TRACEAI Synthetic Demo Dataset** | Version 1.0 | Created 2026-09-18

---

## Purpose

This dataset exists to provide a small, controlled, reproducible demo dataset for the TRACEAI hackathon project.

TRACEAI traces where an AI training record came from and preserves evidence about its SOURCE, LICENCE, TRANSFORMATION, DATASET, TRAINING, and AUDIT trail.

This dataset provides:

1. Sample text and image records for ingestion
2. Provenance metadata for every record
3. Controlled similarity levels (LOW / MEDIUM / HIGH) for demonstrating the provenance review workflow
4. A schema and data dictionary for downstream team members to consume
5. Validation scripts to confirm data integrity

---

## Source

All records in this dataset are **SYNTHETIC / PROJECT-CREATED**.

- No records are sourced from external datasets.
- No records are scraped from the web.
- No copyrighted content is included.
- All image records are AI-generated for demo purposes.
- All text records are hand-authored for demo purposes.

---

## Licence

All records in this dataset are **project-created demo data**.

- `license`: Project-created demo data
- `license_verified`: `true` (project-created — no external licence to verify)
- `source_url`: `null` (no external source)

> **IMPORTANT**: This licence status applies ONLY to the demo data files in `data/sample/`. The copyright index in `mock_data/copyright_index/` is governed by its own metadata. Do not confuse the two datasets.

---

## Number of Records

| Type  | Count |
|-------|-------|
| Text  | 3     |
| Image | 3     |
| Total | 6     |

---

## Format

- **TXT** — Plain text documents (UTF-8)
- **PNG** — Synthetic images
- **JSON** — Provenance metadata and schema files

---

## Fields

Every record in `sample_sources.json` contains the following fields:

| Field | Required | Owner |
|---|---|---|
| `record_id` | YES | DATA LAYER |
| `file_name` | YES | DATA LAYER |
| `file_path` | YES | DATA LAYER |
| `record_type` | YES | DATA LAYER |
| `source` | YES | DATA LAYER |
| `source_type` | YES | DATA LAYER |
| `source_url` | NO | DATA LAYER |
| `license` | YES | DATA LAYER |
| `license_verified` | YES | DATA LAYER |
| `dataset` | YES | DATA LAYER |
| `dataset_version` | YES | DATA LAYER |
| `transformation` | YES | DATA LAYER |
| `parent_record` | NO | DATA LAYER |
| `created_at` | YES | DATA LAYER |
| `similarity_demo_category` | NO | DATA LAYER |
| `similarity_demo_note` | NO | DATA LAYER |
| `notes` | NO | DATA LAYER |
| `sha256` | — | DOWNSTREAM (gateway) |
| `phash` | — | DOWNSTREAM (AI) |
| `embedding_id` | — | DOWNSTREAM (AI/FAISS) |

See `data/data_dictionary.md` for full field documentation.  
See `data/schema.json` for the machine-readable schema.

---

## Dataset Structure

```
data/
|
+-- sample/
|   +-- documents/
|   |   +-- sample_document_1.txt   (DOC-001, LOW)
|   |   +-- sample_document_2.txt   (DOC-002, MEDIUM)
|   |   +-- sample_document_3.txt   (DOC-003, HIGH)
|   |
|   +-- images/
|   |   +-- sample_image_1.png      (IMG-001, LOW)
|   |   +-- sample_image_2.png      (IMG-002, MEDIUM)
|   |   +-- sample_image_3.png      (IMG-003, HIGH)
|   |
|   +-- sample_sources.json         (provenance metadata for all 6 records)
|
+-- dataset_manifest.json           (dataset-level descriptor)
+-- schema.json                     (field schema definition)
+-- data_dictionary.md              (field documentation)
+-- README.md                       (this file)
+-- validate_data.py                (data quality validation script)
+-- check_hashes.py                 (SHA-256 hash verification script)
+-- DATA_QUALITY_REPORT.md          (validation results report)
```

---

## How TRACEAI Uses the Data

### 1. Ingestion

The TRACEAI ingestion gateway (`traceai/gateway.py`) discovers assets by scanning a directory. It uses `AssetInput.from_file()` to:
- Read file bytes
- Detect MIME type and track (TEXT/IMAGE) via byte inspection
- Compute SHA-256 hash

The files in `data/sample/documents/` and `data/sample/images/` are the input assets. Point the gateway at `data/sample/` or specific subdirectories.

CLI usage:
```bash
python main.py scan --input-dir ./data/sample --index-dir ./mock_data/copyright_index
```

### 2. Fingerprinting

At ingestion, `AssetInput.from_file()` computes the SHA-256 hash.  
For images, the AI image track computes a perceptual hash (pHash).  
These are DOWNSTREAM operations and are NOT pre-computed in the data layer.

### 3. Similarity Analysis

The text track uses bi-encoder recall + cross-encoder re-ranking against the copyright index in `mock_data/copyright_index/`.

The image track uses pHash Hamming distance + CLIP cosine similarity.

The sample data provides three controlled test cases (LOW/MEDIUM/HIGH) to exercise these pipelines.

### 4. Provenance Tracking

Every record in `sample_sources.json` carries:
- `source`: where the record came from
- `source_type`: classification (synthetic/licensed/etc.)
- `source_url`: external URL if applicable
- `transformation`: how the record was created or derived
- `parent_record`: lineage reference

The W3C PROV-O lineage graph is built downstream by `traceai/crypto/lineage.py`. The data layer provides the raw provenance fields that the lineage graph uses.

### 5. Licence Metadata Tracking

Every record carries `license` and `license_verified` fields. These fields allow the audit layer to check licence status before issuing a cryptographic clearance certificate.

### 6. Lineage

The `parent_record` field creates a basic lineage graph:

```
DOC-001 (root)
  |
  +-- DOC-002 (MEDIUM — same template, different domain)
  |
  +-- DOC-003 (HIGH — near-duplicate)

IMG-001 (root)
  |
  +-- IMG-002 (MEDIUM — same scene, added pond)
  |
  +-- IMG-003 (HIGH — near-duplicate)
```

### 7. Evidence / Report Generation

The scan report (`ScanReport`) produced by the gateway aggregates:
- Asset status (PASSED / BLOCKED / HUMAN_REVIEW)
- Matched source
- Cryptographic certificate (if PASSED)
- W3C PROV-O lineage graph

The `similarity_demo_category` and `similarity_demo_note` fields in `sample_sources.json` document the expected review outcome for each demo record.

---

## Similarity Demonstration

> **IMPORTANT**: LOW / MEDIUM / HIGH are DEMO REVIEW CATEGORIES, NOT legal conclusions.  
> They guide human review. They do not determine copyright infringement.

| Category | Demo Records | Description |
|---|---|---|
| **LOW** | DOC-001, IMG-001 | Reference / unrelated records. Low provenance review signal. |
| **MEDIUM** | DOC-002, IMG-002 | Partial overlap with reference. Medium provenance review signal. |
| **HIGH** | DOC-003, IMG-003 | Highly similar to reference. Requires provenance and licence review before AI training use. |

### Test Case Documentation

**TEST 1 — LOW** (DOC-001 / IMG-001)
- Expected review category: LOW
- Purpose: Demonstrates the PASSED / CLEAR outcome for unrelated content.
- Content: Oceanographic sensor report (unrelated to copyright index).

**TEST 2 — MEDIUM** (DOC-002 / IMG-002)
- Expected review category: MEDIUM / HUMAN_REVIEW
- Purpose: Demonstrates the HUMAN_REVIEW outcome for partially similar content.
- Content: Agricultural sensor report (same structure as DOC-001, different domain).

**TEST 3 — HIGH** (DOC-003 / IMG-003)
- Expected review category: HIGH — requires provenance/licence review
- Purpose: Demonstrates the BLOCKED / HUMAN_REVIEW outcome for highly similar content.
- Content: Near-duplicate of DOC-001 with minor wording changes.
- NOTE: The actual gateway outcome depends on similarity thresholds configured in `traceai/config.py`. The data layer records the INTENDED demo category only.

---

## Dataset Versioning

| Version | Description |
|---|---|
| **1.0** | Initial synthetic demo dataset (2026-09-18) |
| 1.x | Metadata corrections or additional fields — backward compatible |
| 2.0 | Major structural change to the dataset or new record modalities |

To release a new version: update `dataset_version` in `dataset_manifest.json`, update all records in `sample_sources.json`, and update this README.

---

## Limitations

- **Small dataset**: 6 records total (3 text, 3 image). Not representative of production scale.
- **Synthetic data**: All records are project-created. Not sourced from real-world datasets.
- **Demo only**: Intended for hackathon demonstration, not production deployment.
- **Not enterprise-scale**: Does not represent the variety or volume of real AI training datasets.
- **Does not establish legal ownership**: No legal claim about any external content.
- **No copyright compliance guarantee**: External source verification is required for any production use.
- **Similarity categories are indicative**: LOW/MEDIUM/HIGH are demo labels, not legal determinations.

---

## Validation

Run the data quality validation script:

```bash
python data/validate_data.py
```

Run SHA-256 hash verification:

```bash
python data/check_hashes.py
```

See `data/DATA_QUALITY_REPORT.md` for the latest validation results.

---

*Maintained by: TRACEAI Data Engineer*  
*Dataset: TRACEAI Synthetic Demo Dataset v1.0*  
*Repository: https://github.com/Abhilash123-hub/smart_amrita_hackathon*
