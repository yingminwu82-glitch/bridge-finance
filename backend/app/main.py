"""
FastAPI application for GBA Bridge Finance.
Main entry point with all API routes.
"""
import os
import sys
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import (
    get_engine, get_session_maker, init_db, Base,
    Enterprise, User, Document, OcrField, Transaction, TransactionEntity,
    TransactionLink, RiskAlert, CashflowItem, Scenario, FundingGap,
    Product, Recommendation, Review, MonitoringEvent, AuditLog
)
from app.seed import seed_database
from app.services.ocr_service import process_document, get_file_type
from app.services.doc_understanding import (
    cross_document_verification, calculate_completeness_score,
    generate_ai_summary, convert_to_unified
)
from app.services.risk_engine import (
    assess_document_risk, assess_counterparty_risk, assess_transaction_risk,
    assess_financing_risk, assess_fx_liquidity_risk, aggregate_risk,
    generate_risk_explanation, is_high_risk, should_escalate
)
from app.services.cashflow_service import (
    calculate_funding_gap, simulate_scenario, get_default_scenarios,
    build_cashflow_timeline, generate_cashflow_summary
)
from app.services.product_matcher import (
    SimpleRAG, match_products, generate_recommendation_summary,
    identify_transaction_stage
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Database Setup ───
# Use in-memory SQLite when running on Vercel (no persistent filesystem).
# Set GBA_DB_PATH env var to use a file-based database for local development.
DB_PATH = os.environ.get("GBA_DB_PATH", "sqlite:///:memory:") if os.environ.get("VERCEL") else "sqlite:///./gba_bridge_finance.db"
engine = None
SessionLocal = None


def get_db():
    global engine, SessionLocal
    if engine is None:
        try:
            engine = init_db(DB_PATH)
            SessionLocal = get_session_maker(engine)
            # Seed database and commit
            with SessionLocal() as session:
                seed_database(session)
                session.commit()
                logger.info(f"Database initialized and seeded. DB_PATH={DB_PATH}")
        except Exception as e:
            logger.error(f"Database init/seed failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── FastAPI App ───
app = FastAPI(
    title="GBA Bridge Finance API",
    description="跨境贸易金融智能分析与产品推荐系统 - AI 辅助分析，不构成信贷审批",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve uploaded files (only works in local dev; serverless uses /tmp)
if not os.environ.get("VERCEL"):
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Boundary declaration constant
BOUNDARY_DECLARATION = (
    "AI 辅助分析，不构成信贷审批；正式申请、合规审查、风险评估与最终授信由 ICBC 按现有流程完成。"
    "AI-assisted analysis, not a credit approval; formal application, compliance review, "
    "risk assessment and final credit decision are conducted by ICBC under existing processes."
)

ILLUSTRATIVE_NOTE = "Illustrative assumptions — all amounts, exchange rates and dates are for demonstration purposes only."


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "GBA Bridge Finance API", "version": "1.0.0"}


@app.get("/api/boundary")
async def get_boundary_declaration():
    """Get the AI boundary declaration shown across the platform."""
    return {
        "declaration": BOUNDARY_DECLARATION,
        "illustrative_note": ILLUSTRATIVE_NOTE,
    }


# ─── Auth Routes ───
@app.post("/api/auth/login")
async def login(username: str, password: str, db: Session = Depends(get_db)):
    """Simple demo login - returns user info and token."""
    user = db.query(User).filter(User.username == username).first()
    if not user or user.password_hash != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    enterprise = None
    if user.enterprise_id:
        enterprise = db.query(Enterprise).filter(Enterprise.id == user.enterprise_id).first()

    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "enterprise_id": user.enterprise_id,
            "assigned_enterprise_ids": user.assigned_enterprise_ids,
        },
        "enterprise": {
            "id": enterprise.id,
            "name": enterprise.name,
            "name_en": enterprise.name_en,
            "region": enterprise.region,
        } if enterprise else None,
        "token": f"demo-token-{user.id}",
        "boundary_declaration": BOUNDARY_DECLARATION,
    }


# ─── Enterprise Routes ───
@app.get("/api/enterprises")
async def list_enterprises(db: Session = Depends(get_db)):
    enterprises = db.query(Enterprise).all()
    return {"enterprises": [{"id": e.id, "name": e.name, "name_en": e.name_en,
                              "region": e.region, "industry": e.industry,
                              "main_currencies": e.main_currencies,
                              "business_model": e.business_model} for e in enterprises]}


@app.get("/api/enterprises/{enterprise_id}")
async def get_enterprise(enterprise_id: int, db: Session = Depends(get_db)):
    ent = db.query(Enterprise).filter(Enterprise.id == enterprise_id).first()
    if not ent:
        raise HTTPException(status_code=404, detail="Enterprise not found")
    return {
        "id": ent.id, "name": ent.name, "name_en": ent.name_en,
        "registration_number": ent.registration_number, "region": ent.region,
        "industry": ent.industry, "main_supplier_region": ent.main_supplier_region,
        "main_customer_region": ent.main_customer_region,
        "main_currencies": ent.main_currencies,
        "annual_trade_volume": ent.annual_trade_volume,
        "existing_bank_services": ent.existing_bank_services,
        "current_financing": ent.current_financing,
        "business_model": ent.business_model,
    }


@app.post("/api/enterprises")
async def create_enterprise(name: str, name_en: str = "", region: str = "",
                             industry: str = "", db: Session = Depends(get_db)):
    ent = Enterprise(name=name, name_en=name_en, region=region, industry=industry)
    db.add(ent)
    db.commit()
    db.refresh(ent)
    return {"id": ent.id, "name": ent.name}


