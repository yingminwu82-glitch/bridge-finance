"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import {
  apiGet, apiPost, formatCurrency, riskClass, Transaction, ILLUSTRATIVE_NOTE,
} from "@/lib/api";

const EChartsReact = dynamic(() => import("echarts-for-react"), { ssr: false });

export default function CashflowPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedTx, setSelectedTx] = useState<number>(1);
  const [forecast, setForecast] = useState<any>(null);
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [riskData, setRiskData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [riskResult, setRiskResult] = useState<any>(null);

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
      apiGet(`/api/transactions/${selectedTx}`),
    ]).then(([fc, sc, tx]) => {
      setForecast(fc);
      setScenarios(sc.scenarios || []);
      setRiskData(tx);
      setLoading(false);
    });
  }, [selectedTx]);

  const handleRiskAnalyze = async () => {
    setAnalyzing(true);
    try {
      const result = await apiPost(`/api/risk/analyze?transaction_id=${selectedTx}`);
      setRiskResult(result);
      // Refresh transaction data
      const tx = await apiGet(`/api/transactions/${selectedTx}`);
      setRiskData(tx);
    } catch (err) {
      console.error(err);
    }
    setAnalyzing(false);
  };

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
        <h1 className="text-2xl font-bold mb-1">多币种现金流与情景模拟</h1>
        <p className="text-sm text-[#6b6b73]">Future Cash Position · Funding Gap · 场景压力测试</p>
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
      </div>

      {loading ? (
        <div className="py-16 text-center text-[#9b9ba3]">加载中...</div>
      ) : (
        <div className="space-y-4">
          {/* Cashflow timeline */}
          <div className="card">
            <h2 className="font-bold mb-2">现金流时间线</h2>
            <EChartsReact option={timelineOption} style={{ height: 300 }} />
            <p className="illustrative-note mt-2">{ILLUSTRATIVE_NOTE}</p>
          </div>

          {/* Funding gap */}
          {forecast?.funding_gap && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="card">
                <h2 className="font-bold mb-3">资金缺口分析 (Funding Gap)</h2>
                {forecast.funding_gap.gaps?.length > 0 ? (
                  <div className="space-y-3">
                    {forecast.funding_gap.gaps.map((gap: any, i: number) => (
                      <div key={i} className="p-3 rounded-lg bg-[#fef3c7] border border-[#f0d060]">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium">缺口币种: {gap.gap_currency}</span>
                          <span className="text-lg font-bold text-[#dc2626]">
                            {formatCurrency(gap.gap_amount, gap.gap_currency)}
                          </span>
                        </div>
                        <div className="text-xs text-[#6b6b73] space-y-1">
                          <div>持续时间: {gap.gap_duration_days} 天</div>
                          <div>开始日期: {gap.gap_start_date}</div>
                          {gap.gap_end_date && <div>结束日期: {gap.gap_end_date}</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-sm text-[#9b9ba3]">
                    未检测到资金缺口
                  </div>
                )}
                <div className="mt-3 pt-3 border-t border-[#e5e5e8]">
                  <div className="text-xs text-[#9b9ba3] mb-1">主要原因</div>
                  <p className="text-sm text-[#6b6b73]">{forecast.funding_gap.primary_cause}</p>
                </div>
              </div>

              {/* Summary */}
              <div className="card">
                <h2 className="font-bold mb-3">分析摘要</h2>
                <p className="text-sm text-[#6b6b73] mb-3">{forecast.summary}</p>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-[#9b9ba3]">最低流动性缓冲 (CNY)</span>
                    <span>{formatCurrency(forecast.funding_gap.min_liquidity_buffer?.CNY || 0, "CNY")}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#9b9ba3]">最低流动性缓冲 (USD)</span>
                    <span>{formatCurrency(forecast.funding_gap.min_liquidity_buffer?.USD || 0, "USD")}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#9b9ba3]">最低流动性缓冲 (HKD)</span>
                    <span>{formatCurrency(forecast.funding_gap.min_liquidity_buffer?.HKD || 0, "HKD")}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Scenario simulation */}
          <div className="card">
            <h2 className="font-bold mb-2">情景模拟 (Scenario Simulation)</h2>
            <EChartsReact option={scenarioOption} style={{ height: 300 }} />
            <p className="illustrative-note mt-2">{ILLUSTRATIVE_NOTE}</p>
          </div>

          {/* Scenario details table */}
          <div className="card">
            <h2 className="font-bold mb-3">情景详情</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#e5e5e8] text-left">
                    <th className="py-2 pr-4">情景</th>
                    <th className="py-2 pr-4">参数</th>
                    <th className="py-2 pr-4">最大资金缺口</th>
                    <th className="py-2 pr-4">主要风险</th>
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

          {/* Risk analysis */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold">风险规则引擎</h2>
              <button
                onClick={handleRiskAnalyze}
                className="btn-primary btn-sm"
                disabled={analyzing}
              >
                {analyzing ? "分析中..." : "运行风险分析"}
              </button>
            </div>

            {riskResult ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  <div className="p-3 rounded-lg bg-[#f7f7f8]">
                    <div className="text-xs text-[#9b9ba3]">交易完整度</div>
                    <div className="text-xl font-bold" style={{ color: "#a91624" }}>
                      {riskResult.completeness_score}/100
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-[#f7f7f8]">
                    <div className="text-xs text-[#9b9ba3]">整体风险</div>
                    <div className={`text-xl font-bold px-2 py-0.5 rounded inline-block ${riskClass(riskResult.overall_risk)}`}>
                      {riskResult.overall_risk}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-[#f7f7f8]">
                    <div className="text-xs text-[#9b9ba3]">需人工复核</div>
                    <div className="text-xl font-bold">
                      {riskResult.requires_manual_review ? "是 ⚠" : "否"}
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-sm mb-2">风险维度</h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {Object.entries(riskResult.risk_dimensions || {}).map(([dim, level]: [string, any]) => (
                      <div key={dim} className="flex items-center justify-between p-2 rounded border border-[#e5e5e8] text-xs">
                        <span>{dim}</span>
                        <span className={`px-2 py-0.5 rounded ${riskClass(level)}`}>{level}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-sm mb-2">风险告警</h3>
                  <div className="space-y-2">
                    {riskResult.alerts?.map((alert: any, i: number) => (
                      <div
                        key={i}
                        className="p-3 rounded-lg border"
                        style={{
                          borderColor: alert.alert_level === "High" ? "#dc2626" : alert.alert_level === "Medium" ? "#f59e0b" : "#16a34a",
                          background: alert.alert_level === "High" ? "#fee2e2" : alert.alert_level === "Medium" ? "#fef3c7" : "#dcfce7",
                        }}
                      >
                        <div className="flex items-start justify-between mb-1">
                          <span className="font-medium text-sm">{alert.alert_message}</span>
                          <span className={`text-xs px-2 py-0.5 rounded ${riskClass(alert.alert_level)} whitespace-nowrap ml-2`}>
                            {alert.alert_level}
                          </span>
                        </div>
                        <details className="mt-1">
                          <summary className="text-xs cursor-pointer text-[#6b6b73]">Why? 展开原因</summary>
                          <div className="text-xs mt-2 space-y-1">
                            {alert.main_factors?.length > 0 && (
                              <div>
                                <span className="font-medium">主要因素：</span>
                                <ul className="list-disc ml-5 mt-0.5">
                                  {alert.main_factors.map((f: string, j: number) => <li key={j}>{f}</li>)}
                                </ul>
                              </div>
                            )}
                            {alert.positive_factors?.length > 0 && (
                              <div>
                                <span className="font-medium">正面因素：</span>
                                <ul className="list-disc ml-5 mt-0.5">
                                  {alert.positive_factors.map((f: string, j: number) => <li key={j}>{f}</li>)}
                                </ul>
                              </div>
                            )}
                            <p className="mt-1 text-[#6b6b73]">{alert.explanation}</p>
                          </div>
                        </details>
                      </div>
                    ))}
                  </div>
                </div>

                {riskResult.requires_manual_review && (
                  <div className="p-4 rounded-lg bg-[#fee2e2] border border-[#dc2626] text-sm">
                    ⚠ 高风险交易已标记，必须进入人工复核流程：Flag → Escalate → RM Review
                  </div>
                )}

                <div className="flex gap-2">
                  <a href={`/app/report?tx=${selectedTx}`} className="btn-primary btn-sm">
                    生成预审报告 →
                  </a>
                </div>
              </div>
            ) : (
              <p className="text-sm text-[#9b9ba3]">点击"运行风险分析"查看详细风险评估</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
