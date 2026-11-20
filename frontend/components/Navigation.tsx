"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLang } from "./LanguageProvider";
import { LanguageSwitcher } from "./LanguageSwitcher";

const linkKeys = [
  { href: "/app/dashboard", key: "nav_home" },
  { href: "/app/documents", key: "nav_documents" },
  { href: "/app/graph", key: "nav_graph" },
  { href: "/app/cashflow", key: "nav_cashflow" },
  { href: "/app/report", key: "nav_report" },
];

const rmLinkKeys = [
  { href: "/rm/dashboard", key: "nav_rm_dashboard" },
];

export function Navigation({ role = "enterprise" }: { role?: "enterprise" | "rm" }) {
  const pathname = usePathname();
  const { t } = useLang();
  const links = role === "rm" ? rmLinkKeys : linkKeys;

  return (
    <nav
      className="sticky top-0 z-50 shadow-sm"
      style={{
        background: "linear-gradient(135deg, #a91624 0%, #7a0f1a 100%)",
        color: "white",
      }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
        <Link href="/" className="flex items-center gap-2 font-bold text-lg shrink-0">
          <span>{t("brand")}</span>
          <span className="text-xs font-normal opacity-70 hidden sm:inline">{t("brand_sub")}</span>
        </Link>
        <div className="flex items-center gap-1 overflow-x-auto">
          {links.map((link) => {
            const active = pathname === link.href || pathname?.startsWith(link.href + "/");
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition-all ${
                  active ? "bg-white/20 font-semibold" : "hover:bg-white/10"
                }`}
              >
                {t(link.key)}
              </Link>
            );
          })}
          {role === "enterprise" && (
            <Link
              href="/rm/dashboard"
              className="px-3 py-1.5 rounded-lg text-sm whitespace-nowrap hover:bg-white/10 border-l border-white/20 ml-1"
            >
              {t("nav_rm_view")} →
            </Link>
          )}
          <div className="border-l border-white/20 ml-1 pl-1">
            <LanguageSwitcher />
          </div>
        </div>
      </div>
    </nav>
  );
}
