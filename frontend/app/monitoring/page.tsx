"use client";

import { useState, useEffect } from "react";
import { apiGet } from "@/lib/api";
import { BoundaryBanner } from "@/components/BoundaryBanner";
import { Navigation } from "@/components/Navigation";

export default function MonitoringPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    apiGet("/api/monitoring/events").then((data) => {
      setEvents(data.events || []);
      setLoading(false);
    });
  }, []);

  const filteredEvents = filter === "all"
    ? events
    : events.filter((e) => e.severity === filter);

  const severityColor = (sev: string) => {
    if (sev === "critical") return { bg: "#fee2e2", border: "#dc2626", color: "#991b1b" };
    if (sev === "warning") return { bg: "#fef3c7", border: "#f59e0b", color: "#92400e" };
    return { bg: "#dbeafe", border: "#2563eb", color: "#1e40af" };
  };

  const eventTypeLabel: Record<string, string> = {
    shipment_update: "物流更新",
    payment_received: "收款到账",
    payment_overdue: "收款逾期",
    fx_change: "汇率变动",
    new_funding_gap: "新增资金缺口",
  };

  return (
    <div className="min-h-screen">
      <Navigation role="enterprise" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
        <BoundaryBanner compact />
      </div>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 pb-12">
        <div className="fade-in">
          <div className="mb-6">
            <h1 className="text-2xl font-bold mb-1">交易后监控与告警</h1>
            <p className="text-sm text-[#6b6b73]">持续监控交易动态 · 物流、收款、汇率、资金缺口变化</p>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <div className="card text-center" style={{ padding: 16 }}>
              <div className="text-3xl font-bold" style={{ color: "#a91624" }}>{events.length}</div>
              <div className="text-xs text-[#6b6b73] mt-1">总事件</div>
            </div>
            <div className="card text-center" style={{ padding: 16 }}>
              <div className="text-3xl font-bold text-[#dc2626]">
                {events.filter((e) => e.severity === "critical").length}
              </div>
              <div className="text-xs text-[#6b6b73] mt-1">严重告警</div>
            </div>
            <div className="card text-center" style={{ padding: 16 }}>
              <div className="text-3xl font-bold text-[#f59e0b]">
                {events.filter((e) => e.severity === "warning").length}
              </div>
              <div className="text-xs text-[#6b6b73] mt-1">警告</div>
            </div>
            <div className="card text-center" style={{ padding: 16 }}>
              <div className="text-3xl font-bold text-[#2563eb]">
                {events.filter((e) => e.severity === "info").length}
              </div>
              <div className="text-xs text-[#6b6b73] mt-1">信息</div>
            </div>
          </div>

          {/* Filter */}
          <div className="flex gap-2 mb-4">
            {[
              { val: "all", label: "全部" },
              { val: "critical", label: "严重" },
              { val: "warning", label: "警告" },
              { val: "info", label: "信息" },
            ].map((f) => (
              <button
                key={f.val}
                onClick={() => setFilter(f.val)}
                className={`px-3 py-1.5 rounded-lg text-sm border transition ${
                  filter === f.val
                    ? "bg-[#a91624] text-white border-[#a91624]"
                    : "bg-white border-[#e5e5e8] hover:border-[#a91624]"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Event timeline */}
          {loading ? (
            <div className="py-16 text-center text-[#9b9ba3]">加载中...</div>
          ) : (
            <div className="card">
              <div className="space-y-3">
                {filteredEvents.map((event) => {
                  const colors = severityColor(event.severity);
                  return (
                    <div
                      key={event.id}
                      className="p-3 rounded-lg border-l-4"
                      style={{
                        background: colors.bg,
                        borderColor: colors.border,
                        color: colors.color,
                      }}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: colors.border, color: "white" }}>
                              {eventTypeLabel[event.event_type] || event.event_type}
                            </span>
                            <span className="text-xs opacity-70">
                              交易 #{event.transaction_id}
                            </span>
                          </div>
                          <p className="text-sm">{event.event_description}</p>
                          {event.metadata && (
                            <details className="mt-1">
                              <summary className="text-xs cursor-pointer opacity-60">详细信息</summary>
                              <pre className="text-xs mt-1 opacity-60 whitespace-pre-wrap">
                                {JSON.stringify(event.metadata, null, 2)}
                              </pre>
                            </details>
                          )}
                        </div>
                        <div className="text-xs opacity-60 whitespace-nowrap ml-2">
                          {new Date(event.created_at).toLocaleString("zh-CN")}
                        </div>
                      </div>
                    </div>
                  );
                })}
                {filteredEvents.length === 0 && (
                  <div className="text-center py-8 text-sm text-[#9b9ba3]">暂无事件</div>
                )}
              </div>
            </div>
          )}

          <div className="mt-6">
            <BoundaryBanner />
          </div>
        </div>
      </main>
    </div>
  );
}
