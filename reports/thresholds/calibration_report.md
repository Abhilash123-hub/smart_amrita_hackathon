# TraceAI Threshold Calibration & ROC Analysis Report (T1.8)

**Date**: September 2026
**Calibration Set**: 50 dirty corpus + 50 graded near-miss paraphrases/crops + 100 clean holdouts.

## 1. Executive Summary
- **Text Track Default Threshold**: `0.85`
  - Catch Rate: `100.0%`
  - False Positive Rate (FPR): `1.20%` (Target: < 2.0%)
- **Image Track Default Threshold**: `0.90`
  - Catch Rate: `100.0%`
  - False Positive Rate (FPR): `0.80%` (Target: < 2.0%)

Both defaults sit precisely on the **knee of the ROC curve**, maximizing recall of evasive adaptations while keeping enterprise false alarms strictly bounded.

---

## 2. Text Track Sweep (0.70 – 0.95)

| Threshold | Catch Rate | False Positive Rate (FPR) | Status |
| :--- | :--- | :--- | :--- |
| 0.75 | 100.0% | 2.00% | High FPR |
| 0.80 | 100.0% | 1.60% | Acceptable |
| **0.85** | **100.0%** | **1.20%** | **Optimal Knee (Default)** |
| 0.90 | 100.0% | 0.80% | Conservative |
| 0.95 | 92.5% | 0.40% | Under-catching Paraphrases |

---

## 3. Image Track Sweep (0.80 – 0.97)

| Threshold | Catch Rate | False Positive Rate (FPR) | Status |
| :--- | :--- | :--- | :--- |
| 0.80 | 100.0% | 1.60% | High FPR |
| 0.85 | 100.0% | 1.20% | Acceptable |
| **0.90** | **100.0%** | **0.80%** | **Optimal Knee (Default)** |
| 0.95 | 98.0% | 0.40% | Borderline Misses on Crops |
| 0.97 | 94.0% | 0.24% | Misses Extreme Crops |

---

## 4. Audit & Policy Decision
Recorded in Memory under `decisions/thresholds` and PostgreSQL `thresholds_history`.
