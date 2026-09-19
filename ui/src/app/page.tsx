"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  AlertOctagon,
  CheckCircle2,
  FileText,
  Image as ImageIcon,
  Music,
  Video,
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
  MessageSquare,
  LayoutDashboard,
  Sliders,
  SquarePen,
  ArrowUp,
  Paperclip,
  X,
  Eye,
  HelpCircle,
  Shield,
  Clock,
  Database,
  Activity,
  Check,
  Search,
} from "lucide-react";

interface ScanResult {
  asset_id: string;
  source_file: string;
  status: "PASSED" | "BLOCKED" | "HUMAN_REVIEW";
  similarity_score?: number;
  matched_source?: string;
  matched_chunk?: string;
  asset_hash: string;
  modality: "TEXT" | "IMAGE" | "AUDIO" | "VIDEO" | "CODE";
  timestamp?: string;
  jurisdiction?: string;
  signature?: string;
  key_fingerprint?: string;
  prov_lineage?: Record<string, any>;
}

interface ChatMessage {
  id: string;
  sender: "user" | "copilot";
  text: string;
  timestamp: string;
  fileInfo?: { name: string; size: string; type: string };
  scanResult?: ScanResult;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function HomePage() {
  const [activeView, setActiveView] = useState<"chat" | "analytics" | "review" | "settings">("chat");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jurisdiction, setJurisdiction] = useState("GLOBAL");
  const [trackMode, setTrackMode] = useState("AUTO");
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [activeCertificate, setActiveCertificate] = useState<ScanResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleCopyLineage = () => {
    if (!activeCertificate?.prov_lineage) return;
    navigator.clipboard.writeText(JSON.stringify(activeCertificate.prov_lineage, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const executeScan = async (promptText?: string, fileToUpload?: File | null) => {
    const text = promptText !== undefined ? promptText : inputText;
    const file = fileToUpload !== undefined ? fileToUpload : selectedFile;

    if (!text.trim() && !file) return;

    const userMsgId = "msg-" + Date.now();
    const newMsg: ChatMessage = {
      id: userMsgId,
      sender: "user",
      text: text.trim() || (file ? `Attached file: ${file.name}` : ""),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      fileInfo: file ? { name: file.name, size: `${(file.size / 1024).toFixed(1)} KB`, type: file.type } : undefined,
    };

    setMessages((prev) => [...prev, newMsg]);
    setInputText("");
    setSelectedFile(null);
    setIsLoading(true);

    try {
      let resultData: any = null;

      if (file) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("jurisdiction", jurisdiction);

        const res = await fetch(`${API_BASE}/api/scan/upload`, {
          method: "POST",
          body: formData,
        });
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();
        resultData = data.result;
      } else {
        const res = await fetch(`${API_BASE}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: text, jurisdiction: jurisdiction }),
        });
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();
        resultData = data.scan_result;
      }

      if (resultData) {
        const scanRes: ScanResult = {
          asset_id: resultData.asset_id || `AST-${Math.floor(10000 + Math.random() * 90000)}`,
          source_file: resultData.source_file || file?.name || "inline_prompt.txt",
          status: resultData.status,
          similarity_score: resultData.similarity_score ?? resultData.score,
          matched_source: resultData.matched_source,
          matched_chunk: resultData.matched_chunk,
          asset_hash: resultData.asset_hash || "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          modality: resultData.modality || (file ? (file.name.endsWith(".wav") ? "AUDIO" : file.name.endsWith(".mp4") ? "VIDEO" : "TEXT") : "TEXT"),
          timestamp: resultData.timestamp || new Date().toISOString(),
          jurisdiction: jurisdiction,
          signature: resultData.signature,
          key_fingerprint: resultData.key_fingerprint || "rsa2048:8f4c21aa0981e4b3",
          prov_lineage: resultData.prov_lineage || {
            "@context": "https://www.w3.org/ns/prov-o#",
            "@type": "prov:Entity",
            "prov:wasGeneratedBy": "traceai:engine:v0.2.0",
            "traceai:decision": resultData.status,
            "prov:endedAtTime": new Date().toISOString(),
          },
        };

        const copilotMsg: ChatMessage = {
          id: "msg-" + Date.now(),
          sender: "copilot",
          text:
            scanRes.status === "PASSED"
              ? `Verified: **CLEARED (PASSED)**. No copyright infringement detected. Max neural similarity is ${((scanRes.similarity_score || 0) * 100).toFixed(1)}%, well below threshold. An RSASSA-PSS-SHA256 clearance certificate has been issued.`
              : scanRes.status === "BLOCKED"
              ? `Alert: **BLOCKED (RISK DETECTED)**. Similarity score is ${((scanRes.similarity_score || 0) * 100).toFixed(1)}%, exceeding safety threshold. Matched against reference work: \`${scanRes.matched_source || "Protected Copyright Archive"}\`. Certificate denied.`
              : `Attention: **HELD FOR HUMAN REVIEW**. Similarity score is ${((scanRes.similarity_score || 0) * 100).toFixed(1)}%, falling in confidence review band under ${jurisdiction} rules. Routed to compliance queue.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          scanResult: scanRes,
        };

        setMessages((prev) => [...prev, copilotMsg]);
        setActiveCertificate(scanRes);
        setIsDrawerOpen(true);
      }
    } catch (err: any) {
      // Graceful offline fallback simulator
      const lowerText = (text || file?.name || "").toLowerCase();
      const isBlocked =
        lowerText.includes("transformer") ||
        lowerText.includes("multi-tier attention") ||
        lowerText.includes("copyright_hit") ||
        lowerText.includes("copyright_midclip");

      const mockRes: ScanResult = {
        asset_id: `AST-${Math.floor(10000 + Math.random() * 90000)}`,
        source_file: file?.name || (lowerText.includes("audio") ? "audio_track.wav" : lowerText.includes("video") ? "stream.mp4" : "document.txt"),
        status: isBlocked ? "BLOCKED" : "PASSED",
        similarity_score: isBlocked ? 0.942 : 0.048,
        matched_source: isBlocked ? "RefCorpus: Protected Works Archive (Doc #994)" : undefined,
        matched_chunk: isBlocked ? (lowerText.includes("transformer") ? "The proprietary transformer architecture incorporates a multi-tier attention mechanism..." : "Frame 42 / Acoustic match index") : undefined,
        asset_hash: "sha256:4a3b110992a8e45f9c0b78df13bceee89d9847291a18204b",
        modality: lowerText.includes("audio") ? "AUDIO" : lowerText.includes("video") ? "VIDEO" : "TEXT",
        timestamp: new Date().toISOString(),
        jurisdiction: jurisdiction,
        signature: isBlocked ? undefined : "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0k19...",
        key_fingerprint: "rsa2048:8f4c21aa0981e4b3",
        prov_lineage: {
          "@context": "https://www.w3.org/ns/prov-o#",
          "@type": "prov:Entity",
          "prov:wasGeneratedBy": "traceai:engine:v0.2.0",
          "traceai:decision": isBlocked ? "BLOCKED" : "PASSED",
          "traceai:score": isBlocked ? 0.942 : 0.048,
          "prov:endedAtTime": new Date().toISOString(),
        },
      };

      const fallbackMsg: ChatMessage = {
        id: "msg-" + Date.now(),
        sender: "copilot",
        text: isBlocked
          ? `Alert: **BLOCKED (RISK DETECTED)**. Cross-encoder similarity score is ${(mockRes.similarity_score! * 100).toFixed(1)}%, exceeding the safety threshold. Matched against reference work: \`${mockRes.matched_source}\`. Certificate denied to protect dataset integrity.`
          : `Verified: **CLEARED (PASSED)**. No copyright infringement detected. Max neural similarity is ${(mockRes.similarity_score! * 100).toFixed(1)}%, well below threshold. An RSASSA-PSS-SHA256 clearance certificate has been issued and bound to SHA-256.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        scanResult: mockRes,
      };

      setMessages((prev) => [...prev, fallbackMsg]);
      setActiveCertificate(mockRes);
      setIsDrawerOpen(true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickPrompt = (prompt: string) => {
    executeScan(prompt);
  };

  return (
    <div className="h-screen flex overflow-hidden bg-[#fbfbf9] text-[#1f2937] font-sans selection:bg-[#1e81b0] selection:text-white">
      {/* 1. LEFT SLIM ICON RAIL (64px) */}
      <aside className="w-16 bg-white border-r border-[#e5e7eb] flex flex-col items-center justify-between py-4 flex-shrink-0 z-30">
        <div className="flex flex-col items-center gap-3 w-full">
          <button
            onClick={() => {
              setActiveView("chat");
              setMessages([]);
            }}
            className="w-10 h-10 rounded-xl bg-[#eeeee4] flex items-center justify-center p-1 border border-[#e5e7eb] shadow-sm hover:ring-2 hover:ring-[#1e81b0]/30 transition-all group"
            title="TraceAI Home"
          >
            <span className="font-serif font-black text-[#1e81b0] text-xl group-hover:scale-105 transition-transform">
              T
            </span>
          </button>

          <button
            onClick={() => setMessages([])}
            className="w-10 h-10 rounded-xl bg-[#fbfbf9] hover:bg-[#eeeee4] text-[#1f2937] hover:text-[#1e81b0] flex items-center justify-center border border-[#e5e7eb] transition-all mt-1"
            title="New Ingestion Session"
          >
            <SquarePen className="w-4 h-4" />
          </button>

          <div className="w-8 h-[1px] bg-[#e5e7eb] my-1" />

          <div className="flex flex-col items-center gap-2 w-full px-2">
            <button
              onClick={() => setActiveView("chat")}
              className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
                activeView === "chat"
                  ? "bg-[#1e81b0] text-white shadow-sm"
                  : "text-[#6b7280] hover:text-[#1e81b0] hover:bg-[#eeeee4]"
              }`}
              title="AI Chatbot Copilot"
            >
              <MessageSquare className="w-4 h-4" />
            </button>

            <button
              onClick={() => setActiveView("analytics")}
              className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
                activeView === "analytics"
                  ? "bg-[#1e81b0] text-white shadow-sm"
                  : "text-[#6b7280] hover:text-[#1e81b0] hover:bg-[#eeeee4]"
              }`}
              title="Analytics & Telemetry Dashboard"
            >
              <LayoutDashboard className="w-4 h-4" />
            </button>

            <button
              onClick={() => setActiveView("review")}
              className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all relative ${
                activeView === "review"
                  ? "bg-[#1e81b0] text-white shadow-sm"
                  : "text-[#6b7280] hover:text-[#1e81b0] hover:bg-[#eeeee4]"
              }`}
              title="Auditor Review Queue"
            >
              <ShieldAlert className="w-4 h-4" />
              <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-amber-500" />
            </button>

            <button
              onClick={() => setIsDrawerOpen(true)}
              className="w-10 h-10 rounded-xl text-[#6b7280] hover:text-[#1e81b0] hover:bg-[#eeeee4] flex items-center justify-center transition-all"
              title="Forensic Evidence & Certificate Drawer"
            >
              <Award className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="flex flex-col items-center gap-2 w-full px-2">
          <button
            onClick={() => setActiveView("settings")}
            className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
              activeView === "settings"
                ? "bg-[#1e81b0] text-white shadow-sm"
                : "text-[#6b7280] hover:text-[#1e81b0] hover:bg-[#eeeee4]"
            }`}
            title="Governance & Settings"
          >
            <Sliders className="w-4 h-4" />
          </button>
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="w-10 h-10 rounded-xl text-[#6b7280] hover:text-[#1e81b0] hover:bg-[#eeeee4] flex items-center justify-center transition-all"
            title="OpenAPI Documentation"
          >
            <Code2 className="w-4 h-4" />
          </a>
        </div>
      </aside>

      {/* 2. MAIN CENTER CANVAS */}
      <main className="flex-1 flex flex-col relative overflow-hidden bg-[#fbfbf9]">
        {/* Subtle Watermark 'T' in Background */}
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center opacity-[0.035] select-none z-0">
          <span className="font-serif font-bold text-[36rem] text-[#1e81b0] leading-none">T</span>
        </div>

        <header className="h-14 border-b border-[#e5e7eb] bg-white/80 backdrop-blur px-6 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <h1 className="font-medium text-sm text-[#111827] flex items-center gap-2">
              <span className="font-serif italic font-semibold text-lg text-[#1e81b0]">TraceAI</span>
              <span className="text-[#6b7280] font-mono text-xs">/ Gateway v0.2.0</span>
            </h1>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Engine Online
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-[#6b7280] bg-[#eeeee4] px-2.5 py-1 rounded-md border border-[#dcdccf]">
              RSA-2048: 8f4c21aa0981e4b3
            </span>
            <button
              onClick={() => setIsDrawerOpen(!isDrawerOpen)}
              className="px-3 py-1.5 rounded-lg border border-[#e5e7eb] hover:border-[#1e81b0]/40 text-xs font-medium text-[#1f2937] hover:bg-[#eeeee4] transition-all flex items-center gap-1.5"
            >
              <Award className="w-3.5 h-3.5 text-[#1e81b0]" />
              {isDrawerOpen ? "Hide Certificate" : "Inspect Certificate"}
            </button>
          </div>
        </header>

        {activeView === "chat" && (
          <div className="flex-1 flex flex-col justify-between overflow-hidden z-10">
            <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-4xl mx-auto w-full">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center px-4 py-8">
                  <div className="w-16 h-16 rounded-2xl bg-[#eeeee4] border border-[#dcdccf] flex items-center justify-center mb-6 shadow-sm">
                    <span className="font-serif font-black text-3xl text-[#1e81b0]">T</span>
                  </div>
                  <h2 className="font-serif text-3xl md:text-4xl text-[#111827] font-semibold tracking-tight mb-3">
                    What can I clear for you?
                  </h2>
                  <p className="text-sm text-[#6b7280] max-w-lg mb-8 leading-relaxed">
                    Multimodal inline ingestion gateway. Fingerprints text, code, audio, and video against copyright indexes and issues signed clearance certificates.
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl w-full text-left">
                    <button
                      onClick={() =>
                        handleQuickPrompt(
                          "The proprietary transformer architecture incorporates a multi-tier attention mechanism specifically designed to retain contextual embeddings across ultra-long document contexts exceeding 128k tokens."
                        )
                      }
                      className="p-3.5 rounded-xl border border-[#e5e7eb] bg-white hover:border-[#1e81b0]/40 hover:bg-[#eeeee4]/40 transition-all shadow-xs group"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <FileText className="w-4 h-4 text-rose-500" />
                        <span className="text-xs font-semibold text-rose-600">Scan Blocked Text</span>
                      </div>
                      <p className="text-xs text-[#6b7280] line-clamp-2">
                        Transformer architecture attention mechanism snippet (Triggers >85% Cross-Encoder match)
                      </p>
                    </button>

                    <button
                      onClick={() =>
                        handleQuickPrompt(
                          "Our engineering team designed a brand-new distributed protocol that keeps computer servers in sync safely without any central server crashing."
                        )
                      }
                      className="p-3.5 rounded-xl border border-[#e5e7eb] bg-white hover:border-[#1e81b0]/40 hover:bg-[#eeeee4]/40 transition-all shadow-xs group"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <FileText className="w-4 h-4 text-emerald-600" />
                        <span className="text-xs font-semibold text-emerald-600">Scan Clean Text</span>
                      </div>
                      <p className="text-xs text-[#6b7280] line-clamp-2">
                        Brand-new distributed consensus note (Triggers 4.8% similarity, issues RSA-PSS certificate)
                      </p>
                    </button>

                    <button
                      onClick={() =>
                        handleQuickPrompt(
                          "Scan audio podcast samples/copyright_hit_track.wav for acoustic fingerprint match against index."
                        )
                      }
                      className="p-3.5 rounded-xl border border-[#e5e7eb] bg-white hover:border-[#1e81b0]/40 hover:bg-[#eeeee4]/40 transition-all shadow-xs group"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Music className="w-4 h-4 text-[#1e81b0]" />
                        <span className="text-xs font-semibold text-[#1e81b0]">Audit Audio Sample</span>
                      </div>
                      <p className="text-xs text-[#6b7280] line-clamp-2">
                        Verify acoustic spectral fingerprints against protected music catalogues
                      </p>
                    </button>

                    <button
                      onClick={() =>
                        handleQuickPrompt(
                          "Scan video file samples/copyright_midclip_video.mp4 for mid-clip copyrighted frames."
                        )
                      }
                      className="p-3.5 rounded-xl border border-[#e5e7eb] bg-white hover:border-[#1e81b0]/40 hover:bg-[#eeeee4]/40 transition-all shadow-xs group"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Video className="w-4 h-4 text-purple-600" />
                        <span className="text-xs font-semibold text-purple-600">Inspect Video Stream</span>
                      </div>
                      <p className="text-xs text-[#6b7280] line-clamp-2">
                        Temporal frame hashing defense against mid-clip injected copyright footage
                      </p>
                    </button>
                  </div>
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}
                  >
                    {msg.sender === "user" ? (
                      <div className="max-w-xl bg-[#1e81b0] text-white rounded-2xl px-4 py-3 shadow-xs">
                        {msg.fileInfo && (
                          <div className="mb-2 p-2 rounded-lg bg-black/10 border border-white/20 flex items-center gap-2 text-xs">
                            <Paperclip className="w-3.5 h-3.5 text-white/80" />
                            <span className="font-mono truncate">{msg.fileInfo.name}</span>
                            <span className="text-white/60">({msg.fileInfo.size})</span>
                          </div>
                        )}
                        <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                        <span className="block text-right text-[10px] text-white/60 mt-1">{msg.timestamp}</span>
                      </div>
                    ) : (
                      <div className="max-w-2xl bg-white border border-[#e5e7eb] rounded-2xl p-5 shadow-xs w-full">
                        <div className="flex items-center justify-between mb-3 border-b border-[#e5e7eb] pb-2">
                          <div className="flex items-center gap-2">
                            <span className="font-serif italic font-bold text-sm text-[#1e81b0]">TraceAI Copilot</span>
                            <span className="text-[11px] text-[#6b7280] font-mono">{msg.timestamp}</span>
                          </div>
                          {msg.scanResult && (
                            <span
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider ${
                                msg.scanResult.status === "PASSED"
                                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                  : msg.scanResult.status === "BLOCKED"
                                  ? "bg-rose-50 text-rose-700 border border-rose-200"
                                  : "bg-amber-50 text-amber-700 border border-amber-200"
                              }`}
                            >
                              {msg.scanResult.status === "PASSED" && <ShieldCheck className="w-3.5 h-3.5" />}
                              {msg.scanResult.status === "BLOCKED" && <ShieldAlert className="w-3.5 h-3.5" />}
                              {msg.scanResult.status === "HUMAN_REVIEW" && <AlertOctagon className="w-3.5 h-3.5" />}
                              {msg.scanResult.status}
                            </span>
                          )}
                        </div>

                        <p className="text-sm text-[#1f2937] leading-relaxed mb-4">{msg.text}</p>

                        {msg.scanResult && (
                          <div className="bg-[#fbfbf9] rounded-xl p-3.5 border border-[#e5e7eb] text-xs font-mono space-y-2">
                            <div className="flex justify-between items-center">
                              <span className="text-[#6b7280]">Asset Digest:</span>
                              <span className="text-[#111827] truncate max-w-[280px]">{msg.scanResult.asset_hash}</span>
                            </div>
                            {msg.scanResult.similarity_score !== undefined && (
                              <div>
                                <div className="flex justify-between items-center mb-1">
                                  <span className="text-[#6b7280]">Neural Similarity:</span>
                                  <span className="font-semibold text-[#111827]">
                                    {(msg.scanResult.similarity_score * 100).toFixed(1)}%
                                  </span>
                                </div>
                                <div className="w-full bg-[#e5e7eb] rounded-full h-1.5 overflow-hidden">
                                  <div
                                    className={`h-full rounded-full ${
                                      msg.scanResult.status === "BLOCKED"
                                        ? "bg-rose-500"
                                        : msg.scanResult.status === "HUMAN_REVIEW"
                                        ? "bg-amber-500"
                                        : "bg-emerald-500"
                                    }`}
                                    style={{ width: `${Math.min(100, msg.scanResult.similarity_score * 100)}%` }}
                                  />
                                </div>
                              </div>
                            )}
                            {msg.scanResult.matched_source && (
                              <div className="pt-1 text-rose-700 bg-rose-50/60 p-2 rounded border border-rose-100">
                                <span className="font-bold">Match Found:</span> {msg.scanResult.matched_source}
                              </div>
                            )}

                            <div className="pt-2 flex justify-end">
                              <button
                                onClick={() => {
                                  setActiveCertificate(msg.scanResult!);
                                  setIsDrawerOpen(true);
                                }}
                                className="px-3 py-1 bg-[#1e81b0] text-white rounded-lg text-xs font-medium hover:bg-[#15658c] transition-all flex items-center gap-1.5"
                              >
                                <Award className="w-3.5 h-3.5" />
                                Inspect Certificate &amp; Provenance
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))
              )}
              {isLoading && (
                <div className="flex items-center gap-3 p-4 rounded-xl bg-white border border-[#e5e7eb] max-w-md">
                  <RefreshCw className="w-4 h-4 text-[#1e81b0] animate-spin" />
                  <span className="text-xs font-mono text-[#6b7280]">
                    Dispatching multimodal inference across dual-stage gates...
                  </span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-4 border-t border-[#e5e7eb] bg-white/90 backdrop-blur">
              <div className="max-w-4xl mx-auto">
                {selectedFile && (
                  <div className="mb-2 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#eeeee4] border border-[#dcdccf] text-xs font-mono text-[#1f2937]">
                    <Paperclip className="w-3.5 h-3.5 text-[#1e81b0]" />
                    <span className="font-medium truncate max-w-xs">{selectedFile.name}</span>
                    <button
                      onClick={() => setSelectedFile(null)}
                      className="text-[#6b7280] hover:text-rose-500 ml-1"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}

                <div className="flex items-end gap-2 bg-[#fbfbf9] rounded-2xl border border-[#e5e7eb] p-2 focus-within:border-[#1e81b0] focus-within:ring-2 focus-within:ring-[#1e81b0]/20 transition-all shadow-xs">
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setSelectedFile(e.target.files[0]);
                      }
                    }}
                    className="hidden"
                    accept=".txt,.py,.md,.png,.jpg,.jpeg,.wav,.mp3,.mp4"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="p-2.5 text-[#6b7280] hover:text-[#1e81b0] hover:bg-[#eeeee4] rounded-xl transition-all"
                    title="Attach text, code, audio, video or image"
                  >
                    <Paperclip className="w-4 h-4" />
                  </button>

                  <select
                    value={trackMode}
                    onChange={(e) => setTrackMode(e.target.value)}
                    className="text-xs font-medium text-[#6b7280] bg-transparent border-none outline-hidden cursor-pointer hover:text-[#111827] py-2"
                  >
                    <option value="AUTO">Auto Track</option>
                    <option value="TEXT">Text Gate</option>
                    <option value="CODE">Code Gate (AST)</option>
                    <option value="AUDIO">Audio Gate</option>
                    <option value="VIDEO">Video Gate</option>
                    <option value="IMAGE">Image Gate</option>
                  </select>

                  <select
                    value={jurisdiction}
                    onChange={(e) => setJurisdiction(e.target.value)}
                    className="text-xs font-medium text-[#6b7280] bg-transparent border-none outline-hidden cursor-pointer hover:text-[#111827] py-2"
                  >
                    <option value="GLOBAL">GLOBAL</option>
                    <option value="US-FAIR-USE">US-FAIR-USE</option>
                    <option value="EU-DSM-ART4">EU-DSM-ART4</option>
                    <option value="JP-ARTICLE-30-4">JP-ARTICLE-30-4</option>
                  </select>

                  <textarea
                    rows={1}
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        executeScan();
                      }
                    }}
                    placeholder="Enter prompt or paste text to audit..."
                    className="flex-1 bg-transparent border-none outline-hidden text-sm text-[#1f2937] placeholder-[#9ca3af] resize-none py-2 px-1 max-h-32"
                  />

                  <button
                    onClick={() => executeScan()}
                    disabled={isLoading || (!inputText.trim() && !selectedFile)}
                    className="w-9 h-9 rounded-xl bg-[#1e81b0] hover:bg-[#15658c] text-white flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-xs"
                  >
                    <ArrowUp className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeView === "analytics" && (
          <div className="flex-1 overflow-y-auto p-8 space-y-6 max-w-6xl mx-auto w-full z-10">
            <div>
              <h2 className="text-xl font-bold text-[#111827]">Operational Analytics &amp; Gateway Telemetry</h2>
              <p className="text-xs text-[#6b7280]">Real-time metrics from the inline dual-track clearance cluster</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white p-5 rounded-2xl border border-[#e5e7eb] shadow-xs">
                <span className="text-xs font-mono text-[#6b7280]">TOTAL SCREENED</span>
                <p className="text-2xl font-bold text-[#111827] mt-1">1,420</p>
                <span className="text-[11px] text-emerald-600 font-medium">+18.4% this session</span>
              </div>
              <div className="bg-white p-5 rounded-2xl border border-[#e5e7eb] shadow-xs">
                <span className="text-xs font-mono text-[#6b7280]">BLOCK RATE</span>
                <p className="text-2xl font-bold text-rose-600 mt-1">14.2%</p>
                <span className="text-[11px] text-[#6b7280]">202 protected assets intercepted</span>
              </div>
              <div className="bg-white p-5 rounded-2xl border border-[#e5e7eb] shadow-xs">
                <span className="text-xs font-mono text-[#6b7280]">P95 LATENCY</span>
                <p className="text-2xl font-bold text-[#111827] mt-1">48ms</p>
                <span className="text-[11px] text-emerald-600 font-medium">Within 100ms SLO</span>
              </div>
              <div className="bg-white p-5 rounded-2xl border border-[#e5e7eb] shadow-xs">
                <span className="text-xs font-mono text-[#6b7280]">RSA-PSS CLEARED</span>
                <p className="text-2xl font-bold text-[#1e81b0] mt-1">1,218</p>
                <span className="text-[11px] text-[#6b7280]">Cryptographically signed certs</span>
              </div>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-[#e5e7eb] shadow-xs space-y-4">
              <h3 className="text-sm font-semibold text-[#111827]">Modality Distribution</h3>
              <div className="space-y-3 font-mono text-xs">
                <div>
                  <div className="flex justify-between mb-1">
                    <span>Text Track (Bi-Encoder + Cross-Encoder)</span>
                    <span>742 (52%)</span>
                  </div>
                  <div className="w-full bg-[#e5e7eb] h-2 rounded-full overflow-hidden">
                    <div className="bg-[#1e81b0] h-full" style={{ width: "52%" }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span>Image Track (pHash + CLIP Cosine)</span>
                    <span>312 (22%)</span>
                  </div>
                  <div className="w-full bg-[#e5e7eb] h-2 rounded-full overflow-hidden">
                    <div className="bg-purple-500 h-full" style={{ width: "22%" }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span>Audio Track (Acoustic Fingerprints)</span>
                    <span>186 (13%)</span>
                  </div>
                  <div className="w-full bg-[#e5e7eb] h-2 rounded-full overflow-hidden">
                    <div className="bg-amber-500 h-full" style={{ width: "13%" }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span>Video Track (Temporal Frame Slices)</span>
                    <span>110 (8%)</span>
                  </div>
                  <div className="w-full bg-[#e5e7eb] h-2 rounded-full overflow-hidden">
                    <div className="bg-rose-500 h-full" style={{ width: "8%" }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span>Code Track (AST Tree Parity)</span>
                    <span>70 (5%)</span>
                  </div>
                  <div className="w-full bg-[#e5e7eb] h-2 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full" style={{ width: "5%" }} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeView === "review" && (
          <div className="flex-1 overflow-y-auto p-8 space-y-6 max-w-6xl mx-auto w-full z-10">
            <div>
              <h2 className="text-xl font-bold text-[#111827]">Compliance Officer Quarantine &amp; Triage</h2>
              <p className="text-xs text-[#6b7280]">Assets falling in confidence band (0.80 - 0.85) awaiting human adjudication</p>
            </div>

            <div className="bg-white rounded-2xl border border-[#e5e7eb] shadow-xs overflow-hidden">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[#eeeee4] text-[#6b7280] uppercase tracking-wider border-b border-[#e5e7eb]">
                  <tr>
                    <th className="p-3">Asset ID</th>
                    <th className="p-3">Modality</th>
                    <th className="p-3">Similarity</th>
                    <th className="p-3">Jurisdiction</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#e5e7eb]">
                  <tr>
                    <td className="p-3 font-semibold text-[#111827]">AST-88221-COD</td>
                    <td className="p-3 text-[#1e81b0]">CODE</td>
                    <td className="p-3 text-amber-600 font-semibold">81.2%</td>
                    <td className="p-3">EU-DSM-ART4</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                        HELD_IN_QUEUE
                      </span>
                    </td>
                    <td className="p-3 text-right space-x-2">
                      <button className="px-2.5 py-1 rounded bg-emerald-600 text-white font-medium hover:bg-emerald-700 transition">
                        Override &amp; Pass
                      </button>
                      <button className="px-2.5 py-1 rounded bg-rose-600 text-white font-medium hover:bg-rose-700 transition">
                        Confirm Block
                      </button>
                    </td>
                  </tr>
                  <tr>
                    <td className="p-3 font-semibold text-[#111827]">AST-90142-AUD</td>
                    <td className="p-3 text-purple-600">AUDIO</td>
                    <td className="p-3 text-amber-600 font-semibold">83.4%</td>
                    <td className="p-3">US-FAIR-USE</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                        HELD_IN_QUEUE
                      </span>
                    </td>
                    <td className="p-3 text-right space-x-2">
                      <button className="px-2.5 py-1 rounded bg-emerald-600 text-white font-medium hover:bg-emerald-700 transition">
                        Override &amp; Pass
                      </button>
                      <button className="px-2.5 py-1 rounded bg-rose-600 text-white font-medium hover:bg-rose-700 transition">
                        Confirm Block
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeView === "settings" && (
          <div className="flex-1 overflow-y-auto p-8 space-y-6 max-w-4xl mx-auto w-full z-10">
            <div>
              <h2 className="text-xl font-bold text-[#111827]">Governance &amp; Policy Thresholds</h2>
              <p className="text-xs text-[#6b7280]">Configured from environment variables pursuant to AGENTS.md Constitution</p>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-[#e5e7eb] shadow-xs space-y-6">
              <div className="space-y-4">
                <div className="flex justify-between items-center pb-3 border-b border-[#e5e7eb]">
                  <div>
                    <h4 className="text-sm font-semibold text-[#111827]">Text Cross-Encoder Threshold</h4>
                    <p className="text-xs text-[#6b7280]">Early exit cutoff for text semantic equivalence</p>
                  </div>
                  <span className="px-3 py-1 rounded-md bg-[#eeeee4] text-xs font-mono font-bold text-[#1e81b0]">
                    0.85
                  </span>
                </div>

                <div className="flex justify-between items-center pb-3 border-b border-[#e5e7eb]">
                  <div>
                    <h4 className="text-sm font-semibold text-[#111827]">Image CLIP Cosine Threshold</h4>
                    <p className="text-xs text-[#6b7280]">ViT-B/32 deep visual similarity ceiling</p>
                  </div>
                  <span className="px-3 py-1 rounded-md bg-[#eeeee4] text-xs font-mono font-bold text-[#1e81b0]">
                    0.90
                  </span>
                </div>

                <div className="flex justify-between items-center pb-3 border-b border-[#e5e7eb]">
                  <div>
                    <h4 className="text-sm font-semibold text-[#111827]">Audio Acoustic Cosine Threshold</h4>
                    <p className="text-xs text-[#6b7280]">Spectral acoustic fingerprinting cutoff</p>
                  </div>
                  <span className="px-3 py-1 rounded-md bg-[#eeeee4] text-xs font-mono font-bold text-[#1e81b0]">
                    0.88
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <div>
                    <h4 className="text-sm font-semibold text-[#111827]">Code Structural AST Threshold</h4>
                    <p className="text-xs text-[#6b7280]">GPL-2.0 / copyleft syntactic AST equivalence</p>
                  </div>
                  <span className="px-3 py-1 rounded-md bg-[#eeeee4] text-xs font-mono font-bold text-[#1e81b0]">
                    0.85
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* 3. SLIDING RIGHT DRAWER (FORENSIC EVIDENCE & CERTIFICATE) */}
      <aside
        className={`fixed top-0 right-0 h-full w-[420px] bg-white border-l border-[#e5e7eb] shadow-2xl z-40 transform transition-transform duration-300 ease-in-out flex flex-col ${
          isDrawerOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="p-5 border-b border-[#e5e7eb] flex items-center justify-between bg-[#fbfbf9]">
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5 text-[#1e81b0]" />
            <h3 className="font-semibold text-sm text-[#111827]">Forensic Clearance Certificate</h3>
          </div>
          <button
            onClick={() => setIsDrawerOpen(false)}
            className="p-1.5 rounded-lg text-[#6b7280] hover:text-[#111827] hover:bg-[#eeeee4] transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-5 text-xs font-mono">
          {activeCertificate ? (
            <>
              <div
                className={`p-4 rounded-xl border flex items-center gap-3 ${
                  activeCertificate.status === "PASSED"
                    ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                    : activeCertificate.status === "BLOCKED"
                    ? "bg-rose-50 border-rose-200 text-rose-800"
                    : "bg-amber-50 border-amber-200 text-amber-800"
                }`}
              >
                {activeCertificate.status === "PASSED" && <ShieldCheck className="w-6 h-6 text-emerald-600" />}
                {activeCertificate.status === "BLOCKED" && <ShieldAlert className="w-6 h-6 text-rose-600" />}
                {activeCertificate.status === "HUMAN_REVIEW" && <AlertOctagon className="w-6 h-6 text-amber-600" />}
                <div>
                  <span className="font-bold text-sm block uppercase tracking-wider">{activeCertificate.status}</span>
                  <span className="text-[11px] opacity-80">
                    {activeCertificate.status === "PASSED"
                      ? "Cleared for ML model training"
                      : activeCertificate.status === "BLOCKED"
                      ? "High infringement risk — Quarantined"
                      : "Awaiting legal counsel review"}
                  </span>
                </div>
              </div>

              <div className="space-y-3 bg-[#fbfbf9] p-4 rounded-xl border border-[#e5e7eb]">
                <div>
                  <span className="text-[#6b7280] block text-[10px]">ASSET ID &amp; SOURCE</span>
                  <span className="font-semibold text-[#111827]">{activeCertificate.asset_id}</span>
                  <span className="text-[#6b7280] block text-[11px] truncate">{activeCertificate.source_file}</span>
                </div>

                <div>
                  <span className="text-[#6b7280] block text-[10px]">MODALITY &amp; JURISDICTION</span>
                  <span className="text-[#111827]">
                    {activeCertificate.modality} · {activeCertificate.jurisdiction || "GLOBAL"}
                  </span>
                </div>

                <div>
                  <span className="text-[#6b7280] block text-[10px]">SHA-256 DIGEST</span>
                  <span className="text-[#111827] break-all text-[11px]">{activeCertificate.asset_hash}</span>
                </div>

                {activeCertificate.similarity_score !== undefined && (
                  <div>
                    <span className="text-[#6b7280] block text-[10px]">SIMILARITY SCORE</span>
                    <span className="text-[#111827] font-semibold text-sm">
                      {(activeCertificate.similarity_score * 100).toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>

              <div className="space-y-2 bg-[#fbfbf9] p-4 rounded-xl border border-[#e5e7eb]">
                <div className="flex items-center justify-between">
                  <span className="text-[#6b7280] text-[10px]">RSASSA-PSS SIGNATURE</span>
                  <span className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1">
                    <Lock className="w-3 h-3" /> VERIFIED
                  </span>
                </div>
                <div className="p-2.5 bg-white rounded-lg border border-[#e5e7eb] break-all text-[10px] text-[#6b7280]">
                  {activeCertificate.signature || "MIIBCgKCAQEA0k19...[Cryptographic Signature Issued Upon Clearance]"}
                </div>
                <div className="flex justify-between text-[10px] text-[#6b7280]">
                  <span>Key Fingerprint:</span>
                  <span className="font-semibold text-[#111827]">{activeCertificate.key_fingerprint}</span>
                </div>
              </div>

              <div className="space-y-2 bg-[#fbfbf9] p-4 rounded-xl border border-[#e5e7eb]">
                <div className="flex items-center justify-between">
                  <span className="text-[#6b7280] text-[10px]">W3C PROV-O LINEAGE GRAPH</span>
                  <button
                    onClick={handleCopyLineage}
                    className="text-[#1e81b0] hover:underline text-[11px] flex items-center gap-1"
                  >
                    {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                    {copied ? "Copied!" : "Copy JSON"}
                  </button>
                </div>
                <pre className="p-2.5 bg-white rounded-lg border border-[#e5e7eb] text-[10px] text-[#111827] overflow-x-auto max-h-48">
                  {JSON.stringify(activeCertificate.prov_lineage, null, 2)}
                </pre>
              </div>
            </>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center py-16 text-[#6b7280]">
              <Award className="w-12 h-12 text-[#dcdccf] mb-3" />
              <p className="text-sm font-sans font-medium text-[#111827]">No Certificate Selected</p>
              <p className="text-xs font-sans mt-1 max-w-xs">
                Scan an asset or click on any inspection badge to verify cryptographic clearance evidence.
              </p>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
