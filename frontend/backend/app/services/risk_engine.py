"""
Risk rules engine.
Five categories: Document Risk, Counterparty Risk, Transaction Risk,
Financing Risk, FX and Liquidity Risk.
Each alert includes What/Why/What-next explanation.
"""
import logging
from typing import Dict, List, Optional
from datetime import date

logger = logging.getLogger(__name__)

RISK_LEVELS = ["Low", "Medium", "High"]
RISK_LEVEL_VALUES = {"Low": 1, "Medium": 2, "High": 3}
VALUE_RISK_LEVELS = {1: "Low", 2: "Medium", 3: "High"}


def assess_document_risk(documents: List[Dict], verification: Dict) -> Dict:
    """Category 1: Document Risk - checks for missing, expired, or conflicting documents."""
    alerts = []
    missing = verification.get("missing_documents", [])
    mismatches = verification.get("mismatches", [])

    if missing:
        level = "High" if "Bill of Lading" in missing and len(missing) > 1 else "Medium"
        alerts.append({
            "alert_type": "document_risk",
            "alert_level": level,
            "code": "doc_missing",
            "params": {"docs": ", ".join(missing)},
            "alert_message": f"Missing Information: {', '.join(missing)} not uploaded.",
            "main_factors": [f"{doc_type} not uploaded" for doc_type in missing],
            "positive_factors": ["Core transaction documents present" if len(missing) <= 1 else "Partial documents present"],
            "explanation": f"The transaction is missing the following document(s): {', '.join(missing)}. "
                         f"This affects the ability to fully verify the transaction. "
                         f"RM should request the missing document(s) from the enterprise.",
        })

    for mismatch in mismatches:
        alerts.append({
            "alert_type": "document_risk",
            "alert_level": "Low" if mismatch["type"] == "Amount Mismatch" else "Medium",
            "code": "doc_mismatch",
            "params": {"type": mismatch["type"], "details": mismatch["details"]},
            "alert_message": f"{mismatch['type']}: {mismatch['details']}",
            "main_factors": [mismatch["details"]],
            "positive_factors": ["Other document fields are consistent"] if not missing else [],
            "explanation": f"A {mismatch['type']} was detected during cross-document verification. "
                         f"This does not necessarily indicate fraud, but RM should verify the discrepancy.",
        })

    return alerts


def assess_counterparty_risk(documents: List[Dict], verification: Dict) -> Dict:
    """Category 2: Counterparty Risk - checks Buyer/Seller/Supplier/Account Holder consistency."""
    alerts = []

    # Check for new payment account (low OCR confidence on account field)
    for doc in documents:
        if doc.get("doc_type") == "Payment Schedule":
            conf = doc.get("ocr_confidence", {})
            if "Account" in conf and conf["Account"] < 0.85:
                alerts.append({
                    "alert_type": "counterparty_risk",
                    "alert_level": "Medium",
                    "code": "account_change",
                    "params": {},
                    "alert_message": "Payment Account Change: Supplier payment account extracted with low confidence.",
                    "main_factors": [f"Payment account OCR confidence: {conf['Account']:.0%}", "Account may differ from historical records"],
                    "positive_factors": ["Supplier name matches across invoice and payment schedule"],
                    "explanation": "The payment account number was extracted with low OCR confidence. "
                                 "This may indicate a new account or OCR error. RM should verify the account "
                                 "with the enterprise before proceeding.",
                })

    # Check for buyer/supplier inconsistency
    for mismatch in verification.get("mismatches", []):
        if "Buyer" in mismatch["type"] or "Supplier" in mismatch["type"]:
            alerts.append({
                "alert_type": "counterparty_risk",
                "alert_level": "High",
                "code": "counterparty_inconsistency",
                "params": {"type": mismatch["type"], "details": mismatch["details"]},
                "alert_message": f"{mismatch['type']}: {mismatch['details']}",
                "main_factors": [mismatch["details"]],
                "positive_factors": [],
                "explanation": f"A {mismatch['type']} was detected. The counterparty information differs across documents. "
                             f"This requires RM verification to confirm the actual transaction parties.",
            })

    return alerts


