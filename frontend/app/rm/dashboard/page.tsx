"use client";

import { useState, useEffect } from "react";
import {
  apiGet, apiPost, formatCurrency, riskClass, DashboardItem, Transaction,
} from "@/lib/api";
import { BoundaryBanner } from "@/components/BoundaryBanner";

export default function RMDashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTx, setSelectedTx] = useState<DashboardItem | null>(null);
  const [txDetail, setTxDetail] = useState<any>(null);
  const [reviewAction, setReviewAction] = useState("");
  const [riskComment, setRiskComment] = useState("");
  const [reviewMessage, setReviewMessage] = useState("");
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  useEffect(() => {
    loadDashboard();
    loadAuditLogs();
  }, []);

  const loadDashboard = () => {
    apiGet("/api/rm/dashboard").then((data) => {
      setDashboard(data.dashboard_items || []);
      setLoading(false);
    });
  };

  const loadAuditLogs = () => {
    apiGet("/api/audit/logs?limit=20").then((data) => {
      setAuditLogs(data.logs || []);
    });
  };

  const selectTx = (item: DashboardItem) => {
    setSelectedTx(item);
    setReviewMessage("");
    apiGet(`/api/transactions/${item.transaction_id}`).then((data) => {
      setTxDetail(data);
      setRecommendations(data.recommendations || []);
    });
  };

  const handleReview = async () => {
    if (!selectedTx || !reviewAction) return;
    try {
      const result = await apiPost(
        `/api/rm/review?transaction_id=${selectedTx.transaction_id}&review_type=${reviewAction}&reviewer=rm&risk_comment=${encodeURIComponent(riskComment)}&submit_to_formal=${reviewAction === "submit_formal"}`
      );
      setReviewMessage(result.message);
      if (reviewAction === "submit_formal") {
        loadDashboard();
      }
    } catch (err: any) {
      setReviewMessage(`错误: ${err.message}`);
    }
    setRiskComment("");
    setReviewAction("");
    loadAuditLogs();
  };

  const handleGenRecs = async () => {
    if (!selectedTx) return;
    try {
      const result = await apiPost(`/api/recommendations/generate?transaction_id=${selectedTx.transaction_id}`);
      setRecommendations(result.recommendations || []);
      setReviewMessage(`生成了 ${result.recommendations?.length || 0} 条产品推荐`);
    } catch (err: any) {
      setReviewMessage(`错误: ${err.message}`);
    }
  };

  if (loading) return <div className="py-20 text-center text-[#9b9ba3]">加载中...</div>;

  return (
    <div className="fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">RM 工作台</h1>
        <p className="text-sm text-[#6b6b73]">客户经理后台 · 企业概览 · 交易审核 · AI 辅助决策</p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="card text-center" style={{ padding: 16 }}>
          <div className="text-3xl font-bold" style={{ color: "#a91624" }}>{dashboard.length}</div>
          <div className="text-xs text-[#6b6b73] mt-1">总交易数</div>
        </div>
        <div className="card text-center" style={{ padding: 16 }}>
          <div className="text-3xl font-bold text-[#dc2626]">
            {dashboard.filter((d) => d.requires_manual_review).length}
          </div>
          <div className="text-xs text-[#6b6b73] mt-1">高风险待复核</div>
        </div>
        <div className="card text-center" style={{ padding: 16 }}>
          <div className="text-3xl font-bold text-[#f59e0b]">
            {dashboard.filter((d) => d.status === "analyzed" || d.status === "draft").length}
          </div>
          <div className="text-xs text-[#6b6b73] mt-1">待审核</div>
        </div>
        <div className="card text-center" style={{ padding: 16 }}>
          <div className="text-3xl font-bold text-[#16a34a]">
            {dashboard.reduce((sum, d) => sum + d.recommendations_count, 0)}
          </div>
          <div className="text-xs text-[#6b6b73] mt-1">产品推荐</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Transaction list */}
        <div className="lg:col-span-1">
          <h2 className="font-bold mb-3">交易列表</h2>
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {dashboard.map((item) => (
              <div
                key={item.transaction_id}
                onClick={() => selectTx(item)}
                className={`card cursor-pointer transition ${selectedTx?.transaction_id === item.transaction_id ? "ring-2 ring-[#a91624]" : ""}`}
                style={{ padding: 12 }}
              >
                <div className="flex items-start justify-between mb-1">
                  <div className="text-sm font-medium">{item.tx_ref}</div>
                  <span className={`text-xs px-2 py-0.5 rounded ${riskClass(item.overall_risk)}`}>
                    {item.overall_risk}
                  </span>
                </div>
                <div className="text-xs text-[#9b9ba3]">{item.enterprise_name}</div>
                <div className="text-xs text-[#6b6b73] mt-1 truncate">{item.buyer}</div>
                <div className="flex gap-2 mt-2 text-xs">
                  <span className="px-1.5 py-0.5 rounded bg-[#f7f7f8]">
                    完整度 {item.completeness_score}
                  </span>
                  {item.requires_manual_review && (
                    <span className="px-1.5 py-0.5 rounded risk-high">需复核</span>
                  )}
                  {item.unconfirmed_documents > 0 && (
                    <span className="px-1.5 py-0.5 rounded risk-medium">
                      {item.unconfirmed_documents} 文档待确认
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Detail panel */}
        <div className="lg:col-span-2 space-y-4">
          {selectedTx ? (
            <>
              {/* AI Summary */}
              <div className="card">
                <h3 className="font-bold mb-2">AI 分析摘要</h3>
                <p className="text-sm text-[#6b6b73] leading-relaxed">{selectedTx.ai_summary}</p>
                <div className="mt-2 flex gap-2 flex-wrap">
                  <a href={`/app/graph?tx=${selectedTx.transaction_id}`} className="btn-secondary btn-sm">
                    交易图谱
                  </a>
                  <a href={`/app/cashflow?tx=${selectedTx.transaction_id}`} className="btn-secondary btn-sm">
                    现金流
                  </a>
                  <a href={`/app/report?tx=${selectedTx.transaction_id}`} className="btn-secondary btn-sm">
                    预审报告
                  </a>
                </div>
              </div>

              {/* Transaction overview */}
              <div className="card">
                <h3 className="font-bold mb-3">交易概览</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                  <div><span className="text-[#9b9ba3]">订单：</span>{formatCurrency(selectedTx.order_amount, selectedTx.order_currency)}</div>
                  <div><span className="text-[#9b9ba3]">发票：</span>{formatCurrency(selectedTx.invoice_amount, selectedTx.invoice_currency)}</div>
                  <div><span className="text-[#9b9ba3]">缺口：</span>{selectedTx.funding_gap_amount ? formatCurrency(selectedTx.funding_gap_amount, selectedTx.funding_gap_currency || "") : "—"}</div>
                  <div><span className="text-[#9b9ba3]">物流：</span>{selectedTx.logistics_status}</div>
                </div>
                <div className="mt-3">
                  <div className="text-xs text-[#9b9ba3] mb-1">风险维度</div>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {Object.entries(selectedTx.risk_dimensions || {}).map(([dim, level]) => (
                      <div key={dim} className="flex justify-between text-xs p-1.5 rounded border border-[#e5e5e8]">
                        <span>{dim}</span>
                        <span className={`px-1.5 py-0.5 rounded ${riskClass(level)}`}>{level}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Risk alerts */}
              {txDetail?.risk_alerts && txDetail.risk_alerts.length > 0 && (
                <div className="card">
                  <h3 className="font-bold mb-3">风险告警 ({txDetail.risk_alerts.length})</h3>
                  <div className="space-y-2">
                    {txDetail.risk_alerts.map((alert: any, i: number) => (
                      <div
                        key={i}
                        className="p-2 rounded text-xs border"
                        style={{
                          borderColor: alert.alert_level === "High" ? "#dc2626" : alert.alert_level === "Medium" ? "#f59e0b" : "#16a34a",
                          background: alert.alert_level === "High" ? "#fee2e2" : alert.alert_level === "Medium" ? "#fef3c7" : "#dcfce7",
                        }}
                      >
                        <div className="flex justify-between">
                          <span className="font-medium">{alert.alert_message}</span>
                          <span className={riskClass(alert.alert_level)}>{alert.alert_level}</span>
                        </div>
                        <details>
                          <summary className="cursor-pointer text-[#6b6b73] mt-1">Why?</summary>
                          <p className="mt-1 text-[#6b6b73]">{alert.explanation}</p>
                        </details>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              <div className="card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold">产品推荐 ({recommendations.length})</h3>
                  <button onClick={handleGenRecs} className="btn-secondary btn-sm">
                    重新生成推荐
                  </button>
                </div>
                <div className="space-y-2">
                  {recommendations.map((rec: any, i: number) => (
                    <div key={i} className="p-3 rounded-lg border border-[#e5e5e8]">
                      <div className="flex items-start justify-between mb-1">
                        <div className="font-medium text-sm">
                          {rec.product_name_cn || rec.transaction_stage}
                        </div>
                        <span className="text-xs px-2 py-0.5 rounded bg-[#f7f7f8]">
                          {rec.transaction_stage}
                        </span>
                      </div>
                      <p className="text-xs text-[#6b6b73] mb-2">{rec.reason}</p>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                        <div><span className="text-[#9b9ba3]">预计额度：</span>{formatCurrency(rec.estimated_amount, rec.estimated_currency)}</div>
                        <div><span className="text-[#9b9ba3]">期限：</span>{rec.estimated_tenor_days} 天</div>
                        <div><span className="text-[#9b9ba3]">用途：</span>{rec.use_of_funds}</div>
                        <div><span className="text-[#9b9ba3]">置信度：</span>{(rec.confidence * 100).toFixed(0)}%</div>
                      </div>
                      <details className="mt-2">
                        <summary className="text-xs cursor-pointer text-[#6b6b73]">Source / Knowledge Reference</summary>
                        <p className="text-xs mt-1 text-[#9b9ba3]">{rec.knowledge_reference}</p>
                      </details>
                    </div>
                  ))}
                  {recommendations.length === 0 && (
                    <p className="text-xs text-[#9b9ba3]">点击"重新生成推荐"获取产品推荐</p>
                  )}
                </div>
              </div>

              {/* RM Actions */}
              <div className="card">
                <h3 className="font-bold mb-3">RM 操作</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-[#9b9ba3] block mb-1">操作类型</label>
                    <select
                      value={reviewAction}
                      onChange={(e) => setReviewAction(e.target.value)}
                      className="w-full p-2 rounded border border-[#e5e5e8] text-sm"
                    >
                      <option value="">选择操作...</option>
                      <option value="ocr_confirm">确认 AI 提取信息 (Approve AI-extracted information)</option>
                      <option value="edit">编辑信息 (Edit)</option>
                      <option value="request_docs">要求补充单据 (Request Additional Documents)</option>
                      <option value="risk_comment">添加风险评论 (Add Risk Comment)</option>
                      <option value="contact">联系企业 (Contact Enterprise)</option>
                      <option value="confirm_service">确认金融服务 (Confirm Financial Service)</option>
                      <option value="submit_formal">提交正式流程 (Submit to Formal Process)</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-[#9b9ba3] block mb-1">备注/风险评论</label>
                    <textarea
                      value={riskComment}
                      onChange={(e) => setRiskComment(e.target.value)}
                      className="w-full p-2 rounded border border-[#e5e5e8] text-sm"
                      rows={2}
                      placeholder="输入备注..."
                    />
                  </div>
                  <button
                    onClick={handleReview}
                    className="btn-primary btn-sm"
                    disabled={!reviewAction}
                  >
                    执行操作
                  </button>
                  {reviewMessage && (
                    <div className="text-sm p-2 rounded bg-[#dcfce7] text-[#166534]">
                      {reviewMessage}
                    </div>
                  )}
                  {selectedTx.requires_manual_review && (
                    <div className="p-3 rounded bg-[#fee2e2] border border-[#dc2626] text-xs text-[#991b1b]">
                      ⚠ 高风险交易：Flag → Escalate → RM Review。AI 输出不构成信贷审批，需人工复核后方可提交正式流程。
                    </div>
                  )}
                </div>
              </div>

              <BoundaryBanner compact />
            </>
          ) : (
            <div className="card text-center py-16 text-[#9b9ba3]">
              选择左侧交易查看详情
            </div>
          )}
        </div>
      </div>

      {/* Audit logs */}
      <div className="mt-8">
        <h2 className="font-bold mb-3">审计日志 (Audit Trail)</h2>
        <div className="card">
          <div className="overflow-x-auto max-h-60 overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-white">
                <tr className="border-b border-[#e5e5e8] text-left">
                  <th className="py-2 pr-4">时间</th>
                  <th className="py-2 pr-4">操作人</th>
                  <th className="py-2 pr-4">操作</th>
                  <th className="py-2 pr-4">详情</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id} className="border-b border-[#f0f0f2]">
                    <td className="py-1.5 pr-4 text-[#9b9ba3]">
                      {new Date(log.created_at).toLocaleString("zh-CN")}
                    </td>
                    <td className="py-1.5 pr-4">{log.actor}</td>
                    <td className="py-1.5 pr-4 font-medium">{log.action}</td>
                    <td className="py-1.5 pr-4 text-[#6b6b73]">{log.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
