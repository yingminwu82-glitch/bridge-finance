"use client";

import { useState, useEffect } from "react";
import {
  apiGet, apiPost, formatCurrency, DashboardItem, Transaction,
} from "@/lib/api";
import { BoundaryBanner } from "@/components/BoundaryBanner";
import { useLang } from "@/components/LanguageProvider";
import { productCategoryKey } from "@/lib/i18n";

export default function RMDashboardPage() {
  const { t, lang } = useLang();
  const [dashboard, setDashboard] = useState<DashboardItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTx, setSelectedTx] = useState<DashboardItem | null>(null);
  const [txDetail, setTxDetail] = useState<any>(null);
  const [reviewAction, setReviewAction] = useState("");
  const [riskComment, setRiskComment] = useState("");
  const [reviewMessage, setReviewMessage] = useState("");
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [preReport, setPreReport] = useState<any>(null);
  const [reportLoading, setReportLoading] = useState(false);

  useEffect(() => {
    loadDashboard();
    loadAuditLogs();
  }, [lang]);

  const loadDashboard = () => {
    apiGet(`/api/rm/dashboard?lang=${lang}`).then((data) => {
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
    setPreReport(null);
    apiGet(`/api/transactions/${item.transaction_id}?lang=${lang}`).then((data) => {
      setTxDetail(data);
      setRecommendations(data.recommendations || []);
    });
    loadPreReport(item.transaction_id);
  };

  const loadPreReport = async (txId: number) => {
    setReportLoading(true);
    try {
      const result = await apiPost(`/api/reports/preassessment?transaction_id=${txId}&lang=${lang}`);
      setPreReport(result);
    } catch (err) {
      setPreReport(null);
    }
    setReportLoading(false);
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
      setReviewMessage(`Error: ${err.message}`);
    }
    setRiskComment("");
    setReviewAction("");
    loadAuditLogs();
  };

  const handleGenRecs = async () => {
    if (!selectedTx) return;
    try {
      const result = await apiPost(`/api/recommendations/generate?transaction_id=${selectedTx.transaction_id}&lang=${lang}`);
      setRecommendations(result.recommendations || []);
      setReviewMessage(`${t("rm_gaps_recs")} ${result.recommendations?.length || 0} ${t("rm_recs_unit")}`);
    } catch (err: any) {
      setReviewMessage(`Error: ${err.message}`);
    }
  };

  if (loading) return <div className="py-20 text-center text-[#9b9ba3]">{t("loading")}</div>;

  return (
    <div className="fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">{t("rm_title")}</h1>
        <p className="text-sm text-[#6b6b73]">{t("rm_subtitle")}</p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        <div className="card text-center" style={{ padding: 16 }}>
          <div className="text-3xl font-bold" style={{ color: "#a91624" }}>{dashboard.length}</div>
          <div className="text-xs text-[#6b6b73] mt-1">{t("rm_total_tx")}</div>
        </div>
        <div className="card text-center" style={{ padding: 16 }}>
          <div className="text-3xl font-bold text-[#f59e0b]">
            {dashboard.filter((d) => d.status === "analyzed" || d.status === "draft").length}
          </div>
          <div className="text-xs text-[#6b6b73] mt-1">{t("rm_pending")}</div>
        </div>
        <div className="card text-center" style={{ padding: 16 }}>
          <div className="text-3xl font-bold text-[#16a34a]">
            {dashboard.reduce((sum, d) => sum + d.recommendations_count, 0)}
          </div>
          <div className="text-xs text-[#6b6b73] mt-1">{t("rm_recommendations")}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Transaction list */}
        <div className="lg:col-span-1">
          <h2 className="font-bold mb-3">{t("rm_tx_list")}</h2>
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
                </div>
                <div className="text-xs text-[#9b9ba3]">{item.enterprise_name}</div>
                <div className="text-xs text-[#6b6b73] mt-1 truncate">{item.buyer}</div>
                <div className="flex gap-2 mt-2 text-xs">
                  <span className="px-1.5 py-0.5 rounded bg-[#f7f7f8]">
                    {t("rm_completeness")} {item.completeness_score}
                  </span>
                  {item.unconfirmed_documents > 0 && (
                    <span className="px-1.5 py-0.5 rounded risk-medium">
                      {item.unconfirmed_documents} {t("doc_pending")}
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
                <h3 className="font-bold mb-2">{t("rm_ai_summary")}</h3>
                <p className="text-sm text-[#6b6b73] leading-relaxed">{selectedTx.ai_summary}</p>
                <div className="mt-2 flex gap-2 flex-wrap">
                  <a href={`/app/graph?tx=${selectedTx.transaction_id}`} className="btn-secondary btn-sm">
                    {t("rm_view_graph")}
                  </a>
                  <a href={`/app/cashflow?tx=${selectedTx.transaction_id}`} className="btn-secondary btn-sm">
                    {t("rm_view_cashflow")}
                  </a>
                  <a href={`/app/report?tx=${selectedTx.transaction_id}`} className="btn-secondary btn-sm">
                    {t("rm_view_report")}
                  </a>
                </div>
              </div>

              {/* Transaction overview */}
              <div className="card">
                <h3 className="font-bold mb-3">{t("rm_tx_overview")}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                  <div><span className="text-[#9b9ba3]">{t("rm_order")}</span>{formatCurrency(selectedTx.order_amount, selectedTx.order_currency)}</div>
                  <div><span className="text-[#9b9ba3]">{t("rm_invoice")}</span>{formatCurrency(selectedTx.invoice_amount, selectedTx.invoice_currency)}</div>
                  <div><span className="text-[#9b9ba3]">{t("rm_gap")}</span>{selectedTx.funding_gap_amount ? formatCurrency(selectedTx.funding_gap_amount, selectedTx.funding_gap_currency || "") : "—"}</div>
                  <div><span className="text-[#9b9ba3]">{t("rm_logistics")}</span>{selectedTx.logistics_status}</div>
                </div>
              </div>

              {/* Pre-assessment Report */}
              {reportLoading ? (
                <div className="card text-center py-8 text-sm text-[#9b9ba3]">{t("rm_report_loading")}</div>
              ) : preReport ? (
                <div className="card">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="font-bold">{t("rm_pre_report")}</h3>
                      <div className="text-xs text-[#9b9ba3] mt-0.5">
                        {t("rpt_report_id")}: {preReport.report_id}
                      </div>
                    </div>
                    <button
                      onClick={() => loadPreReport(selectedTx.transaction_id)}
                      className="btn-secondary btn-sm"
                    >
                      {t("rm_regen_report")}
                    </button>
                  </div>

                  <div className="space-y-4">
                    {/* Enterprise info */}
                    <div>
                      <div className="text-xs font-medium text-[#6b6b73] mb-1.5">{t("rpt_enterprise_info")}</div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                        <div><span className="text-[#9b9ba3]">{t("rm_ent_name")}</span>{preReport.enterprise_info?.name}</div>
                        <div><span className="text-[#9b9ba3]">{t("rm_region")}</span>{preReport.enterprise_info?.region}</div>
                        <div><span className="text-[#9b9ba3]">{t("rm_industry")}</span>{preReport.enterprise_info?.industry}</div>
                        <div><span className="text-[#9b9ba3]">{t("rm_currencies")}</span>{preReport.enterprise_info?.main_currencies}</div>
                      </div>
                    </div>

                    {/* Transaction info */}
                    <div>
                      <div className="text-xs font-medium text-[#6b6b73] mb-1.5">{t("rpt_tx_info")}</div>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                        <div><span className="text-[#9b9ba3]">{t("rm_buyer")}</span>{preReport.transaction_info?.buyer}</div>
                        <div><span className="text-[#9b9ba3]">{t("rm_supplier")}</span>{preReport.transaction_info?.supplier}</div>
                        <div><span className="text-[#9b9ba3]">{t("rm_logistics_status")}</span>{preReport.transaction_info?.logistics_status}</div>
                        <div><span className="text-[#9b9ba3]">{t("rm_order_amount")}</span>{formatCurrency(preReport.transaction_info?.order_amount || 0, preReport.transaction_info?.order_currency || "")}</div>
                        <div><span className="text-[#9b9ba3]">{t("rm_invoice_amount")}</span>{formatCurrency(preReport.transaction_info?.invoice_amount || 0, preReport.transaction_info?.invoice_currency || "")}</div>
                        <div><span className="text-[#9b9ba3]">{t("rm_expected_collection")}</span>{preReport.transaction_info?.expected_collection_date}</div>
                      </div>
                    </div>

                    {/* Funding needs */}
                    {preReport.funding_needs?.funding_gaps?.length > 0 && (
                      <div>
                        <div className="text-xs font-medium text-[#6b6b73] mb-1.5">{t("rm_funding_needs")}</div>
                        <div className="space-y-2">
                          {preReport.funding_needs.funding_gaps.map((gap: any, i: number) => (
                            <div key={i} className="p-2 rounded bg-[#fef3c7] border border-[#f0d060]">
                              <div className="flex justify-between items-center text-xs">
                                <span className="font-medium">{gap.gap_currency} {t("rpt_funding_gap")}</span>
                                <span className="font-bold text-[#dc2626]">{formatCurrency(gap.gap_amount, gap.gap_currency)}</span>
                              </div>
                              <div className="text-xs text-[#6b6b73] mt-0.5">
                                {gap.gap_duration_days} {t("cf_days")} · {gap.primary_cause}
                              </div>
                            </div>
                          ))}
                        </div>
                        {preReport.funding_needs?.scenarios?.length > 0 && (
                          <div className="grid grid-cols-2 md:grid-cols-5 gap-1.5 mt-2">
                            {preReport.funding_needs.scenarios.map((sc: any, i: number) => (
                              <div key={i} className="text-xs p-1.5 rounded border border-[#e5e5e8]">
                                <div className="font-medium truncate">{sc.name}</div>
                                <div className="text-[#dc2626] mt-0.5">{formatCurrency(sc.max_funding_gap, sc.gap_currency)}</div>
                                <div className="text-[#9b9ba3] truncate">{sc.main_risk}</div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Service recommendations */}
                    {preReport.service_recommendations?.length > 0 && (
                      <div>
                        <div className="text-xs font-medium text-[#6b6b73] mb-1.5">{t("rm_service_recs")}</div>
                        <div className="space-y-1.5">
                          {preReport.service_recommendations.map((rec: any, i: number) => (
                            <div key={i} className="p-2 rounded border border-[#e5e5e8]">
                              <div className="flex items-center justify-between mb-0.5">
                                <span className="text-xs font-medium">{rec.product_name}</span>
                                <span className="text-xs text-[#9b9ba3]">{formatCurrency(rec.estimated_amount, rec.estimated_currency)} · {rec.estimated_tenor_days}{t("cf_days")}</span>
                              </div>
                              <p className="text-xs text-[#6b6b73]">{rec.reason}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="text-xs text-[#9b9ba3] pt-2 border-t border-[#e5e5e8]">
                      {t("rm_gen_time")}: {new Date(preReport.generated_at).toLocaleString("zh-CN")} · {t("rm_completeness")}: {preReport.completeness_score}/100
                    </div>
                  </div>
                </div>
              ) : null}

              {/* Recommendations */}
              <div className="card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold">{t("rm_product_recs")} ({recommendations.length})</h3>
                  <button onClick={handleGenRecs} className="btn-secondary btn-sm">
                    {t("rm_regen_recs")}
                  </button>
                </div>
                <div className="space-y-2">
                  {recommendations.map((rec: any, i: number) => {
                    const catKey = productCategoryKey(rec.product_category || rec.category);
                    return (
                    <div key={i} className="p-3 rounded-lg border border-[#e5e5e8]">
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <div className="font-medium text-sm">
                          {rec.product_name_localized || rec.product_name || rec.product_name_cn || rec.transaction_stage}
                        </div>
                        <span className="text-xs px-2 py-0.5 rounded bg-[#f7f7f8] shrink-0">
                          {catKey ? t(catKey) : rec.transaction_stage}
                        </span>
                      </div>
                      <p className="text-xs text-[#6b6b73] mb-2">{rec.reason}</p>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                        <div><span className="text-[#9b9ba3]">{t("rm_estimated_amount")}</span>{formatCurrency(rec.estimated_amount, rec.estimated_currency)}</div>
                        <div><span className="text-[#9b9ba3]">{t("rm_tenor")}</span>{rec.estimated_tenor_days} {t("cf_days")}</div>
                        <div><span className="text-[#9b9ba3]">{t("rm_use")}</span>{rec.use_of_funds}</div>
                        <div><span className="text-[#9b9ba3]">{t("rm_confidence")}</span>{(rec.confidence * 100).toFixed(0)}%</div>
                      </div>
                      <details className="mt-2">
                        <summary className="text-xs cursor-pointer text-[#6b6b73]">{t("rpt_source_ref")}</summary>
                        <p className="text-xs mt-1 text-[#9b9ba3]">{rec.knowledge_reference}</p>
                      </details>
                    </div>
                    );
                  })}
                  {recommendations.length === 0 && (
                    <p className="text-xs text-[#9b9ba3]">{t("rm_no_recs")}</p>
                  )}
                  <p className="text-xs text-[#9b9ba3] pt-1">{t("rec_source_note")}</p>
                </div>
              </div>

              {/* RM Actions */}
              <div className="card">
                <h3 className="font-bold mb-3">{t("rm_actions")}</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-[#9b9ba3] block mb-1">{t("rm_action_type")}</label>
                    <select
                      value={reviewAction}
                      onChange={(e) => setReviewAction(e.target.value)}
                      className="w-full p-2 rounded border border-[#e5e5e8] text-sm"
                    >
                      <option value="">{t("rm_select_action")}</option>
                      <option value="ocr_confirm">{t("rm_ocr_confirm")}</option>
                      <option value="edit">{t("rm_edit")}</option>
                      <option value="request_docs">{t("rm_request_docs")}</option>
                      <option value="contact">{t("rm_contact")}</option>
                      <option value="confirm_service">{t("rm_confirm_service")}</option>
                      <option value="submit_formal">{t("rm_submit_formal")}</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-[#9b9ba3] block mb-1">{t("rm_comment_label")}</label>
                    <textarea
                      value={riskComment}
                      onChange={(e) => setRiskComment(e.target.value)}
                      className="w-full p-2 rounded border border-[#e5e5e8] text-sm"
                      rows={2}
                      placeholder={t("rm_comment_placeholder")}
                    />
                  </div>
                  <button
                    onClick={handleReview}
                    className="btn-primary btn-sm"
                    disabled={!reviewAction}
                  >
                    {t("rm_execute")}
                  </button>
                  {reviewMessage && (
                    <div className="text-sm p-2 rounded bg-[#dcfce7] text-[#166534]">
                      {reviewMessage}
                    </div>
                  )}
                </div>
              </div>

              <BoundaryBanner compact />
            </>
          ) : (
            <div className="card text-center py-16 text-[#9b9ba3]">
              {t("select_tx_detail")}
            </div>
          )}
        </div>
      </div>

      {/* Audit logs */}
      <div className="mt-8">
        <h2 className="font-bold mb-3">{t("rm_audit_trail")}</h2>
        <div className="card">
          <div className="overflow-x-auto max-h-60 overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-white">
                <tr className="border-b border-[#e5e5e8] text-left">
                  <th className="py-2 pr-4">{t("rm_audit_time")}</th>
                  <th className="py-2 pr-4">{t("rm_audit_actor")}</th>
                  <th className="py-2 pr-4">{t("rm_audit_action")}</th>
                  <th className="py-2 pr-4">{t("rm_audit_details")}</th>
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
