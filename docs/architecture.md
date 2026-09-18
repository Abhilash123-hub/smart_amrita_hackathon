# TRACEAI System Architecture

> **Project**: TRACEAI  
> **Problem**: Intellectual Property Cleanliness & AI Training Provenance  
> **Core Objective**: Transforming raw data records into verifiable, traceable cryptographic evidence chains.

---

## 1. High-Level Architecture Overview

```
                        ┌─────────────────────────┐
                        │   Frontend Dashboard    │
                        │  (Tailwind + Lucide UI) │
                        └────────────┬────────────┘
                                     │ REST HTTP / JSON
                                     ▼
                        ┌─────────────────────────┐
                        │ FastAPI Ingestion Server│
                        │  (traceai/api/server.py)│
                        └────────────┬────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│ 1. Exact Identity│        │2. Multimodal AI  │        │  3. Provenance   │
│    (SHA-256)     │        │  (pHash & Sim)   │        │     Lineage      │
│  hasher.py       │        │  tracks/         │        │  data_service.py │
└────────┬─────────┘        └────────┬─────────┘        └────────┬─────────┘
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     ▼
                        ┌─────────────────────────┐
                        │ Transparent Review Engine│
                        │ (LOW / MEDIUM / HIGH)   │
                        └────────────┬────────────┘
                                     ▼
                        ┌─────────────────────────┐
                        │  Evidence Audit Package │
                        │  • Structured JSON      │
                        │  • Styled HTML Cert     │
                        └─────────────────────────┘
```

---

## 2. The Three Evidence Signals

### Signal 1: Exact Identity (SHA-256)
- Computed from raw byte stream of each asset (`compute_sha256_file`).
- Provides tamper-evident verification that the ingested file matches the registered dataset asset.
- Format: `sha256:<64-hex-digest>`.

### Signal 2: Perceptual / Semantic Similarity
- **Images**: 64-bit perceptual hash (`pHash`) computed using DCT frequency domain analysis. Detects crops, scale changes, and visual near-duplicates.
- **Text**: Token-level lexical set overlap, Jaccard coefficient, and SequenceMatcher ratios. Flags near-duplicates and structural paraphrasing.

### Signal 3: Provenance & Lineage DAG
- Preserves the chain: `Source -> License -> Transformation -> Dataset -> Training -> Audit`.
- Formatted according to W3C PROV-O JSON-LD standards.
- Tracks parent-child relationships between derived datasets and source templates.

---

## 3. Data Layer Isolation

The completed data layer (`data/`) serves as the immutable provenance source of truth:
- `data/sample/sample_sources.json`: Provenance metadata catalog.
- `data/dataset_manifest.json`: Dataset-level versioning and modalities descriptor.
- `data/schema.json`: JSON Schema enforcing field boundaries between data layer and runtime AI fields.
- `data/validate_data.py`: Standalone dataset integrity validator.
- `data/check_hashes.py`: Standalone SHA-256 verification tool.
