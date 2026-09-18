# TRACEAI QA Test Plan & Verification Specification

> **Module**: Member 4 — Data + Integration + QA  
> **Dataset**: TRACEAI Synthetic Demo Dataset v1.0 (6 sample records)  
> **Version**: 1.0  
> **Target System**: TRACEAI Multimodal Gateway & Provenance Engine  
> **Date**: 2026-09-18  

---

## 1. Scope & Objective

This test plan defines the formal QA specification to verify the complete integration pipeline:
$$\text{Frontend} \longrightarrow \text{Backend} \longrightarrow \text{AI} \longrightarrow \text{Data Layer} \longrightarrow \text{Response} \longrightarrow \text{Frontend}$$

The evaluation focuses on verifying that:
1. All 6 sample records (`DOC-001` through `IMG-003`) from the preserved data layer load without failure.
2. SHA-256 exact byte identity is computed dynamically from real disk files.
3. Perceptual hashing (`pHash`) is computed dynamically for visual records.
4. Derivation similarity across records is computed mathematically rather than hard-coded.
5. Provenance metadata and W3C PROV-O lineage graphs are retrieved accurately from `data/sample/sample_sources.json`.
6. Transparent Review Indicators (`LOW`, `MEDIUM`, `HIGH`) are calculated without legal conclusions.
7. Evidence audit records can be exported in structured JSON and styled HTML.
8. The system operates fully offline without external API dependencies.

---

## 2. Test Cases Specification & Execution Results

| Test ID | Input / Target | Purpose | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| **TEST-001** | `DOC-001` | Root reference text asset (ocean sensor report) | Review Indicator: `LOW`<br>Composite score $< 0.40$<br>SHA-256: `sha256:8005447d...` | Review Indicator: `LOW`<br>Composite score: `0.0000`<br>SHA-256 verified | **PASS** |
| **TEST-002** | `DOC-002` | Derived text asset (agricultural sensor report with shared template) | Review Indicator: `MEDIUM`<br>Score $0.40 \le S < 0.75$<br>Parent: `DOC-001` | Review Indicator: `MEDIUM`<br>Composite score: `0.6900`<br>Parent linked to `DOC-001` | **PASS** |
| **TEST-003** | `DOC-003` | Near-duplicate text asset (ocean thermal report with minor paraphrasing) | Review Indicator: `HIGH`<br>Score $\ge 0.75$<br>Neutral warning status | Review Indicator: `HIGH`<br>Composite score: `0.8131`<br>Neutral provenance risk warning | **PASS** |
| **TEST-004** | `NONEXISTENT-999` | Query for nonexistent record ID | HTTP 404 with structured error detail | HTTP 404 `{"detail": "Record 'NONEXISTENT-999' not found in dataset."}` | **PASS** |
| **TEST-005** | Missing file path | File existence failure during hashing | `FileNotFoundError` handled gracefully without crash | Clean exception handled; HTTP 500/404 detail returned | **PASS** |
| **TEST-006** | `data/schema.json` | JSON Schema validation of metadata records | All 6 records adhere to schema definition | Schema validation passed (0 type mismatches, 0 missing fields) | **PASS** |
| **TEST-007** | `license_verified=False` | Risk penalty for unverified licence | Transparent penalty (+0.35) elevates risk category | Verified clean: `LOW` (0.20) &rarr; Unverified: `MEDIUM` (0.55) | **PASS** |
| **TEST-008** | `source_type="scraped"` | Risk penalty for untracked/scraped source | Transparent penalty (+0.20) elevates risk category | Synthetic: `LOW` (0.30) &rarr; Scraped: `MEDIUM` (0.50) | **PASS** |
| **TEST-009** | `IMG-001`, `IMG-002`, `IMG-003` | Visual record processing via pHash + SHA-256 | SHA-256 and 16-hex pHash generated; levels: LOW, MEDIUM, HIGH | IMG-001 (`LOW`, 0.0), IMG-002 (`MEDIUM`, 0.7226), IMG-003 (`HIGH`, 0.7625) | **PASS** |
| **TEST-010** | `DOC-001`, `DOC-002`, `DOC-003` | Text record lexical & semantic matching | Correct record modality and similarity ranking | Text track correctly processes UTF-8 bytes and calculates Jaccard/overlap | **PASS** |
| **TEST-011** | `GET /records/{id}/evidence` | Audit evidence package export in JSON and HTML | Valid JSON payload and standalone styled HTML report | JSON: RFC-8259 compliant<br>HTML: Full certificate with CSS | **PASS** |
| **TEST-012** | `GET /` | Static frontend delivery and UI interactive rendering | HTTP 200 with complete dashboard and demo tracer | Served with HTTP 200, 6 demo buttons rendered | **PASS** |
| **TEST-013** | `data/sample/` | Offline execution without external cloud/internet | All 6 records traceable with local Python runtime | Executed 100% locally on CPU without external API calls | **PASS** |

---

## 3. Review Indicator Scoring Logic

The review indicator produces **demonstration review categories only**, not legal conclusions.

### Formula
$$\text{CompositeRisk} = S_{\text{max}} + P_{\text{licence}} + P_{\text{source}}$$

Where:
- $S_{\text{max}} \in [0.0, 1.0]$: Maximum similarity to parent record or reference corpus.
- $P_{\text{licence}} \in \{0.0, 0.35\}$: Licence penalty ($0.0$ if verified, $0.35$ if unverified).
- $P_{\text{source}} \in \{0.0, 0.20\}$: Source risk penalty ($0.20$ if source is scraped/unknown, $0.0$ for synthetic/licensed).

### Category Thresholds
- $\text{CompositeRisk} < 0.40 \implies \mathbf{LOW}$  
  *Status*: `"Low provenance risk — reference / clean record. Cleared for standard review."`
- $0.40 \le \text{CompositeRisk} < 0.75 \implies \mathbf{MEDIUM}$  
  *Status*: `"Moderate provenance risk — partial similarity detected. Human review recommended."`
- $\text{CompositeRisk} \ge 0.75 \implies \mathbf{HIGH}$  
  *Status*: `"Potential provenance risk — high similarity or unverified lineage. Provenance & licence review required before AI training use."`

---

## 4. Test Execution Command
```bash
python -m pytest tests/test_data_integration.py -v
```
All 17 test methods passed with 100% success rate.


---

## 3. Canonical Demo Fixtures Specification (Member 4 Requirement)

| Fixture ID | Filename | Modality | Reference / Source | Purpose | Expected Outcome | Actual Result | Status |
|---|---|---|---|---|---|---|---|
| **CANON-001** | `clean_asset.txt` | `text/plain` | Original synthetic educational text | Clean baseline text | `PASSED` / `CLEAR` (LOW)<br>Certificate issued | `PASSED` / `CLEAR`<br>Cert: issued | **PASS** |
| **CANON-002** | `infringing_asset.txt` | `text/plain` | Paraphrase of `work_txt_001` (`Moby Dick by Herman Melville`) from `mock_data/copyright_index/` | Cross-encoder semantic match | `BLOCKED` / `BLOCKED` (HIGH)<br>Score >= 0.85<br>Matched to Melville | `BLOCKED`<br>Score: 1.0<br>Source: Melville | **PASS** |
| **CANON-003** | `spoofed_asset.txt` | `image/png` (disguised as `.txt`) | Synthetic Pillow graphic | Raw binary magic-byte sniffing | `IMAGE` Track<br>`image/png` sniffed<br>Extension overridden | `IMAGE` Track<br>`image/png`<br>Sniffed: True | **PASS** |
