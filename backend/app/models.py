"""
Database models for GBA Bridge Finance.
All tables follow the schema specified in the project proposal.
"""
import json
from datetime import datetime, date
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float, DateTime, Date,
    Boolean, ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

Base = declarative_base()


class Enterprise(Base):
    __tablename__ = "enterprises"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    name_en = Column(String(200))
    registration_number = Column(String(50))
    region = Column(String(50))  # e.g. Hong Kong, GBA, Overseas
    industry = Column(String(100))
    main_supplier_region = Column(String(100))
    main_customer_region = Column(String(100))
    main_currencies = Column(String(200))  # comma-separated: HKD,CNY,USD
    annual_trade_volume = Column(String(50))
    existing_bank_services = Column(Text)
    current_financing = Column(Text)
    payment_methods = Column(Text)
    business_model = Column(Text)  # description of business model
    business_model_zh = Column(Text)  # Simplified Chinese version
    business_model_tw = Column(Text)  # Traditional Chinese version
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="enterprise")
    documents = relationship("Document", back_populates="enterprise")
    transactions = relationship("Transaction", back_populates="enterprise")
    cashflow_items = relationship("CashflowItem", back_populates="enterprise")
    recommendations = relationship("Recommendation", back_populates="enterprise")
    reviews = relationship("Review", back_populates="enterprise")
    monitoring_events = relationship("MonitoringEvent", back_populates="enterprise")
    audit_logs = relationship("AuditLog", back_populates="enterprise")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)  # plain text for demo
    display_name = Column(String(100))
    role = Column(String(20), nullable=False)  # enterprise_user, rm, risk_team
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=True)
    assigned_enterprise_ids = Column(Text)  # comma-separated for RM
    created_at = Column(DateTime, default=datetime.utcnow)

    enterprise = relationship("Enterprise", back_populates="users")


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20))  # pdf, image, excel
    doc_type = Column(String(50))  # Purchase Order, Invoice, Contract, etc.
    doc_type_confidence = Column(Float, default=0.0)
    ocr_status = Column(String(20), default="pending")  # pending, processing, done, failed
    ocr_text = Column(Text)
    structured_data = Column(JSON)  # extracted fields as JSON
    ocr_confidence = Column(JSON)  # per-field confidence
    low_confidence_fields = Column(JSON)  # fields needing manual verification
    confirmed = Column(Boolean, default=False)  # RM confirmed OCR results
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)

    enterprise = relationship("Enterprise", back_populates="documents")
    transaction = relationship("Transaction", back_populates="documents")
    ocr_fields = relationship("OcrField", back_populates="document")


class OcrField(Base):
    __tablename__ = "ocr_fields"
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    field_name = Column(String(50), nullable=False)  # Supplier, Invoice No., Amount, etc.
    field_value = Column(String(500))
    confidence = Column(Float, default=0.0)
    needs_verification = Column(Boolean, default=False)
    confirmed_by = Column(String(50))
    confirmed_at = Column(DateTime)

    document = relationship("Document", back_populates="ocr_fields")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=False)
    tx_ref = Column(String(50))  # transaction reference
    buyer = Column(String(200))
    seller = Column(String(200))
    supplier = Column(String(200))
    order_amount = Column(Float)
    order_currency = Column(String(10))
    contract_amount = Column(Float)
    contract_currency = Column(String(10))
    invoice_amount = Column(Float)
    invoice_currency = Column(String(10))
    order_date = Column(Date)
    payment_date = Column(Date)
    delivery_date = Column(Date)
    expected_collection_date = Column(Date)
    logistics_status = Column(String(50))  # pending, shipped, delivered, missing
    completeness_score = Column(Integer, default=0)  # 0-100
    overall_risk = Column(String(20))  # Low, Medium, High
    risk_dimensions = Column(JSON)  # detailed risk breakdown
    status = Column(String(30), default="draft")  # draft, analyzed, under_review, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    enterprise = relationship("Enterprise", back_populates="transactions")
    documents = relationship("Document", back_populates="transaction")
    entities = relationship("TransactionEntity", back_populates="transaction")
    links = relationship("TransactionLink", back_populates="transaction")
    risk_alerts = relationship("RiskAlert", back_populates="transaction")
    cashflow_items = relationship("CashflowItem", back_populates="transaction")
    scenarios = relationship("Scenario", back_populates="transaction")
    funding_gaps = relationship("FundingGap", back_populates="transaction")
    recommendations = relationship("Recommendation", back_populates="transaction")
    reviews = relationship("Review", back_populates="transaction")
    monitoring_events = relationship("MonitoringEvent", back_populates="transaction")


class TransactionEntity(Base):
    __tablename__ = "transaction_entities"
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    entity_type = Column(String(30), nullable=False)  # enterprise, customer, supplier, bank_account, logistics, financing
    entity_name = Column(String(200), nullable=False)
    role = Column(String(50))  # Buyer, Seller, Supplier, Consignee, Account Holder
    metadata_json = Column(JSON)

    transaction = relationship("Transaction", back_populates="entities")


class TransactionLink(Base):
    __tablename__ = "transaction_links"
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    source_entity_id = Column(Integer, ForeignKey("transaction_entities.id"), nullable=False)
    target_entity_id = Column(Integer, ForeignKey("transaction_entities.id"), nullable=False)
    link_type = Column(String(50))  # sells_to, purchases_from, belongs_to, corresponds_to, settles, based_on
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)

    transaction = relationship("Transaction", back_populates="links")


