/**
 * API helper for GBA Bridge Finance frontend.
 * Uses Next.js rewrites to proxy /api requests to FastAPI backend.
 */

const API_BASE = "";

export async function apiGet<T = any>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API Error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function apiPost<T = any>(path: string, body?: any): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API Error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function apiPostForm<T = any>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API Error ${res.status}: ${text}`);
  }
  return res.json();
}

// Types
export interface Enterprise {
  id: number;
  name: string;
  name_en: string;
  region: string;
  industry: string;
  main_currencies: string;
  business_model: string;
}

export interface DocumentItem {
  id: number;
  filename: string;
  doc_type: string;
  doc_type_confidence: number;
  ocr_status: string;
  structured_data: Record<string, string>;
  ocr_confidence: Record<string, number>;
  low_confidence_fields: string[];
  confirmed: boolean;
  uploaded_at: string;
  transaction_id: number | null;
}

export interface Transaction {
  id: number;
  tx_ref: string;
  enterprise_id: number;
  buyer: string;
  seller: string;
  supplier: string;
  order_amount: number;
  order_currency: string;
  invoice_amount: number;
  invoice_currency: string;
  completeness_score: number;
  overall_risk: string;
  risk_dimensions: Record<string, string>;
  status: string;
  logistics_status: string;
}

export interface RiskAlert {
  alert_type: string;
  alert_level: string;
  alert_message: string;
  main_factors: string[];
  positive_factors: string[];
  explanation: string;
}

export interface Recommendation {
  id?: number;
  product_id: number;
  product_code?: string;
  product_name?: string;
  product_name_cn?: string;
  category?: string;
  transaction_stage: string;
  reason: string;
  estimated_amount: number;
  estimated_currency: string;
  estimated_tenor_days: number;
  use_of_funds: string;
  required_materials: string[];
  knowledge_reference: string;
  confidence: number;
  status: string;
}

export interface ScenarioResult {
  scenario_name: string;
  parameters: Record<string, number>;
  max_funding_gap: number;
  gap_currency: string;
  main_risk: string;
  modified_cashflows: any[];
}

export interface DashboardItem {
  transaction_id: number;
  tx_ref: string;
  enterprise_name: string;
  enterprise_region: string;
  buyer: string;
  supplier: string;
  order_amount: number;
  order_currency: string;
  invoice_amount: number;
  invoice_currency: string;
  completeness_score: number;
  overall_risk: string;
  risk_dimensions: Record<string, string>;
  status: string;
  logistics_status: string;
  risk_alerts_count: number;
  high_risk_alerts: number;
  recommendations_count: number;
  unconfirmed_documents: number;
  funding_gap_amount: number | null;
  funding_gap_currency: string | null;
  ai_summary: string;
  requires_manual_review: boolean;
}

export function formatCurrency(amount: number, currency: string): string {
  const symbols: Record<string, string> = {
    CNY: "¥", USD: "$", HKD: "HK$", EUR: "€", GBP: "£",
  };
  const symbol = symbols[currency] || "";
  return `${symbol}${Math.abs(amount).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

export function riskClass(level: string): string {
  const l = level.toLowerCase();
  if (l.includes("high")) return "risk-high";
  if (l.includes("medium")) return "risk-medium";
  return "risk-low";
}

export const BOUNDARY_DECLARATION =
  "AI 辅助分析，不构成信贷审批；正式申请、合规审查、风险评估与最终授信由 ICBC 按现有流程完成。AI-assisted analysis, not a credit approval; formal application, compliance review, risk assessment and final credit decision are conducted by ICBC under existing processes.";

export const ILLUSTRATIVE_NOTE =
  "Illustrative assumptions — all amounts, exchange rates and dates are for demonstration purposes only.";
