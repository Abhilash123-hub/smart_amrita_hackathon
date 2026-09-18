# TRACEAI Demo Test Matrix

> **Dataset**: TRACEAI Synthetic Demo Dataset v1.0 (6 Records)  
> **Evaluation Date**: 2026-09-18  
> **Tested Environment**: Python 3.13 / FastAPI / Standalone Offline Localhost  

---

## 1. Demo Test Execution Matrix

| Test ID | Input Condition | Record ID | Modality | Expected Category | Actual Calculated Category | Composite Risk Score | Status |
|---|---|---|---|---|---|---|---|
| **TEST-001** | Clearly Unrelated (Root Reference Document) | `DOC-001` | Text | `LOW` | **`LOW`** | `0.0000` | **PASS** |
| **TEST-002** | Partially Similar Document (Shared Template, Domain Shift) | `DOC-002` | Text | `MEDIUM` | **`MEDIUM`** | `0.6900` | **PASS** |
| **TEST-003** | Highly Similar Document (Near-Duplicate with Paraphrasing) | `DOC-003` | Text | `HIGH` | **`HIGH`** | `0.8131` | **PASS** |
| **TEST-001 (Img)** | Unrelated Visual Reference (Agricultural Aerial Base) | `IMG-001` | Image | `LOW` | **`LOW`** | `0.0000` | **PASS** |
| **TEST-002 (Img)** | Partially Similar Visual Record (Added Pond Feature) | `IMG-002` | Image | `MEDIUM` | **`MEDIUM`** | `0.7226` | **PASS** |
| **TEST-003 (Img)** | Highly Similar Visual Record (Near-Duplicate Scene) | `IMG-003` | Image | `HIGH` | **`HIGH`** | `0.7625` | **PASS** |

---

## 2. Detailed Evidence Breakdown per Scenario

### Scenario 1: Unrelated / Root Reference Record (`DOC-001` & `IMG-001`)
- **Record ID**: `DOC-001`
- **File**: `sample_document_1.txt` (2,000 bytes)
- **Identity Signal**: `sha256:8005447d518ac3463c514afbf98c56f04e405c4e3a1145c3cf1a9c44dbbc0ad6`
- **Similarity Evidence**: Max similarity = `0.0000` (Independent root record, no parent derivation)
- **Provenance Evidence**:
  - Source: `TRACEAI Synthetic Demo Dataset` (`synthetic`)
  - Dataset: `TRACEAI Synthetic Demo Dataset` (`v1.0`)
  - Transformation: `Synthetic text generation`
  - Parent Record: `null` (Root record)
- **Licence Status**: `Project-created demo data` (Verified: `true`)
- **Review Result**: **`LOW`** (`CompositeRisk = 0.0000 < 0.40`)
  - *Assessment*: `"Low provenance risk — reference / clean record. Cleared for standard review."*

---

### Scenario 2: Partially Similar Record (`DOC-002` & `IMG-002`)
- **Record ID**: `DOC-002`
- **File**: `sample_document_2.txt` (2,198 bytes)
- **Identity Signal**: `sha256:5aa7eba5f187832dfabdc996110918e9c9a1ef7bb946c97a403d86ea77aa80cf`
- **Similarity Evidence**: Max similarity to parent `DOC-001` = `0.6900`
- **Provenance Evidence**:
  - Source: `TRACEAI Synthetic Demo Dataset` (`synthetic`)
  - Dataset: `TRACEAI Synthetic Demo Dataset` (`v1.0`)
  - Transformation: `Synthetic text generation — derived from DOC-001 template with domain modification`
  - Parent Record: `DOC-001`
- **Licence Status**: `Project-created demo data` (Verified: `true`)
- **Review Result**: **`MEDIUM`** (`0.40 <= CompositeRisk = 0.6900 < 0.75`)
  - *Assessment*: `"Moderate provenance risk — partial similarity detected. Human review recommended."*

---

### Scenario 3: Highly Similar / Near-Duplicate Record (`DOC-003` & `IMG-003`)
- **Record ID**: `DOC-003`
- **File**: `sample_document_3.txt` (2,424 bytes)
- **Identity Signal**: `sha256:10e1616a22d9abeec6945d675c1410457cea5b5156944436a3f6978e3a907310`
- **Similarity Evidence**: Max similarity to parent `DOC-001` = `0.8131`
- **Provenance Evidence**:
  - Source: `TRACEAI Synthetic Demo Dataset` (`synthetic`)
  - Dataset: `TRACEAI Synthetic Demo Dataset` (`v1.0`)
  - Transformation: `Synthetic text generation — near-duplicate of DOC-001 with minor wording changes`
  - Parent Record: `DOC-001`
- **Licence Status**: `Project-created demo data` (Verified: `true`)
- **Review Result**: **`HIGH`** (`CompositeRisk = 0.8131 >= 0.75`)
  - *Assessment*: `"Potential provenance risk — high similarity or unverified lineage. Provenance & licence review required before AI training use."*
  - *Legal Notice*: Neutral risk indicator for human review; NOT a legal conclusion of copyright infringement.

---

## 3. Visual Record Matrix (`IMG-001`, `IMG-002`, `IMG-003`)

| Record ID | pHash (Perceptual Hash) | SHA-256 Digest | Parent Record | Visual Similarity | Review Category |
|---|---|---|---|---|---|
| `IMG-001` | `905b1bc52d7ae46c` | `sha256:2729680b...` | `null` (Root) | `0.0000` | **`LOW`** |
| `IMG-002` | `a28a95b9f0c70e9e` | `sha256:c5e7a44f...` | `IMG-001` | `0.7226` | **`MEDIUM`** |
| `IMG-003` | `a66a5656b915cf90` | `sha256:03b7c287...` | `IMG-001` | `0.7625` | **`HIGH`** |


---

## 4. Canonical Demo Fixtures Matrix (Member 4 Requirement)

| Test ID | Fixture Filename | Modality | Byte Size | SHA-256 Digest | Reference Work | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|---|---|---|
| **CANON-001** | `clean_asset.txt` | `text/plain` | 657 B | `sha256:a51484a29ab4...` | Original synthetic text | **`LOW / PASSED`** | **`PASSED`** (Risk: CLEAR, Certificate issued) | **PASS** |
| **CANON-002** | `infringing_asset.txt` | `text/plain` | 319 B | `sha256:fc2c2168273b...` | Melville: *Moby Dick* (`work_txt_001`) | **`HIGH / BLOCKED`** | **`BLOCKED`** (Similarity: 1.0, Matched Melville) | **PASS** |
| **CANON-003** | `spoofed_asset.txt` | `image/png` (with `.txt`) | 778 B | `sha256:da903fc920ee...` | Pillow RGB graphic | **`IMAGE Track`** | **`IMAGE Track (image/png)`** sniffed via magic bytes | **PASS** |