def assess_transaction_risk(transaction: Dict, documents: List[Dict]) -> Dict:
    """Category 3: Transaction Risk - checks amount, date, direction, logistics."""
    alerts = []

    # Check date reasonableness
    order_date = transaction.get("order_date")
    payment_date = transaction.get("payment_date")
    delivery_date = transaction.get("delivery_date")
    collection_date = transaction.get("expected_collection_date")

    if payment_date and collection_date:
        if isinstance(payment_date, str):
            payment_date = date.fromisoformat(payment_date)
        if isinstance(collection_date, str):
            collection_date = date.fromisoformat(collection_date)
        gap_days = (collection_date - payment_date).days
        if gap_days > 90:
            alerts.append({
                "alert_type": "transaction_risk",
                "alert_level": "Medium",
                "code": "extended_collection",
                "params": {"days": gap_days},
                "alert_message": f"Extended collection period: {gap_days} days between supplier payment and customer collection.",
                "main_factors": [f"Collection gap: {gap_days} days"],
                "positive_factors": [],
                "explanation": f"The gap between supplier payment and customer collection is {gap_days} days, "
                             f"which is longer than typical. This increases working capital pressure and receivable risk.",
            })

    # Check logistics status
    logistics_status = transaction.get("logistics_status", "pending")
    if logistics_status == "missing" or logistics_status == "pending":
        alerts.append({
            "alert_type": "transaction_risk",
            "alert_level": "Medium",
            "code": "logistics_missing",
            "params": {},
            "alert_message": "Logistics information missing or pending - cannot verify goods movement.",
            "main_factors": ["No logistics document uploaded", "Cannot verify shipment status"],
            "positive_factors": [],
            "explanation": "Without logistics documentation, the system cannot verify that goods have been shipped "
                         "or are in transit. RM should request the bill of lading.",
        })

    return alerts


def assess_financing_risk(transaction: Dict, all_transactions: List[Dict]) -> Dict:
    """Category 4: Financing Risk - checks for duplicate financing, already-financed invoices."""
    alerts = []

    # Check for duplicate financing (same invoice used in multiple transactions)
    tx_invoice = transaction.get("invoice_amount")
    tx_supplier = transaction.get("supplier")

    if all_transactions:
        for other_tx in all_transactions:
            if other_tx.get("id") == transaction.get("id"):
                continue
            # Check if same supplier and similar invoice amount
            if (other_tx.get("supplier") == tx_supplier and
                other_tx.get("invoice_amount") == tx_invoice):
                alerts.append({
                    "alert_type": "financing_risk",
                    "alert_level": "High",
                    "code": "duplicate_financing",
                    "params": {},
                    "alert_message": "Potential Duplicate Financing: Similar invoice from same supplier found in another transaction.",
                    "main_factors": [f"Supplier: {tx_supplier}", f"Invoice amount match with transaction {other_tx.get('tx_ref')}"],
                    "positive_factors": [],
                    "explanation": "A potential duplicate financing situation has been detected. The same supplier and "
                                 "invoice amount appear in another transaction. This requires immediate RM verification.",
                })
                break

    if not alerts:
        alerts.append({
            "alert_type": "financing_risk",
            "alert_level": "Low",
            "code": "no_duplicate",
            "params": {},
            "alert_message": "No duplicate financing indicator detected.",
            "main_factors": [],
            "positive_factors": ["No duplicate invoices detected across transactions", "Invoice appears unique"],
            "explanation": "The system has checked all transactions for this enterprise and found no duplicate "
                         "financing indicators. The invoice appears to be unique.",
        })

    return alerts


def assess_fx_liquidity_risk(transaction: Dict, cashflow_items: List[Dict],
                              funding_gap: Optional[Dict] = None) -> Dict:
    """Category 5: FX and Liquidity Risk - multi-currency exposure, timing mismatches."""
    alerts = []

    # Collect currencies
    currencies = set()
    for cf in cashflow_items:
        currencies.add(cf.get("currency", ""))

    order_curr = transaction.get("order_currency", "")
    invoice_curr = transaction.get("invoice_currency", "")
    if order_curr:
        currencies.add(order_curr)
    if invoice_curr:
        currencies.add(invoice_curr)

    currencies.discard("")
    multi_currency = len(currencies) > 1

    if multi_currency:
        # Check if CNY and USD both present (common FX risk pattern)
        has_cny = "CNY" in currencies
        has_usd = "USD" in currencies

        if has_cny and has_usd:
            order_amt = transaction.get("order_amount", 0)
            invoice_amt = transaction.get("invoice_amount", 0)

            alerts.append({
                "alert_type": "fx_risk",
                "alert_level": "High",
                "code": "fx_exposure",
                "params": {
                    "inv_cur": invoice_curr, "inv_amt": f"{invoice_amt:,.0f}",
                    "ord_cur": order_curr, "ord_amt": f"{order_amt:,.0f}",
                },
                "alert_message": f"High FX Exposure: {invoice_curr} {invoice_amt:,.0f} supplier payment paired with "
                               f"{order_curr} {order_amt:,.0f} customer collection.",
                "main_factors": [
                    f"{invoice_curr} outflow paired with {order_curr} inflow",
                    f"Exchange rate volatility could affect actual payment cost",
                    f"Multi-currency gap: {len(currencies)} currencies involved"
                ],
                "positive_factors": ["Transaction documents support the trade background"],
                "explanation": f"The enterprise has {invoice_curr} supplier payments and {order_curr} customer collections. "
                             f"Exchange rate movements between {invoice_curr} and {order_curr} could significantly "
                             f"affect the actual cost of supplier payments. FX risk management is recommended.",
            })

    # Check funding gap
    if funding_gap and funding_gap.get("gap_amount", 0) > 0:
        gap_amt = funding_gap["gap_amount"]
        gap_curr = funding_gap.get("gap_currency", "")
        gap_days = funding_gap.get("gap_duration_days", 0)

        level = "High" if gap_amt > 10000000 else ("Medium" if gap_amt > 1000000 else "Low")
        alerts.append({
            "alert_type": "fx_risk",
            "alert_level": level,
            "code": "funding_gap",
            "params": {"cur": gap_curr, "amt": f"{gap_amt:,.0f}", "days": gap_days},
            "alert_message": f"Potential Funding Gap: {gap_curr} {gap_amt:,.0f} over {gap_days} days.",
            "main_factors": [f"Funding gap: {gap_curr} {gap_amt:,.0f}", f"Duration: {gap_days} days", "Timing mismatch between payment and collection"],
            "positive_factors": [],
            "explanation": f"A funding gap of {gap_curr} {gap_amt:,.0f} has been identified, lasting approximately "
                         f"{gap_days} days. This gap arises from the timing mismatch between supplier payment "
                         f"and customer collection. The enterprise may need short-term financing.",
        })

    return alerts


