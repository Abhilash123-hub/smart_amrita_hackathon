# TRACEAI REST API Reference

> Base URL: `http://127.0.0.1:8000`  
> Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

---

## 1. Core Health & Info

### `GET /health` or `GET /api/health`
Health check confirming gateway and data layer availability.
- **Response `200 OK`**:
```json
{
  "status": "HEALTHY",
  "service": "TraceAI Enterprise Gateway",
  "version": "0.2.0",
  "data_layer_status": "READY",
  "records_loaded": 6,
  "timestamp": "2026-09-18T17:00:00.000000Z"
}
```

### `GET /api/info`
Operational metadata, active modalities, thresholds, and public key fingerprint.

---

## 2. Records & Provenance Endpoints

### `GET /records` or `GET /api/records`
List all sample records from the completed data layer.
- **Query Parameters**:
  - `record_type` (optional): Filter by `"text"` or `"image"`.
- **Response `200 OK`**:
```json
{
  "records": [
    {
      "record_id": "DOC-001",
      "file_name": "sample_document_1.txt",
      "record_type": "text",
      "license": "Project-created demo data",
      "license_verified": true
    }
  ]
}
```

### `GET /records/{record_id}` or `GET /api/records/{record_id}`
Retrieve a single record's provenance metadata.
- **Path Parameter**: `record_id` (e.g. `DOC-001`, `IMG-003`).
- **Response `200 OK`** or **`404 Not Found`**.

### `GET /records/{record_id}/provenance`
Retrieve W3C PROV-O structured lineage graph for the record.

---

## 3. Analysis & Similarity Endpoints

### `POST /analyze` or `POST /api/analyze`
Execute end-to-end trace: Identity (SHA-256) + Similarity + Provenance + Review Indicator.
- **Request Body**:
```json
{
  "record_id": "DOC-003"
}
```
- **Response `200 OK`**:
```json
{
  "record_id": "DOC-003",
  "record_type": "text",
  "sha256": "sha256:10e1616a22d9abeec6945d675c1410457cea5b5156944436a3f6978e3a907310",
  "source": "TRACEAI Synthetic Demo Dataset",
  "license": "Project-created demo data",
  "license_verified": true,
  "parent_record": "DOC-001",
  "similarity_results": [
    {
      "record_id": "DOC-001",
      "similarity": 0.8131
    }
  ],
  "provenance_completeness": 100.0,
  "review_indicator": "HIGH",
  "composite_risk_score": 0.8131,
  "review_status": "Potential provenance risk — high similarity or unverified lineage. Provenance & licence review required before AI training use."
}
```

### `POST /similarity/search`
Search nearest matching records across the dataset.
- **Request Body**:
```json
{
  "record_id": "DOC-003",
  "top_k": 3
}
```

### `GET /records/{record_id}/evidence`
Export evidence audit package.
- **Query Parameter**:
  - `format`: `"json"` (default) or `"html"`.
- **Response**: Application JSON or styled HTML audit certificate.
