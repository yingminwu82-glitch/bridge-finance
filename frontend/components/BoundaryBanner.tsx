"use client";

import { BOUNDARY_DECLARATION, ILLUSTRATIVE_NOTE } from "@/lib/api";

export function BoundaryBanner({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <div
        className="text-xs px-3 py-2 rounded-lg border"
        style={{
          background: "#fff8e1",
          borderColor: "#f0d060",
          color: "#856404",
        }}
      >
        ⚠ {BOUNDARY_DECLARATION}
      </div>
    );
  }
  return (
    <div className="boundary-banner">
      <div className="flex items-start gap-2">
        <span className="text-base">⚠</span>
        <div>
          <p className="font-semibold">AI 治理边界声明 / AI Governance Boundary</p>
          <p className="mt-1">{BOUNDARY_DECLARATION}</p>
          <p className="illustrative-note mt-1">{ILLUSTRATIVE_NOTE}</p>
        </div>
      </div>
    </div>
  );
}
