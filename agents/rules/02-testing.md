# Rule 02: Testing Standards and Quality Gates

## Test-First Methodology
- Write tests alongside or before pipeline changes.
- Every task card requires corresponding automated tests in `tests/`.

## Test Pyramid & Speed
- **Unit Tests**:
  - Mock heavyweight ML models (`AutoModel`, `CLIPModel`, `CrossEncoder`) using fast deterministic vectors so unit tests execute in seconds.
  - Assert chunking geometry, early-exit conditions, schema validation, and crypto math.
- **Integration Tests**:
  - Test end-to-end flow with the dirty dataset fixture.
  - Require 100% catch rate on evasive/dirty assets (30% synonym-replaced text, 85-95% cropped images).
  - Verify clean holdout false-positive rate remains strictly under 2%.

## Coverage Gates
- Minimum **85% overall branch/line coverage** required for merge.
- Minimum **95% coverage on `core/crypto.py`**; signing and verification logic must be exhaustively covered.
- Verification command:
  ```bash
  pytest -q --cov=src/traceai --cov-fail-under=85
  ```
