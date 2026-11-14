"use client";

import { useState, useEffect, useRef } from "react";
import { apiGet, Transaction, riskClass, formatCurrency } from "@/lib/api";

export default function GraphPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedTx, setSelectedTx] = useState<number>(1);
  const [graphData, setGraphData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [riskResult, setRiskResult] = useState<any>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    apiGet("/api/transactions").then((data) => {
      setTransactions(data.transactions || []);
    });
  }, []);

  useEffect(() => {
    if (!selectedTx) return;
    setLoading(true);
    apiGet(`/api/transactions/${selectedTx}/graph`).then((data) => {
      setGraphData(data);
      setLoading(false);
    });
    apiGet(`/api/transactions/${selectedTx}`).then((data) => {
      setRiskResult(data);
    });
  }, [selectedTx]);

  // Draw graph on canvas
  useEffect(() => {
    if (!graphData || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.clientWidth;
    const h = 420;
    canvas.width = w;
    canvas.height = h;

    ctx.clearRect(0, 0, w, h);

    // Layout nodes in a radial pattern
    const nodes = graphData.nodes || [];
    const edges = graphData.edges || [];
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(w, h) * 0.32;

    const nodePositions: Record<string, { x: number; y: number }> = {};
    const entityNodes = nodes.filter((n: any) => n.data.type !== "document");
    const docNodes = nodes.filter((n: any) => n.data.type === "document");

    // Place enterprise at center
    entityNodes.forEach((node: any, i: number) => {
      if (node.data.type === "enterprise") {
        nodePositions[node.data.id] = { x: cx, y: cy };
      } else {
        const angle = (i / entityNodes.length) * Math.PI * 2 - Math.PI / 2;
        nodePositions[node.data.id] = {
          x: cx + Math.cos(angle) * radius,
          y: cy + Math.sin(angle) * radius,
        };
      }
    });

    // Place documents in outer ring
    docNodes.forEach((node: any, i: number) => {
      const angle = (i / Math.max(docNodes.length, 1)) * Math.PI * 2 - Math.PI / 2;
      const r = radius * 1.5;
      nodePositions[node.data.id] = {
        x: cx + Math.cos(angle) * r,
        y: cy + Math.sin(angle) * r,
      };
    });

    // Draw edges
    edges.forEach((edge: any) => {
      const src = nodePositions[edge.data.source];
      const tgt = nodePositions[edge.data.target];
      if (!src || !tgt) return;

      ctx.beginPath();
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
      ctx.strokeStyle = "#c1c1c8";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Draw label at midpoint
      const mx = (src.x + tgt.x) / 2;
      const my = (src.y + tgt.y) / 2;
      ctx.fillStyle = "#9b9ba3";
      ctx.font = "10px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(edge.data.label, mx, my - 4);
    });

    // Draw nodes
    nodes.forEach((node: any) => {
      const pos = nodePositions[node.data.id];
      if (!pos) return;

      const isEntity = node.data.type !== "document";
      const colors: Record<string, string> = {
        enterprise: "#a91624",
        customer: "#2563eb",
        supplier: "#16a34a",
        bank_account: "#f59e0b",
        logistics: "#8b5cf6",
        financing: "#ec4899",
        document: "#6b6b73",
      };
      const color = colors[node.data.type] || "#6b6b73";

      // Circle
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, isEntity ? 28 : 18, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 3;
      ctx.stroke();

      // Label
      ctx.fillStyle = "#1a1a1a";
      ctx.font = "11px sans-serif";
      ctx.textAlign = "center";
      const label = node.data.label.length > 15
        ? node.data.label.substring(0, 13) + "..."
        : node.data.label;
      ctx.fillText(label, pos.x, pos.y + (isEntity ? 42 : 32));
    });
  }, [graphData]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!graphData || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Find clicked node (approximate hit detection)
    const nodes = graphData.nodes || [];
    // We need positions - recompute
    const w = canvas.clientWidth;
    const h = 420;
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(w, h) * 0.32;
    const entityNodes = nodes.filter((n: any) => n.data.type !== "document");
    const docNodes = nodes.filter((n: any) => n.data.type === "document");

    const positions: Record<string, { x: number; y: number; node: any }> = {};
    entityNodes.forEach((node: any, i: number) => {
      if (node.data.type === "enterprise") {
        positions[node.data.id] = { x: cx, y: cy, node };
      } else {
        const angle = (i / entityNodes.length) * Math.PI * 2 - Math.PI / 2;
        positions[node.data.id] = { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius, node };
      }
    });
    docNodes.forEach((node: any, i: number) => {
      const angle = (i / Math.max(docNodes.length, 1)) * Math.PI * 2 - Math.PI / 2;
      const r = radius * 1.5;
      positions[node.data.id] = { x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r, node };
    });

    for (const id in positions) {
      const pos = positions[id];
      const dist = Math.sqrt((x - pos.x) ** 2 + (y - pos.y) ** 2);
      if (dist < 30) {
        setSelectedNode(pos.node.data);
        return;
      }
    }
    setSelectedNode(null);
  };

  return (
    <div className="fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">交易关系图谱</h1>
        <p className="text-sm text-[#6b6b73]">可视化交易链：企业 → 客户/供应商 → 单据 → 资金流</p>
      </div>

      {/* Transaction selector */}
      <div className="flex gap-2 mb-4 flex-wrap items-center">
        {transactions.map((tx) => (
          <button
            key={tx.id}
            onClick={() => setSelectedTx(tx.id)}
            className={`px-3 py-1.5 rounded-lg text-sm border transition ${
              selectedTx === tx.id
                ? "bg-[#a91624] text-white border-[#a91624]"
                : "bg-white border-[#e5e5e8] hover:border-[#a91624]"
            }`}
          >
            {tx.tx_ref}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Graph canvas */}
        <div className="lg:col-span-2">
          <div className="card">
            {loading ? (
              <div className="py-16 text-center text-[#9b9ba3]">加载图谱中...</div>
            ) : (
              <>
                <canvas
                  ref={canvasRef}
                  onClick={handleCanvasClick}
                  className="w-full cursor-pointer"
                  style={{ height: 420 }}
                />
                <div className="flex gap-3 flex-wrap mt-3 text-xs">
                  {[
                    { c: "#a91624", l: "企业" },
                    { c: "#2563eb", l: "客户" },
                    { c: "#16a34a", l: "供应商" },
                    { c: "#f59e0b", l: "银行账户" },
                    { c: "#8b5cf6", l: "物流" },
                    { c: "#6b6b73", l: "单据" },
                  ].map((item) => (
                    <div key={item.l} className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded-full" style={{ background: item.c }} />
                      <span>{item.l}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Side panel: selected node + risk + completeness */}
        <div className="space-y-4">
          {/* Selected node detail */}
          <div className="card">
            <h3 className="font-bold text-sm mb-2">节点详情</h3>
            {selectedNode ? (
              <div className="space-y-2 text-sm">
                <div><span className="text-[#9b9ba3]">名称：</span>{selectedNode.label}</div>
                <div><span className="text-[#9b9ba3]">类型：</span>{selectedNode.type}</div>
                {selectedNode.role && <div><span className="text-[#9b9ba3]">角色：</span>{selectedNode.role}</div>}
                {selectedNode.doc_type && <div><span className="text-[#9b9ba3]">文档类型：</span>{selectedNode.doc_type}</div>}
              </div>
            ) : (
              <p className="text-xs text-[#9b9ba3]">点击图谱中的节点查看详情</p>
            )}
          </div>

          {/* Completeness & risk */}
          {riskResult && (
            <>
              <div className="card">
                <h3 className="font-bold text-sm mb-2">交易完整度</h3>
                <div className="flex items-center gap-3">
                  <div className="text-3xl font-bold" style={{ color: "#a91624" }}>
                    {riskResult.completeness_score}
                  </div>
                  <div className="text-xs text-[#9b9ba3]">/ 100</div>
                </div>
                {riskResult.documents && (
                  <div className="mt-3 space-y-1">
                    {riskResult.documents.map((d: any) => (
                      <div key={d.id} className="text-xs flex items-center justify-between">
                        <span>{d.doc_type}</span>
                        <span className={d.confirmed ? "text-[#16a34a]" : "text-[#f59e0b]"}>
                          {d.confirmed ? "✓" : "○"}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="card">
                <h3 className="font-bold text-sm mb-2">风险维度</h3>
                <div className="space-y-2">
                  {Object.entries(riskResult.risk_dimensions || {}).map(([dim, level]: [string, any]) => (
                    <div key={dim} className="flex items-center justify-between text-xs">
                      <span>{dim}</span>
                      <span className={`px-2 py-0.5 rounded ${riskClass(level)}`}>{level}</span>
                    </div>
                  ))}
                </div>
                <a
                  href={`/app/cashflow?tx=${selectedTx}`}
                  className="btn-primary btn-sm mt-3 inline-block"
                >
                  查看现金流与风险分析 →
                </a>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
