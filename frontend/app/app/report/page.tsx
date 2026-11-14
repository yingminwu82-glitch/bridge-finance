"use client";

import { useState, useEffect } from "react";
import {
  apiGet, apiPost, formatCurrency, riskClass, Transaction,
} from "@/lib/api";
import { BoundaryBanner } from "@/components/BoundaryBanner";

export default function ReportPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedTx, setSelectedTx] = useState<number>(1);
  const [report, setReport] = useState<any>(null);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    apiGet("/api/transactions").then((data) => {
      setTransactions(data.transactions || []);
    });
  }, []);

  const generateReport = async () => {
    setGenerating(true);
    try {
      const result = await apiPost(`/api/reports/preassessment?transaction_id=${selectedTx}`);
      setReport(result);
    } catch (err) {
      console.error(err);
    }
    setGenerating(false);
  };

  return (
    <div className="fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">融资预评估报告</h1>
        <p className="text-sm text-[#6b6b73]">标准化报告生成 · 含 AI 摘要 · 需 RM 审核</p>
      </div>

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
        <button
          onClick={generateReport}
          className="btn-primary btn-sm ml-2"
          disabled={generating}
        >
          {generating ? "生成中..." : "生成报告"}
        </button>
      </div>

      {report ? (
        <div className="space-y-4">
          {/* Report header */}
          <div className="card">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h2 className="text-lg font-bold">融资预评估报告</h2>
                <div className="text-xs text-[#9b9ba3] mt-1">
                  报告编号: {report.report_id}
                </div>
              </div>
              <div className="text-right text-xs text-[#9b9ba3]">
                <div>生成时间: {new Date(report.generated_at).toLocaleString("zh-CN")}</div>
                <div>交易编号: {report.transaction_ref}</div>
              </div>
            </div>
            <BoundaryBanner compact />
          </div>

          {/* AI Summary */}
          {report.ai_summary && (
            <div className="card">
              <h3 className="font-bold mb-2">AI 分析摘要</h3>
              <p className="text-sm text-[#6b6b73] leading-relaxed">{report.ai_summary}</p>
            </div>
          )}

          {/* Enterprise info */}
          <div className="card">
            <h3 className="font-bold mb-3">企业信息</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div><span className="text-[#9b9ba3]">企业名称：</span>{report.enterprise_info?.name}</div>
              <div><span className="text-[#9b9ba3]">区域：</span>{report.enterprise_info?.region}</div>
              <div><span className="text-[#9b9ba3]">行业：</span>{report.enterprise_info?.industry}</div>
              <div><span className="text-[#9b9ba3]">主要币种：</span>{report.enterprise_info?.main_currencies}</div>
            </div>
            <div className="mt-2 text-sm">
              <span className="text-[#9b9ba3]">经营模式：</span>{report.enterprise_info?.business_model}
            </div>
          </div>

          {/* Transaction info */}
          <div className="card">
            <h3 className="font-bold mb-3">交易信息</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
              <div><span className="text-[#9b9ba3]">买家：</span>{report.transaction_info?.buyer}</div>
              <div><span className="text-[#9b9ba3]">供应商：</span>{report.transaction_info?.supplier}</div>
              <div><span className="text-[#9b9ba3]">物流状态：</span>{report.transaction_info?.logistics_status}</div>
              <div><span className="text-[#9b9ba3]">订单金额：</span>{formatCurrency(report.transaction_info?.order_amount || 0, report.transaction_info?.order_currency || "")}</div>
              <div><span className="text-[#9b9ba3]">合同金额：</span>{formatCurrency(report.transaction_info?.contract_amount || 0, report.transaction_info?.contract_currency || "")}</div>
              <div><span className="text-[#9b9ba3]">发票金额：</span>{formatCurrency(report.transaction_info?.invoice_amount || 0, report.transaction_info?.invoice_currency || "")}</div>
              <div><span className="text-[#9b9ba3]">订单日期：</span>{report.transaction_info?.order_date}</div>
              <div><span className="text-[#9b9ba3]">付款日期：</span>{report.transaction_info?.payment_date}</div>
              <div><span className="text-[#9b9ba3]">预计收款：</span>{report.transaction_info?.expected_collection_date}</div>
            </div>
            <div className="mt-3">
              <div className="text-xs text-[#9b9ba3] mb-1">交易单据</div>
              <div className="flex gap-2 flex-wrap">
                {report.transaction_info?.documents?.map((d: any, i: number) => (
                  <span key={i} className="text-xs px-2 py-1 rounded bg-[#f7f7f8]">
                    {d.doc_type} {d.confirmed ? "✓" : "○"}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Risk analysis */}
          <div className="card">
            <h3 className="font-bold mb-3">风险分析</h3>
            <div className="flex items-center gap-4 mb-3">
              <div>
                <div className="text-xs text-[#9b9ba3]">完整度评分</div>
                <div className="text-2xl font-bold" style={{ color: "#a91624" }}>{report.completeness_score}/100</div>
              </div>
              <div>
                <div className="text-xs text-[#9b9ba3]">整体风险</div>
                <div className={`text-2xl font-bold px-2 py-0.5 rounded inline-block ${riskClass(report.risk_analysis?.overall_risk || "Low")}`}>
                  {report.risk_analysis?.overall_risk}
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-3">
              {Object.entries(report.risk_analysis?.risk_dimensions || {}).map(([dim, level]: [string, any]) => (
                <div key={dim} className="flex items-center justify-between p-2 rounded border border-[#e5e5e8] text-xs">
                  <span>{dim}</span>
                  <span className={`px-2 py-0.5 rounded ${riskClass(level)}`}>{level}</span>
                </div>
              ))}
            </div>
            {report.risk_analysis?.alerts?.map((alert: any, i: number) => (
              <div key={i} className="text-xs p-2 rounded mb-1" style={{
                background: alert.alert_level === "High" ? "#fee2e2" : alert.alert_level === "Medium" ? "#fef3c7" : "#dcfce7",
              }}>
                <span className="font-medium">[{alert.alert_level}]</span> {alert.alert_message}
              </div>
            ))}
          </div>

          {/* Funding needs */}
          <div className="card">
            <h3 className="font-bold mb-3">资金需求分析</h3>
            {report.funding_needs?.funding_gaps?.map((gap: any, i: number) => (
              <div key={i} className="p-3 rounded-lg bg-[#fef3c7] border border-[#f0d060] mb-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">{gap.gap_currency} 资金缺口</span>
                  <span className="font-bold text-[#dc2626]">{formatCurrency(gap.gap_amount, gap.gap_currency)}</span>
                </div>
                <div className="text-xs text-[#6b6b73] mt-1">
                  持续 {gap.gap_duration_days} 天 · {gap.primary_cause}
                </div>
              </div>
            ))}
            <div className="mt-3">
              <div className="text-xs text-[#9b9ba3] mb-1">情景模拟摘要</div>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                {report.funding_needs?.scenarios?.map((sc: any, i: number) => (
                  <div key={i} className="text-xs p-2 rounded border border-[#e5e5e8]">
                    <div className="font-medium truncate">{sc.name}</div>
                    <div className="text-[#dc2626] mt-1">{formatCurrency(sc.max_funding_gap, sc.gap_currency)}</div>
                    <div className="text-[#9b9ba3]">{sc.main_risk}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Service recommendations */}
          <div className="card">
            <h3 className="font-bold mb-3">金融服务推荐</h3>
            {report.service_recommendations?.map((rec: any, i: number) => (
              <div key={i} className="p-3 rounded-lg border border-[#e5e5e8] mb-2">
                <div className="font-medium text-sm mb-1">{rec.product_name}</div>
                <p className="text-xs text-[#6b6b73] mb-2">{rec.reason}</p>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div><span className="text-[#9b9ba3]">预计融资额：</span>{formatCurrency(rec.estimated_amount, rec.estimated_currency)}</div>
                  <div><span className="text-[#9b9ba3]">期限：</span>{rec.estimated_tenor_days} 天</div>
                  <div><span className="text-[#9b9ba3]">资金用途：</span>{rec.use_of_funds}</div>
                </div>
                <details className="mt-2">
                  <summary className="text-xs cursor-pointer text-[#6b6b73]">Source / Knowledge Reference</summary>
                  <p className="text-xs mt-1 text-[#9b9ba3]">{rec.knowledge_reference}</p>
                </details>
              </div>
            ))}
          </div>

          {/* RM review required */}
          {report.rm_review_required && (
            <div className="p-4 rounded-lg bg-[#fee2e2] border border-[#dc2626]">
              <div className="font-bold text-sm text-[#991b1b]">⚠ 需 RM 人工复核</div>
              <p className="text-sm mt-1 text-[#991b1b]">
                该交易为高风险交易，AI 输出不构成信贷审批。请 RM 审核后决定是否提交正式流程。
              </p>
              <a href={`/rm/dashboard?tx=${selectedTx}`} className="btn-primary btn-sm mt-2 inline-block">
                进入 RM 工作台 →
              </a>
            </div>
          )}

          <BoundaryBanner />
        </div>
      ) : (
        <div className="card text-center py-16">
          <div className="text-4xl mb-3">📋</div>
          <p className="text-[#9b9ba3] mb-4">点击"生成报告"按钮生成融资预评估报告</p>
          <button onClick={generateReport} className="btn-primary" disabled={generating}>
            {generating ? "生成中..." : "生成报告"}
          </button>
        </div>
      )}
    </div>
  );
}
