# TraceAI Attorney Cryptographic Verification Workflow (Task Card T2.5)

## Overview
TraceAI provides an independent, zero-privilege verification flow for IP counsel and compliance auditors.
Attorneys can verify whether a training dataset asset was cleared without exposing raw training corpora or relying on TraceAI internal databases.

---

## 3-Step Verification Protocol

### Step 1: Download Active Public Key
Attorneys obtain the authorized public signing key PEM directly from the gateway:
```bash
curl -s http://localhost:8000/v1/keys/public > traceai_public.pem
```

### Step 2: Compute Asset SHA-256 Locally
Hash the raw asset locally on counsel's machine to confirm byte-for-byte fidelity:
```bash
sha256sum original_training_sample.txt
# Output: sha256:<64 lowercase hex characters>
```

### Step 3: Submit Verification Request to Endpoint
Submit the issued `ClearanceCertificate` JSON along with the raw asset bytes to `/v1/verify`:
```bash
curl -X POST http://localhost:8000/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "certificate": {
      "certificate_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "asset_id": "sample-01",
      "asset_hash": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "verdict": "PASSED",
      "issued_at": "2026-09-18T10:00:00Z",
      "rsa_signature": "<BASE64_SIGNATURE>"
    },
    "raw_content_text": "Content of training sample"
  }'
```

### Verification Outcomes:
1. **`SIGNATURE_VALID`**: Certificate is mathematically authentic and strictly bound to the asset hash.
2. **`HASH_MISMATCH`**: The submitted file bytes do not match the hash certified by TraceAI.
3. **`SIGNATURE_INVALID`**: The certificate signature was tampered with or issued by an untrusted key.
