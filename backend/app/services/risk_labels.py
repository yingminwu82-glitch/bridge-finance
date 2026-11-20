"""
Localization helpers for risk engine output.

The risk engine emits structured alerts:
    {
        "alert_type": "document_risk",
        "alert_level": "Medium",
        "alert_message": <English sentence>,
        "main_factors": [...],
        "positive_factors": [...],
        "explanation": <English paragraph>,
        "code": "<stable machine key>",      # added by risk_engine
        "params": {...},                      # parameters for formatting
    }

This module renders those alerts into the requested language, so the Data Model
(document types, amounts, currencies, names) stays untouched while the human
readable text is localized.
"""
from typing import Dict

# Stable machine keys → per-language templates
TEMPLATES: Dict[str, Dict[str, Dict[str, str]]] = {
    # ── Document risk ──
    "doc_missing": {
        "zh-CN": {"msg": "资料缺失：{docs} 未上传。", "exp": "本交易缺少以下单据：{docs}，影响对交易的完整核实。客户经理应向企业索取缺失单据。"},
        "zh-TW": {"msg": "資料缺失：{docs} 未上傳。", "exp": "本交易缺少以下單據：{docs}，影響對交易的完整核實。客戶經理應向企業索取缺失單據。"},
        "en": {"msg": "Missing Information: {docs} not uploaded.", "exp": "The transaction is missing the following document(s): {docs}. This affects the ability to fully verify the transaction. RM should request the missing document(s) from the enterprise."},
    },
    "doc_mismatch": {
        "zh-CN": {"msg": "{type}：{details}", "exp": "跨单据核验中发现{type}。这不一定代表欺诈，但客户经理应核实该差异。"},
        "zh-TW": {"msg": "{type}：{details}", "exp": "跨單據核驗中發現{type}。這不一定代表欺詐，但客戶經理應核實該差異。"},
        "en": {"msg": "{type}: {details}", "exp": "A {type} was detected during cross-document verification. This does not necessarily indicate fraud, but RM should verify the discrepancy."},
    },
    "buyer_inconsistency": {"zh-CN": {"msg": "买方不一致", "exp": "买方不一致"}, "zh-TW": {"msg": "買方不一致", "exp": "買方不一致"}, "en": {"msg": "Buyer Inconsistency", "exp": "Buyer Inconsistency"}},
    "supplier_inconsistency": {"zh-CN": {"msg": "供应商不一致", "exp": "供应商不一致"}, "zh-TW": {"msg": "供應商不一致", "exp": "供應商不一致"}, "en": {"msg": "Supplier Inconsistency", "exp": "Supplier Inconsistency"}},
    "amount_mismatch": {"zh-CN": {"msg": "金额不一致", "exp": "金额不一致"}, "zh-TW": {"msg": "金額不一致", "exp": "金額不一致"}, "en": {"msg": "Amount Mismatch", "exp": "Amount Mismatch"}},
    # ── Counterparty risk ──
    "account_change": {
        "zh-CN": {"msg": "付款账户变更：供应商付款账户提取置信度较低。", "exp": "付款账号的 OCR 识别置信度较低，可能为新账户或识别误差。客户经理应在推进前与企业核实该账户。"},
        "zh-TW": {"msg": "付款帳戶變更：供應商付款帳戶提取置信度較低。", "exp": "付款帳號的 OCR 識別置信度較低，可能為新帳戶或識別誤差。客戶經理應在推進前與企業核實該帳戶。"},
        "en": {"msg": "Payment Account Change: Supplier payment account extracted with low confidence.", "exp": "The payment account number was extracted with low OCR confidence. This may indicate a new account or OCR error. RM should verify the account with the enterprise before proceeding."},
    },
    "counterparty_inconsistency": {
        "zh-CN": {"msg": "{type}：{details}", "exp": "检测到{type}。各单据中的交易对手信息不一致，需客户经理核实实际交易对手。"},
        "zh-TW": {"msg": "{type}：{details}", "exp": "檢測到{type}。各單據中的交易對手資訊不一致，需客戶經理核實實際交易對手。"},
        "en": {"msg": "{type}: {details}", "exp": "A {type} was detected. The counterparty information differs across documents. This requires RM verification to confirm the actual transaction parties."},
    },
    # ── Transaction risk ──
    "extended_collection": {
        "zh-CN": {"msg": "收款周期偏长：供应商付款与客户收款间隔 {days} 天。", "exp": "供应商付款与客户收款之间间隔 {days} 天，长于常规水平，加大营运资金压力与应收账款风险。"},
        "zh-TW": {"msg": "收款週期偏長：供應商付款與客戶收款間隔 {days} 天。", "exp": "供應商付款與客戶收款之間間隔 {days} 天，長於常規水平，加大營運資金壓力與應收帳款風險。"},
        "en": {"msg": "Extended collection period: {days} days between supplier payment and customer collection.", "exp": "The gap between supplier payment and customer collection is {days} days, which is longer than typical. This increases working capital pressure and receivable risk."},
    },
    "logistics_missing": {
        "zh-CN": {"msg": "物流信息缺失或待定——无法核实货物流动。", "exp": "缺少物流单据时，系统无法核验货物是否已发运或在途。客户经理应索取提单（Bill of Lading）。"},
        "zh-TW": {"msg": "物流資訊缺失或待定——無法核實貨物流動。", "exp": "缺少物流單據時，系統無法核驗貨物是否已發運或在途。客戶經理應索取提單（Bill of Lading）。"},
        "en": {"msg": "Logistics information missing or pending - cannot verify goods movement.", "exp": "Without logistics documentation, the system cannot verify that goods have been shipped or are in transit. RM should request the bill of lading."},
    },
    # ── Financing risk ──
    "duplicate_financing": {
        "zh-CN": {"msg": "疑似重复融资：在其他交易中发现同一供应商的相似发票。", "exp": "检测到疑似重复融资情况：同一供应商及发票金额出现在另一笔交易中，需客户经理立即核实。"},
        "zh-TW": {"msg": "疑似重複融資：在其他交易中發現同一供應商的相似發票。", "exp": "檢測到疑似重複融資情況：同一供應商及發票金額出現在另一筆交易中，需客戶經理立即核實。"},
        "en": {"msg": "Potential Duplicate Financing: Similar invoice from same supplier found in another transaction.", "exp": "A potential duplicate financing situation has been detected. The same supplier and invoice amount appear in another transaction. This requires immediate RM verification."},
    },
    "no_duplicate": {
        "zh-CN": {"msg": "未检测到重复融资迹象。", "exp": "系统已核对该企业的全部交易，未发现重复融资迹象，该发票看来是唯一的。"},
        "zh-TW": {"msg": "未檢測到重複融資跡象。", "exp": "系統已核對該企業的全部交易，未發現重複融資跡象，該發票看來是唯一的。"},
        "en": {"msg": "No duplicate financing indicator detected.", "exp": "The system has checked all transactions for this enterprise and found no duplicate financing indicators. The invoice appears to be unique."},
    },
    # ── FX & liquidity risk ──
    "fx_exposure": {
        "zh-CN": {"msg": "较高外汇敞口：{inv_cur} {inv_amt} 供应商付款对应 {ord_cur} {ord_amt} 客户收款。", "exp": "企业存在 {inv_cur} 供应商付款与 {ord_cur} 客户收款。{inv_cur} 与 {ord_cur} 之间的汇率波动会显著影响供应商付款的实际成本，建议进行外汇风险管理。"},
        "zh-TW": {"msg": "較高外匯敞口：{inv_cur} {inv_amt} 供應商付款對應 {ord_cur} {ord_amt} 客戶收款。", "exp": "企業存在 {inv_cur} 供應商付款與 {ord_cur} 客戶收款。{inv_cur} 與 {ord_cur} 之間的匯率波動會顯著影響供應商付款的實際成本，建議進行外匯風險管理。"},
        "en": {"msg": "High FX Exposure: {inv_cur} {inv_amt} supplier payment paired with {ord_cur} {ord_amt} customer collection.", "exp": "The enterprise has {inv_cur} supplier payments and {ord_cur} customer collections. Exchange rate movements between {inv_cur} and {ord_cur} could significantly affect the actual cost of supplier payments. FX risk management is recommended."},
    },
    "funding_gap": {
        "zh-CN": {"msg": "潜在资金缺口：{cur} {amt}，持续 {days} 天。", "exp": "已识别约 {cur} {amt} 的资金缺口，持续约 {days} 天，源于供应商付款与客户收款之间的时间错配。企业可能需要短期融资。"},
        "zh-TW": {"msg": "潛在資金缺口：{cur} {amt}，持續 {days} 天。", "exp": "已識別約 {cur} {amt} 的資金缺口，持續約 {days} 天，源於供應商付款與客戶收款之間的時間錯配。企業可能需要短期融資。"},
        "en": {"msg": "Potential Funding Gap: {cur} {amt} over {days} days.", "exp": "A funding gap of {cur} {amt} has been identified, lasting approximately {days} days. This gap arises from the timing mismatch between supplier payment and customer collection. The enterprise may need short-term financing."},
    },
}

