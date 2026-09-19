# 🛡️ TraceAI — Multimodal Ingestion Gateway & Cryptographic Clearance

> **Inline ingestion gateway that intercepts multimodal data (text and images) before reaching ML training pipelines, fingerprints them against a copyrighted works index, and generates cryptographic clearance certificates with W3C PROV-O provenance.**

---

## 🌟 Key Architecture & Capabilities

```
[Raw Assets: Text & Images]
           │
           ▼
┌──────────────────────────────────────────────┐
│       TraceAI Ingestion Gateway              │
│  • Byte Magic Sniffing (Anti-Spoofing)       │
│  • SHA-256 Byte Hash Computation             │
│  • Concurrent Multimodal Dispatch            │
└──────────────┬───────────────────────────────┘
               │
       ┌───────┴────────────────────────┐
       ▼                                ▼
┌──────────────────────┐    ┌──────────────────────┐
│      Text Track      │    │     Image Track      │
│ 1. Bi-Encoder Recall │    │ 1. pHash Hamming (<5)│
│ 2. Cross-Encoder     │    │ 2. CLIP Cosine (>0.9)│
│    Re-Ranker (>0.85) │    │                      │
└──────────────┬───────┘    └───────────┬──────────┘
               │                        │
               └───────────┬────────────┘
                           ▼
┌──────────────────────────────────────────────┐
│         Resolution & Evidence Layer          │
│  • High Risk: Flag & BLOCKED                 │
│  • Clean: Issue RSA-PSS Clearance Cert       │
│  • W3C PROV-O JSON-LD Lineage Graph          │
│  • Strict Pydantic JSON Payload              │
└──────────────────────────────────────────────┘
```

1. **Byte-Level Inspection & Anti-Spoofing**: Ignores misleading file extensions and metadata labels (e.g. `.public_domain`). Inspects raw magic headers directly.
2. **Two-Stage Text Track**:
   - **Stage 1 (Recall)**: Dense semantic retrieval via Bi-Encoder + FAISS index.
   - **Stage 2 (Precision)**: Pairwise cross-encoder re-ranking (`threshold > 0.85`) to catch paraphrasing and reworded copyrighted text.
3. **Two-Stage Image Track**:
   - **Stage 1 (Cheap Filter)**: Perceptual hashing (`pHash`) with Hamming distance (`< 5`).
   - **Stage 2 (Deep Compare)**: Visual embedding comparison (`CLIP cosine similarity > 0.90`) to catch cropped, resized, or color-altered images.
4. **Cryptographic Clearance & Provenance**:
   - Signs clean asset SHA-256 hashes using RSA-PSS.
   - Emits immutable W3C PROV-O JSON-LD lineage graphs.
   - Independent verification tool to check certificate authenticity.
5. **Modern AI Web Platform**:
   - Interactive web dashboard (FastAPI + TailwindCSS + Lucide).
   - Drag-and-drop file ingestion, one-click demo loaders, and live certificate inspector.

---

## 🚀 Quickstart Guide

### 1. Clone & Setup Environment

```bash
git clone https://github.com/Abhilash123-hub/smart_amrita_hackathon.git
cd smart_amrita_hackathon

# Create virtual environment (Python 3.10+)
python -m venv .venv

# Activate on Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### 2. Launch the AI Web Dashboard

**Option A (One-Click Windows Launcher):**
Just double-click `run_app.bat` in the root folder, or run:
```powershell
.\run_app.ps1
```

**Option B (Command Line):**
```bash
python app.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.
API documentation is available at **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**.

*(Note: Both the FastAPI engine on port 8000 and the Next.js frontend in `ui/` on port 3000 are 100% synchronized with the modern AI Copilot Chatbot interface).*

---

## 💻 CLI Usage

### Generate RSA Keys
```bash
python main.py generate-keys --output-dir ./keys
```

### Run an Ingestion Scan
```bash
# Minimal schema output
python main.py scan --input-dir ./tests --minimal

# Full scan with custom keys and JSON report export
python main.py scan --input-dir ./mock_data/dirty_dataset --index-dir ./mock_data/copyright_index --output ./scan_results.json
```

### Verify a Certificate
```bash
python main.py verify-cert \
  --asset-hash "sha256:..." \
  --signature "..." \
  --public-key ./keys/traceai_public.pem
```

---

## 🧪 Testing

Run the full automated test suite:
```bash
pytest -v
```

---

## 📋 Output Format Specification

```json
{
  "asset_id": "book_excerpt_0421.txt",
  "status": "BLOCKED",
  "track": "TEXT",
  "matched_source": "© O'Reilly Media",
  "similarity_score": 0.94,
  "asset_hash": "sha256:9f3c...e7a1",
  "certificate_id": null
}
```
*(If clean, `status` is `"PASSED"`, `matched_source` is `null`, and `certificate_id` contains a UUID with an RSA-PSS signed certificate).*
