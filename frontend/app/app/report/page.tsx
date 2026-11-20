"use client";

import { useState, useEffect } from "react";
import {
  apiGet, apiPost, formatCurrency, Transaction,
} from "@/lib/api";
import { BoundaryBanner } from "@/components/BoundaryBanner";
import { useLang } from "@/components/LanguageProvider";
import { productCategoryKey } from "@/lib/i18n";

export default function ReportPage() {
  const { t, lang } = useLang();
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
      const result = await apiPost(`/api/reports/preassessment?transaction_id=${selectedTx}&lang=${lang}`);
      setReport(result);
    } catch (err) {
      console.error(err);
    }
    setGenerating(false);
  };

  return (
    <div className="fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">{t("rpt_title")}</h1>
        <p className="text-sm text-[#6b6b73]">{t("rpt_subtitle")}</p>
      </div>

      <div className="flex gap-2 mb-4 flex-wrap items-center">
        {transactions.map((tr) => (
          <button
            key={tr.id}
            onClick={() => setSelectedTx(tr.id)}
            className={`px-3 py-1.5 rounded-lg text-sm border transition ${
              selectedTx === tr.id
                ? "bg-[#a91624] text-white border-[#a91624]"
                : "bg-white border-[#e5e5e8] hover:border-[#a91624]"
            }`}
          >
            {tr.tx_ref}
          </button>
        ))}
        <button
          onClick={generateReport}
          className="btn-primary btn-sm ml-2"
          disabled={generating}
        >
          {generating ? t("generating") : t("generate")}
        </button>
      </div>

      {report ? (
        <div className="space-y-4">
          {/* Report header */}
          <div className="card">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h2 className="text-lg font-bold">{t("rpt_title")}</h2>
                <div className="text-xs text-[#9b9ba3] mt-1">
                  {t("rpt_report_id")}: {report.report_id}
                </div>
              </div>
              <div className="text-right text-xs text-[#9b9ba3]">
                <div>{t("rpt_gen_time")}: {new Date(report.generated_at).toLocaleString("zh-CN")}</div>
                <div>{t("rpt_tx_ref")}: {report.transaction_ref}</div>
              </div>
            </div>
            <BoundaryBanner compact />
          </div>

          {/* AI Summary */}
          {report.ai_summary && (
            <div className="card">
              <h3 className="font-bold mb-2">{t("rpt_ai_summary")}</h3>
              <p className="text-sm text-[#6b6b73] leading-relaxed">{report.ai_summary}</p>
            </div>
          )}

          {/* Enterprise info */}
          <div className="card">
            <h3 className="font-bold mb-3">{t("rpt_enterprise_info")}</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div><span className="text-[#9b9ba3]">{t("rpt_ent_name")}</span>{report.enterprise_info?.name}</div>
              <div><span className="text-[#9b9ba3]">{t("rpt_region")}</span>{report.enterprise_info?.region}</div>
              <div><span className="text-[#9b9ba3]">{t("rpt_industry")}</span>{report.enterprise_info?.industry}</div>
              <div><span className="text-[#9b9ba3]">{t("rpt_currencies")}</span>{report.enterprise_info?.main_currencies}</div>
            </div>
            <div className="mt-2 text-sm">
              <span className="text-[#9b9ba3]">{t("rpt_business_model")}</span>{report.enterprise_info?.business_model}
            </div>
          </div>

          {/* Transaction info */}
          <div className="card">
            <h3 className="font-bold mb-3">{t("rpt_tx_info")}</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
              <div><span className="text-[#9b9ba3]">{t("rpt_buyer")}</span>{report.transaction_info?.buyer}</div>
              <div><span className="text-[#9b9ba3]">{t("rpt_supplier")}</span>{report.transaction_info?.supplier}</div>
              <div><span className="text-[#9b9ba3]">{t("rpt_logistics")}</span>{report.transaction_info?.logistics_status}</div>
              <div><span className="text-[#9b9ba3]">{t("rpt_order_amount")}</span>{formatCurrency(report.transaction_info?.order_amount || 0, report.transaction_info?.order_currency || "")}</div>
              <div><span className="text-[#9b9ba3]">{t("rpt_contract_amount")}</span>{formatCurrency(report.transaction_info?.contract_amount || 0, report.transaction_info?.contract_currency || "")}</div>
              <div><span className="text-[#9b9ba3]">{t("rpt_invoice_amount")}</span>{formatCurrency(report.transaction_info?.invoice_amount || 0, report.transaction_info?.invoice_currency || "")}</div>
              <div><span className="text-[#9b9ba3]">{t("rpt_order_date")}</span>{report.transaction_info?.order_date}</div>
              <div><span className="text-[#9b9ba3]">{t("rpt_payment_date")}</span>{report.transaction_info?.payment_date}</div>
              <div><span className="text-[#9b9ba3]">{t("rpt_expected_collection")}</span>{report.transaction_info?.expected_collection_date}</div>
            </div>
            <div className="mt-3">
              <div className="text-xs text-[#9b9ba3] mb-1">{t("rpt_documents")}</div>
              <div className="flex gap-2 flex-wrap">
                {report.transaction_info?.documents?.map((d: any, i: number) => (
                  <span key={i} className="text-xs px-2 py-1 rounded bg-[#f7f7f8]">
                    {d.doc_type} {d.confirmed ? "✓" : "○"}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Funding needs */}
          <div className="card">
            <h3 className="font-bold mb-3">{t("rpt_funding_needs")}</h3>
            {report.funding_needs?.funding_gaps?.map((gap: any, i: number) => (
              <div key={i} className="p-3 rounded-lg bg-[#fef3c7] border border-[#f0d060] mb-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">{gap.gap_currency} {t("rpt_funding_gap")}</span>
                  <span className="font-bold text-[#dc2626]">{formatCurrency(gap.gap_amount, gap.gap_currency)}</span>
                </div>
                <div className="text-xs text-[#6b6b73] mt-1">
                  {gap.gap_duration_days} {t("cf_days")} · {gap.primary_cause}
                </div>
              </div>
            ))}
            <div className="mt-3">
              <div className="text-xs text-[#9b9ba3] mb-1">{t("rpt_scenario_summary")}</div>
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
            <h3 className="font-bold mb-3">{t("rpt_service_recs")}</h3>
            {report.service_recommendations?.map((rec: any, i: number) => {
              const catKey = productCategoryKey(rec.product_category || rec.category);
              return (
                <div key={i} className="p-3 rounded-lg border border-[#e5e5e8] mb-2">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="font-medium text-sm">{rec.product_name}</div>
                    {catKey && (
                      <span className="text-xs px-2 py-0.5 rounded bg-[#f7f7f8] text-[#6b6b73] shrink-0">
                        {t(catKey)}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[#6b6b73] mb-2">{rec.reason}</p>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div><span className="text-[#9b9ba3]">{t("rpt_estimated_amount")}</span>{formatCurrency(rec.estimated_amount, rec.estimated_currency)}</div>
                    <div><span className="text-[#9b9ba3]">{t("rpt_tenor")}</span>{rec.estimated_tenor_days} {t("cf_days")}</div>
                    <div><span className="text-[#9b9ba3]">{t("rpt_use_of_funds")}</span>{rec.use_of_funds}</div>
                  </div>
                  <details className="mt-2">
                    <summary className="text-xs cursor-pointer text-[#6b6b73]">{t("rpt_source_ref")}</summary>
                    <p className="text-xs mt-1 text-[#9b9ba3]">{rec.knowledge_reference}</p>
                  </details>
                </div>
              );
            })}
            {(!report.service_recommendations || report.service_recommendations.length === 0) && (
              <p className="text-xs text-[#9b9ba3]">{t("rm_no_recs")}</p>
            )}
            <p className="text-xs text-[#9b9ba3] mt-2">{t("rec_source_note")}</p>
          </div>

          {/* RM review link */}
          <div className="p-4 rounded-lg bg-[#f0f7ff] border border-[#2563eb]">
            <div className="font-bold text-sm text-[#1e40af]">{t("rpt_rm_review")}</div>
            <p className="text-sm mt-1 text-[#1e40af]">
              {t("rpt_rm_review_desc")}
            </p>
            <a href={`/rm/dashboard?tx=${selectedTx}`} className="btn-primary btn-sm mt-2 inline-block">
              {t("rpt_enter_rm")}
            </a>
          </div>

          <BoundaryBanner />
        </div>
      ) : (
        <div className="card text-center py-16">
          <div className="text-4xl mb-3">📋</div>
          <p className="text-[#9b9ba3] mb-4">{t("rpt_empty_hint")}</p>
          <button onClick={generateReport} className="btn-primary" disabled={generating}>
            {generating ? t("generating") : t("generate")}
          </button>
        </div>
      )}
    </div>
  );
}