# ─── Document Routes ───
@app.post("/api/documents/upload")
async def upload_document(enterprise_id: int, file: UploadFile = File(...),
                           transaction_id: Optional[int] = None,
                           db: Session = Depends(get_db)):
    """Upload a document and process it through OCR."""
    # Save file (use /tmp on Vercel serverless, local uploads dir otherwise)
    upload_dir = os.environ.get("UPLOAD_DIR", "/tmp" if os.environ.get("VERCEL") else os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads"))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Process document
    result = process_document(file_path, file.filename)

    # Create document record
    doc = Document(
        enterprise_id=enterprise_id,
        transaction_id=transaction_id,
        filename=file.filename,
        file_path=f"uploads/{file.filename}",
        file_type=result["file_type"],
        doc_type=result["doc_type"],
        doc_type_confidence=result["doc_type_confidence"],
        ocr_status="done",
        ocr_text=result["ocr_text"],
        structured_data=result["structured_data"],
        ocr_confidence=result["ocr_confidence"],
        low_confidence_fields=result["low_confidence_fields"],
        confirmed=False,
        processed_at=datetime.utcnow(),
    )
    db.add(doc)
    db.flush()

    # Create OcrField records
    for field_name, field_value in result["structured_data"].items():
        conf = result["ocr_confidence"].get(field_name, 0.95)
        ocr_field = OcrField(
            document_id=doc.id,
            field_name=field_name,
            field_value=str(field_value),
            confidence=conf,
            needs_verification=conf < 0.85,
        )
        db.add(ocr_field)

    # Audit log
    audit = AuditLog(
        enterprise_id=enterprise_id,
        actor="enterprise_user",
        action="upload_document",
        target_type="document",
        target_id=doc.id,
        details=f"Uploaded {file.filename} - classified as {result['doc_type']}",
    )
    db.add(audit)
    db.commit()
    db.refresh(doc)

    return {
        "id": doc.id,
        "filename": doc.filename,
        "doc_type": doc.doc_type,
        "doc_type_confidence": doc.doc_type_confidence,
        "ocr_status": doc.ocr_status,
        "structured_data": doc.structured_data,
        "ocr_confidence": doc.ocr_confidence,
        "low_confidence_fields": doc.low_confidence_fields,
        "needs_verification": len(doc.low_confidence_fields) > 0,
        "message": "Document processed. Low-confidence fields require RM verification before proceeding."
                   if doc.low_confidence_fields else "Document processed successfully.",
    }


@app.get("/api/documents")
async def list_documents(enterprise_id: Optional[int] = None,
                          transaction_id: Optional[int] = None,
                          db: Session = Depends(get_db)):
    query = db.query(Document)
    if enterprise_id:
        query = query.filter(Document.enterprise_id == enterprise_id)
    if transaction_id:
        query = query.filter(Document.transaction_id == transaction_id)
    docs = query.all()
    return {"documents": [{
        "id": d.id,
        "filename": d.filename,
        "doc_type": d.doc_type,
        "doc_type_confidence": d.doc_type_confidence,
        "ocr_status": d.ocr_status,
        "structured_data": d.structured_data,
        "ocr_confidence": d.ocr_confidence,
        "low_confidence_fields": d.low_confidence_fields,
        "confirmed": d.confirmed,
        "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
        "transaction_id": d.transaction_id,
    } for d in docs]}


@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    ocr_fields = db.query(OcrField).filter(OcrField.document_id == doc_id).all()

    return {
        "id": doc.id,
        "filename": doc.filename,
        "doc_type": doc.doc_type,
        "doc_type_confidence": doc.doc_type_confidence,
        "ocr_status": doc.ocr_status,
        "ocr_text": doc.ocr_text,
        "structured_data": doc.structured_data,
        "ocr_confidence": doc.ocr_confidence,
        "low_confidence_fields": doc.low_confidence_fields,
        "confirmed": doc.confirmed,
        "ocr_fields": [{
            "id": f.id,
            "field_name": f.field_name,
            "field_value": f.field_value,
            "confidence": f.confidence,
            "needs_verification": f.needs_verification,
            "confirmed_by": f.confirmed_by,
        } for f in ocr_fields],
    }


@app.post("/api/documents/{doc_id}/ocr")
async def process_ocr(doc_id: int, db: Session = Depends(get_db)):
    """Re-process OCR for a document."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = os.path.join(UPLOAD_DIR, doc.filename)
    if not os.path.exists(file_path):
        # On serverless, original file may not persist — reprocess from stored structured data
        # Return current data if file is gone
        return {
            "id": doc.id,
            "filename": doc.filename,
            "doc_type": doc.doc_type,
            "doc_type_confidence": doc.doc_type_confidence,
            "structured_data": doc.structured_data,
            "ocr_confidence": doc.ocr_confidence,
            "low_confidence_fields": doc.low_confidence_fields,
            "message": "Original file not available (serverless); returning existing OCR data."
        }

    result = process_document(file_path, doc.filename)

    doc.doc_type = result["doc_type"]
    doc.doc_type_confidence = result["doc_type_confidence"]
    doc.ocr_text = result["ocr_text"]
    doc.structured_data = result["structured_data"]
    doc.ocr_confidence = result["ocr_confidence"]
    doc.low_confidence_fields = result["low_confidence_fields"]
    doc.ocr_status = "done"
    doc.processed_at = datetime.utcnow()

    # Update OcrField records
    db.query(OcrField).filter(OcrField.document_id == doc_id).delete()
    for field_name, field_value in result["structured_data"].items():
        conf = result["ocr_confidence"].get(field_name, 0.95)
        ocr_field = OcrField(
            document_id=doc_id,
            field_name=field_name,
            field_value=str(field_value),
            confidence=conf,
            needs_verification=conf < 0.85,
        )
        db.add(ocr_field)

    db.commit()
    return {
        "id": doc.id,
        "doc_type": doc.doc_type,
        "doc_type_confidence": doc.doc_type_confidence,
        "structured_data": doc.structured_data,
        "ocr_confidence": doc.ocr_confidence,
        "low_confidence_fields": doc.low_confidence_fields,
        "message": "OCR re-processed successfully."
    }


@app.post("/api/documents/{doc_id}/confirm")
async def confirm_ocr_fields(doc_id: int, reviewer: str = "rm",
                              db: Session = Depends(get_db)):
    """Confirm OCR fields (RM verifies low-confidence fields)."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.confirmed = True
    fields = db.query(OcrField).filter(OcrField.document_id == doc_id).all()
    for f in fields:
        f.needs_verification = False
        f.confirmed_by = reviewer
        f.confirmed_at = datetime.utcnow()

    audit = AuditLog(
        enterprise_id=doc.enterprise_id,
        actor=reviewer,
        action="confirm_ocr",
        target_type="document",
        target_id=doc_id,
        details=f"OCR fields confirmed by {reviewer}",
    )
    db.add(audit)
    db.commit()

    return {"message": "OCR fields confirmed.", "confirmed": True}


# ─── Transaction Routes ───
@app.get("/api/transactions")
async def list_transactions(enterprise_id: Optional[int] = None,
                             db: Session = Depends(get_db)):
    query = db.query(Transaction)
    if enterprise_id:
        query = query.filter(Transaction.enterprise_id == enterprise_id)
    txs = query.all()
    return {"transactions": [{
        "id": t.id,
        "tx_ref": t.tx_ref,
        "enterprise_id": t.enterprise_id,
        "buyer": t.buyer,
        "seller": t.seller,
        "supplier": t.supplier,
        "order_amount": t.order_amount,
        "order_currency": t.order_currency,
        "invoice_amount": t.invoice_amount,
        "invoice_currency": t.invoice_currency,
        "completeness_score": t.completeness_score,
        "overall_risk": t.overall_risk,
        "status": t.status,
        "logistics_status": t.logistics_status,
    } for t in txs]}


@app.get("/api/transactions/{tx_id}")
async def get_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    documents = db.query(Document).filter(Document.transaction_id == tx_id).all()
    risk_alerts = db.query(RiskAlert).filter(RiskAlert.transaction_id == tx_id).all()
    cashflows = db.query(CashflowItem).filter(
        CashflowItem.transaction_id == tx_id,
        CashflowItem.scenario_id.is_(None)
    ).all()
    scenarios = db.query(Scenario).filter(Scenario.transaction_id == tx_id).all()
    recommendations = db.query(Recommendation).filter(
        Recommendation.transaction_id == tx_id
    ).all()
    funding_gaps = db.query(FundingGap).filter(FundingGap.transaction_id == tx_id).all()

    return {
        "id": tx.id,
        "tx_ref": tx.tx_ref,
        "enterprise_id": tx.enterprise_id,
        "buyer": tx.buyer,
        "seller": tx.seller,
        "supplier": tx.supplier,
        "order_amount": tx.order_amount,
        "order_currency": tx.order_currency,
        "contract_amount": tx.contract_amount,
        "contract_currency": tx.contract_currency,
        "invoice_amount": tx.invoice_amount,
        "invoice_currency": tx.invoice_currency,
        "order_date": tx.order_date.isoformat() if tx.order_date else None,
        "payment_date": tx.payment_date.isoformat() if tx.payment_date else None,
        "delivery_date": tx.delivery_date.isoformat() if tx.delivery_date else None,
        "expected_collection_date": tx.expected_collection_date.isoformat() if tx.expected_collection_date else None,
        "logistics_status": tx.logistics_status,
        "completeness_score": tx.completeness_score,
        "overall_risk": tx.overall_risk,
        "risk_dimensions": tx.risk_dimensions,
        "status": tx.status,
        "documents": [{
            "id": d.id,
            "filename": d.filename,
            "doc_type": d.doc_type,
            "doc_type_confidence": d.doc_type_confidence,
            "structured_data": d.structured_data,
            "ocr_confidence": d.ocr_confidence,
            "low_confidence_fields": d.low_confidence_fields,
            "confirmed": d.confirmed,
        } for d in documents],
        "risk_alerts": [{
            "id": r.id,
            "alert_type": r.alert_type,
            "alert_level": r.alert_level,
            "alert_message": r.alert_message,
            "main_factors": r.main_factors,
            "positive_factors": r.positive_factors,
            "explanation": r.explanation,
            "resolved": r.resolved,
        } for r in risk_alerts],
        "cashflows": [{
            "id": c.id,
            "flow_type": c.flow_type,
            "description": c.description,
            "currency": c.currency,
            "amount": c.amount,
            "flow_date": c.flow_date.isoformat() if c.flow_date else None,
        } for c in cashflows],
        "scenarios": [{
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "parameters": s.parameters,
            "max_funding_gap": s.max_funding_gap,
            "gap_currency": s.gap_currency,
            "main_risk": s.main_risk,
        } for s in scenarios],
        "funding_gaps": [{
            "id": f.id,
            "gap_currency": f.gap_currency,
            "gap_amount": f.gap_amount,
            "gap_duration_days": f.gap_duration_days,
            "gap_start_date": f.gap_start_date.isoformat() if f.gap_start_date else None,
            "gap_end_date": f.gap_end_date.isoformat() if f.gap_end_date else None,
            "primary_cause": f.primary_cause,
        } for f in funding_gaps],
        "recommendations": [{
            "id": r.id,
            "product_id": r.product_id,
            "transaction_stage": r.transaction_stage,
            "reason": r.reason,
            "estimated_amount": r.estimated_amount,
            "estimated_currency": r.estimated_currency,
            "estimated_tenor_days": r.estimated_tenor_days,
            "use_of_funds": r.use_of_funds,
            "required_materials": r.required_materials,
            "knowledge_reference": r.knowledge_reference,
            "confidence": r.confidence,
            "status": r.status,
        } for r in recommendations],
    }


@app.get("/api/transactions/{tx_id}/graph")
async def get_transaction_graph(tx_id: int, db: Session = Depends(get_db)):
    """Get the transaction relationship graph data."""
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    entities = db.query(TransactionEntity).filter(
        TransactionEntity.transaction_id == tx_id
    ).all()
    links = db.query(TransactionLink).filter(
        TransactionLink.transaction_id == tx_id
    ).all()
    documents = db.query(Document).filter(Document.transaction_id == tx_id).all()

    # Build nodes
    nodes = []
    for ent in entities:
        nodes.append({
            "data": {
                "id": f"entity_{ent.id}",
                "label": ent.entity_name,
                "type": ent.entity_type,
                "role": ent.role,
            }
        })

    # Add document nodes
    for doc in documents:
        nodes.append({
            "data": {
                "id": f"doc_{doc.id}",
                "label": doc.doc_type or doc.filename,
                "type": "document",
                "doc_type": doc.doc_type,
                "filename": doc.filename,
            }
        })

    # Build edges
    edges = []
    for link in links:
        edges.append({
            "data": {
                "id": f"link_{link.id}",
                "source": f"entity_{link.source_entity_id}",
                "target": f"entity_{link.target_entity_id}",
                "label": link.link_type,
            }
        })

    # Add document-to-entity edges (documents belong to transaction)
    for doc in documents:
        # Find the most relevant entity for this document
        if doc.doc_type == "Purchase Order":
            for ent in entities:
                if ent.entity_type == "customer":
                    edges.append({"data": {"id": f"doc_link_{doc.id}", "source": f"doc_{doc.id}", "target": f"entity_{ent.id}", "label": "from_buyer"}})
                    break
        elif doc.doc_type == "Commercial Invoice":
            for ent in entities:
                if ent.entity_type == "supplier":
                    edges.append({"data": {"id": f"doc_link_{doc.id}", "source": f"doc_{doc.id}", "target": f"entity_{ent.id}", "label": "from_supplier"}})
                    break
        elif doc.doc_type == "Sales Contract":
            for ent in entities:
                if ent.entity_type == "enterprise":
                    edges.append({"data": {"id": f"doc_link_{doc.id}", "source": f"doc_{doc.id}", "target": f"entity_{ent.id}", "label": "belongs_to"}})
                    break

    return {
        "transaction_id": tx_id,
        "tx_ref": tx.tx_ref,
        "nodes": nodes,
        "edges": edges,
        "buyer": tx.buyer,
        "seller": tx.seller,
        "supplier": tx.supplier,
    }


# ─── Risk Analysis Routes ───
@app.post("/api/risk/analyze")
async def analyze_risk(transaction_id: int, db: Session = Depends(get_db)):
    """Run risk analysis on a transaction."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    documents = db.query(Document).filter(Document.transaction_id == transaction_id).all()
    all_transactions = db.query(Transaction).filter(
        Transaction.enterprise_id == tx.enterprise_id
    ).all()

    # Convert to dicts for analysis
    doc_dicts = [{
        "doc_type": d.doc_type,
        "structured_data": d.structured_data or {},
        "ocr_confidence": d.ocr_confidence or {},
    } for d in documents]

    tx_dict = {
        "id": tx.id,
        "order_date": tx.order_date,
        "payment_date": tx.payment_date,
        "delivery_date": tx.delivery_date,
        "expected_collection_date": tx.expected_collection_date,
        "logistics_status": tx.logistics_status,
        "order_currency": tx.order_currency,
        "invoice_currency": tx.invoice_currency,
        "order_amount": tx.order_amount,
        "invoice_amount": tx.invoice_amount,
        "supplier": tx.supplier,
    }

    # Cross-document verification
    verification = cross_document_verification(doc_dicts)

    # Completeness score
    completeness = calculate_completeness_score(doc_dicts, verification)
    tx.completeness_score = completeness

    # Run all risk assessments
    all_alerts = []
    all_alerts.extend(assess_document_risk(doc_dicts, verification))
    all_alerts.extend(assess_counterparty_risk(doc_dicts, verification))
    all_alerts.extend(assess_transaction_risk(tx_dict, doc_dicts))

    all_tx_dicts = [{
        "id": t.id,
        "tx_ref": t.tx_ref,
        "supplier": t.supplier,
        "invoice_amount": t.invoice_amount,
    } for t in all_transactions]
    all_alerts.extend(assess_financing_risk(tx_dict, all_tx_dicts))

    # Get cashflows for FX risk
    cashflows = db.query(CashflowItem).filter(
        CashflowItem.transaction_id == transaction_id,
        CashflowItem.scenario_id.is_(None)
    ).all()
    cf_dicts = [{
        "currency": c.currency,
        "amount": c.amount,
        "flow_type": c.flow_type,
        "flow_date": c.flow_date,
    } for c in cashflows]

    # Get funding gap
    fg = db.query(FundingGap).filter(
        FundingGap.transaction_id == transaction_id
    ).first()
    fg_dict = None
    if fg:
        fg_dict = {
            "gap_amount": fg.gap_amount,
            "gap_currency": fg.gap_currency,
            "gap_duration_days": fg.gap_duration_days,
        }

    all_alerts.extend(assess_fx_liquidity_risk(tx_dict, cf_dicts, fg_dict))

    # Aggregate risk
    aggregated = aggregate_risk(all_alerts)
    explanation = generate_risk_explanation(
        aggregated["overall_risk"],
        aggregated["dimensions"],
        aggregated["main_factors"],
        aggregated["positive_factors"],
    )

    # Update transaction
    tx.overall_risk = aggregated["overall_risk"]
    tx.risk_dimensions = aggregated["dimensions"]

    # Clear old alerts and save new ones
    db.query(RiskAlert).filter(RiskAlert.transaction_id == transaction_id).delete()
    for alert in all_alerts:
        if alert.get("alert_level") == "Low" and "No duplicate" in alert.get("alert_message", ""):
            # Skip low-level "no issue" alerts from financing risk
            continue
        ra = RiskAlert(
            transaction_id=transaction_id,
            alert_type=alert["alert_type"],
            alert_level=alert["alert_level"],
            alert_message=alert["alert_message"],
            main_factors=alert.get("main_factors", []),
            positive_factors=alert.get("positive_factors", []),
            explanation=alert.get("explanation", ""),
        )
        db.add(ra)

    # Audit log
    audit = AuditLog(
        enterprise_id=tx.enterprise_id,
        actor="system",
        action="risk_analysis",
        target_type="transaction",
        target_id=transaction_id,
        details=f"Risk analysis completed. Overall: {aggregated['overall_risk']}, Completeness: {completeness}/100",
    )
    db.add(audit)
    db.commit()

    return {
        "transaction_id": transaction_id,
        "completeness_score": completeness,
        "overall_risk": aggregated["overall_risk"],
        "risk_dimensions": aggregated["dimensions"],
        "alerts": [{
            "alert_type": a["alert_type"],
            "alert_level": a["alert_level"],
            "alert_message": a["alert_message"],
            "main_factors": a.get("main_factors", []),
            "positive_factors": a.get("positive_factors", []),
            "explanation": a.get("explanation", ""),
        } for a in all_alerts if not (a.get("alert_level") == "Low" and "No duplicate" in a.get("alert_message", ""))],
        "explanation": explanation,
        "high_risk": is_high_risk(aggregated["overall_risk"]),
        "requires_manual_review": is_high_risk(aggregated["overall_risk"]) or should_escalate(all_alerts),
        "boundary_declaration": BOUNDARY_DECLARATION,
    }


# ─── Cashflow Routes ───
@app.post("/api/cashflow/forecast")
async def forecast_cashflow(transaction_id: int, db: Session = Depends(get_db)):
    """Calculate multi-currency cash flow forecast and funding gap."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    cashflows = db.query(CashflowItem).filter(
        CashflowItem.transaction_id == transaction_id,
        CashflowItem.scenario_id.is_(None)
    ).all()

    cf_dicts = [{
        "flow_type": c.flow_type,
        "description": c.description,
        "currency": c.currency,
        "amount": c.amount,
        "flow_date": c.flow_date,
    } for c in cashflows]

    timeline = build_cashflow_timeline(cf_dicts)
    gap_result = calculate_funding_gap(cf_dicts)
    summary = generate_cashflow_summary(cf_dicts, gap_result)

    return {
        "transaction_id": transaction_id,
        "cashflow_timeline": timeline,
        "funding_gap": gap_result,
        "summary": summary,
        "illustrative_note": ILLUSTRATIVE_NOTE,
        "boundary_declaration": BOUNDARY_DECLARATION,
    }