def aggregate_risk(alerts: List[Dict]) -> Dict:
    """Aggregate all risk alerts into overall risk level and dimensions."""
    dimensions = {
        "Document Consistency": "Low Risk",
        "Missing Information": "Low Risk",
        "Duplicate Financing Indicator": "Low Risk",
        "Payment Account Change": "Low Risk",
        "FX Exposure": "Low Risk",
        "Overall Transaction Risk": "Low"
    }

    max_level = 1  # Start at Low

    for alert in alerts:
        level_val = RISK_LEVEL_VALUES.get(alert.get("alert_level", "Low"), 1)

        # Map alert to dimension
        atype = alert.get("alert_type", "")
        if atype == "document_risk":
            msg = alert.get("alert_message", "")
            if "Missing" in msg:
                dimensions["Missing Information"] = VALUE_RISK_LEVELS[max(level_val, RISK_LEVEL_VALUES[dimensions["Missing Information"].replace(" Risk", "")])]
                dimensions["Missing Information"] = f"{alert['alert_level']} Risk"
            else:
                dimensions["Document Consistency"] = f"{alert['alert_level']} Risk"
        elif atype == "counterparty_risk":
            msg = alert.get("alert_message", "")
            if "Account" in msg:
                dimensions["Payment Account Change"] = f"{alert['alert_level']} Risk"
        elif atype == "financing_risk":
            if alert["alert_level"] == "High":
                dimensions["Duplicate Financing Indicator"] = "High Risk"
            # Low level means no duplicate detected
        elif atype == "fx_risk":
            dimensions["FX Exposure"] = f"{alert['alert_level']} Risk"

        max_level = max(max_level, level_val)

    overall = VALUE_RISK_LEVELS[max_level]
    dimensions["Overall Transaction Risk"] = overall

    # Collect all main factors and positive factors
    all_main_factors = []
    all_positive_factors = []
    for alert in alerts:
        all_main_factors.extend(alert.get("main_factors", []))
        all_positive_factors.extend(alert.get("positive_factors", []))

    return {
        "overall_risk": overall,
        "dimensions": dimensions,
        "main_factors": list(set(all_main_factors)),
        "positive_factors": list(set(all_positive_factors)),
    }


def localize_alerts(alerts: List[Dict], lang: str) -> List[Dict]:
    """Return alerts with localized human-readable text (Data Model untouched)."""
    if not lang or lang == "en":
        return alerts
    from app.services.risk_labels import localize_alert
    return [localize_alert(a, lang) for a in alerts]


def generate_risk_explanation(overall_risk: str, dimensions: Dict,
                               main_factors: List[str], positive_factors: List[str],
                               lang: str = "zh-CN") -> str:
    """Generate a localized human-readable risk explanation (Why?)."""
    from app.services.i18n import generate_risk_explanation_i18n
    return generate_risk_explanation_i18n(lang, overall_risk, dimensions,
                                           main_factors, positive_factors)


def is_high_risk(overall_risk: str) -> bool:
    """Check if a transaction is high risk and must enter manual review."""
    return overall_risk == "High"


def should_escalate(alerts: List[Dict]) -> bool:
    """Check if any high-risk alert requires escalation."""
    return any(alert.get("alert_level") == "High" for alert in alerts)
