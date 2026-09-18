# TRACEAI Canonical Demonstration Fixtures

This directory contains the three canonical demo fixtures required for evaluating and demonstrating the TRACEAI Gateway:

1. clean_asset.txt - Wholesome / original public text (Expected: LOW risk, PASSED)
2. infringing_asset.txt - Paraphrased excerpt of an existing reference work (Expected: HIGH risk, BLOCKED)
3. spoofed_asset.txt - Real binary PNG image saved with a misleading .txt extension (Expected: Magic-byte sniffing detects image/png)

## Legal Disclaimer & Technical Signal Notice
All risk bands (LOW, MEDIUM, HIGH, CLEAR, BLOCKED) and review statuses are **technical demonstration indicators** produced by the software algorithms. They are designed to trigger human review or automated compliance pipelines, and **do NOT constitute legal conclusions or judicial determinations of copyright infringement**.

## Fixture Details

| Fixture ID | Filename | Format | Size | Magic Bytes / Signature | Reference / Source | Expected TRACEAI Outcome |
|---|---|---|---|---|---|---|
| CANON-001 | clean_asset.txt | 	ext/plain | 657 B | UTF-8 plain text | Original synthetic educational text | **PASSED** (Risk: CLEAR / LOW, Certificate Issued) |
| CANON-002 | infringing_asset.txt | 	ext/plain | 319 B | UTF-8 plain text | Paraphrase of work_txt_001 (Moby Dick by Herman Melville) from mock_data/copyright_index/ | **BLOCKED** (Risk: BLOCKED / HIGH, Score: >= 0.85, Matched to Melville) |
| CANON-003 | spoofed_asset.txt | image/png | 778 B | 89 50 4E 47 0D 0A 1A 0A (PNG) | Synthetic Pillow graphic | **IMAGE Track** (image/png sniffed despite .txt suffix) |

## Provenance & License Transparency
- clean_asset.txt: Synthetic text created for TRACEAI; unencumbered (CC0-1.0 equivalent).
- infringing_asset.txt: Synthetic paraphrase created to test cross-encoder semantic re-ranking against mock_data/copyright_index/texts/copyright_work_001.txt. In the simulated repository index, this work is cataloged as (c) Moby Dick by Herman Melville (Protected Literary Archive).
- spoofed_asset.txt: Synthetic binary PNG generated via Pillow; unencumbered (CC0-1.0 equivalent).
