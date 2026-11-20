"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { Lang, translate } from "@/lib/i18n";

interface LangContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: string) => string;
}

const LangContext = createContext<LangContextValue>({
  lang: "zh-CN",
  setLang: () => {},
  t: (key) => key,
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("zh-CN");

  useEffect(() => {
    const saved = typeof localStorage !== "undefined" ? localStorage.getItem("gba-lang") : null;
    if (saved === "zh-CN" || saved === "zh-TW" || saved === "en") {
      setLangState(saved);
    }
  }, []);

  const setLang = useCallback((newLang: Lang) => {
    setLangState(newLang);
    if (typeof localStorage !== "undefined") {
      localStorage.setItem("gba-lang", newLang);
    }
  }, []);

  const t = useCallback((key: string) => translate(lang, key), [lang]);

  return (
    <LangContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang() {
  return useContext(LangContext);
}
