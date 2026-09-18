# Rule 03: Threshold Governance and Configuration

## Configured, Never Hardcoded
- The default operational thresholds are:
  - **Text Cross-Encoder Block Threshold**: `0.85`
  - **Image CLIP Cosine Similarity Block Threshold**: `0.90`
- These values must be loaded exclusively through `traceai.config.GatewayConfig` via environment variables:
  - `TRACEAI_TEXT_BLOCK_THRESHOLD`
  - `TRACEAI_IMAGE_BLOCK_THRESHOLD`
- Raw float literals `0.85` and `0.90` are forbidden in production pipeline code outside config and unit test assertions.

## Calibration and Audit Trail
- Changing any threshold requires running the calibration harness (`scripts/calibrate_thresholds.py`).
- Threshold revisions must generate a calibration report showing the ROC curve knee and certifying FPR < 2%.
- All adjustments are recorded in the PostgreSQL `thresholds_history` table and documented in Memory under `decisions/thresholds`.
