"""
Financial product matching engine with simple RAG.
Matches ICBC products to transaction stages and funding needs.
Uses retrieval-first, generation-second approach to prevent AI hallucination.
"""
import logging
import json
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

# Transaction lifecycle stages in order
TRANSACTION_STAGES = ["Order", "Procurement", "Shipment", "Receivable", "Collection"]

# Stage to financial need mapping
STAGE_NEEDS = {
    "Order": "Pre-delivery Funding Need (procurement funding for confirmed order)",
    "Procurement": "Supplier Payment Funding Need (CNY funding and settlement)",
    "Shipment": "Working Capital Gap (goods in transit, payment pending)",
    "Receivable": "Receivables Financing Need (customer payment not yet received)",
    "Collection": "Settlement and FX Need (multi-currency receipts)",
}


class SimpleRAG:
    """Simple Retrieval-Augmented Generation using keyword matching.
    No external LLM required - works fully offline."""

    def __init__(self, knowledge_base: List[Dict]):
        self.knowledge_base = knowledge_base
        # Build simple inverted index
        self.index = defaultdict(list)
        for i, entry in enumerate(knowledge_base):
            text = (entry.get("knowledge_base_entry", "") + " " +
                   entry.get("product_name", "") + " " +
                   entry.get("product_name_cn", "") + " " +
                   entry.get("category", "") + " " +
                   entry.get("description", "")).lower()
            for word in text.split():
                self.index[word].append(i)

    def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[int, float, str]]:
        """Retrieve relevant knowledge base entries for a query."""
        query_words = query.lower().split()
        scores = defaultdict(float)

        for word in query_words:
            for idx in self.index.get(word, []):
                scores[idx] += 1

        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for idx, score in ranked:
            entry = self.knowledge_base[idx]
            relevance = min(score / max(len(query_words), 1), 1.0)
            source_text = entry.get("knowledge_base_entry", "")
            results.append((idx, relevance, source_text))

        return results

    def generate_explanation(self, transaction_data: Dict, product: Dict,
                              stage: str, retrieved_sources: List) -> str:
        """Generate an explanation for a product recommendation using retrieved knowledge."""
        parts = []

        # What
        parts.append(f"At the {stage} stage, the enterprise may benefit from {product['product_name']} ({product['product_name_cn']}).")

        # Why - based on transaction data
        order_curr = transaction_data.get("order_currency", "")
        invoice_curr = transaction_data.get("invoice_currency", "")
        gap_amount = transaction_data.get("funding_gap_amount", 0)
        gap_curr = transaction_data.get("funding_gap_currency", "")

        reasons = []
        if stage in ("Order", "Procurement") and gap_amount:
            reasons.append(f"a funding gap of {gap_curr} {gap_amount:,.0f} has been identified")
        if stage == "Procurement" and invoice_curr == "CNY":
            reasons.append(f"CNY payment to GBA supplier requires cross-border settlement")
        if stage in ("Shipment", "Receivable") and order_curr and invoice_curr and order_curr != invoice_curr:
            reasons.append(f"timing mismatch between {invoice_curr} supplier payment and {order_curr} customer collection")
        if stage == "Receivable":
            reasons.append("goods have been shipped but customer payment has not yet been received")
        if order_curr and invoice_curr and order_curr != invoice_curr:
            reasons.append(f"FX exposure from {invoice_curr}/{order_curr} currency mismatch")

        if reasons:
            parts.append(f"The recommendation is primarily driven by: {'; '.join(reasons)}.")

        # Source reference
        if retrieved_sources:
            source_text = retrieved_sources[0][2][:200]
            parts.append(f"Source: {source_text}...")

        return " ".join(parts)


def identify_transaction_stage(transaction: Dict) -> str:
    """Identify the current transaction stage based on transaction data."""
    logistics_status = transaction.get("logistics_status", "pending")
    collection_date = transaction.get("expected_collection_date")
    payment_date = transaction.get("payment_date")
    delivery_date = transaction.get("delivery_date")
    order_date = transaction.get("order_date")

    # If collection date has passed and payment received → Collection
    # If goods delivered but not collected → Receivable
    # If goods shipped but not delivered → Shipment
    # If supplier payment due → Procurement
    # If order confirmed → Order

    if logistics_status == "delivered" and collection_date:
        return "Receivable"
    elif logistics_status in ("shipped", "in_transit"):
        return "Shipment"
    elif payment_date:
        return "Procurement"
    elif order_date:
        return "Order"

    return "Order"  # Default