class RiskAlert(Base):
    __tablename__ = "risk_alerts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    alert_type = Column(String(50))  # document_risk, counterparty_risk, transaction_risk, financing_risk, fx_risk
    alert_level = Column(String(20))  # Low, Medium, High
    alert_code = Column(String(50))  # stable machine key for i18n (e.g. doc_missing)
    alert_params = Column(JSON)  # parameters for localized templating
    alert_message = Column(Text)
    main_factors = Column(JSON)  # list of factors contributing to risk
    positive_factors = Column(JSON)  # list of factors reducing risk
    explanation = Column(Text)  # Why explanation
    resolved = Column(Boolean, default=False)
    resolved_by = Column(String(50))
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="risk_alerts")


class CashflowItem(Base):
    __tablename__ = "cashflow_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=False)
    flow_type = Column(String(30))  # inflow, outflow
    description = Column(String(200))
    description_code = Column(String(50))  # stable key for i18n
    description_params = Column(JSON)  # template parameters
    currency = Column(String(10))
    amount = Column(Float)
    flow_date = Column(Date)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=True)  # null = baseline

    transaction = relationship("Transaction", back_populates="cashflow_items")
    enterprise = relationship("Enterprise", back_populates="cashflow_items")
    scenario = relationship("Scenario", back_populates="cashflow_items")


class Scenario(Base):
    __tablename__ = "scenarios"
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    name = Column(String(100))  # Base Case, Customer Delay +15 days, etc.
    description = Column(Text)
    parameters = Column(JSON)  # delay_days, fx_change_pct, etc.
    max_funding_gap = Column(Float)
    gap_currency = Column(String(10))
    main_risk = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="scenarios")
    cashflow_items = relationship("CashflowItem", back_populates="scenario")


class FundingGap(Base):
    __tablename__ = "funding_gaps"
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    gap_currency = Column(String(10))
    gap_amount = Column(Float)
    gap_duration_days = Column(Integer)
    gap_start_date = Column(Date)
    gap_end_date = Column(Date)
    primary_cause = Column(Text)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="funding_gaps")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_code = Column(String(20), unique=True)
    product_name = Column(String(100))
    product_name_cn = Column(String(100))
    product_name_tw = Column(String(100))  # Traditional Chinese product name
    category = Column(String(50))  # Trade Finance, Bank Guarantee, Cross-border Lending, Treasury, SME Financing
    description = Column(Text)
    eligibility = Column(Text)
    required_materials = Column(JSON)
    applicable_stages = Column(JSON)  # list of transaction stages
    typical_amount_range = Column(String(100))
    typical_tenor = Column(String(100))
    knowledge_base_entry = Column(Text)  # RAG source text
    created_at = Column(DateTime, default=datetime.utcnow)


class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    transaction_stage = Column(String(50))
    reason = Column(Text)
    estimated_amount = Column(Float)
    estimated_currency = Column(String(10))
    estimated_tenor_days = Column(Integer)
    use_of_funds = Column(String(200))
    required_materials = Column(JSON)
    knowledge_reference = Column(Text)  # Source/Knowledge Reference
    confidence = Column(Float, default=0.0)
    status = Column(String(30), default="pending")  # pending, accepted, rejected, converted
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="recommendations")
    enterprise = relationship("Enterprise", back_populates="recommendations")


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=False)
    reviewer = Column(String(50))
    review_type = Column(String(50))  # ocr_confirm, edit, request_docs, risk_comment, contact, confirm_service, submit_formal
    review_content = Column(Text)
    risk_comment = Column(Text)
    submitted_to_formal = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="reviews")
    enterprise = relationship("Enterprise", back_populates="reviews")


class MonitoringEvent(Base):
    __tablename__ = "monitoring_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=False)
    event_type = Column(String(50))  # shipment_update, payment_received, payment_overdue, fx_change, new_funding_gap
    event_description = Column(Text)
    severity = Column(String(20))  # info, warning, critical
    metadata_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="monitoring_events")
    enterprise = relationship("Enterprise", back_populates="monitoring_events")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=True)
    actor = Column(String(50))
    action = Column(String(50))
    target_type = Column(String(50))
    target_id = Column(Integer)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    enterprise = relationship("Enterprise", back_populates="audit_logs")


# Database engine and session
# Default to in-memory SQLite for serverless (Vercel) compatibility.
# Set GBA_DB_PATH env var to use a file-based database for local development.
import os as _os
DB_PATH = _os.environ.get("GBA_DB_PATH", "sqlite:///./gba_bridge_finance.db")

def get_engine(db_path=None):
    path = db_path or DB_PATH
    if path == ":memory:" or "sqlite:///:memory:" in path:
        # For in-memory SQLite, use StaticPool to share a single connection
        # across all sessions — otherwise tables created by create_all
        # won't be visible to sessions using a different connection.
        from sqlalchemy.pool import StaticPool
        return create_engine(
            "sqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(path, echo=False, connect_args={"check_same_thread": False})

def get_session_maker(engine):
    return sessionmaker(bind=engine)

def init_db(db_path=None):
    """Create all tables."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine
