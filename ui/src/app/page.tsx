"use client";

import React, { useState } from "react";
import SplitPane from "../components/SplitPane";
import {
  ShieldCheck,
  ShieldAlert,
  UserCheck,
  Split,
  Search,
  CheckCircle2,
  AlertOctagon,
  FileText,
  Image as ImageIcon,
  Code2,
  Lock,
  ExternalLink,
  Copy,
  ChevronRight,
  Maximize2,
  RefreshCw,
  Award,
  Layers,
  Sparkles,
} from "lucide-react";

interface AssetRecord {
  id: string;
  name: string;
  hash: string;
  track: "TEXT" | "IMAGE" | "CODE";
  status: "PASSED" | "BLOCKED" | "HUMAN_REVIEW";
  similarity: number;
  matchedSource?: string;
  matchedChunk?: string;
  timestamp: string;
  jurisdiction: string;
  signature?: string;
  keyFingerprint?: string;
  provLineage: Record<string, any>;
}

const INITIAL_ASSETS: AssetRecord[] = [
  {
    id: "AST-88219-TXT",
    name: "corpus_shard_402.txt",
    hash: "sha256:4a3b110992a8e45f9c0b78df13bceee89d9847291a18204b",
    track: "TEXT",
    status: "BLOCKED",
    similarity: 0.942,
    matchedSource: "RefCorpus: New York Times 2023 Tech Archive (Doc #994)",
    matchedChunk: "The proprietary transformer architecture incorporates a multi-tier attention mechanism...",
    timestamp: "2026-09-18T17:15:22Z",
    jurisdiction: "US-FAIR-USE",
    signature: undefined,
    provLineage: {
      "@context": "https://www.w3.org/ns/prov-o#",
      "@type": "prov:Entity",
      "prov:wasGeneratedBy": "traceai:engine:v0.2.0",
      "prov:wasInvalidatedBy": "traceai:gate:cross_encoder",
      "prov:endedAtTime": "2026-09-18T17:15:22Z",
      "traceai:decision": "BLOCKED",
      "traceai:score": 0.942,
    },
  },
  {
    id: "AST-88220-IMG",
    name: "generated_concept_artwork.png",
    hash: "sha256:77bc09281aef034bce909283741829034871239840192834",
    track: "IMAGE",
    status: "PASSED",
    similarity: 0.124,
    matchedSource: undefined,
    timestamp: "2026-09-18T17:18:04Z",
    jurisdiction: "GLOBAL",
    signature: "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0k19...",
    keyFingerprint: "rsa2048:8f4c21aa0981e4b3",
    provLineage: {
      "@context": "https://www.w3.org/ns/prov-o#",
      "@type": "prov:Entity",
      "prov:wasGeneratedBy": "traceai:engine:v0.2.0",
      "prov:wasAssociatedWith": "traceai:signer:rsa_pss",
      "prov:endedAtTime": "2026-09-18T17:18:04Z",
      "traceai:decision": "PASSED",
      "traceai:score": 0.124,
    },
  },
  {
    id: "AST-88221-COD",
    name: "auth_middleware_controller.py",
    hash: "sha256:109923847291823904812390841209384019283471029384",
    track: "CODE",
    status: "HUMAN_REVIEW",
    similarity: 0.812,
    matchedSource: "RefCorpus: GitHub Linux GPL-2.0 Kernel Subsystem",
    matchedChunk: "static inline int trace_event_raw_event_sched_switch(...)",
    timestamp: "2026-09-18T17:21:40Z",
    jurisdiction: "EU-DSM-ART4",
    provLineage: {
      "@context": "https://www.w3.org/ns/prov-o#",
      "@type": "prov:Entity",
      "prov:wasGeneratedBy": "traceai:router:confidence_band",
      "prov:endedAtTime": "2026-09-18T17:21:40Z",
      "traceai:decision": "HELD_IN_QUEUE",
      "traceai:score": 0.812,
    },
  },
  {
    id: "AST-88222-TXT",
    name: "synthetic_dialogue_batch_12.jsonl",
    hash: "sha256:998124019283401928340192834019283401928340192834",
    track: "TEXT",
    status: "PASSED",
    similarity: 0.083,
    timestamp: "2026-09-18T17:24:11Z",
    jurisdiction: "GLOBAL",
    signature: "MIIBCgKCAQEAu819028301928301928301928301928301928...",
    keyFingerprint: "rsa2048:8f4c21aa0981e4b3",
    provLineage: {
      "@context": "https://www.w3.org/ns/prov-o#",
      "@type": "prov:Entity",
      "prov:wasGeneratedBy": "traceai:engine:v0.2.0",
      "prov:endedAtTime": "2026-09-18T17:24:11Z",
      "traceai:decision": "PASSED",
    },
  },
];

export default function HomePage() {
  const [splitOrientation, setSplitOrientation] = useState<"vertical" | "horizontal">("vertical");
  const [activeAssetId, setActiveAssetId] = useState<string>(INITIAL_ASSETS[0].id);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [splitSize, setSplitSize] = useState<number | undefined>(undefined);
  const [copied, setCopied] = useState(false);

  const activeAsset = INITIAL_ASSETS.find((a) => a.id === activeAssetId) || INITIAL_ASSETS[0];

  const filteredAssets = INITIAL_ASSETS.filter((a) => {
    if (filterStatus !== "ALL" && a.status !== filterStatus) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        a.id.toLowerCase().includes(q) ||
        a.name.toLowerCase().includes(q) ||
        a.hash.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const handleCopyLineage = () => {
    navigator.clipboard.writeText(JSON.stringify(activeAsset.provLineage, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="h-screen flex flex-col bg-bg-root text-text-body overflow-hidden selection:bg-accent-brand selection:text-bg-root">
      {/* HEADER BAR */}
      <header className="h-14 bg-accent-brand text-white px-4 flex items-center justify-between flex-shrink-0 z-20 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-white text-accent-brand flex items-center justify-center font-black shadow">
            <ShieldCheck className="w-5 h-5 text-accent-brand" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold tracking-tight text-white">
                TraceAI Copilot
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/20 border border-white/30 text-white font-bold">
                AI CHATBOT & EVIDENCE
              </span>
            </div>
            <p className="text-[11px] text-white/80">
              Multimodal Copyright Fingerprinting & Cryptographic Clearance
            </p>
          </div>
        </div>

        {/* CONTROLS */}
        <div className="flex items-center gap-2">
          {/* Orientation Toggle */}
          <button
            onClick={() =>
              setSplitOrientation((prev) => (prev === "vertical" ? "horizontal" : "vertical"))
            }
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-bg-elevated hover:bg-border-strong border border-border-subtle text-xs text-text-primary transition-all"
            title="Toggle Split Orientation (Vertical / Horizontal)"
          >
            <Split className="w-3.5 h-3.5 text-accent-brand" />
            <span className="font-mono uppercase text-[10px]">
              {splitOrientation === "vertical" ? "Vertical Split" : "Horizontal Split"}
            </span>
          </button>

          {/* Quick Resets */}
          <div className="hidden sm:flex items-center bg-bg-root border border-border-subtle rounded-lg p-0.5 text-[10px] font-mono">
            <button
              onClick={() => setSplitSize(undefined)}
              className="px-2 py-1 rounded hover:bg-bg-elevated text-text-muted hover:text-text-primary"
            >
              50/50
            </button>
            <button
              onClick={() => setSplitSize(360)}
              className="px-2 py-1 rounded hover:bg-bg-elevated text-text-muted hover:text-text-primary"
            >
              Left 360px
            </button>
          </div>
        </div>
      </header>

      {/* KPI STATS BAR */}
      <section className="border-b border-border-subtle bg-bg-panel-2 px-4 py-2.5 grid grid-cols-2 md:grid-cols-4 gap-3 flex-shrink-0 text-xs">
        <div className="flex items-center justify-between border-r border-border-subtle/50 pr-4">
          <span className="text-[11px] text-text-muted">Screened (24h)</span>
          <span className="font-mono font-bold text-text-primary">1,284,903</span>
        </div>
        <div className="flex items-center justify-between border-r border-border-subtle/50 pr-4">
          <span className="text-[11px] text-text-muted">Block Rate</span>
          <span className="font-mono font-bold text-status-blocked">3.1%</span>
        </div>
        <div className="flex items-center justify-between border-r border-border-subtle/50 pr-4">
          <span className="text-[11px] text-text-muted">P95 Latency</span>
          <span className="font-mono font-bold text-text-primary">412 ms</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-text-muted">RSA-PSS Cleared</span>
          <span className="font-mono font-bold text-status-passed">1,244,760</span>
        </div>
      </section>

      {/* MAIN SPLIT PANE WORKSPACE */}
      <div className="flex-1 min-h-0 relative">
        <SplitPane
          split={splitOrientation}
          minSize={300}
          defaultSize={splitOrientation === "vertical" ? 420 : 320}
          size={splitSize}
          onChange={(sz) => setSplitSize(sz)}
          className="bg-bg-root"
          pane1ClassName="bg-bg-panel-2 border-r border-border-subtle"
          pane2ClassName="bg-bg-root"
        >
          {/* PANE 1: ASSET INGESTION STREAM & LIST */}
          <div className="h-full flex flex-col min-h-0">
            {/* SEARCH & FILTERS */}
            <div className="p-3 border-b border-border-subtle space-y-2.5 flex-shrink-0">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-text-muted absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search assets, hashes..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs bg-bg-root border border-border-subtle rounded-lg text-text-primary placeholder:text-text-faint focus:outline-none focus:border-accent-brand font-mono"
                />
              </div>

              {/* Status Filter Tabs */}
              <div className="flex items-center gap-1 text-[11px]">
                {["ALL", "PASSED", "BLOCKED", "HUMAN_REVIEW"].map((st) => (
                  <button
                    key={st}
                    onClick={() => setFilterStatus(st)}
                    className={`px-2 py-1 rounded font-medium transition-all ${
                      filterStatus === st
                        ? "bg-accent-brand/15 text-accent-brand border border-accent-brand/30"
                        : "text-text-muted hover:text-text-primary hover:bg-bg-elevated"
                    }`}
                  >
                    {st === "HUMAN_REVIEW" ? "REVIEW" : st}
                  </button>
                ))}
              </div>
            </div>

            {/* ASSET LIST */}
            <div className="flex-1 overflow-y-auto divide-y divide-border-subtle/60">
              {filteredAssets.length === 0 ? (
                <div className="p-8 text-center text-xs text-text-faint">
                  No assets match current criteria.
                </div>
              ) : (
                filteredAssets.map((asset) => {
                  const isSelected = asset.id === activeAsset.id;
                  return (
                    <div
                      key={asset.id}
                      onClick={() => setActiveAssetId(asset.id)}
                      className={`p-3 cursor-pointer transition-all flex items-start gap-3 border-l-2 ${
                        isSelected
                          ? "bg-bg-elevated/70 border-l-accent-brand"
                          : "hover:bg-bg-panel/50 border-l-transparent"
                      }`}
                    >
                      <div className="w-8 h-8 rounded bg-bg-root border border-border-subtle flex items-center justify-center flex-shrink-0 mt-0.5">
                        {asset.track === "TEXT" && <FileText className="w-4 h-4 text-accent-brand" />}
                        {asset.track === "IMAGE" && <ImageIcon className="w-4 h-4 text-accent-secondary" />}
                        {asset.track === "CODE" && <Code2 className="w-4 h-4 text-status-review" />}
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-1">
                          <span className="font-semibold text-xs text-text-primary truncate">
                            {asset.name}
                          </span>
                          <span
                            className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${
                              asset.status === "PASSED"
                                ? "bg-status-passed/10 text-status-passed border border-status-passed/20"
                                : asset.status === "BLOCKED"
                                ? "bg-status-blocked/10 text-status-blocked border border-status-blocked/20"
                                : "bg-status-review/10 text-status-review border border-status-review/20"
                            }`}
                          >
                            {asset.status}
                          </span>
                        </div>
                        <div className="text-[10px] font-mono text-text-faint truncate mt-0.5">
                          {asset.hash}
                        </div>
                        <div className="flex items-center justify-between text-[10px] text-text-muted mt-1.5">
                          <span className="font-mono">{asset.id}</span>
                          <span className="font-mono">
                            Risk: {(asset.similarity * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* PANE 2: FORENSIC INSPECTOR & EVIDENCE VAULT */}
          <div className="h-full flex flex-col min-h-0 overflow-y-auto">
            {/* INSPECTOR TOP BAR */}
            <div className="p-4 border-b border-border-subtle bg-bg-panel flex items-center justify-between flex-shrink-0">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-base font-bold text-text-primary">
                    {activeAsset.name}
                  </span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-bg-elevated border border-border-strong text-text-muted">
                    {activeAsset.id}
                  </span>
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-bold flex items-center gap-1 ${
                      activeAsset.status === "PASSED"
                        ? "bg-status-passed/10 text-status-passed border border-status-passed/30"
                        : activeAsset.status === "BLOCKED"
                        ? "bg-status-blocked/10 text-status-blocked border border-status-blocked/30"
                        : "bg-status-review/10 text-status-review border border-status-review/30"
                    }`}
                  >
                    {activeAsset.status === "PASSED" && <ShieldCheck className="w-3.5 h-3.5" />}
                    {activeAsset.status === "BLOCKED" && <ShieldAlert className="w-3.5 h-3.5" />}
                    {activeAsset.status === "HUMAN_REVIEW" && <UserCheck className="w-3.5 h-3.5" />}
                    {activeAsset.status}
                  </span>
                </div>
                <div className="text-xs font-mono text-text-faint mt-1">
                  Content-Addressed Digest: <span className="text-text-muted">{activeAsset.hash}</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyLineage}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-elevated hover:bg-border-strong text-xs font-semibold text-text-primary border border-border-subtle transition-all"
                >
                  <Copy className="w-3.5 h-3.5" />
                  {copied ? "Copied!" : "Copy JSON-LD"}
                </button>
              </div>
            </div>

            {/* FORENSIC CONTENT BODY */}
            <div className="p-6 space-y-6 flex-1">
              {/* Threat Radar / Analysis Row */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-bg-panel border border-border-subtle">
                  <span className="text-xs text-text-muted uppercase font-bold tracking-wider">
                    Pipeline Track
                  </span>
                  <div className="text-lg font-bold text-text-primary mt-1 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-accent-brand" />
                    {activeAsset.track} Track
                  </div>
                  <div className="text-xs text-text-faint mt-1">
                    Bi-Encoder FAISS + Cross-Encoder Gate
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-bg-panel border border-border-subtle">
                  <span className="text-xs text-text-muted uppercase font-bold tracking-wider">
                    Max Similarity Score
                  </span>
                  <div
                    className={`text-lg font-bold font-mono mt-1 ${
                      activeAsset.similarity >= 0.85
                        ? "text-status-blocked"
                        : activeAsset.similarity >= 0.7
                        ? "text-status-review"
                        : "text-status-passed"
                    }`}
                  >
                    {(activeAsset.similarity * 100).toFixed(2)}%
                  </div>
                  <div className="text-xs text-text-faint mt-1">
                    Threshold: Text 0.85 / Image 0.90
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-bg-panel border border-border-subtle">
                  <span className="text-xs text-text-muted uppercase font-bold tracking-wider">
                    Jurisdiction Ruleset
                  </span>
                  <div className="text-lg font-bold text-text-primary mt-1 font-mono">
                    {activeAsset.jurisdiction}
                  </div>
                  <div className="text-xs text-text-faint mt-1">
                    EU DSM Art 4 / US Fair Use compliant
                  </div>
                </div>
              </div>

              {/* SIDE BY SIDE EVIDENCE COMPARISON */}
              {activeAsset.matchedSource ? (
                <div className="p-5 rounded-xl bg-bg-panel border border-border-subtle space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-status-blocked flex items-center gap-1.5">
                      <AlertOctagon className="w-4 h-4" />
                      Detected Copyright Infringement & Crop Evidence
                    </h3>
                    <span className="text-xs font-mono text-text-muted">
                      Source: {activeAsset.matchedSource}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-3 rounded-lg bg-bg-root border border-border-subtle space-y-1">
                      <span className="text-[10px] uppercase font-bold text-text-muted">
                        Ingested Asset Substring
                      </span>
                      <pre className="text-xs font-mono text-status-blocked bg-status-blocked/5 p-2 rounded border border-status-blocked/20 whitespace-pre-wrap">
                        {activeAsset.matchedChunk}
                      </pre>
                    </div>

                    <div className="p-3 rounded-lg bg-bg-root border border-border-subtle space-y-1">
                      <span className="text-[10px] uppercase font-bold text-text-muted">
                        Reference Index Signature Match
                      </span>
                      <pre className="text-xs font-mono text-text-body bg-bg-panel p-2 rounded border border-border-subtle whitespace-pre-wrap">
                        {activeAsset.matchedChunk}
                      </pre>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-5 rounded-xl bg-bg-panel border border-border-subtle flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-status-passed/10 border border-status-passed/20 flex items-center justify-center text-status-passed">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-text-primary">
                      Clean Asset — Zero Infringements Detected
                    </h3>
                    <p className="text-xs text-text-faint mt-0.5">
                      Passed dual-track coarse and fine deep neural filters. Safe for model training and deployment.
                    </p>
                  </div>
                </div>
              )}

              {/* CRYPTOGRAPHIC CERTIFICATE & W3C PROV-O */}
              <div className="p-5 rounded-xl bg-bg-panel border border-border-subtle space-y-4">
                <div className="flex items-center justify-between border-b border-border-subtle pb-3">
                  <div className="flex items-center gap-2">
                    <Award className="w-4 h-4 text-accent-brand" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                      Cryptographic Clearance Certificate (RSASSA-PSS-SHA256)
                    </h3>
                  </div>
                  {activeAsset.signature && (
                    <span className="text-[11px] font-mono text-status-passed bg-status-passed/10 px-2 py-0.5 rounded border border-status-passed/20">
                      Valid Signature Bound to Asset
                    </span>
                  )}
                </div>

                {activeAsset.signature ? (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs text-text-faint">
                      <span>Public Key Fingerprint:</span>
                      <span className="font-mono text-text-primary">{activeAsset.keyFingerprint}</span>
                    </div>
                    <div className="text-xs text-text-faint">
                      <span>Signature (Base64):</span>
                      <pre className="mt-1 p-2 bg-bg-root border border-border-subtle rounded text-[11px] font-mono text-accent-brand truncate select-all">
                        {activeAsset.signature}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-text-faint italic">
                    Certificate was not issued because asset status is {activeAsset.status}.
                  </div>
                )}

                {/* Lineage Graph */}
                <div className="space-y-1.5 pt-2">
                  <span className="text-[10px] uppercase font-bold text-text-muted">
                    W3C PROV-O JSON-LD Provenance Graph
                  </span>
                  <pre className="p-3 bg-bg-root border border-border-subtle rounded-lg text-xs font-mono text-accent-brand overflow-x-auto select-all max-h-48">
                    {JSON.stringify(activeAsset.provLineage, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </SplitPane>
      </div>
    </div>
  );
}
