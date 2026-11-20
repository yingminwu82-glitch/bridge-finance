"""
Document understanding service.
Handles document classification, unified data structure conversion,
cross-document verification, and transaction completeness scoring.
"""
import logging
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

# Unified data structure fields
UNIFIED_FIELDS = ["Buyer", "Seller", "Supplier", "Amount", "Currency", "Date", "Payment", "Logistics"]

# Mapping from document-specific fields to unified structure
FIELD_MAPPING = {
    "Purchase Order": {
        "Buyer": "Buyer",
        "Seller": "Seller",
        "Order No.": "Order No.",
        "Order Amount": "Amount",
        "Currency": "Currency",
        "Order Date": "Date",
        "Delivery Date": "Logistics",
        "Delivery Terms": "Logistics",
    },
    "Sales Contract": {
        "Buyer": "Buyer",
        "Seller": "Seller",
        "Contract No.": "Contract No.",
        "Contract Value": "Amount",
        "Currency": "Currency",
        "Contract Date": "Date",
        "Payment Terms": "Payment",
    },
    "Commercial Invoice": {
        "Supplier": "Supplier",
        "Invoice No.": "Invoice No.",
        "Invoice Date": "Date",
        "Amount": "Amount",
        "Currency": "Currency",
        "Payment Due Date": "Payment",
        "Buyer": "Buyer",
    },
    "Payment Schedule": {
        "Payment Date": "Payment",
        "Amount": "Amount",
        "Currency": "Currency",
        "Account": "Account",
        "Beneficiary": "Supplier",
    },
    "Bill of Lading": {
        "Shipment No.": "Logistics",
        "Origin": "Logistics",
        "Destination": "Logistics",
        "Shipment Date": "Logistics",
        "Quantity": "Logistics",
    },
}


def convert_to_unified(doc_type: str, structured_data: Dict) -> Dict[str, str]:
    """Convert document-specific fields to unified data structure."""
    mapping = FIELD_MAPPING.get(doc_type, {})
    unified = {}

    for src_field, unified_field in mapping.items():
        if src_field in structured_data:
            value = structured_data[src_field]
            if unified_field in unified:
                unified[unified_field] += f" | {value}"
            else:
                unified[unified_field] = value

    return unified


def cross_document_verification(documents: List[Dict]) -> Dict:
    """
    Verify consistency across multiple documents.
    Returns: {
        "consistencies": [...],
        "mismatches": [...],
        "missing_documents": [...],
    }
    """
    consistencies = []
    mismatches = []
    missing_documents = []

    # Collect amounts from different documents
    amounts = {}
    currencies = {}
    buyers = {}
    suppliers = {}

    for doc in documents:
        doc_type = doc.get("doc_type", "")
        data = doc.get("structured_data", {})

        if "Buyer" in data:
            buyers[doc_type] = data["Buyer"]
        if "Supplier" in data:
            suppliers[doc_type] = data["Supplier"]
        if "Amount" in data or "Order Amount" in data or "Contract Value" in data:
            amt = data.get("Amount") or data.get("Order Amount") or data.get("Contract Value")
            amounts[doc_type] = amt
        if "Currency" in data:
            currencies[doc_type] = data["Currency"]

    # Check buyer consistency
    unique_buyers = set(buyers.values())
    if len(unique_buyers) == 1 and len(buyers) > 1:
        consistencies.append(f"Buyer consistent across documents: {list(buyers.values())[0]}")
    elif len(unique_buyers) > 1:
        mismatches.append({
            "type": "Buyer Inconsistency",
            "details": f"Buyer differs across documents: {dict(buyers)}"
        })

    # Check supplier consistency
    unique_suppliers = set(suppliers.values())
    if len(unique_suppliers) == 1 and len(suppliers) > 1:
        consistencies.append(f"Supplier consistent across documents: {list(suppliers.values())[0]}")
    elif len(unique_suppliers) > 1:
        mismatches.append({
            "type": "Supplier Inconsistency",
            "details": f"Supplier differs across documents: {dict(suppliers)}"
        })

    # Check amount consistency (accounting for currency differences)
    # For cross-border trade, amounts may be in different currencies
    if len(amounts) > 1:
        # If all same currency, check exact match
        unique_currencies_for_amounts = set()
        for doc_type in amounts:
            if doc_type in currencies:
                unique_currencies_for_amounts.add(currencies[doc_type])

        if len(unique_currencies_for_amounts) <= 1:
            unique_amounts = set(str(a) for a in amounts.values())
            if len(unique_amounts) == 1:
                consistencies.append(f"Amount consistent across documents: {list(amounts.values())[0]}")
            else:
                mismatches.append({
                    "type": "Amount Mismatch",
                    "details": f"Amounts differ across documents: {dict(amounts)}"
                })
        else:
            consistencies.append(f"Amounts in different currencies (expected for cross-border trade): {dict(amounts)}")

    # Check for missing document types
    required_types = ["Purchase Order", "Sales Contract", "Commercial Invoice"]
    present_types = [doc.get("doc_type") for doc in documents]
    for req in required_types:
        if req not in present_types:
            missing_documents.append(req)

    # Check for logistics document
    has_logistics = any(
        doc.get("doc_type") in ("Bill of Lading", "Packing List")
        for doc in documents
    )
    if not has_logistics:
        missing_documents.append("Bill of Lading")

    return {
        "consistencies": consistencies,
        "mismatches": mismatches,
        "missing_documents": missing_documents,
    }