def match_products(transaction: Dict, products: List[Dict],
                    funding_gap: Optional[Dict] = None,
                    rag: Optional[SimpleRAG] = None) -> List[Dict]:
    """
    Match ICBC products to the transaction based on stage, funding gap, and currency.
    Returns list of recommendations with explanations and source references.
    """
    if rag is None:
        rag = SimpleRAG(products)

    stage = identify_transaction_stage(transaction)
    recommendations = []

    order_curr = transaction.get("order_currency", "")
    invoice_curr = transaction.get("invoice_currency", "")
    multi_currency = order_curr != invoice_curr and order_curr and invoice_curr

    gap_amount = 0
    gap_curr = ""
    gap_days = 0
    if funding_gap and funding_gap.get("gaps"):
        first_gap = funding_gap["gaps"][0]
        gap_amount = first_gap["gap_amount"]
        gap_curr = first_gap["gap_currency"]
        gap_days = first_gap.get("gap_duration_days", 0)

    # Build query for RAG retrieval
    query_parts = [stage.lower()]
    if invoice_curr:
        query_parts.append(invoice_curr.lower())
    if order_curr:
        query_parts.append(order_curr.lower())
    if gap_amount:
        query_parts.append("funding")
        query_parts.append("financing")
    if multi_currency:
        query_parts.append("fx")
        query_parts.append("exchange")
    query = " ".join(query_parts)

    retrieved = rag.retrieve(query, top_k=5)

    # Match products by applicable stages
    for product in products:
        applicable_stages = product.get("applicable_stages", [])
        if isinstance(applicable_stages, str):
            try:
                applicable_stages = json.loads(applicable_stages)
            except:
                applicable_stages = []

        if stage in applicable_stages:
            # Generate explanation
            tx_data_for_rag = {
                "order_currency": order_curr,
                "invoice_currency": invoice_curr,
                "funding_gap_amount": gap_amount,
                "funding_gap_currency": gap_curr,
            }
            explanation = rag.generate_explanation(tx_data_for_rag, product, stage, retrieved)

            # Find the most relevant retrieved source for this product
            source_ref = ""
            for idx, rel, src in retrieved:
                if idx == product.get("id") or product.get("product_code", "") in src:
                    source_ref = src[:300]
                    break
            if not source_ref and retrieved:
                source_ref = retrieved[0][2][:300]

            # Determine estimated amount and tenor
            est_amount = gap_amount if gap_amount else 0
            est_curr = gap_curr if gap_curr else invoice_curr
            est_tenor = gap_days if gap_days else 60

            # Determine use of funds based on stage
            use_of_funds_map = {
                "Order": "Procurement funding for confirmed order",
                "Procurement": "Supplier payment",
                "Shipment": "Working capital during transit",
                "Receivable": "Bridging receivable period",
                "Collection": "Settlement and FX management",
            }

            required_materials = product.get("required_materials", [])
            if isinstance(required_materials, str):
                try:
                    required_materials = json.loads(required_materials)
                except:
                    required_materials = []

            recommendations.append({
                "product_id": product.get("id"),
                "product_code": product.get("product_code"),
                "product_name": product.get("product_name"),
                "product_name_cn": product.get("product_name_cn"),
                "category": product.get("category"),
                "transaction_stage": stage,
                "reason": explanation,
                "estimated_amount": est_amount,
                "estimated_currency": est_curr,
                "estimated_tenor_days": est_tenor,
                "use_of_funds": use_of_funds_map.get(stage, "Trade financing"),
                "required_materials": required_materials,
                "knowledge_reference": f"{product.get('product_code')}: {source_ref}",
                "confidence": min(0.95, 0.70 + len(explanation) / 1000),
            })

    return recommendations


def generate_recommendation_summary(recommendations: List[Dict]) -> str:
    """Generate a summary of all recommendations."""
    if not recommendations:
        return "No product recommendations at this time."

    parts = [f"Based on the current transaction stage, {len(recommendations)} potential ICBC service(s) have been identified:"]
    for rec in recommendations:
        parts.append(f"- {rec['product_name_cn']} ({rec['product_name']}): {rec['reason'][:100]}...")

    parts.append("\nNote: These are AI-assisted recommendations for RM reference only. "
                 "Formal service confirmation and approval will be conducted through ICBC's existing processes.")
    return "\n".join(parts)
