"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiGet, formatCurrency, riskClass, Enterprise, Transaction } from "@/lib/api";

export default function DashboardPage() {
  const [enterprises, setEnterprises] = useState<Enterprise[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedEnt, setSelectedEnt] = useState<number>(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiGet("/api/enterprises"),
      apiGet("/api/transactions"),
    ]).then(([entData, txData]) => {
      setEnterprises(entData.enterprises || []);
      setTransactions(txData.transactions || []);
      setLoading(false);
    });
  }, []);

  const entTxns = transactions.filter((t) => t.enterprise_id === selectedEnt);

  if (loading) return <div className="py-20 text-center text-[#9b9ba3]">加载中...</div>;

  return (
    <div className="fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">企业端首页</h1>
        <p className="text-sm text-[#6b6b73]">查看企业交易概况、风险状态与融资需求</p>
      </div>

      {/* Enterprise selector */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {enterprises.map((e) => (
          <button
            key={e.id}
            onClick={() => setSelectedEnt(e.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium border transition ${
              selectedEnt === e.id
                ? "bg-[#a91624] text-white border-[#a91624]"
                : "bg-white border-[#e5e5e8] hover:border-[#a91624]"
            }`}
          >
            {e.name}
          </button>
        ))}
      </div>

      {/* Enterprise info */}
      {enterprises.filter((e) => e.id === selectedEnt).map((ent) => (
        <div key={ent.id} className="card mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-xs text-[#9b9ba3] mb-1">区域</div>
              <div className="font-medium">{ent.region}</div>
            </div>
            <div>
              <div className="text-xs text-[#9b9ba3] mb-1">行业</div>
              <div className="font-medium">{ent.industry}</div>
            </div>
            <div>
              <div className="text-xs text-[#9b9ba3] mb-1">主要币种</div>
              <div className="font-medium">{ent.main_currencies}</div>
            </div>
            <div>
              <div className="text-xs text-[#9b9ba3] mb-1">主要供应商地区</div>
              <div className="font-medium text-sm">{ent.region === "Hong Kong" ? "大湾区 (深圳、东莞)" : "Greater Bay Area"}</div>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-[#e5e5e8]">
            <div className="text-xs text-[#9b9ba3] mb-1">经营模式</div>
            <p className="text-sm text-[#6b6b73]">{ent.business_model}</p>
          </div>
        </div>
      ))}

      {/* Transaction cards */}
      <h2 className="text-lg font-bold mb-4">交易概览</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {entTxns.map((tx) => (
          <div key={tx.id} className="card hover:shadow-lg transition cursor-pointer">
            <Link href={`/app/documents?tx=${tx.id}`} className="block">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="font-semibold text-sm">{tx.tx_ref}</div>
                  <div className="text-xs text-[#9b9ba3] mt-1">
                    买家: {tx.buyer}
                  </div>
                  <div className="text-xs text-[#9b9ba3]">
                    供应商: {tx.supplier}
                  </div>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-medium ${riskClass(tx.overall_risk || "Low")}`}>
                  {tx.overall_risk || "Low"} Risk
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3 text-sm mb-3">
                <div>
                  <div className="text-xs text-[#9b9ba3]">订单金额</div>
                  <div className="font-medium">{formatCurrency(tx.order_amount, tx.order_currency)}</div>
                </div>
                <div>
                  <div className="text-xs text-[#9b9ba3]">发票金额</div>
                  <div className="font-medium">{formatCurrency(tx.invoice_amount, tx.invoice_currency)}</div>
                </div>
                <div>
                  <div className="text-xs text-[#9b9ba3]">完整度</div>
                  <div className="font-medium">{tx.completeness_score}/100</div>
                </div>
              </div>

              <div className="flex gap-2 text-xs">
                <span className="px-2 py-0.5 rounded bg-[#f7f7f8] text-[#6b6b73]">
                  物流: {tx.logistics_status}
                </span>
                <span className="px-2 py-0.5 rounded bg-[#f7f7f8] text-[#6b6b73]">
                  状态: {tx.status}
                </span>
              </div>
            </Link>
          </div>
        ))}
      </div>

      {/* Quick links */}
      <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { href: "/app/documents", label: "单据上传与 OCR", icon: "📄" },
          { href: "/app/graph", label: "交易关系图谱", icon: "🔗" },
          { href: "/app/cashflow", label: "现金流与情景", icon: "💱" },
          { href: "/app/report", label: "预审报告", icon: "📋" },
        ].map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="card text-center hover:shadow-lg transition"
          >
            <div className="text-2xl mb-2">{link.icon}</div>
            <div className="text-sm font-medium">{link.label}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