@app.post("/api/scenarios/simulate")
async def simulate_scenarios(transaction_id: int,
                              scenario_name: Optional[str] = None,
                              parameters: Optional[dict] = None,
                              db: Session = Depends(get_db)):
    """Simulate a scenario for a transaction."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    cashflows = db.query(CashflowItem).filter(
        CashflowItem.transaction_id == transaction_id,
        CashflowItem.scenario_id.is_(None)
    ).all()

    cf_dicts = [{
        "flow_type": c.flow_type,
        "description": c.description,
        "currency": c.currency,
        "amount": c.amount,
        "flow_date": c.flow_date,
    } for c in cashflows]

    # If no specific scenario requested, run all default scenarios
    if scenario_name and parameters:
        result = simulate_scenario(cf_dicts, scenario_name, parameters)
        return {
            "transaction_id": transaction_id,
            "scenario": result,
            "illustrative_note": ILLUSTRATIVE_NOTE,
        }
    else:
        # Run all default scenarios
        all_scenarios = get_default_scenarios()
        results = []
        for sc in all_scenarios:
            result = simulate_scenario(cf_dicts, sc["name"], sc["parameters"])
            results.append(result)

        return {
            "transaction_id": transaction_id,
            "scenarios": results,
            "illustrative_note": ILLUSTRATIVE_NOTE,
        }


# ─── Recommendations Routes ───
@app.get("/api/recommendations")
async def get_recommendations(transaction_id: Optional[int] = None,
                               db: Session = Depends(get_db)):
    """Get product recommendations for a transaction."""
    if transaction_id:
        tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")

        recs = db.query(Recommendation).filter(
            Recommendation.transaction_id == transaction_id
        ).all()
    else:
        recs = db.query(Recommendation).all()

    return {"recommendations": [{
        "id": r.id,
        "transaction_id": r.transaction_id,
        "product_id": r.product_id,
        "transaction_stage": r.transaction_stage,
        "reason": r.reason,
        "estimated_amount": r.estimated_amount,
        "estimated_currency": r.estimated_currency,
        "estimated_tenor_days": r.estimated_tenor_days,
        "use_of_funds": r.use_of_funds,
        "required_materials": r.required_materials,
        "knowledge_reference": r.knowledge_reference,
        "confidence": r.confidence,
        "status": r.status,
    } for r in recs]}


@app.post("/api/recommendations/generate")
async def generate_recommendations(transaction_id: int, db: Session = Depends(get_db)):
    """Generate new product recommendations for a transaction using the matching engine."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    products = db.query(Product).all()
    product_dicts = [{
        "id": p.id,
        "product_code": p.product_code,
        "product_name": p.product_name,
        "product_name_cn": p.product_name_cn,
        "category": p.category,
        "description": p.description,
        "applicable_stages": p.applicable_stages if isinstance(p.applicable_stages, list) else
            (json.loads(p.applicable_stages) if isinstance(p.applicable_stages, str) else []),
        "required_materials": p.required_materials if isinstance(p.required_materials, list) else
            (json.loads(p.required_materials) if isinstance(p.required_materials, str) else []),
        "knowledge_base_entry": p.knowledge_base_entry,
    } for p in products]

    # Get funding gap
    fg = db.query(FundingGap).filter(FundingGap.transaction_id == transaction_id).first()
    fg_dict = None
    if fg:
        fg_dict = {
            "gaps": [{
                "gap_amount": fg.gap_amount,
                "gap_currency": fg.gap_currency,
                "gap_duration_days": fg.gap_duration_days,
            }],
        }

    tx_dict = {
        "order_currency": tx.order_currency,
        "invoice_currency": tx.invoice_currency,
        "order_amount": tx.order_amount,
        "invoice_amount": tx.invoice_amount,
        "logistics_status": tx.logistics_status,
        "expected_collection_date": tx.expected_collection_date,
        "payment_date": tx.payment_date,
    }

    # Generate recommendations
    recommendations = match_products(tx_dict, product_dicts, fg_dict)

    # Clear old recommendations and save new ones
    db.query(Recommendation).filter(Recommendation.transaction_id == transaction_id).delete()
    for rec in recommendations:
        new_rec = Recommendation(
            transaction_id=transaction_id,
            enterprise_id=tx.enterprise_id,
            product_id=rec["product_id"],
            transaction_stage=rec["transaction_stage"],
            reason=rec["reason"],
            estimated_amount=rec["estimated_amount"],
            estimated_currency=rec["estimated_currency"],
            estimated_tenor_days=rec["estimated_tenor_days"],
            use_of_funds=rec["use_of_funds"],
            required_materials=rec["required_materials"],
            knowledge_reference=rec["knowledge_reference"],
            confidence=rec["confidence"],
            status="pending",
        )
        db.add(new_rec)

    audit = AuditLog(
        enterprise_id=tx.enterprise_id,
        actor="system",
        action="generate_recommendations",
        target_type="transaction",
        target_id=transaction_id,
        details=f"Generated {len(recommendations)} product recommendations",
    )
    db.add(audit)
    db.commit()

    return {
        "transaction_id": transaction_id,
        "recommendations": recommendations,
        "summary": generate_recommendation_summary(recommendations),
        "boundary_declaration": BOUNDARY_DECLARATION,
    }


