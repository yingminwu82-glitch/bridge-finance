"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiGet, formatCurrency, Enterprise, Transaction } from "@/lib/api";
import { useLang } from "@/components/LanguageProvider";

export default function DashboardPage() {
  const { t, lang } = useLang();
  const [enterprises, setEnterprises] = useState<Enterprise[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedEnt, setSelectedEnt] = useState<number>(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiGet(`/api/enterprises?lang=${lang}`),
      apiGet("/api/transactions"),
    ]).then(([entData, txData]) => {
      setEnterprises(entData.enterprises || []);
      setTransactions(txData.transactions || []);
      setLoading(false);
    });
  }, [lang]);

  const entTxns = transactions.filter((tr) => tr.enterprise_id === selectedEnt);

  if (loading) return <div className="py-20 text-center text-[#9b9ba3]">{t("loading")}</div>;

  return (
    <div className="fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">{t("dash_title")}</h1>
        <p className="text-sm text-[#6b6b73]">{t("dash_subtitle")}</p>
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
              <div className="text-xs text-[#9b9ba3] mb-1">{t("dash_region")}</div>
              <div className="font-medium">{ent.region}</div>
            </div>
            <div>
              <div className="text-xs text-[#9b9ba3] mb-1">{t("dash_industry")}</div>
              <div className="font-medium">{ent.industry}</div>
            </div>
            <div>
              <div className="text-xs text-[#9b9ba3] mb-1">{t("dash_main_currencies")}</div>
              <div className="font-medium">{ent.main_currencies}</div>
            </div>
            <div>
              <div className="text-xs text-[#9b9ba3] mb-1">{t("dash_supplier_region")}</div>
              <div className="font-medium text-sm">{ent.region === "Hong Kong" ? "大湾区 (深圳、东莞)" : "Greater Bay Area"}</div>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-[#e5e5e8]">
            <div className="text-xs text-[#9b9ba3] mb-1">{t("dash_business_model")}</div>
            <p className="text-sm text-[#6b6b73]">{ent.business_model}</p>
          </div>
        </div>
      ))}

      {/* Transaction cards */}
      <h2 className="text-lg font-bold mb-4">{t("dash_transactions")}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {entTxns.map((tr) => (
          <div key={tr.id} className="card hover:shadow-lg transition cursor-pointer">
            <Link href={`/app/documents?tx=${tr.id}`} className="block">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="font-semibold text-sm">{tr.tx_ref}</div>
                  <div className="text-xs text-[#9b9ba3] mt-1">
                    {t("dash_buyer")}: {tr.buyer}
                  </div>
                  <div className="text-xs text-[#9b9ba3]">
                    {t("dash_supplier")}: {tr.supplier}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 text-sm mb-3">
                <div>
                  <div className="text-xs text-[#9b9ba3]">{t("dash_order_amount")}</div>
                  <div className="font-medium">{formatCurrency(tr.order_amount, tr.order_currency)}</div>
                </div>
                <div>
                  <div className="text-xs text-[#9b9ba3]">{t("dash_invoice_amount")}</div>
                  <div className="font-medium">{formatCurrency(tr.invoice_amount, tr.invoice_currency)}</div>
                </div>
                <div>
                  <div className="text-xs text-[#9b9ba3]">{t("dash_completeness")}</div>
                  <div className="font-medium">{tr.completeness_score}/100</div>
                </div>
              </div>

              <div className="flex gap-2 text-xs">
                <span className="px-2 py-0.5 rounded bg-[#f7f7f8] text-[#6b6b73]">
                  {t("dash_logistics")}: {tr.logistics_status}
                </span>
                <span className="px-2 py-0.5 rounded bg-[#f7f7f8] text-[#6b6b73]">
                  {t("dash_status")}: {tr.status}
                </span>
              </div>
            </Link>
          </div>
        ))}
      </div>

      {/* Quick links */}
      <div className="mt-8">
        <h2 className="text-lg font-bold mb-4">{t("dash_quick_links")}</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { href: "/app/documents", label: t("dash_doc_ocr"), icon: "📄" },
            { href: "/app/graph", label: t("dash_graph"), icon: "🔗" },
            { href: "/app/cashflow", label: t("dash_cashflow_scenario"), icon: "💱" },
            { href: "/app/report", label: t("dash_pre_report"), icon: "📋" },
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
    </div>
  );
}
