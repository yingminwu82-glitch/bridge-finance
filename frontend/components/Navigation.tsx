"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const enterpriseLinks = [
  { href: "/app/dashboard", label: "首页" },
  { href: "/app/documents", label: "单据管理" },
  { href: "/app/graph", label: "交易图谱" },
  { href: "/app/cashflow", label: "现金流" },
  { href: "/app/report", label: "预审报告" },
  { href: "/monitoring", label: "监控告警" },
];

const rmLinks = [
  { href: "/rm/dashboard", label: "RM 工作台" },
  { href: "/monitoring", label: "监控告警" },
];

export function Navigation({ role = "enterprise" }: { role?: "enterprise" | "rm" }) {
  const pathname = usePathname();
  const links = role === "rm" ? rmLinks : enterpriseLinks;

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
          <span>湾区融桥</span>
          <span className="text-xs font-normal opacity-70 hidden sm:inline">GBA Bridge Finance</span>
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
                {link.label}
              </Link>
            );
          })}
          {role === "enterprise" && (
            <Link
              href="/rm/dashboard"
              className="px-3 py-1.5 rounded-lg text-sm whitespace-nowrap hover:bg-white/10 border-l border-white/20 ml-1"
            >
              RM 视角 →
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