# ─── Report Routes ───
@app.post("/api/reports/preassessment")
async def generate_preassessment_report(transaction_id: int, db: Session = Depends(get_db)):
    """Generate a standardized financing pre-assessment report."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    enterprise = db.query(Enterprise).filter(Enterprise.id == tx.enterprise_id).first()
    documents = db.query(Document).filter(Document.transaction_id == transaction_id).all()
    risk_alerts = db.query(RiskAlert).filter(RiskAlert.transaction_id == transaction_id).all()
    cashflows = db.query(CashflowItem).filter(
        CashflowItem.transaction_id == transaction_id,
        CashflowItem.scenario_id.is_(None)
    ).all()
    scenarios = db.query(Scenario).filter(Scenario.transaction_id == transaction_id).all()
    funding_gaps = db.query(FundingGap).filter(FundingGap.transaction_id == transaction_id).all()
    recommendations = db.query(Recommendation).filter(
        Recommendation.transaction_id == transaction_id
    ).all()

    # Generate AI summary
    tx_dict = {
        "buyer": tx.buyer,
        "supplier": tx.supplier,
        "order_amount": tx.order_amount,
        "order_currency": tx.order_currency,
        "invoice_amount": tx.invoice_amount,
        "invoice_currency": tx.invoice_currency,
    }
    fg_dict = None
    if funding_gaps:
        fg = funding_gaps[0]
        fg_dict = {
            "gap_amount": fg.gap_amount,
            "gap_currency": fg.gap_currency,
            "gap_duration_days": fg.gap_duration_days,
        }

    ai_summary = generate_ai_summary(tx_dict, tx.completeness_score or 0,
                                      tx.overall_risk or "Low", fg_dict)

    report = {
        "report_id": f"RPT-{tx.tx_ref}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "generated_at": datetime.utcnow().isoformat(),
        "transaction_id": transaction_id,
        "transaction_ref": tx.tx_ref,
        "boundary_declaration": BOUNDARY_DECLARATION,
        "illustrative_note": ILLUSTRATIVE_NOTE,

        "enterprise_info": {
            "name": enterprise.name,
            "name_en": enterprise.name_en,
            "region": enterprise.region,
            "industry": enterprise.industry,
            "main_supplier_region": enterprise.main_supplier_region,
            "main_customer_region": enterprise.main_customer_region,
            "main_currencies": enterprise.main_currencies,
            "business_model": enterprise.business_model,
        },
        "transaction_info": {
            "buyer": tx.buyer,
            "seller": tx.seller,
            "supplier": tx.supplier,
            "order_amount": tx.order_amount,
            "order_currency": tx.order_currency,
            "contract_amount": tx.contract_amount,
            "contract_currency": tx.contract_currency,
            "invoice_amount": tx.invoice_amount,
            "invoice_currency": tx.invoice_currency,
            "order_date": tx.order_date.isoformat() if tx.order_date else None,
            "payment_date": tx.payment_date.isoformat() if tx.payment_date else None,
            "delivery_date": tx.delivery_date.isoformat() if tx.delivery_date else None,
            "expected_collection_date": tx.expected_collection_date.isoformat() if tx.expected_collection_date else None,
            "logistics_status": tx.logistics_status,
            "documents": [{"filename": d.filename, "doc_type": d.doc_type,
                           "confirmed": d.confirmed} for d in documents],
        },
        "completeness_score": tx.completeness_score,
        "risk_analysis": {
            "overall_risk": tx.overall_risk,
            "risk_dimensions": tx.risk_dimensions,
            "alerts": [{
                "alert_type": r.alert_type,
                "alert_level": r.alert_level,
                "alert_message": r.alert_message,
                "explanation": r.explanation,
            } for r in risk_alerts],
        },
        "funding_needs": {
            "funding_gaps": [{
                "gap_currency": f.gap_currency,
                "gap_amount": f.gap_amount,
                "gap_duration_days": f.gap_duration_days,
                "primary_cause": f.primary_cause,
            } for f in funding_gaps],
            "cashflow_items": [{
                "flow_type": c.flow_type,
                "description": c.description,
                "currency": c.currency,
                "amount": c.amount,
                "flow_date": c.flow_date.isoformat() if c.flow_date else None,
            } for c in cashflows],
            "scenarios": [{
                "name": s.name,
                "max_funding_gap": s.max_funding_gap,
                "gap_currency": s.gap_currency,
                "main_risk": s.main_risk,
            } for s in scenarios],
        },
        "service_recommendations": [{
            "product_name": r.transaction_stage,  # Will be enriched
            "reason": r.reason,
            "estimated_amount": r.estimated_amount,
            "estimated_currency": r.estimated_currency,
            "estimated_tenor_days": r.estimated_tenor_days,
            "use_of_funds": r.use_of_funds,
            "knowledge_reference": r.knowledge_reference,
        } for r in recommendations],
        "ai_summary": ai_summary,
        "rm_review_required": is_high_risk(tx.overall_risk or "Low"),
    }

    audit = AuditLog(
        enterprise_id=tx.enterprise_id,
        actor="system",
        action="generate_report",
        target_type="transaction",
        target_id=transaction_id,
        details=f"Pre-assessment report generated: {report['report_id']}",
    )
    db.add(audit)
    db.commit()

    return report


# ─── RM Review Routes ───
@app.post("/api/rm/review")
async def rm_review(transaction_id: int, review_type: str,
                     reviewer: str = "rm", content: str = "",
                     risk_comment: str = "",
                     submit_to_formal: bool = False,
                     db: Session = Depends(get_db)):
    """RM performs a review action on a transaction."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    review = Review(
        transaction_id=transaction_id,
        enterprise_id=tx.enterprise_id,
        reviewer=reviewer,
        review_type=review_type,
        review_content=content,
        risk_comment=risk_comment,
        submitted_to_formal=submit_to_formal,
    )
    db.add(review)

    # Update transaction status
    if review_type == "submit_formal" or submit_to_formal:
        tx.status = "under_review"
    elif review_type == "confirm_service":
        tx.status = "under_review"

    # Audit log
    action_map = {
        "ocr_confirm": "Confirm AI-extracted information",
        "edit": "Edit information",
        "request_docs": "Request additional documents",
        "risk_comment": "Add risk comment",
        "contact": "Contact enterprise",
        "confirm_service": "Confirm financial service",
        "submit_formal": "Submit to formal process",
    }
    audit = AuditLog(
        enterprise_id=tx.enterprise_id,
        actor=reviewer,
        action=review_type,
        target_type="transaction",
        target_id=transaction_id,
        details=f"RM action: {action_map.get(review_type, review_type)}. Comment: {risk_comment or content}",
    )
    db.add(audit)
    db.commit()
    db.refresh(review)

    return {
        "id": review.id,
        "review_type": review_type,
        "message": f"RM review action recorded: {action_map.get(review_type, review_type)}",
        "transaction_status": tx.status,
        "submitted_to_formal": submit_to_formal,
        "boundary_declaration": BOUNDARY_DECLARATION if submit_to_formal else None,
    }