# Localized terminology used inside params (e.g. mismatch types, factors)
TERMS: Dict[str, Dict[str, str]] = {
    "Buyer Inconsistency": {"zh-CN": "买方不一致", "zh-TW": "買方不一致", "en": "Buyer Inconsistency"},
    "Supplier Inconsistency": {"zh-CN": "供应商不一致", "zh-TW": "供應商不一致", "en": "Supplier Inconsistency"},
    "Amount Mismatch": {"zh-CN": "金额不一致", "zh-TW": "金額不一致", "en": "Amount Mismatch"},
    "not uploaded": {"zh-CN": "未上传", "zh-TW": "未上傳", "en": "not uploaded"},
}


def _term(text: str, lang: str) -> str:
    return TERMS.get(text, {}).get(lang, text)


def localize_alert(alert: Dict, lang: str) -> Dict:
    """Return a copy of the alert with localized alert_message / explanation.

    The alert_type / alert_level / main_factors / positive_factors remain
    untouched to preserve the Data Model. Only the free-text narrative is
    localized using the stable `code` + `params`.
    """
    if not lang or lang == "en":
        return alert

    code = alert.get("code")
    tmpl = TEMPLATES.get(code, {}).get(lang) if code else None
    if not tmpl:
        return alert

    params = dict(alert.get("params", {}) or {})
    # Localize known enum-like params
    if "type" in params:
        params["type"] = _term(params["type"], lang)
    if "docs" in params:
        params["docs"] = params["docs"]

    localized = dict(alert)
    try:
        localized["alert_message"] = tmpl["msg"].format(**params)
        localized["explanation"] = tmpl["exp"].format(**params)
    except (KeyError, IndexError):
        return alert
    return localized