def calculate_completeness_score(documents: List[Dict], verification: Dict) -> int:
    """
    Calculate Transaction Completeness Score (0-100).
    Based on document presence, field completeness, and cross-document consistency.
    """
    score = 0
    max_score = 100

    # Document type presence (40 points)
    doc_types_present = set()
    for doc in documents:
        doc_types_present.add(doc.get("doc_type"))

    doc_type_weights = {
        "Purchase Order": 10,
        "Sales Contract": 10,
        "Commercial Invoice": 10,
        "Payment Schedule": 5,
        "Bill of Lading": 5,
    }
    for dt, weight in doc_type_weights.items():
        if dt in doc_types_present:
            score += weight

    # Field completeness (30 points)
    total_fields = 0
    filled_fields = 0
    for doc in documents:
        structured = doc.get("structured_data", {})
        total_fields += len(structured)
        filled_fields += sum(1 for v in structured.values() if v)

    if total_fields > 0:
        score += int((filled_fields / total_fields) * 30)

    # Cross-document consistency (20 points)
    consistencies = verification.get("consistencies", [])
    mismatches = verification.get("mismatches", [])
    score += min(len(consistencies) * 7, 20)
    score -= min(len(mismatches) * 10, 20)

    # Missing documents penalty (10 points)
    missing = verification.get("missing_documents", [])
    score -= min(len(missing) * 4, 10)

    return max(0, min(100, score))


def generate_ai_summary(transaction_data: Dict, completeness_score: int,
                        risk_level: str, funding_gap: Optional[Dict],
                        lang: str = "zh-CN") -> str:
    """Generate a localized AI-style transaction summary.

    Delegates narrative generation to app.services.i18n so the Data Model
    (names, currencies, amounts) stays untouched while the text is localized.
    """
    from app.services.i18n import generate_ai_summary_i18n
    return generate_ai_summary_i18n(lang, transaction_data, completeness_score,
                                    risk_level, funding_gap)


def check_duplicate_financing(transactions: List[Dict], invoice_no: str = None,
                               order_no: str = None) -> Dict:
    """
    Check if the same invoice or order has been used in multiple financing applications.
    """
    if not invoice_no and not order_no:
        return {"duplicate_detected": False, "details": "No invoice or order number provided for duplicate check."}

    duplicates = []
    for tx in transactions:
        tx_invoices = tx.get("invoice_numbers", [])
        tx_orders = tx.get("order_numbers", [])

        if invoice_no and invoice_no in tx_invoices and tx.get("id") != tx.get("current_tx_id"):
            duplicates.append({
                "transaction_id": tx.get("id"),
                "tx_ref": tx.get("tx_ref"),
                "matched_field": "invoice_no",
                "matched_value": invoice_no
            })

        if order_no and order_no in tx_orders and tx.get("id") != tx.get("current_tx_id"):
            duplicates.append({
                "transaction_id": tx.get("id"),
                "tx_ref": tx.get("tx_ref"),
                "matched_field": "order_no",
                "matched_value": order_no
            })

    return {
        "duplicate_detected": len(duplicates) > 0,
        "duplicates": duplicates,
        "details": f"Found {len(duplicates)} potential duplicate(s)." if duplicates else "No duplicates detected."
    }
