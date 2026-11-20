"""
Lightweight backend i18n for generated (AI) text.
Supports Simplified Chinese (zh-CN), Traditional Chinese (zh-TW) and English (en).

Note: This module localizes *generated* narrative text (AI summaries, risk
explanations, recommendation reasons). It does NOT translate the Data Model —
buyer / supplier names, currencies, document types and amounts are kept as data.
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

SUPPORTED_LANGS = ("zh-CN", "zh-TW", "en")
DEFAULT_LANG = "zh-CN"


def normalize_lang(lang: Optional[str]) -> str:
    """Normalize a language code to one of the supported values."""
    if not lang:
        return DEFAULT_LANG
    lang = lang.strip()
    if lang in SUPPORTED_LANGS:
        return lang
    low = lang.lower()
    if low.startswith("zh"):
        # zh-HK / zh-TW / zh-Hant → non-simplified
        if any(k in low for k in ("tw", "hk", "hant")):
            return "zh-TW"
        return "zh-CN"
    if low.startswith("en"):
        return "en"
    return DEFAULT_LANG


# ─── Small helper ───
def _pick(lang: str, zh: str, tw: str, en: str) -> str:
    if lang == "en":
        return en
    if lang == "zh-TW":
        return tw
    return zh


def generate_ai_summary_i18n(lang: str, transaction_data: Dict, completeness_score: int,
                              risk_level: str, funding_gap: Optional[Dict]) -> str:
    """Localized AI-style transaction summary for the RM dashboard."""
    lang = normalize_lang(lang)

    buyer = transaction_data.get("buyer") or _pick(lang, "未知买家", "未知買家", "Unknown buyer")
    supplier = transaction_data.get("supplier") or _pick(lang, "未知供应商", "未知供應商", "Unknown supplier")
    order_amt = transaction_data.get("order_amount") or 0
    order_curr = transaction_data.get("order_currency") or ""
    invoice_amt = transaction_data.get("invoice_amount") or 0
    invoice_curr = transaction_data.get("invoice_currency") or ""

    parts = []

    # Opening sentences
    parts.append(_pick(
        lang,
        f"企业向 {supplier} 采购货物，用于交付海外客户 {buyer} 的订单。",
        f"企業向 {supplier} 採購貨物，用於交付海外客戶 {buyer} 的訂單。",
        f"The enterprise is purchasing goods from {supplier} for an overseas customer order from {buyer}.",
    ))

    if order_amt and invoice_amt:
        parts.append(_pick(
            lang,
            f"订单金额 {order_curr} {order_amt:,.0f}，供应商付款 {invoice_curr} {invoice_amt:,.0f}。",
            f"訂單金額 {order_curr} {order_amt:,.0f}，供應商付款 {invoice_curr} {invoice_amt:,.0f}。",
            f"The order value is {order_curr} {order_amt:,.0f}, with supplier payment of {invoice_curr} {invoice_amt:,.0f}.",
        ))

    if funding_gap:
        gap_amt = funding_gap.get("gap_amount", 0)
        gap_curr = funding_gap.get("gap_currency", "")
        gap_days = funding_gap.get("gap_duration_days", 0)
        parts.append(_pick(
            lang,
            f"主要资金压力来自 {invoice_curr} 供应商付款与 {order_curr} 客户收款之间的时间错配，"
            f"预计产生约 {gap_curr} {gap_amt:,.0f}、持续 {gap_days} 天的资金缺口。",
            f"主要資金壓力來自 {invoice_curr} 供應商付款與 {order_curr} 客戶收款之間的時間錯配，"
            f"預計產生約 {gap_curr} {gap_amt:,.0f}、持續 {gap_days} 天的資金缺口。",
            f"The main funding pressure arises from the timing mismatch between {invoice_curr} supplier payments "
            f"and {order_curr} customer collections, creating an estimated {gap_curr} {gap_amt:,.0f} funding gap over {gap_days} days.",
        ))

    if completeness_score < 100:
        parts.append(_pick(
            lang,
            f"交易完整度为 {completeness_score}/100，部分单据仍待补充。",
            f"交易完整度為 {completeness_score}/100，部分單據仍待補充。",
            f"Transaction completeness is {completeness_score}/100, with some documents still pending.",
        ))

    if risk_level and risk_level != "Low":
        risk_word = {
            "High": _pick(lang, "高", "高", "high"),
            "Medium": _pick(lang, "中", "中", "medium"),
        }.get(risk_level, risk_level)
        parts.append(_pick(
            lang,
            f"综合风险评估为{risk_word}风险，建议客户经理（RM）复核。",
            f"綜合風險評估為{risk_word}風險，建議客戶經理（RM）覆核。",
            f"Overall transaction risk is assessed as {risk_word}, requiring RM review.",
        ))

    return " ".join(parts)


def generate_risk_explanation_i18n(lang: str, overall_risk: str, dimensions: Dict,
                                    main_factors, positive_factors) -> str:
    """Localized human-readable risk explanation (Why?)."""
    lang = normalize_lang(lang)

    level_word = {
        "High": _pick(lang, "高", "高", "High"),
        "Medium": _pick(lang, "中", "中", "Medium"),
        "Low": _pick(lang, "低", "低", "Low"),
    }.get(overall_risk, overall_risk)

    parts = []
    parts.append(_pick(
        lang,
        f"综合交易风险：{level_word}。",
        f"綜合交易風險：{level_word}。",
        f"Overall Transaction Risk: {level_word}.",
    ))

    if main_factors:
        parts.append(_pick(
            lang,
            f"推动风险的主要因素：{'；'.join(main_factors)}。",
            f"推動風險的主要因素：{'；'.join(main_factors)}。",
            f"Main factors contributing to risk: {'; '.join(main_factors)}.",
        ))
    if positive_factors:
        parts.append(_pick(
            lang,
            f"降低风险的正面因素：{'；'.join(positive_factors)}。",
            f"降低風險的正面因素：{'；'.join(positive_factors)}。",
            f"Positive factors reducing risk: {'; '.join(positive_factors)}.",
        ))

    if overall_risk == "High":
        parts.append(_pick(
            lang,
            "下一步：该交易须进入人工复核（标记 → 升级 → RM 复核）。AI 输出不构成信贷决策。",
            "下一步：該交易須進入人工覆核（標記 → 升級 → RM 覆核）。AI 輸出不構成信貸決策。",
            "Next step: This transaction must enter manual review (Flag → Escalate → RM Review). AI output does not constitute a credit decision.",
        ))
    elif overall_risk == "Medium":
        parts.append(_pick(
            lang,
            "下一步：建议 RM 复核后再进入正式流程。",
            "下一步：建議 RM 覆核後再進入正式流程。",
            "Next step: RM review recommended before proceeding to formal process.",
        ))
    else:
        parts.append(_pick(
            lang,
            "下一步：交易风险较低，但正式审批前仍需 RM 核实。",
            "下一步：交易風險較低，但正式審批前仍需 RM 核實。",
            "Next step: Transaction appears low risk, but RM verification is still required before formal approval.",
        ))

    return " ".join(parts)
