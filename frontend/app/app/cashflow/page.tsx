"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import {
  apiGet, apiPost, formatCurrency, Transaction,
} from "@/lib/api";
import { useLang } from "@/components/LanguageProvider";

const EChartsReact = dynamic(() => import("echarts-for-react"), { ssr: false });

export default function CashflowPage() {
  const { t } = useLang();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedTx, setSelectedTx] = useState<number>(1);
  const [forecast, setForecast] = useState<any>(null);
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet("/api/transactions").then((data) => {
      setTransactions(data.transactions || []);
    });
  }, []);

  useEffect(() => {
    if (!selectedTx) return;
    setLoading(true);
    Promise.all([
      apiPost(`/api/cashflow/forecast?transaction_id=${selectedTx}`),
      apiPost(`/api/scenarios/simulate?transaction_id=${selectedTx}`),
    ]).then(([fc, sc]) => {
      setForecast(fc);
      setScenarios(sc.scenarios || []);
      setLoading(false);
    });
  }, [selectedTx]);

  // Build ECharts cashflow timeline option
  const timelineOption = forecast ? {
    tooltip: {
      trigger: "axis",
      formatter: (params: any) => {
        let html = `<b>${params[0].axisValue}</b><br/>`;
        params.forEach((p: any) => {
          const sign = p.value >= 0 ? "+" : "";
          html += `${p.marker} ${p.seriesName}: ${sign}${formatCurrency(p.value, p.seriesName.split(" ")[0])}<br/>`;
        });
        return html;
      },
    },
    legend: { top: 0 },
    grid: { left: "3%", right: "4%", bottom: "3%", top: 40, containLabel: true },
    xAxis: {
      type: "category",
      data: forecast.cashflow_timeline?.map((c: any) => c.date) || [],
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        fontSize: 11,
        formatter: (v: number) => v >= 1000000 ? (v / 1000000).toFixed(1) + "M" : v >= 1000 ? (v / 1000).toFixed(0) + "K" : v.toString(),
      },
    },
    series: forecast.cashflow_timeline?.reduce((acc: any[], c: any) => {
      const existing = acc.find((s) => s.name.startsWith(c.currency));
      if (existing) {
        existing.data.push(c.amount);
      } else {
        acc.push({
          name: `${c.currency} ${c.type}`,
          type: "bar",
          data: [c.amount],
          itemStyle: {
            color: c.type === "inflow" ? "#16a34a" : "#dc2626",
          },
        });
      }
      return acc;
    }, []) || [],
  } : {};

  // Scenario comparison chart
  const scenarioOption = scenarios.length > 0 ? {
    tooltip: { trigger: "axis" },
    legend: { top: 0 },
    grid: { left: "3%", right: "4%", bottom: "3%", top: 40, containLabel: true },
    xAxis: {
      type: "category",
      data: scenarios.map((s) => s.scenario_name),
      axisLabel: { fontSize: 10, rotate: 20 },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        fontSize: 11,
        formatter: (v: number) => v >= 1000000 ? (v / 1000000).toFixed(1) + "M" : v >= 1000 ? (v / 1000).toFixed(0) + "K" : v.toString(),
      },
    },
    series: [
      {
        name: "Max Funding Gap",
        type: "bar",
        data: scenarios.map((s) => Math.abs(s.max_funding_gap)),
        itemStyle: {
          color: (params: any) => {
            const colors = ["#a91624", "#f59e0b", "#8b5cf6", "#2563eb", "#dc2626"];
            return colors[params.dataIndex % colors.length];
          },
        },
        label: {
          show: true,
          position: "top",
          formatter: (p: any) => p.value >= 1000000 ? (p.value / 1000000).toFixed(1) + "M" : (p.value / 1000).toFixed(0) + "K",
          fontSize: 10,
        },
      },
    ],
  } : {};

  return (
    <div className="fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">{t("cf_title")}</h1>
        <p className="text-sm text-[#6b6b73]">{t("cf_subtitle")}</p>
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
      </div>

      {loading ? (
        <div className="py-16 text-center text-[#9b9ba3]">{t("loading")}</div>
      ) : (
        <div className="space-y-4">
          {/* Cashflow timeline */}
          <div className="card">
            <h2 className="font-bold mb-2">{t("cf_timeline")}</h2>
            <EChartsReact option={timelineOption} style={{ height: 300 }} />
            <p className="illustrative-note mt-2">{t("boundary_illustrative")}</p>
          </div>

          {/* Funding gap */}
          {forecast?.funding_gap && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="card">
                <h2 className="font-bold mb-3">{t("cf_funding_gap")}</h2>
                {forecast.funding_gap.gaps?.length > 0 ? (
                  <div className="space-y-3">
                    {forecast.funding_gap.gaps.map((gap: any, i: number) => (
                      <div key={i} className="p-3 rounded-lg bg-[#fef3c7] border border-[#f0d060]">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium">{t("cf_gap_currency")}: {gap.gap_currency}</span>
                          <span className="text-lg font-bold text-[#dc2626]">
                            {formatCurrency(gap.gap_amount, gap.gap_currency)}
                          </span>
                        </div>
                        <div className="text-xs text-[#6b6b73] space-y-1">
                          <div>{t("cf_duration")}: {gap.gap_duration_days} {t("cf_days")}</div>
                          <div>{t("cf_start_date")}: {gap.gap_start_date}</div>
                          {gap.gap_end_date && <div>{t("cf_end_date")}: {gap.gap_end_date}</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-sm text-[#9b9ba3]">
                    {t("cf_no_gap")}
                  </div>
                )}
                <div className="mt-3 pt-3 border-t border-[#e5e5e8]">
                  <div className="text-xs text-[#9b9ba3] mb-1">{t("cf_primary_cause")}</div>
                  <p className="text-sm text-[#6b6b73]">{forecast.funding_gap.primary_cause}</p>
                </div>
              </div>

              {/* Summary */}
              <div className="card">
                <h2 className="font-bold mb-3">{t("cf_summary")}</h2>
                <p className="text-sm text-[#6b6b73] mb-3">{forecast.summary}</p>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-[#9b9ba3]">{t("cf_min_liquidity")} (CNY)</span>
                    <span>{formatCurrency(forecast.funding_gap.min_liquidity_buffer?.CNY || 0, "CNY")}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#9b9ba3]">{t("cf_min_liquidity")} (USD)</span>
                    <span>{formatCurrency(forecast.funding_gap.min_liquidity_buffer?.USD || 0, "USD")}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#9b9ba3]">{t("cf_min_liquidity")} (HKD)</span>
                    <span>{formatCurrency(forecast.funding_gap.min_liquidity_buffer?.HKD || 0, "HKD")}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Scenario simulation */}
          <div className="card">
            <h2 className="font-bold mb-2">{t("cf_scenario_sim")}</h2>
            <EChartsReact option={scenarioOption} style={{ height: 300 }} />
            <p className="illustrative-note mt-2">{t("boundary_illustrative")}</p>
          </div>

          {/* Scenario details table */}
          <div className="card">
            <h2 className="font-bold mb-3">{t("cf_scenario_detail")}</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#e5e5e8] text-left">
                    <th className="py-2 pr-4">{t("cf_scenario")}</th>
                    <th className="py-2 pr-4">{t("cf_params")}</th>
                    <th className="py-2 pr-4">{t("cf_max_gap")}</th>
                    <th className="py-2 pr-4">{t("cf_main_risk")}</th>
                  </tr>
                </thead>
                <tbody>
                  {scenarios.map((sc) => (
                    <tr key={sc.scenario_name} className="border-b border-[#f0f0f2]">
                      <td className="py-2 pr-4 font-medium">{sc.scenario_name}</td>
                      <td className="py-2 pr-4 text-xs text-[#6b6b73]">
                        {Object.entries(sc.parameters).map(([k, v]) => `${k}: ${v}`).join(", ")}
                      </td>
                      <td className="py-2 pr-4">
                        <span className="font-bold text-[#dc2626]">
                          {formatCurrency(Math.abs(sc.max_funding_gap), sc.gap_currency)}
                        </span>
                      </td>
                      <td className="py-2 pr-4">
                        <span className="text-xs px-2 py-0.5 rounded risk-medium">{sc.main_risk}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Generate pre-assessment report */}
          <div className="card text-center">
            <a href={`/app/report?tx=${selectedTx}`} className="btn-primary btn-sm">
              {t("cf_gen_report")}
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
