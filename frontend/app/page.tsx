"use client";

import Link from "next/link";
import { BoundaryBanner } from "@/components/BoundaryBanner";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { useLang } from "@/components/LanguageProvider";

export default function HomePage() {
  const { t } = useLang();

  const capabilities = [
    { icon: "📄", title: t("home_cap_1_title"), desc: t("home_cap_1_desc") },
    { icon: "🔍", title: t("home_cap_2_title"), desc: t("home_cap_2_desc") },
    { icon: "💱", title: t("home_cap_3_title"), desc: t("home_cap_3_desc") },
    { icon: "🔗", title: t("home_cap_4_title"), desc: t("home_cap_4_desc") },
  ];

  const steps = [
    { step: "01", title: t("home_flow_1_title"), desc: t("home_flow_1_desc") },
    { step: "02", title: t("home_flow_2_title"), desc: t("home_flow_2_desc") },
    { step: "03", title: t("home_flow_3_title"), desc: t("home_flow_3_desc") },
    { step: "04", title: t("home_flow_4_title"), desc: t("home_flow_4_desc") },
  ];

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
              <div className="font-bold text-lg leading-tight">{t("home_brand")}</div>
              <div className="text-xs opacity-70 tracking-wider">{t("home_brand_sub")}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <Link
              href="/app/dashboard"
              className="bg-white text-[#a91624] px-5 py-2 rounded-lg font-semibold text-sm hover:opacity-90 transition whitespace-nowrap"
            >
              {t("home_enter_app")}
            </Link>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
          <div className="max-w-2xl">
            <div className="inline-block bg-white/10 backdrop-blur px-3 py-1 rounded-full text-xs mb-4">
              {t("home_badge")}
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold leading-tight mb-6">
              {t("home_hero_title_1")}
              <br />
              {t("home_hero_title_2")}
            </h1>
            <p className="text-lg opacity-90 mb-8 leading-relaxed">
              {t("home_hero_desc_1")}
              <br />
              {t("home_hero_desc_2")}
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/app/dashboard"
                className="bg-white text-[#a91624] px-6 py-3 rounded-xl font-semibold hover:opacity-90 transition"
              >
                {t("home_enterprise_entry")}
              </Link>
              <Link
                href="/rm/dashboard"
                className="border border-white/30 px-6 py-3 rounded-xl font-semibold hover:bg-white/10 transition"
              >
                {t("home_rm_entry")}
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Service capabilities */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <h2 className="text-2xl font-bold text-center mb-2">{t("home_cap_title")}</h2>
        <p className="text-center text-[#6b6b73] mb-10">{t("home_cap_subtitle")}</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {capabilities.map((item) => (
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
          <h2 className="text-2xl font-bold text-center mb-10">{t("home_flow_title")}</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {steps.map((item, i) => (
              <div key={item.step} className="relative">
                {i < steps.length - 1 && (
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
          <h2 className="text-2xl font-bold mb-4">{t("home_demo_title")}</h2>
          <p className="opacity-90 mb-8">{t("home_demo_desc")}</p>
          <Link
            href="/app/dashboard"
            className="inline-block bg-white text-[#a91624] px-8 py-3 rounded-xl font-semibold hover:opacity-90 transition"
          >
            {t("home_demo_cta")}
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#1a1a1a] text-white/60 py-8 text-center text-sm">
        <p>{t("home_footer")}</p>
      </footer>
    </div>
  );
}
