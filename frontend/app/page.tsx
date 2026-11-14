"use client";

import Link from "next/link";
import { BoundaryBanner } from "@/components/BoundaryBanner";

export default function HomePage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <header
        className="text-white"
        style={{
          background: "linear-gradient(135deg, #a91624 0%, #7a0f1a 60%, #5a0a14 100%)",
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl grid place-items-center text-xl font-bold"
              style={{ background: "rgba(255,255,255,0.15)" }}
            >
              湾
            </div>
            <div>
              <div className="font-bold text-lg leading-tight">湾区融桥</div>
              <div className="text-xs opacity-70 tracking-wider">GBA BRIDGE FINANCE</div>
            </div>
          </div>
          <Link
            href="/app/dashboard"
            className="bg-white text-[#a91624] px-5 py-2 rounded-lg font-semibold text-sm hover:opacity-90 transition"
          >
            进入应用 →
          </Link>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
          <div className="max-w-2xl">
            <div className="inline-block bg-white/10 backdrop-blur px-3 py-1 rounded-full text-xs mb-4">
              工银亚洲 · 大湾区跨境贸易金融智能分析平台
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold leading-tight mb-6">
              跨境贸易金融<br />
              智能分析与产品推荐
            </h1>
            <p className="text-lg opacity-90 mb-8 leading-relaxed">
              连接交易资料 · 看清经营与现金流 · 匹配金融服务 · 持续跟进交易
              <br />
              为大湾区跨境经营中小企业提供全流程 AI 辅助金融分析。
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/app/dashboard"
                className="bg-white text-[#a91624] px-6 py-3 rounded-xl font-semibold hover:opacity-90 transition"
              >
                企业端入口
              </Link>
              <Link
                href="/rm/dashboard"
                className="border border-white/30 px-6 py-3 rounded-xl font-semibold hover:bg-white/10 transition"
              >
                RM 工作台
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Service capabilities */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <h2 className="text-2xl font-bold text-center mb-2">服务能力</h2>
        <p className="text-center text-[#6b6b73] mb-10">
          从交易资料到金融服务，全流程 AI 辅助分析
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { icon: "📄", title: "交易信息结构化", desc: "OCR 识别 · 文档分类 · 统一数据结构" },
            { icon: "🔍", title: "资金需求早识别", desc: "多币种现金流预测 · 缺口分析 · 场景模拟" },
            { icon: "💱", title: "多币种视角", desc: "CNY/USD/HKD 多币种 · FX 风险评估" },
            { icon: "🔗", title: "全流程服务连接", desc: "贸易融资 · 跨境结算 · 保理 · 外汇管理" },
          ].map((item) => (
            <div key={item.title} className="card text-center">
              <div className="text-3xl mb-3">{item.icon}</div>
              <h3 className="font-semibold mb-1">{item.title}</h3>
              <p className="text-xs text-[#6b6b73]">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Process flow */}
      <section className="bg-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <h2 className="text-2xl font-bold text-center mb-10">服务流程</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[
              { step: "01", title: "连接交易资料", desc: "上传订单、合同、发票、物流、付款通知" },
              { step: "02", title: "看清经营与现金流", desc: "AI 结构化 · 多币种现金流 · 资金缺口" },
              { step: "03", title: "匹配金融服务", desc: "产品推荐 · RAG 知识库 · 可解释输出" },
              { step: "04", title: "持续跟进交易", desc: "交易后监控 · 动态预警 · 重算提醒" },
            ].map((item, i) => (
              <div key={item.step} className="relative">
                {i < 3 && (
                  <div className="hidden md:block absolute top-6 -right-2 text-[#a91624] text-xl">→</div>
                )}
                <div
                  className="w-12 h-12 rounded-xl grid place-items-center font-bold text-white mb-3"
                  style={{ background: "#a91624" }}
                >
                  {item.step}
                </div>
                <h3 className="font-semibold mb-1">{item.title}</h3>
                <p className="text-sm text-[#6b6b73]">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Boundary */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        <BoundaryBanner />
      </section>

      {/* Demo entry */}
      <section className="bg-[#a91624] text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <h2 className="text-2xl font-bold mb-4">立即体验演示</h2>
          <p className="opacity-90 mb-8">
            内置案例：香港贸易商 USD 500K 订单 / 大型供应链 USD 5M 订单
          </p>
          <Link
            href="/app/dashboard"
            className="inline-block bg-white text-[#a91624] px-8 py-3 rounded-xl font-semibold hover:opacity-90 transition"
          >
            进入企业端演示 →
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#1a1a1a] text-white/60 py-8 text-center text-sm">
        <p>© 2026 GBA Bridge Finance · ICBC (Asia) · 仅供演示，不构成实际金融服务</p>
      </footer>
    </div>
  );
}