@app.get("/api/rm/dashboard")
async def rm_dashboard(reviewer: str = "rm", db: Session = Depends(get_db)):
    """Get RM dashboard data - overview of all assigned transactions."""
    transactions = db.query(Transaction).all()

    dashboard_items = []
    for tx in transactions:
        enterprise = db.query(Enterprise).filter(Enterprise.id == tx.enterprise_id).first()
        risk_alerts = db.query(RiskAlert).filter(
            RiskAlert.transaction_id == tx.id,
            RiskAlert.resolved == False
        ).all()
        recommendations = db.query(Recommendation).filter(
            Recommendation.transaction_id == tx.id
        ).all()
        documents = db.query(Document).filter(Document.transaction_id == tx.id).all()
        missing_docs = [d for d in documents if not d.confirmed]
        funding_gaps = db.query(FundingGap).filter(FundingGap.transaction_id == tx.id).all()

        # Generate AI summary
        tx_dict = {
            "buyer": tx.buyer,
            "supplier": tx.supplier,
            "order_amount": tx.order_amount,
            "order_currency": tx.order_currency,
            "invoice_amount": tx.invoice_amount,
            "invoice_currency": tx.invoice_currency,
        }
        fg_dict = None
        if funding_gaps:
            fg = funding_gaps[0]
            fg_dict = {
                "gap_amount": fg.gap_amount,
                "gap_currency": fg.gap_currency,
                "gap_duration_days": fg.gap_duration_days,
            }

        ai_summary = generate_ai_summary(tx_dict, tx.completeness_score or 0,
                                          tx.overall_risk or "Low", fg_dict)

        dashboard_items.append({
            "transaction_id": tx.id,
            "tx_ref": tx.tx_ref,
            "enterprise_name": enterprise.name if enterprise else "Unknown",
            "enterprise_region": enterprise.region if enterprise else "",
            "buyer": tx.buyer,
            "supplier": tx.supplier,
            "order_amount": tx.order_amount,
            "order_currency": tx.order_currency,
            "invoice_amount": tx.invoice_amount,
            "invoice_currency": tx.invoice_currency,
            "completeness_score": tx.completeness_score,
            "overall_risk": tx.overall_risk,
            "risk_dimensions": tx.risk_dimensions,
            "status": tx.status,
            "logistics_status": tx.logistics_status,
            "risk_alerts_count": len(risk_alerts),
            "high_risk_alerts": sum(1 for r in risk_alerts if r.alert_level == "High"),
            "recommendations_count": len(recommendations),
            "unconfirmed_documents": len(missing_docs),
            "funding_gap_amount": funding_gaps[0].gap_amount if funding_gaps else None,
            "funding_gap_currency": funding_gaps[0].gap_currency if funding_gaps else None,
            "ai_summary": ai_summary,
            "requires_manual_review": is_high_risk(tx.overall_risk or "Low"),
        })

    return {
        "dashboard_items": dashboard_items,
        "total_transactions": len(dashboard_items),
        "high_risk_count": sum(1 for d in dashboard_items if d["requires_manual_review"]),
        "pending_review_count": sum(1 for d in dashboard_items if d["status"] in ("analyzed", "draft")),
        "boundary_declaration": BOUNDARY_DECLARATION,
    }


