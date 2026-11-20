"use client";

import { useLang } from "./LanguageProvider";

export function BoundaryBanner({ compact = false }: { compact?: boolean }) {
  const { t } = useLang();

  if (compact) {
    return (
      <div
        className="text-xs px-3 py-2 rounded-lg border"
        style={{
          background: "#fff8e1",
          borderColor: "#f0d060",
          color: "#856404",
        }}
      >
        ⚠ {t("boundary_title")} · {t("boundary_desc")}
      </div>
    );
  }
  return (
    <div className="boundary-banner">
      <div className="flex items-start gap-2">
        <span className="text-base">⚠</span>
        <div>
          <p className="font-semibold">{t("boundary_title")}</p>
          <p className="mt-1">{t("boundary_desc")}</p>
          <p className="illustrative-note mt-1">{t("boundary_illustrative")}</p>
        </div>
      </div>
    </div>
  );
}
