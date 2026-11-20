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
                             stage: str, retrieved_sources: List,
                             lang: str = "zh-CN") -> str:
        """Generate an explanation for a product recommendation using retrieved knowledge.

        Supports localized output for zh-CN / zh-TW / en.
        """
        from app.services.i18n import normalize_lang, _pick
        lang = normalize_lang(lang)

        parts = []

        # Localized product names
        name_cn = product.get("product_name_cn") or product.get("product_name", "")
        name_tw = product.get("product_name_tw") or name_cn
        name_en = product.get("product_name") or name_cn
        product_name_localized = _pick(lang, name_cn, name_tw, name_en)
        product_name_alt = _pick(lang, name_en, name_en, name_cn)

        stage_label = {
            "Order": _pick(lang, "订单", "訂單", "Order"),
            "Procurement": _pick(lang, "采购", "採購", "Procurement"),
            "Shipment": _pick(lang, "发货运输", "發貨運輸", "Shipment"),
            "Receivable": _pick(lang, "应收账款", "應收帳款", "Receivable"),
            "Collection": _pick(lang, "收款结算", "收款結算", "Collection"),
        }.get(stage, stage)

        # What
        parts.append(_pick(
            lang,
            f"当前处于{stage_label}阶段，企业可考虑 {product_name_localized}（{product_name_alt}）。",
            f"目前處於{stage_label}階段，企業可考慮 {product_name_localized}（{product_name_alt}）。",
            f"At the {stage_label} stage, the enterprise may benefit from {product_name_localized} ({product_name_alt}).",
        ))

        # Why - based on transaction data
        order_curr = transaction_data.get("order_currency", "")
        invoice_curr = transaction_data.get("invoice_currency", "")
        gap_amount = transaction_data.get("funding_gap_amount", 0)
        gap_curr = transaction_data.get("funding_gap_currency", "")

        reasons = []
        if stage in ("Order", "Procurement") and gap_amount:
            reasons.append(_pick(
                lang,
                f"已识别约 {gap_curr} {gap_amount:,.0f} 的资金缺口",
                f"已識別約 {gap_curr} {gap_amount:,.0f} 的資金缺口",
                f"a funding gap of {gap_curr} {gap_amount:,.0f} has been identified",
            ))
        if stage == "Procurement" and invoice_curr == "CNY":
            reasons.append(_pick(
                lang,
                "向大湾区供应商支付人民币需要跨境结算支持",
                "向大灣區供應商支付人民幣需要跨境結算支持",
                "CNY payment to GBA supplier requires cross-border settlement",
            ))
        if stage in ("Shipment", "Receivable") and order_curr and invoice_curr and order_curr != invoice_curr:
            reasons.append(_pick(
                lang,
                f"{invoice_curr} 供应商付款与 {order_curr} 客户收款之间存在时间错配",
                f"{invoice_curr} 供應商付款與 {order_curr} 客戶收款之間存在時間錯配",
                f"timing mismatch between {invoice_curr} supplier payment and {order_curr} customer collection",
            ))
        if stage == "Receivable":
            reasons.append(_pick(
                lang,
                "货物已发运但客户付款尚未到账",
                "貨物已發運但客戶付款尚未到帳",
                "goods have been shipped but customer payment has not yet been received",
            ))
        if order_curr and invoice_curr and order_curr != invoice_curr:
            reasons.append(_pick(
                lang,
                f"{invoice_curr}/{order_curr} 币种错配带来外汇风险",
                f"{invoice_curr}/{order_curr} 幣別錯配帶來外匯風險",
                f"FX exposure from {invoice_curr}/{order_curr} currency mismatch",
            ))

        if reasons:
            parts.append(_pick(
                lang,
                f"推荐主要依据：{'；'.join(reasons)}。",
                f"推薦主要依據：{'；'.join(reasons)}。",
                f"The recommendation is primarily driven by: {'; '.join(reasons)}.",
            ))

        # Source reference (prefer the recommended product's own knowledge entry)
        source_text = (product.get("knowledge_base_entry")
                       or (retrieved_sources[0][2] if retrieved_sources else ""))
        source_text = source_text[:200]
        if source_text:
            parts.append(_pick(
                lang,
                f"知识来源：{source_text}...",
                f"知識來源：{source_text}...",
                f"Source: {source_text}...",
            ))

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
                    rag: Optional[SimpleRAG] = None,
                    lang: str = "zh-CN",
                    max_results: int = 6) -> List[Dict]:
    """
    Match ICBC products to the transaction based on stage, funding gap, and currency.
    Returns list of recommendations with explanations and source references.
    `lang` controls the language of the generated `reason` text.
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

    from app.services.i18n import normalize_lang, _pick
    lang_n = normalize_lang(lang)

    # Match products by applicable stages (seed order = priority)
    for pos, product in enumerate(products):
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
            explanation = rag.generate_explanation(tx_data_for_rag, product, stage, retrieved, lang=lang)

            # Find the most relevant retrieved source for this product
            source_ref = ""
            for idx, rel, src in retrieved:
                if idx == pos:
                    source_ref = src[:300]
                    break
            if not source_ref:
                source_ref = product.get("knowledge_base_entry", "")[:300]

            # Determine estimated amount and tenor
            est_amount = gap_amount if gap_amount else 0
            est_curr = gap_curr if gap_curr else invoice_curr
            est_tenor = gap_days if gap_days else 60

            # Determine use of funds based on stage (localized)
            use_of_funds_map = {
                "Order": _pick(lang_n, "已确认订单的采购资金", "已確認訂單的採購資金", "Procurement funding for confirmed order"),
                "Procurement": _pick(lang_n, "供应商付款", "供應商付款", "Supplier payment"),
                "Shipment": _pick(lang_n, "在途期间营运资金", "在途期間營運資金", "Working capital during transit"),
                "Receivable": _pick(lang_n, "应收账款周转过渡", "應收帳款週轉過渡", "Bridging receivable period"),
                "Collection": _pick(lang_n, "结算与外汇管理", "結算與外匯管理", "Settlement and FX management"),
            }

            required_materials = product.get("required_materials", [])
            if isinstance(required_materials, str):
                try:
                    required_materials = json.loads(required_materials)
                except:
                    required_materials = []

            name_cn = product.get("product_name_cn") or product.get("product_name", "")
            name_tw = product.get("product_name_tw") or name_cn
            name_en = product.get("product_name") or name_cn

            recommendations.append({
                "product_id": product.get("id"),
                "product_code": product.get("product_code"),
                "product_name": product.get("product_name"),
                "product_name_cn": product.get("product_name_cn"),
                "product_name_tw": product.get("product_name_tw"),
                "product_name_localized": _pick(lang_n, name_cn, name_tw, name_en),
                "category": product.get("category"),
                "description": product.get("description"),
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

    return recommendations[:max_results]


def generate_recommendation_summary(recommendations: List[Dict], lang: str = "zh-CN") -> str:
    """Generate a localized summary of all recommendations."""
    from app.services.i18n import normalize_lang, _pick
    lang = normalize_lang(lang)

    if not recommendations:
        return _pick(lang, "暂无产品推荐。", "暫無產品推薦。", "No product recommendations at this time.")

    parts = [_pick(
        lang,
        f"根据当前交易阶段，共识别 {len(recommendations)} 项潜在工银服务：",
        f"根據目前交易階段，共識別 {len(recommendations)} 項潛在工銀服務：",
        f"Based on the current transaction stage, {len(recommendations)} potential ICBC service(s) have been identified:",
    )]
    for rec in recommendations:
        name_cn = rec.get('product_name_cn')
        name_tw = rec.get('product_name_tw') or name_cn
        name_en = rec.get('product_name')
        name_localized = rec.get('product_name_localized')
        if name_localized:
            name = name_localized
        elif lang == "en":
            name = name_en or name_cn
        elif lang == "zh-TW":
            name = name_tw
        else:
            name = name_cn
        parts.append(f"- {name}: {rec['reason'][:120]}...")

    parts.append(_pick(
        lang,
        "\n说明：以上为 AI 辅助推荐，仅供客户经理（RM）参考。正式服务确认及审批将按工银现有流程执行。",
        "\n說明：以上為 AI 輔助推薦，僅供客戶經理（RM）參考。正式服務確認及審批將按工銀現有流程執行。",
        "\nNote: These are AI-assisted recommendations for RM reference only. "
        "Formal service confirmation and approval will be conducted through ICBC's existing processes.",
    ))
    return "\n".join(parts)