# ─── Monitoring Routes ───
@app.get("/api/monitoring/events")
async def get_monitoring_events(transaction_id: Optional[int] = None,
                                 enterprise_id: Optional[int] = None,
                                 db: Session = Depends(get_db)):
    """Get monitoring events."""
    query = db.query(MonitoringEvent)
    if transaction_id:
        query = query.filter(MonitoringEvent.transaction_id == transaction_id)
    if enterprise_id:
        query = query.filter(MonitoringEvent.enterprise_id == enterprise_id)
    events = query.order_by(desc(MonitoringEvent.created_at)).all()

    return {"events": [{
        "id": e.id,
        "transaction_id": e.transaction_id,
        "enterprise_id": e.enterprise_id,
        "event_type": e.event_type,
        "event_description": e.event_description,
        "severity": e.severity,
        "metadata": e.metadata_json,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    } for e in events]}


# ─── Audit Log Routes ───
@app.get("/api/audit/logs")
async def get_audit_logs(enterprise_id: Optional[int] = None,
                          limit: int = Query(50, le=200),
                          db: Session = Depends(get_db)):
    """Get audit logs."""
    query = db.query(AuditLog)
    if enterprise_id:
        query = query.filter(AuditLog.enterprise_id == enterprise_id)
    logs = query.order_by(desc(AuditLog.created_at)).limit(limit).all()

    return {"logs": [{
        "id": l.id,
        "enterprise_id": l.enterprise_id,
        "actor": l.actor,
        "action": l.action,
        "target_type": l.target_type,
        "target_id": l.target_id,
        "details": l.details,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    } for l in logs]}


# ─── Products Routes ───
@app.get("/api/products")
async def list_products(db: Session = Depends(get_db)):
    """List all ICBC products in the knowledge base."""
    products = db.query(Product).all()
    return {"products": [{
        "id": p.id,
        "product_code": p.product_code,
        "product_name": p.product_name,
        "product_name_cn": p.product_name_cn,
        "category": p.category,
        "description": p.description,
        "eligibility": p.eligibility,
        "required_materials": p.required_materials,
        "applicable_stages": p.applicable_stages,
        "typical_amount_range": p.typical_amount_range,
        "typical_tenor": p.typical_tenor,
    } for p in products]}


if __name__ == "__main__":
    import uvicorn
    # Initialize database
    engine = init_db(DB_PATH)
    SessionLocal = get_session_maker(engine)
    with SessionLocal() as session:
        seeded = seed_database(session)
        if seeded:
            logger.info("Database seeded successfully.")
        else:
            logger.info("Database already seeded.")

    uvicorn.run(app, host="0.0.0.0", port=8000)
