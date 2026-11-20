"use client";

import { useState, useRef, useEffect } from "react";
import { useLang } from "./LanguageProvider";
import { LANGS } from "@/lib/i18n";

export function LanguageSwitcher() {
  const { lang, setLang } = useLang();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, []);

  const current = LANGS.find((l) => l.code === lang) || LANGS[0];

  return (
    <div ref={ref} className="relative shrink-0">
      <button
        onClick={() => setOpen(!open)}
        className="px-2 py-1 rounded-lg text-sm text-white/90 hover:bg-white/15 transition flex items-center gap-1 whitespace-nowrap"
        title={current.label}
      >
        <span>{current.short}</span>
        <svg
          className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 bg-white rounded-lg shadow-lg border border-[#e5e5e8] py-1 min-w-[140px] z-50">
          {LANGS.map((l) => (
            <button
              key={l.code}
              onClick={() => {
                setLang(l.code);
                setOpen(false);
              }}
              className={`w-full text-left px-3 py-1.5 text-sm transition ${
                lang === l.code
                  ? "bg-[#fef2f2] text-[#a91624] font-medium"
                  : "text-[#1a1a1a] hover:bg-[#f7f7f8]"
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
