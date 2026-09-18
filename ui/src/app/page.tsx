import React from "react";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-bg-root text-text-body p-6">
      <header className="flex items-center justify-between border-b border-border-subtle pb-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-accent-brand text-bg-root flex items-center justify-center font-bold">
            T
          </div>
          <div>
            <h1 className="text-lg font-bold text-text-primary">TraceAIOps</h1>
            <p className="text-xs text-text-faint">Security Operations Console</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="px-2 py-0.5 text-xs font-mono rounded bg-accent-brand/10 border border-accent-brand/30 text-accent-brand">
            PROD
          </span>
        </div>
      </header>

      {/* KPI Row */}
      <section className="grid grid-cols-4 gap-4 mb-6">
        <div className="p-4 rounded-lg bg-bg-panel border border-border-subtle">
          <span className="text-xs text-text-muted">ASSETS SCANNED (24H)</span>
          <p className="text-2xl font-bold text-text-primary mt-1">1,284,903</p>
        </div>
        <div className="p-4 rounded-lg bg-bg-panel border border-border-subtle">
          <span className="text-xs text-text-muted">BLOCK RATE</span>
          <p className="text-2xl font-bold text-status-blocked mt-1">3.1%</p>
        </div>
        <div className="p-4 rounded-lg bg-bg-panel border border-border-subtle">
          <span className="text-xs text-text-muted">P95 SCAN LATENCY</span>
          <p className="text-2xl font-bold text-text-primary mt-1">412 ms</p>
        </div>
        <div className="p-4 rounded-lg bg-bg-panel border border-border-subtle">
          <span className="text-xs text-text-muted">CERTIFICATES ISSUED</span>
          <p className="text-2xl font-bold text-status-passed mt-1">1,244,760</p>
        </div>
      </section>

      {/* Main Console Regions */}
      <section className="grid grid-cols-3 gap-6">
        <div className="col-span-2 p-4 rounded-lg bg-bg-panel border border-border-subtle">
          <h2 className="text-sm font-semibold text-text-primary mb-3">Live Scan Stream</h2>
          <div className="text-xs font-mono text-text-muted border border-border-subtle rounded p-3">
            [WebSocket Connected] Listening to /v1/stream...
          </div>
        </div>
        <div className="p-4 rounded-lg bg-bg-panel border border-border-subtle">
          <h2 className="text-sm font-semibold text-text-primary mb-3">Risk Distribution</h2>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-status-passed">Clean (Passed)</span>
              <span>88%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-status-review">Review Band</span>
              <span>9%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-status-blocked">Blocked</span>
              <span>3%</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
