"""Emit all 30 Task Cards from the TraceAI Enterprise Build Guide."""

import json
from pathlib import Path

CARDS = [
    # Phase 1
    {
        "id": "T1.1",
        "phase": "Phase 1 - Fingerprinting Engine",
        "title": "Sliding-window chunker",
        "objective": "Split documents into 256-token chunks with 50-token overlap using bi-encoder tokenizer.",
        "agent_steps": [
            "Implement chunk_text(text, size=256, overlap=50) with token-level windows.",
            "Return chunk metadata: offsets, token counts, parent asset id.",
            "Property test: reassembling windows covers the document; no chunk exceeds 256 tokens."
        ],
        "files": ["src/traceai/pipelines/text_track.py", "tests/test_chunker.py"],
        "acceptance_criteria": [
            "A 10,000-token document yields ceil((10000-50)/(256-50)) windows, all within size.",
            "A sentence deliberately placed across a boundary appears fully in at least one chunk."
        ],
        "verification": "pytest tests/test_chunker.py -q",
        "depends_on": ["T0.2"],
        "status": "pending"
    },
    {
        "id": "T1.2",
        "phase": "Phase 1 - Fingerprinting Engine",
        "title": "Bi-encoder recall over FAISS HNSW",
        "objective": "Embed chunks with all-MiniLM-L6-v2 and recall top-K=5 neighbors using inner-product search.",
        "agent_steps": [
            "Wrap IndexStore interface: add, search, save, load (FAISS backend).",
            "Build IndexHNSWFlat with inner product metric; normalize at write and query time.",
            "Encode in batches; expose per-chunk latency metrics."
        ],
        "files": ["src/traceai/db/index_store.py", "src/traceai/pipelines/text_track.py"],
        "acceptance_criteria": [
            "Querying a verbatim chunk returns its source at rank 1 with similarity above 0.9.",
            "p95 recall-stage latency is under 50 ms per chunk on CPU for seed index.",
            "Index snapshots save and reload bit-identically."
        ],
        "verification": "pytest tests/test_index_store.py -q",
        "depends_on": ["T1.1"],
        "status": "pending"
    },
    {
        "id": "T1.3",
        "phase": "Phase 1 - Fingerprinting Engine",
        "title": "Cross-Encoder re-ranker with early exit",
        "objective": "Score pairs with ms-marco-MiniLM-L-6-v2; block when exceeding threshold; early exit < 0.5.",
        "agent_steps": [
            "Implement two-stage scan() matching specification.",
            "Format pairs [CLS] chunk [SEP] candidate [SEP]; batch predict.",
            "Early exit: if best recall similarity is under 0.5, return PASSED with score 0.",
            "Emit structured scan logs: gate, candidates, scores, decision, latency."
        ],
        "files": ["src/traceai/pipelines/text_track.py", "tests/test_text_track.py"],
        "acceptance_criteria": [
            "All 10 dirty-text assets are flagged; verbatim and paraphrase alike.",
            "Clean holdout assets pass with best scores under 0.6.",
            "Early-exit path demonstrably skips cross-encoder calls (assert via spy)."
        ],
        "verification": "pytest tests/test_text_track.py -q",
        "depends_on": ["T1.2"],
        "status": "pending"
    },
    {
        "id": "T1.4",
        "phase": "Phase 1 - Fingerprinting Engine",
        "title": "pHash coarse filter over Redis",
        "objective": "Compute perceptual hashes and match against Redis dictionary at Hamming distance < 5.",
        "agent_steps": [
            "Implement phash_index: load dictionary, query by Hamming distance, add.",
            "Batch-load 50-image seed dictionary at worker start.",
            "Metric: fraction of images filtered at stage 1 (target above 90% on clean sets)."
        ],
        "files": ["src/traceai/pipelines/image_track.py", "src/traceai/db/redis_cache.py"],
        "acceptance_criteria": [
            "Recompressed and lightly color-shifted copies of seed images are recalled.",
            "Unrelated images pass with zero GPU invocations.",
            "Dictionary round-trips through Redis without loss."
        ],
        "verification": "pytest tests/test_image_track.py -q -k phash",
        "depends_on": ["T0.2"],
        "status": "pending"
    },
    {
        "id": "T1.5",
        "phase": "Phase 1 - Fingerprinting Engine",
        "title": "CLIP deep compare",
        "objective": "Embed candidates with clip-vit-base-patch32; block when cosine similarity exceeds 0.90.",
        "agent_steps": [
            "Implement CLIP embedding for PIL images; normalize and search image index.",
            "Compare against top neighbors; threshold from config only.",
            "Record per-image latency and device placement."
        ],
        "files": ["src/traceai/pipelines/image_track.py"],
        "acceptance_criteria": [
            "All 10 dirty-image assets (85-95% crops) are blocked at default threshold.",
            "Clean images pass with similarity well under 0.8.",
            "No image reaches CLIP unless pHash recalled it."
        ],
        "verification": "pytest tests/test_image_track.py -q",
        "depends_on": ["T1.4"],
        "status": "pending"
    },
    {
        "id": "T1.6",
        "phase": "Phase 1 - Fingerprinting Engine",
        "title": "Evidence crops with OpenCV",
        "objective": "For blocked images, generate visual proof: bounding box around highest-correlation region.",
        "agent_steps": [
            "Implement template-match localization between ingested image and matched source.",
            "Render side-by-side evidence PNG with scores and hashes burned into the margin.",
            "Store under evidence locker layout from Phase 2 (content-addressed path)."
        ],
        "files": ["src/traceai/pipelines/evidence.py"],
        "acceptance_criteria": [
            "Evidence artifact renders for every blocked dirty image.",
            "Bounding box overlaps true inserted region in manifest.",
            "Artifact bytes are deterministic for identical inputs."
        ],
        "verification": "pytest tests/test_evidence_crops.py -q",
        "depends_on": ["T1.5"],
        "status": "pending"
    },
    {
        "id": "T1.7",
        "phase": "Phase 1 - Fingerprinting Engine",
        "title": "Gateway wiring and batch scan end-to-end",
        "objective": "Connect FastAPI ingest, dispatch, and both tracks so POST /v1/ingest returns per-asset verdicts.",
        "agent_steps": [
            "Implement POST /v1/ingest with IngestRequest validation and idempotency keys.",
            "Task fan-out by MIME; collect results into batch status endpoint.",
            "traceai scan CLI: local directory in, verdict table out.",
            "Integration test drives the full loop."
        ],
        "files": ["src/traceai/api.py", "src/traceai/cli.py", "src/traceai/worker.py"],
        "acceptance_criteria": [
            "End-to-end integration test flags 100% of dirty dataset through HTTP path.",
            "Re-submitting same batch does not double-scan (idempotency verified).",
            "CLI and API produce identical verdicts for same input directory."
        ],
        "verification": "pytest tests/test_integration.py -q",
        "depends_on": ["T1.3", "T1.6"],
        "status": "pending"
    },
    {
        "id": "T1.8",
        "phase": "Phase 1 - Fingerprinting Engine",
        "title": "Threshold calibration harness",
        "objective": "Prove defaults: sweep thresholds over labeled calibration set, emit ROC summaries.",
        "agent_steps": [
            "Build calibration set: dirty corpus plus graded near-miss paraphrases and crops.",
            "Sweep text 0.70-0.95 and image 0.80-0.97 in 0.01 steps; capture catch rate and FPR.",
            "Generate calibration report artifact for human review.",
            "Record decision and metric table in Memory under decisions/thresholds."
        ],
        "files": ["scripts/calibrate_thresholds.py", "reports/thresholds/*.md"],
        "acceptance_criteria": [
            "Report shows defaults on the knee of ROC with FPR under 2%.",
            "Any default change lands as a config PR referencing report.",
            "Decision and metric table recorded in Memory."
        ],
        "verification": "python scripts/calibrate_thresholds.py --report-only",
        "depends_on": ["T1.7"],
        "status": "pending"
    },
    # Phase 2
    {
        "id": "T2.1",
        "phase": "Phase 2 - Evidence, Crypto and Lineage",
        "title": "Evidence layer with RSA-PSS signing",
        "objective": "Implement hash_asset_bytes and issue_clearance_certificate: canonical JSON, RSA-2048 PSS.",
        "agent_steps": [
            "Implement src/traceai/core/crypto.py with key loading abstraction.",
            "Canonicalize payloads (sort_keys, separators) before signing; verify() counterpart included.",
            "Unit tests cover tamper detection: any byte change breaks verification."
        ],
        "files": ["src/traceai/core/crypto.py", "tests/test_crypto.py"],
        "acceptance_criteria": [
            "Sign-verify round-trip passes; flipped payload bits fail verification.",
            "Private key never appears in logs, errors, or test fixtures.",
            "Signature uses PSS with MGFSHA256 and MAX_LENGTH salt."
        ],
        "verification": "pytest tests/test_crypto.py -q",
        "depends_on": ["T0.2"],
        "status": "pending"
    },
    {
        "id": "T2.2",
        "phase": "Phase 2 - Evidence, Crypto and Lineage",
        "title": "Evidence locker storage layout",
        "objective": "Content-addressed, write-once S3/MinIO layout for blocked-asset proof bundles.",
        "agent_steps": [
            "Implement locker paths: evidence/<asset_hash[:2]>/<asset_hash>/ with crop, score snapshot, match metadata.",
            "Enable object lock (WORM) in production profile; document retention period.",
            "Local MinIO service added to docker-compose with same API surface."
        ],
        "files": ["src/traceai/db/evidence_locker.py", "docker-compose.yml"],
        "acceptance_criteria": [
            "Re-writing same evidence key raises; objects are immutable.",
            "Evidence URIs recorded on ScanResult resolve to retrievable bundles.",
            "Retention policy documented and enforced by bucket config."
        ],
        "verification": "pytest tests/test_evidence_locker.py -q",
        "depends_on": ["T2.1"],
        "status": "pending"
    },
    {
        "id": "T2.3",
        "phase": "Phase 2 - Evidence, Crypto and Lineage",
        "title": "Audit log persistence",
        "objective": "Append-only Postgres audit log for every verdict, with monthly partitions.",
        "agent_steps": [
            "Migrate audit_events partitioned by month; insert on every scan completion.",
            "Expose query endpoints: by batch, by asset hash, by time range.",
            "Never update or delete: corrections are compensating events."
        ],
        "files": ["migrations/0002_audit_events.sql", "src/traceai/db/audit.py"],
        "acceptance_criteria": [
            "All integration-test scans appear in audit log with full payloads.",
            "Partition pruning is observable in EXPLAIN for range queries.",
            "Update/delete attempts fail at DB role level."
        ],
        "verification": "pytest tests/test_audit.py -q",
        "depends_on": ["T2.1"],
        "status": "pending"
    },
    {
        "id": "T2.4",
        "phase": "Phase 2 - Evidence, Crypto and Lineage",
        "title": "PROV-O lineage projection",
        "objective": "Project scans into Neo4j using W3C PROV-O vocabulary: Entity, Activity, Agent triangle.",
        "agent_steps": [
            "Implement prov_o.py JSON-LD generation plus Cypher upserts.",
            "Derive lineage edges from source_uri so domain-level queries work.",
            "Async projection that catches up from audit log on restart."
        ],
        "files": ["src/traceai/lineage/prov_o.py", "migrations/0003_neo4j_constraints.cpy"],
        "acceptance_criteria": [
            "Round-trip: scan then query shows full Entity-Activity-Agent triangle.",
            "Domain query returns manifest-verified results.",
            "Killing Neo4j mid-scan loses nothing: catches up from audit log."
        ],
        "verification": "pytest tests/test_lineage.py -q",
        "depends_on": ["T2.3"],
        "status": "pending"
    },
    {
        "id": "T2.5",
        "phase": "Phase 2 - Evidence, Crypto and Lineage",
        "title": "Verification endpoint and attorney flow",
        "objective": "Verify RSA signature and hash from certificate and original bytes without exposing tenant data.",
        "agent_steps": [
            "POST /v1/verify: multipart certificate + file; re-hash, verify signature, return verdict.",
            "Public key distribution endpoint with key rotation metadata.",
            "Document attorney workflow: download key, hash locally, submit, receive proof."
        ],
        "files": ["src/traceai/api.py", "docs/attorney-verification.md"],
        "acceptance_criteria": [
            "Round-trip verification succeeds for sampled certificate.",
            "Verification of tampered file fails with precise reason code.",
            "No cross-tenant information leaks through error messages."
        ],
        "verification": "pytest tests/test_verify_endpoint.py -q",
        "depends_on": ["T2.1"],
        "status": "pending"
    },
    # Phase 3
    {
        "id": "T3.1",
        "phase": "Phase 3 - Enterprise Dashboard UI",
        "title": "Next.js 15 scaffold and design tokens",
        "objective": "Initialize ui/ workspace with Tailwind 4 and shadcn/ui; encode Chapter 13 tokens.",
        "agent_steps": [
            "Create Next.js 15 app router project with TypeScript strict mode.",
            "Encode full token table as CSS custom properties.",
            "Set up shadcn/ui with dark-only theme; add TanStack Query and Recharts."
        ],
        "files": ["ui/**"],
        "acceptance_criteria": [
            "Tokens route renders every token with contrast values.",
            "All grays and accents match Chapter 13 hex values exactly.",
            "pnpm build passes with zero type errors."
        ],
        "verification": "cd ui && pnpm build && pnpm test",
        "depends_on": ["T2.5"],
        "status": "pending"
    },
    {
        "id": "T3.2",
        "phase": "Phase 3 - Enterprise Dashboard UI",
        "title": "App shell: nav, topbar, live status",
        "objective": "Build application shell from mock: left nav groups, topbar with environment badge.",
        "agent_steps": [
            "Implement shell layout with exact nav sections of Chapter 14.",
            "Global search routes: asset hash, batch id, certificate uuid.",
            "Environment badge always visible with wrong-env guard."
        ],
        "files": ["ui/src/app/(shell)/**"],
        "acceptance_criteria": [
            "Navigation matches mock structurally at 1440 and 1920 widths.",
            "Search resolves known fixture asset, batch, and certificate.",
            "Shell renders in under 200 ms TTFB locally."
        ],
        "verification": "cd ui && pnpm e2e -- --grep shell",
        "depends_on": ["T3.1"],
        "status": "pending"
    },
    {
        "id": "T3.3",
        "phase": "Phase 3 - Enterprise Dashboard UI",
        "title": "Scan Console screen",
        "objective": "Live telemetry view: KPI cards, risk distribution, live scan stream table, throughput sparkline.",
        "agent_steps": [
            "Implement five regions from mock with recorded fixtures.",
            "KPI cards subscribe to /v1/metrics/summary; stream table to WebSocket feed.",
            "Verdict badges use status color semantics of Chapter 13."
        ],
        "files": ["ui/src/app/(shell)/console/**"],
        "acceptance_criteria": [
            "Fixture replay matches mock layout within spacing tolerance.",
            "Live mode updates stream table without full-page re-render.",
            "Empty, loading, and error states implemented per Chapter 14 spec."
        ],
        "verification": "cd ui && pnpm e2e -- --grep console",
        "depends_on": ["T3.2"],
        "status": "pending"
    },
    {
        "id": "T3.4",
        "phase": "Phase 3 - Enterprise Dashboard UI",
        "title": "Batch Monitor and Queues screens",
        "objective": "Operational drill-down: batch lists with progress, per-asset status, retry actions; worker health.",
        "agent_steps": [
            "Batch table with server-side pagination over /v1/batches.",
            "Batch detail: assets with verdicts, elapsed time, retry buttons.",
            "Queues view: depth, in-flight, worker heartbeats from /v1/ops endpoints."
        ],
        "files": ["ui/src/app/(shell)/batches/**", "ui/src/app/(shell)/ops/**"],
        "acceptance_criteria": [
            "Retry action re-enqueues and UI reflects state change within 2 seconds.",
            "Batch detail renders 10k-asset batches with virtualized table.",
            "All mutations require operator scope."
        ],
        "verification": "cd ui && pnpm e2e -- --grep batches",
        "depends_on": ["T3.2"],
        "status": "pending"
    },
    {
        "id": "T3.5",
        "phase": "Phase 3 - Enterprise Dashboard UI",
        "title": "Evidence Locker and Lineage Explorer",
        "objective": "Evidence browsing with side-by-side crop comparison; lineage graph visualization.",
        "agent_steps": [
            "Evidence list with filters and detail split view.",
            "Lineage Explorer: query by asset hash or source domain; render E-A-A graph.",
            "Graph interactions: zoom, node focus, path highlight, PNG export."
        ],
        "files": ["ui/src/app/(shell)/evidence/**", "ui/src/app/(shell)/lineage/**"],
        "acceptance_criteria": [
            "Split view renders ingested vs source with bounding box overlay.",
            "Domain lineage query returns fixture subgraph within 3 seconds.",
            "Graph export includes score and hash annotations."
        ],
        "verification": "cd ui && pnpm e2e -- --grep evidence,lineage",
        "depends_on": ["T3.2"],
        "status": "pending"
    },
    {
        "id": "T3.6",
        "phase": "Phase 3 - Enterprise Dashboard UI",
        "title": "Certificate Registry and Attorney Portal",
        "objective": "Registry with search and export bundles; standalone attorney portal for cryptographic verification.",
        "agent_steps": [
            "Registry table over /v1/certificates with copy-uuid, export bundle actions.",
            "Attorney portal: upload certificate + file, run /v1/verify, show proof result.",
            "Portal is separately deployable and themed for external legal use."
        ],
        "files": ["ui/src/app/(shell)/certificates/**", "ui-portal/**"],
        "acceptance_criteria": [
            "Export bundle contains certificate JSON, public key, and instructions.",
            "Portal verifies good certificate and rejects tampered one with reason.",
            "Portal works against read-only API credential."
        ],
        "verification": "cd ui && pnpm e2e -- --grep certificates",
        "depends_on": ["T3.2"],
        "status": "pending"
    },
    {
        "id": "T3.7",
        "phase": "Phase 3 - Enterprise Dashboard UI",
        "title": "Accessibility, density and dark-mode QA pass",
        "objective": "Enterprise acceptance pass: contrast, keyboard navigation, table density, dark-mode consistency.",
        "agent_steps": [
            "Automated contrast audit against Chapter 13 requirements (4.5:1 body, 3:1 large).",
            "Keyboard paths for every primary flow; visible focus rings.",
            "Density pass: 32 px row rhythm for scan tables; no layout shift on live updates."
        ],
        "files": ["ui/**"],
        "acceptance_criteria": [
            "axe-core reports zero critical violations on all shell routes.",
            "Full keyboard walkthrough of scan-to-evidence flow succeeds.",
            "Dark tokens are the only theme."
        ],
        "verification": "cd ui && pnpm test:a11y",
        "depends_on": ["T3.3", "T3.4", "T3.5", "T3.6"],
        "status": "pending"
    },
    # Phase 4
    {
        "id": "T4.1",
        "phase": "Phase 4 - Production Hardening and Scale",
        "title": "Milvus migration behind IndexStore",
        "objective": "Swap FAISS for Milvus 2.5 HNSW collections with per-tenant namespaces.",
        "agent_steps": [
            "Implement MilvusIndexStore against same five-method interface.",
            "Backfill job: stream reference corpus into collections; dual-run against FAISS.",
            "Shadow-verify: identical top-5 on 10k query sample before cutover."
        ],
        "files": ["src/traceai/db/milvus_store.py", "scripts/backfill_index.py"],
        "acceptance_criteria": [
            "Contract tests pass for both backends from one suite.",
            "Shadow run shows recall agreement above 99.5% on sample.",
            "Cutover is a config flip; rollback rehearsed."
        ],
        "verification": "pytest tests/test_index_store.py -q --backend both",
        "depends_on": ["T1.2"],
        "status": "pending"
    },
    {
        "id": "T4.2",
        "phase": "Phase 4 - Production Hardening and Scale",
        "title": "ONNX export and Triton deployment",
        "objective": "Export MiniLM, Cross-Encoder, and CLIP to ONNX; serve via Triton with dynamic batching.",
        "agent_steps": [
            "Export scripts with parity tests: ONNX vs PyTorch outputs within 1e-3 cosine.",
            "Triton model repository with dynamic batching (window 8 ms).",
            "Workers call Triton via gRPC; PyTorch path retained as fallback flag."
        ],
        "files": ["scripts/export_onnx.py", "deploy/triton/**", "src/traceai/db/inference.py"],
        "acceptance_criteria": [
            "Parity tests pass on 1k samples for all three models.",
            "Triton p95 batch latency beats local PyTorch by at least 3x under load.",
            "Fallback flag restores Phase 1 behavior without redeploy."
        ],
        "verification": "pytest tests/test_inference_parity.py -q",
        "depends_on": ["T1.3", "T1.5"],
        "status": "pending"
    },
    {
        "id": "T4.3",
        "phase": "Phase 4 - Production Hardening and Scale",
        "title": "Kubernetes manifests and GitOps",
        "objective": "Deploy full topology: API HPA on CPU, workers HPA on queue depth, StatefulSets with PVs.",
        "agent_steps": [
            "Author manifests for every tier in Figure 12.1.",
            "HPA policies: API on 70% CPU; workers on Redis queue depth.",
            "Pre-baked worker images with model weights; zero cold-start downloads."
        ],
        "files": ["deploy/k8s/**", "docker/Dockerfile.workers"],
        "acceptance_criteria": [
            "Fresh cluster bring-up from manifests reaches healthy in under 10 minutes.",
            "Worker pod start to first scanned asset is under 20 seconds.",
            "Rolling update of workers drops zero in-flight tasks."
        ],
        "verification": "kubectl apply -k deploy/k8s/overlays/prod && kubectl get pods -A",
        "depends_on": ["T0.4"],
        "status": "pending"
    },
    {
        "id": "T4.4",
        "phase": "Phase 4 - Production Hardening and Scale",
        "title": "Secrets, keys and KMS wiring",
        "objective": "Move signing keys to KMS/Vault with rotation metadata; applications reference, never read, key material.",
        "agent_steps": [
            "External Secrets Operator binds KMS-backed secrets to pod envs.",
            "Signing service requests PSS signatures from KMS; key never leaves.",
            "Rotation runbook: new key id in certificates, old key verifies historical artifacts."
        ],
        "files": ["deploy/secrets/**", "src/traceai/core/kms_signer.py"],
        "acceptance_criteria": [
            "No private key material exists in images, volumes, or env dumps.",
            "Certificates record key id; both current and previous keys verify.",
            "Secret rotation drill completes without downtime."
        ],
        "verification": "pytest tests/test_kms_signer.py -q",
        "depends_on": ["T2.1"],
        "status": "pending"
    },
    {
        "id": "T4.5",
        "phase": "Phase 4 - Production Hardening and Scale",
        "title": "Observability stack and SLO dashboards",
        "objective": "Prometheus, Grafana, Loki, Sentry, and OpenTelemetry traces wired to degradation behaviors.",
        "agent_steps": [
            "Instrument scan latency histograms, queue depth, GPU utilization, verdict counters.",
            "Trace one asset end-to-end: gateway to certificate, span per plane.",
            "SLO dashboards for Table 2.2 requirements with alert rules."
        ],
        "files": ["deploy/observability/**", "src/traceai/telemetry.py"],
        "acceptance_criteria": [
            "p95 scan latency alert fires in staged overload test.",
            "A single trace shows every plane for one asset with attributes.",
            "Degraded-index drill surfaces on dashboard within one minute."
        ],
        "verification": "pytest tests/test_telemetry.py -q",
        "depends_on": ["T1.7", "T2.3"],
        "status": "pending"
    },
    {
        "id": "T4.6",
        "phase": "Phase 4 - Production Hardening and Scale",
        "title": "Load test to SLO certification",
        "objective": "Prove Table 2.2: 10k assets/minute sustained with p95 verdict latency under 500 ms.",
        "agent_steps": [
            "Locust/k6 scenario replaying realistic mixed MIME batches.",
            "Run 60-minute soak; capture latency, throughput, error budget burn.",
            "Tune HPA and Triton batching; document certified configuration."
        ],
        "files": ["load/**", "reports/load-certification.md"],
        "acceptance_criteria": [
            "Sustained 10k/min for 60 minutes with p95 under 500 ms and error rate under 0.1%.",
            "No unbounded queue growth; autoscaling events documented.",
            "Certification report signed off as Phase 4 exit gate."
        ],
        "verification": "k6 run load/soak.js --quiet",
        "depends_on": ["T4.3", "T4.5"],
        "status": "pending"
    },
    {
        "id": "T4.7",
        "phase": "Phase 4 - Production Hardening and Scale",
        "title": "Plugin ecosystem and registry API",
        "objective": "Ship traceai-hf dataset wrapper, PyTorch DataLoader hook, and public Fingerprint Registry API.",
        "agent_steps": [
            "traceai-hf package: wraps load_dataset, scans streams, attaches certificates.",
            "DataLoader hook with at-rest and in-flight modes.",
            "Registry API: rightsholder auth, submission workflow, attestation status, revocation."
        ],
        "files": ["packages/traceai-hf/**", "src/traceai/registry/**"],
        "acceptance_criteria": [
            "Wrapper blocks dirty HuggingFace fixture end-to-end with evidence.",
            "Registry submissions appear in reference index within one cycle.",
            "Revocation removes works from matching within same cycle."
        ],
        "verification": "pytest packages/traceai-hf/tests -q && pytest tests/test_registry.py -q",
        "depends_on": ["T1.7", "T2.5"],
        "status": "pending"
    }
]

def main():
    target_dir = Path("agents/taskcards")
    target_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for card in CARDS:
        card_file = target_dir / f"{card['id']}.json"
        card_file.write_text(json.dumps(card, indent=2), encoding="utf-8")
        count += 1
    print(f"Emitted {count} task cards into {target_dir}")

if __name__ == "__main__":
    main()
