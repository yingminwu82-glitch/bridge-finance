"""
Seed data for GBA Bridge Finance.
Includes enterprises, users, transactions, products, and demo documents.
"""
import json
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app.models import (
    Enterprise, User, Document, OcrField, Transaction, TransactionEntity,
    TransactionLink, RiskAlert, CashflowItem, Scenario, FundingGap,
    Product, Recommendation, Review, MonitoringEvent, AuditLog
)


# ─── ICBC Product Knowledge Base ───
PRODUCTS_DATA = [
    # ── Import trade finance ──
    {
        "product_code": "IF001",
        "product_name": "Import Invoice Financing",
        "product_name_cn": "进口发票融资",
        "product_name_tw": "進口發票融資",
        "category": "Trade Finance",
        "description": "Financing at the time of purchasing goods, by presenting the supplier's invoice and shipping documents. Suitable when the enterprise must pay the supplier before the overseas customer settles.",
        "eligibility": "Genuine import trade background; supplier invoice and shipping documents available; supplier payment falls due before customer collection.",
        "required_materials": ["Purchase Order", "Commercial Invoice", "Bill of Lading", "Payment Schedule"],
        "applicable_stages": ["Procurement"],
        "typical_amount_range": "CNY 500K - 30M",
        "typical_tenor": "30-90 days",
        "knowledge_base_entry": "ICBC (Asia) Import Invoice Financing lets an importer obtain short-term financing at the time of purchasing goods by presenting the supplier's commercial invoice and shipping documents. It is suitable for procurement funding when payment is due to the supplier before collection from the overseas customer, reducing pressure on working capital."
    },
    {
        "product_code": "ILC002",
        "product_name": "Import Letter of Credit Issuance",
        "product_name_cn": "进口信用证开立",
        "product_name_tw": "進口信用證開立",
        "category": "Trade Finance",
        "description": "ICBC (Asia) issues the import L/C to the exporter according to the importer's instructions, improving negotiation position, securing the transaction and reducing funds tied up before settlement.",
        "eligibility": "Importer and exporter agree to settle by L/C; underlying trade contract and import documents available.",
        "required_materials": ["Purchase Order", "Sales Contract", "L/C Application"],
        "applicable_stages": ["Order", "Procurement"],
        "typical_amount_range": "CNY 500K - 50M",
        "typical_tenor": "Up to 180 days",
        "knowledge_base_entry": "ICBC (Asia) Import Letter of Credit Issuance supports importers who settle with exporters by L/C. The bank issues the L/C according to the applicant's instructions, giving the exporter a conditional payment commitment from the issuing bank, improving bargaining power, securing trade documentation and reducing funds tied up before settlement."
    },
    {
        "product_code": "BBL003",
        "product_name": "Back-to-Back / Front-to-Back L/C",
        "product_name_cn": "背对背信用证",
        "product_name_tw": "背對背信用證",
        "category": "Trade Finance",
        "description": "For trade intermediaries: issue an import L/C (baby L/C) to the supplier based on the master L/C received from the downstream buyer, keeping upstream and downstream parties confidential.",
        "eligibility": "Enterprise acts as trade intermediary; holds a master L/C as beneficiary; needs to pay upstream suppliers before downstream collection.",
        "required_materials": ["Master L/C", "Sales Contract", "Supplier Contract"],
        "applicable_stages": ["Order", "Procurement"],
        "typical_amount_range": "CNY 1M - 100M",
        "typical_tenor": "Up to 180 days",
        "knowledge_base_entry": "ICBC (Asia) Back-to-Back or Front-to-Back L/C issuance allows a trade intermediary holding a master L/C to issue a baby L/C to its supplier for the same goods. The importer's bank L/C serves as the payment source, payment is secured for the upstream supplier, and buyer and supplier information stays confidential. Suitable for procurement funding of trading companies."
    },
    {
        "product_code": "SGR004",
        "product_name": "Shipping Guarantee",
        "product_name_cn": "提货担保",
        "product_name_tw": "提貨擔保",
        "category": "Trade Finance",
        "description": "Support goods delivery before the shipping documents arrive, avoiding demurrage, port storage costs and losses from delayed clearance; the guarantee is discharged when the shipping documents are received.",
        "eligibility": "Goods have arrived but shipping documents have not; the shipment is under an ICBC (Asia) L/C and the importer is the applicant.",
        "required_materials": ["Bill of Lading Copy", "Commercial Invoice", "Shipping Guarantee Application"],
        "applicable_stages": ["Shipment"],
        "typical_amount_range": "Based on shipment value",
        "typical_tenor": "Until documents arrive",
        "knowledge_base_entry": "ICBC (Asia) Shipping Guarantee facilitates clearance before the arrival of shipping documents, reducing demurrage, storage and delay costs. It is applicable when goods have arrived but documents are still in transit under an ICBC (Asia) L/C, and is discharged upon receipt of the original documents."
    },
    # ── Export trade finance ──
    {
        "product_code": "PLO005",
        "product_name": "Packing Loan / Order Financing",
        "product_name_cn": "打包放款／订单融资",
        "product_name_tw": "打包放款／訂單融資",
        "category": "Trade Finance",
        "description": "Pre-shipment financing for raw material procurement, production and packaging, based on a valid order or export L/C, repaid from the export proceeds.",
        "eligibility": "Valid purchase order or export L/C; pre-shipment funding need for raw materials, production or freight.",
        "required_materials": ["Purchase Order", "Sales Contract", "Supplier Contract"],
        "applicable_stages": ["Order", "Procurement"],
        "typical_amount_range": "CNY 500K - 30M",
        "typical_tenor": "30-120 days",
        "knowledge_base_entry": "ICBC (Asia) Packing Loan and Order Financing provide pre-shipment working capital based on a confirmed order or export L/C, covering raw material procurement, production, packing and freight. The loan eases funding needs before shipment and improves working capital turnover."
    },
    {
        "product_code": "EFI006",
        "product_name": "Export Invoice Financing",
        "product_name_cn": "出口发票融资",
        "product_name_tw": "出口發票融資",
        "category": "Trade Finance",
        "description": "Post-shipment financing against the commercial invoice and shipping documents, converting receivables into cash before the customer pays.",
        "eligibility": "Goods shipped under open account or collection; commercial invoice and shipping documents available; receivable within 30-120 days.",
        "required_materials": ["Commercial Invoice", "Bill of Lading", "Sales Contract"],
        "applicable_stages": ["Shipment", "Receivable"],
        "typical_amount_range": "USD 50K - 5M (or equivalent)",
        "typical_tenor": "30-120 days",
        "knowledge_base_entry": "ICBC (Asia) Export Invoice Financing provides post-shipment financing against the exporter's commercial invoice and shipping documents, improving cash flow before the overseas buyer pays and accelerating working capital turnover after shipment."
    },
    {
        "product_code": "EXN007",
        "product_name": "Export L/C Negotiation",
        "product_name_cn": "出口信用证议付",
        "product_name_tw": "出口信用證議付",
        "category": "Trade Finance",
        "description": "Negotiation of export documents under an L/C, providing funds to the exporter upon document presentation and reducing the need to wait for the issuing bank's reimbursement.",
        "eligibility": "Export L/C received; compliant documents presented; shipment completed.",
        "required_materials": ["Export L/C", "Commercial Invoice", "Bill of Lading"],
        "applicable_stages": ["Shipment", "Receivable"],
        "typical_amount_range": "USD 50K - 5M (or equivalent)",
        "typical_tenor": "30-90 days",
        "knowledge_base_entry": "ICBC (Asia) Export L/C Negotiation advances funds against compliant export documents presented under a letter of credit. The exporter obtains financing without waiting for the issuing bank's reimbursement, improving liquidity and working capital turnover."
    },
    {
        "product_code": "FOR008",
        "product_name": "Forfaiting",
        "product_name_cn": "福费廷",
        "product_name_tw": "福費廷",
        "category": "Trade Finance",
        "description": "Purchase of medium- to long-term receivables under an L/C without recourse, converting future collection into immediate cash.",
        "eligibility": "Receivables under an L/C; documents accepted by the issuing bank; enterprise prefers non-recourse financing.",
        "required_materials": ["Export L/C", "Commercial Invoice", "Bill of Lading"],
        "applicable_stages": ["Receivable"],
        "typical_amount_range": "USD 100K - 10M (or equivalent)",
        "typical_tenor": "90-360 days",
        "knowledge_base_entry": "ICBC (Asia) Forfaiting purchases export receivables under a letter of credit on a without-recourse basis, converting future collection into immediate cash and removing credit, interest rate, exchange rate and country risks from the enterprise's balance sheet."
    },
    {
        "product_code": "FAC009",
        "product_name": "Factoring and Account Receivables Financing",
        "product_name_cn": "保理及应收账融资",
        "product_name_tw": "保理及應收賬融資",
        "category": "Trade Finance",
        "description": "Financing and management of accounts receivable from overseas buyers, including receivables financing to bridge the collection period.",
        "eligibility": "Valid receivables from genuine trade; buyer and receivable confirmed; collection period 30-120 days.",
        "required_materials": ["Commercial Invoice", "Bill of Lading", "Receivable Confirmation"],
        "applicable_stages": ["Receivable", "Collection"],
        "typical_amount_range": "USD 50K - 5M (or equivalent)",
        "typical_tenor": "30-120 days",
        "knowledge_base_entry": "ICBC (Asia) Factoring and Account Receivables Financing provides receivables financing and management based on genuine trade receivables, bridging the collection period and improving liquidity while goods have been shipped but payment is not yet received."
    },
    # ── Bank guarantee ──
    {
        "product_code": "BGS010",
        "product_name": "Bank Guarantee and Stand-by L/C",
        "product_name_cn": "担保函及备用信用证",
        "product_name_tw": "擔保函及備用信用證",
        "category": "Bank Guarantee",
        "description": "Bid bonds, performance guarantees, payment guarantees and stand-by L/Cs supporting tender, contract performance and payment obligations in cross-border trade.",
        "eligibility": "Genuine underlying contract or tender; the counterparty accepts a bank-issued guarantee or stand-by L/C.",
        "required_materials": ["Contract", "Guarantee Application", "Financial Statements"],
        "applicable_stages": ["Order", "Procurement"],
        "typical_amount_range": "Based on contract value",
        "typical_tenor": "90-365 days",
        "knowledge_base_entry": "ICBC (Asia) Bank Guarantee and Stand-by L/C services issue bid bonds, performance guarantees, payment guarantees and stand-by letters of credit based on the enterprise's credit standing and underlying trade contract, supporting tender participation, contract performance and payment obligations."
    },
    # ── Cross-border finance ──
    {
        "product_code": "CBR011",
        "product_name": "Cross-border RMB Trade Finance",
        "product_name_cn": "跨境人民币贸易融资",
        "product_name_tw": "跨境人民幣貿易融資",
        "category": "Cross-border Settlement",
        "description": "RMB-denominated trade financing and settlement for payments to Mainland suppliers and receipts from Mainland customers, enabling offshore RMB funding for genuine cross-border trade.",
        "eligibility": "Genuine cross-border trade; CNY-denominated payment or receipt with a Mainland counterparty.",
        "required_materials": ["Purchase Contract", "Commercial Invoice", "Payment Notice"],
        "applicable_stages": ["Procurement", "Collection"],
        "typical_amount_range": "CNY 100K - 50M",
        "typical_tenor": "Same-day to 180 days",
        "knowledge_base_entry": "ICBC (Asia) Cross-border RMB Trade Finance supports RMB-denominated settlement and financing for Hong Kong enterprises trading with Mainland suppliers and customers, including cross-border RMB trade finance and offshore RMB funding for genuine trade, reducing currency conversion costs."
    },
    {
        "product_code": "OBL012",
        "product_name": "Outbound Guarantee (Nei Bao Wai Dai)",
        "product_name_cn": "内保外贷",
        "product_name_tw": "內保外貸",
        "category": "Cross-border Lending",
        "description": "Cross-border financing where a Mainland guarantee supports a loan extended by ICBC (Asia) to the enterprise's offshore entity.",
        "eligibility": "Mainland parent or group company can provide a guarantee; offshore borrower has genuine funding need.",
        "required_materials": ["Mainland Guarantee", "Loan Application", "Trade Contract"],
        "applicable_stages": ["Order", "Procurement"],
        "typical_amount_range": "CNY 5M - 200M",
        "typical_tenor": "1-3 years",
        "knowledge_base_entry": "ICBC (Asia) Outbound Guarantee (Nei Bao Wai Dai) enables cross-border financing by using a Mainland guarantee to support an offshore loan, helping group companies obtain funding for procurement and operations through ICBC's cross-border network."
    },
    {
        "product_code": "XBL013",
        "product_name": "Cross-border Loan",
        "product_name_cn": "跨境直贷",
        "product_name_tw": "跨境直貸",
        "category": "Cross-border Lending",
        "description": "Direct cross-border lending to the enterprise or its offshore entity for trade and operating needs, arranged through ICBC's cross-border network.",
        "eligibility": "Genuine cross-border funding need; credit assessment and group structure acceptable to the bank.",
        "required_materials": ["Financial Statements", "Trade Contract", "Group Structure"],
        "applicable_stages": ["Procurement"],
        "typical_amount_range": "CNY 5M - 200M",
        "typical_tenor": "1-3 years",
        "knowledge_base_entry": "ICBC (Asia) Cross-border Loan provides direct cross-border financing for enterprises with genuine trade or operating funding needs, leveraging the bank's cross-border network and credit assessment to support procurement and working capital."
    },
    # ── SME and treasury ──
    {
        "product_code": "SME014",
        "product_name": "SME Loan Services",
        "product_name_cn": "中小企贷款服务",
        "product_name_tw": "中小企貸款服務",
        "category": "SME Financing",
        "description": "SME financing solutions including working capital loans and trade-based lending, with flexible tenors aligned to the operating cycle.",
        "eligibility": "SME with ongoing trade activity and identified funding need; financial statements and cash flow forecast available.",
        "required_materials": ["Financial Statements", "Cash Flow Forecast", "Transaction Analysis Report"],
        "applicable_stages": ["Procurement", "Receivable", "Collection"],
        "typical_amount_range": "HKD 500K - 10M",
        "typical_tenor": "30-180 days",
        "knowledge_base_entry": "ICBC (Asia) SME Loan Services provide working capital and trade-based financing for small and medium enterprises, with amounts and tenors aligned to the operating cycle and cash flow position, supporting procurement and bridging receivable periods."
    },
    {
        "product_code": "FXF015",
        "product_name": "FX Forward",
        "product_name_cn": "外汇远期",
        "product_name_tw": "外匯遠期",
        "category": "Treasury",
        "description": "Forward foreign exchange contracts to lock in an exchange rate for future supplier payments or customer collections, managing multi-currency exposure.",
        "eligibility": "Identified FX exposure from genuine trade; future payment or collection in a foreign currency.",
        "required_materials": ["Transaction Analysis Report", "Cash Flow Forecast"],
        "applicable_stages": ["Shipment", "Receivable", "Collection"],
        "typical_amount_range": "USD 10K - 10M",
        "typical_tenor": "Spot to 180 days forward",
        "knowledge_base_entry": "ICBC (Asia) FX Forward locks in an exchange rate for a future date, helping enterprises manage foreign exchange exposure from multi-currency trade flows such as USD collections against CNY supplier payments. Widely used for FX risk hedging together with FX swap, FX option and CNY/CNH forward products."
    },
    {
        "product_code": "NDF016",
        "product_name": "CNY Non-Deliverable Forward / CNH Deliverable Forward",
        "product_name_cn": "人民币远期（交割／不交割）",
        "product_name_tw": "人民幣遠期（交收／不交收）",
        "category": "Treasury",
        "description": "RMB forward contracts with deliverable (CNH) or non-deliverable (CNY NDF) settlement to hedge RMB exchange rate exposure.",
        "eligibility": "RMB exposure from genuine cross-border trade; cash flow forecast showing future CNY receipts or payments.",
        "required_materials": ["Cash Flow Forecast", "FX Exposure Report"],
        "applicable_stages": ["Collection"],
        "typical_amount_range": "CNY 1M - 50M",
        "typical_tenor": "Spot to 180 days forward",
        "knowledge_base_entry": "ICBC (Asia) CNY Non-Deliverable Forward and CNH Deliverable Forward help enterprises hedge RMB exchange rate exposure. The non-deliverable forward settles in a convertible currency, while the CNH deliverable forward settles in offshore RMB, supporting RMB trade settlement and FX risk management."
    },
]


# ─── Enterprises ───
ENTERPRISES_DATA = [
    {
        "name": "利丰贸易（香港）有限公司",
        "name_en": "Li & Fung Trading (HK) Co., Ltd.",
        "registration_number": "HK-12345678",
        "region": "Hong Kong",
        "industry": "Global Supply Chain Management",
        "main_supplier_region": "Greater Bay Area (Shenzhen, Dongguan, Guangzhou)",
        "main_customer_region": "United States, Europe",
        "main_currencies": "HKD, CNY, USD, EUR",
        "annual_trade_volume": "HKD 800M",
        "existing_bank_services": "Account, Settlement, FX",
        "current_financing": "Trade Finance Facility HKD 50M",
        "payment_methods": "T/T, L/C",
        "business_model": "Global supply chain management company headquartered in Hong Kong. Connects overseas customers (US, Europe) with GBA suppliers through sourcing, production management, and logistics coordination. Pays suppliers in CNY, receives from customers in USD/EUR, covers operating costs in HKD.",
        "business_model_zh": "总部位于香港的全球供应链管理公司。通过采购、生产管理和物流协调，将海外客户（美国、欧洲）与大湾区供应商对接。以人民币向供应商付款，以美元/欧元收取客户款项，以港币支付运营成本。",
        "business_model_tw": "總部位於香港的全球供應鏈管理公司。通過採購、生產管理和物流協調，將海外客戶（美國、歐洲）與大灣區供應商對接。以人民幣向供應商付款，以美元/歐元收取客戶款項，以港幣支付運營成本。"
    },
    {
        "name": "深圳科创电子有限公司",
        "name_en": "Shenzhen Tech-Innovation Electronics Co., Ltd.",
        "registration_number": "GD-440300987654",
        "region": "Greater Bay Area",
        "industry": "Electronics Manufacturing",
        "main_supplier_region": "Greater Bay Area",
        "main_customer_region": "Hong Kong (for international settlement), United States",
        "main_currencies": "CNY, USD",
        "annual_trade_volume": "CNY 200M",
        "existing_bank_services": "Account, Settlement",
        "current_financing": "None",
        "payment_methods": "T/T",
        "business_model": "Shenzhen-based electronics manufacturer. Exports products to US customers through Hong Kong for international settlement. CNY-denominated production costs, USD-denominated export revenue.",
        "business_model_zh": "深圳电子产品制造商。通过香港进行国际结算，向美国客户出口产品。生产成本以人民币计价，出口收入以美元计价。",
        "business_model_tw": "深圳電子產品製造商。通過香港進行國際結算，向美國客戶出口產品。生產成本以人民幣計價，出口收入以美元計價。"
    },
]


# ─── Users ───
USERS_DATA = [
    {
        "username": "enterprise",
        "password_hash": "demo123",
        "display_name": "企业用户 · 利丰贸易",
        "role": "enterprise_user",
        "enterprise_id": 1,
        "assigned_enterprise_ids": None,
    },
    {
        "username": "enterprise2",
        "password_hash": "demo123",
        "display_name": "企业用户 · 深圳科创",
        "role": "enterprise_user",
        "enterprise_id": 2,
        "assigned_enterprise_ids": None,
    },
    {
        "username": "rm",
        "password_hash": "demo123",
        "display_name": "客户经理 · 张明",
        "role": "rm",
        "enterprise_id": None,
        "assigned_enterprise_ids": "1,2",
    },
    {
        "username": "risk",
        "password_hash": "demo123",
        "display_name": "风险管理 · 李华",
        "role": "risk_team",
        "enterprise_id": None,
        "assigned_enterprise_ids": "1,2",
    },
]


# ─── Demo Transactions ───
# Case A: Hong Kong trader, USD 500K order, CNY supplier payment, 30-day pay supplier, 75-day collect customer, 45-day gap
TRANSACTION_A = {
    "tx_ref": "TX-A-001",
    "enterprise_id": 1,
    "buyer": "ABC International LLC (USA)",
    "seller": "Li & Fung Trading (HK) Co., Ltd.",
    "supplier": "Shenzhen ABC Electronics Co., Ltd.",
    "order_amount": 500000.0,
    "order_currency": "USD",
    "contract_amount": 500000.0,
    "contract_currency": "USD",
    "invoice_amount": 3600000.0,  # CNY equivalent
    "invoice_currency": "CNY",
    "order_date": date(2026, 10, 1),
    "payment_date": date(2026, 10, 15),  # supplier payment due
    "delivery_date": date(2026, 11, 20),
    "expected_collection_date": date(2026, 12, 20),  # 75 days after order
    "logistics_status": "shipped",
    "completeness_score": 88,
    "overall_risk": "Medium",
    "risk_dimensions": {
        "Document Consistency": "Low Risk",
        "Missing Information": "Medium Risk",
        "Duplicate Financing Indicator": "Low Risk",
        "Payment Account Change": "Medium Risk",
        "FX Exposure": "High Risk",
        "Overall Transaction Risk": "Medium"
    },
    "status": "analyzed",
}

# Case B: Large supply chain, USD 5M order, CNY 30M supplier payment, 70 days after payment collect
TRANSACTION_B = {
    "tx_ref": "TX-B-001",
    "enterprise_id": 1,
    "buyer": "Global Brands Inc. (USA)",
    "seller": "Li & Fung Trading (HK) Co., Ltd.",
    "supplier": "Dongguan XYZ Manufacturing Co., Ltd.",
    "order_amount": 5000000.0,
    "order_currency": "USD",
    "contract_amount": 5000000.0,
    "contract_currency": "USD",
    "invoice_amount": 30000000.0,
    "invoice_currency": "CNY",
    "order_date": date(2026, 9, 1),
    "payment_date": date(2026, 9, 15),  # supplier payment due
    "delivery_date": date(2026, 11, 10),
    "expected_collection_date": date(2026, 11, 24),  # ~70 days after supplier payment
    "logistics_status": "shipped",
    "completeness_score": 88,
    "overall_risk": "Medium",
    "risk_dimensions": {
        "Document Consistency": "Low Risk",
        "Missing Information": "Medium Risk",
        "Duplicate Financing Indicator": "Low Risk",
        "Payment Account Change": "Low Risk",
        "FX Exposure": "High Risk",
        "Overall Transaction Risk": "Medium"
    },
    "status": "analyzed",
}


# ─── Demo Documents Metadata ───
# For each document, we store the structured data that OCR would extract
# This allows the demo to work without actual OCR engine installed
DEMO_DOCUMENTS = [
    # Transaction A documents
    {
        "transaction_id": None,  # will be set after tx created
        "enterprise_id": 1,
        "filename": "PO_ABC_2026.pdf",
        "file_type": "pdf",
        "doc_type": "Purchase Order",
        "doc_type_confidence": 0.98,
        "structured_data": {
            "Buyer": "ABC International LLC",
            "Seller": "Li & Fung Trading (HK) Co., Ltd.",
            "Order No.": "PO-ABC-2026-001",
            "Order Amount": "500,000",
            "Currency": "USD",
            "Order Date": "2026-10-01",
            "Delivery Date": "2026-11-20",
            "Delivery Terms": "FOB Shenzhen"
        },
        "ocr_confidence": {
            "Buyer": 0.98,
            "Seller": 0.97,
            "Order No.": 0.99,
            "Order Amount": 0.99,
            "Currency": 0.99,
            "Order Date": 0.97,
            "Delivery Date": 0.95,
            "Delivery Terms": 0.92
        }
    },
    {
        "transaction_id": None,
        "enterprise_id": 1,
        "filename": "SalesContract_001.pdf",
        "file_type": "pdf",
        "doc_type": "Sales Contract",
        "doc_type_confidence": 0.97,
        "structured_data": {
            "Buyer": "ABC International LLC",
            "Seller": "Li & Fung Trading (HK) Co., Ltd.",
            "Contract No.": "SC-2026-001",
            "Contract Value": "500,000",
            "Currency": "USD",
            "Payment Terms": "T/T 75 days after delivery",
            "Contract Date": "2026-10-01"
        },
        "ocr_confidence": {
            "Buyer": 0.98,
            "Seller": 0.96,
            "Contract No.": 0.99,
            "Contract Value": 0.99,
            "Currency": 0.99,
            "Payment Terms": 0.88,
            "Contract Date": 0.97
        }
    },
    {
        "transaction_id": None,
        "enterprise_id": 1,
        "filename": "SupplierInvoice_INV20260815.pdf",
        "file_type": "pdf",
        "doc_type": "Commercial Invoice",
        "doc_type_confidence": 0.96,
        "structured_data": {
            "Supplier": "Shenzhen ABC Electronics Co., Ltd.",
            "Invoice No.": "INV-2026-0815",
            "Invoice Date": "2026-10-05",
            "Amount": "3,600,000",
            "Currency": "CNY",
            "Payment Due Date": "2026-10-15",
            "Buyer": "Li & Fung Trading (HK) Co., Ltd."
        },
        "ocr_confidence": {
            "Supplier": 0.98,
            "Invoice No.": 0.97,
            "Invoice Date": 0.95,
            "Amount": 0.99,
            "Currency": 0.99,
            "Payment Due Date": 0.82,  # Low confidence - needs verification
            "Buyer": 0.93
        }
    },
    {
        "transaction_id": None,
        "enterprise_id": 1,
        "filename": "PaymentSchedule.xlsx",
        "file_type": "excel",
        "doc_type": "Payment Schedule",
        "doc_type_confidence": 0.99,
        "structured_data": {
            "Payment Date": "2026-10-15",
            "Amount": "3,600,000",
            "Currency": "CNY",
            "Account": "6222-0001-2345-6789",
            "Beneficiary": "Shenzhen ABC Electronics Co., Ltd."
        },
        "ocr_confidence": {
            "Payment Date": 0.99,
            "Amount": 0.99,
            "Currency": 0.99,
            "Account": 0.82,  # Low confidence - new account
            "Beneficiary": 0.95
        }
    },
    # Transaction B documents
    {
        "transaction_id": None,
        "enterprise_id": 1,
        "filename": "PO_GlobalBrands_5M.pdf",
        "file_type": "pdf",
        "doc_type": "Purchase Order",
        "doc_type_confidence": 0.98,
        "structured_data": {
            "Buyer": "Global Brands Inc.",
            "Seller": "Li & Fung Trading (HK) Co., Ltd.",
            "Order No.": "PO-GB-2026-005",
            "Order Amount": "5,000,000",
            "Currency": "USD",
            "Order Date": "2026-09-01",
            "Delivery Date": "2026-11-10",
            "Delivery Terms": "FOB Dongguan"
        },
        "ocr_confidence": {
            "Buyer": 0.98,
            "Seller": 0.97,
            "Order No.": 0.99,
            "Order Amount": 0.99,
            "Currency": 0.99,
            "Order Date": 0.97,
            "Delivery Date": 0.96,
            "Delivery Terms": 0.93
        }
    },
    {
        "transaction_id": None,
        "enterprise_id": 1,
        "filename": "SalesContract_GB_005.pdf",
        "file_type": "pdf",
        "doc_type": "Sales Contract",
        "doc_type_confidence": 0.97,
        "structured_data": {
            "Buyer": "Global Brands Inc.",
            "Seller": "Li & Fung Trading (HK) Co., Ltd.",
            "Contract No.": "SC-2026-005",
            "Contract Value": "5,000,000",
            "Currency": "USD",
            "Payment Terms": "T/T 70 days after delivery",
            "Contract Date": "2026-09-01"
        },
        "ocr_confidence": {
            "Buyer": 0.98,
            "Seller": 0.97,
            "Contract No.": 0.99,
            "Contract Value": 0.99,
            "Currency": 0.99,
            "Payment Terms": 0.91,
            "Contract Date": 0.97
        }
    },
    {
        "transaction_id": None,
        "enterprise_id": 1,
        "filename": "SupplierInvoice_DG_XYZ.pdf",
        "file_type": "pdf",
        "doc_type": "Commercial Invoice",
        "doc_type_confidence": 0.96,
        "structured_data": {
            "Supplier": "Dongguan XYZ Manufacturing Co., Ltd.",
            "Invoice No.": "INV-DG-2026-0901",
            "Invoice Date": "2026-09-05",
            "Amount": "30,000,000",
            "Currency": "CNY",
            "Payment Due Date": "2026-09-15",
            "Buyer": "Li & Fung Trading (HK) Co., Ltd."
        },
        "ocr_confidence": {
            "Supplier": 0.97,
            "Invoice No.": 0.98,
            "Invoice Date": 0.96,
            "Amount": 0.99,
            "Currency": 0.99,
            "Payment Due Date": 0.95,
            "Buyer": 0.94
        }
    },
]


def seed_database(session: Session):
    """Populate the database with seed data."""
    # Check if already seeded
    if session.query(Enterprise).count() > 0:
        return False

    # ─── Create Enterprises ───
    enterprises = []
    for ed in ENTERPRISES_DATA:
        ent = Enterprise(**ed)
        session.add(ent)
        enterprises.append(ent)
    session.flush()

    # ─── Create Users ───
    for i, ud in enumerate(USERS_DATA):
        if ud["enterprise_id"] is not None and ud["enterprise_id"] > len(enterprises):
            continue
        user = User(
            username=ud["username"],
            password_hash=ud["password_hash"],
            display_name=ud["display_name"],
            role=ud["role"],
            enterprise_id=ud["enterprise_id"],
            assigned_enterprise_ids=ud["assigned_enterprise_ids"],
        )
        session.add(user)
    session.flush()

    # ─── Create Products ───
    products = []
    for pd in PRODUCTS_DATA:
        pd_copy = pd.copy()
        # SQLAlchemy JSON column handles serialization; pass lists directly
        prod = Product(**pd_copy)
        session.add(prod)
        products.append(prod)
    session.flush()

    # ─── Create Transactions ───
    tx_a = Transaction(**TRANSACTION_A)
    session.add(tx_a)
    tx_b = Transaction(**TRANSACTION_B)
    session.add(tx_b)
    session.flush()

    # ─── Create Documents ───
    # First 4 documents → Transaction A, last 3 → Transaction B
    for i, dd in enumerate(DEMO_DOCUMENTS):
        tx_id = tx_a.id if i < 4 else tx_b.id
        doc = Document(
            enterprise_id=dd["enterprise_id"],
            transaction_id=tx_id,
            filename=dd["filename"],
            file_path=f"uploads/{dd['filename']}",
            file_type=dd["file_type"],
            doc_type=dd["doc_type"],
            doc_type_confidence=dd["doc_type_confidence"],
            ocr_status="done",
            ocr_text="(Demo document - structured data provided directly)",
            structured_data=dd["structured_data"],
            ocr_confidence=dd["ocr_confidence"],
            low_confidence_fields=[k for k, v in dd["ocr_confidence"].items() if v < 0.85],
            confirmed=False,
            processed_at=datetime.utcnow(),
        )
        session.add(doc)
        session.flush()

        # Create OcrField records
        for field_name, field_value in dd["structured_data"].items():
            conf = dd["ocr_confidence"].get(field_name, 0.95)
            ocr_field = OcrField(
                document_id=doc.id,
                field_name=field_name,
                field_value=field_value,
                confidence=conf,
                needs_verification=conf < 0.85,
            )
            session.add(ocr_field)
    session.flush()

    # ─── Create Transaction Entities and Links ───
    for tx, entities_data in [
        (tx_a, [
            ("enterprise", "Li & Fung Trading (HK) Co., Ltd.", "Seller"),
            ("customer", "ABC International LLC", "Buyer"),
            ("supplier", "Shenzhen ABC Electronics Co., Ltd.", "Supplier"),
            ("bank_account", "6222-0001-2345-6789", "Account Holder"),
            ("logistics", "Shipment SZ→US (in transit)", "Consignee"),
        ]),
        (tx_b, [
            ("enterprise", "Li & Fung Trading (HK) Co., Ltd.", "Seller"),
            ("customer", "Global Brands Inc.", "Buyer"),
            ("supplier", "Dongguan XYZ Manufacturing Co., Ltd.", "Supplier"),
            ("bank_account", "6222-0002-9876-5432", "Account Holder"),
            ("logistics", "Shipment DG→US (in transit)", "Consignee"),
            ("financing", "Financing Application TX-B-001", "Financing"),
        ]),
    ]:
        entity_ids = []
        for etype, ename, role in entities_data:
            ent = TransactionEntity(
                transaction_id=tx.id,
                entity_type=etype,
                entity_name=ename,
                role=role,
            )
            session.add(ent)
            session.flush()
            entity_ids.append(ent.id)

        # Create links: company sells to customer, purchases from supplier, etc.
        links = [
            (0, 1, "sells_to"),     # enterprise → customer
            (0, 2, "purchases_from"),  # enterprise → supplier
            (0, 3, "owns_account"),    # enterprise → bank_account
            (0, 4, "arranges_logistics"),  # enterprise → logistics
        ]
        if len(entity_ids) > 5:
            links.append((5, 2, "based_on"))  # financing → supplier (if exists)
        for src_idx, tgt_idx, link_type in links:
            link = TransactionLink(
                transaction_id=tx.id,
                source_entity_id=entity_ids[src_idx],
                target_entity_id=entity_ids[tgt_idx],
                link_type=link_type,
            )
            session.add(link)
    session.flush()

    # ─── Create Risk Alerts ───
    # Transaction A risks
    risk_a = RiskAlert(
        transaction_id=tx_a.id,
        alert_type="fx_risk",
        alert_level="High",
        alert_message="High CNY/USD exposure: CNY supplier payment with USD customer collection creates significant FX risk.",
        main_factors=["CNY 3.6M supplier payment paired with USD 500K customer collection", "75-day collection period exposes to exchange rate volatility"],
        positive_factors=["Contract and invoice amounts are consistent", "Buyer identity is consistent across documents", "No duplicate financing indicator detected"],
        explanation="The overall transaction risk is Medium because while the document consistency is good, there is high FX exposure and a new supplier payment account (confidence 82%) that requires verification.",
        resolved=False,
    )
    session.add(risk_a)

    risk_a2 = RiskAlert(
        transaction_id=tx_a.id,
        alert_type="counterparty_risk",
        alert_level="Medium",
        alert_message="Payment Account Change: Supplier payment account differs from historical records.",
        main_factors=["New supplier payment account detected (confidence 82%)"],
        positive_factors=["Supplier name matches across invoice and payment schedule"],
        explanation="The payment account number was extracted with low OCR confidence (82%) and may differ from the enterprise's historical supplier payment records. RM verification recommended.",
        resolved=False,
    )
    session.add(risk_a2)

    risk_a3 = RiskAlert(
        transaction_id=tx_a.id,
        alert_type="document_risk",
        alert_level="Medium",
        alert_message="Missing Information: Logistics document (bill of lading) has not been uploaded.",
        main_factors=["Bill of lading not uploaded", "Cannot fully verify goods in transit"],
        positive_factors=["Purchase order, sales contract, invoice, and payment schedule all present and consistent"],
        explanation="While the core transaction documents are complete, the logistics document is missing. This affects the ability to verify the physical movement of goods. RM should request the bill of lading.",
        resolved=False,
    )
    session.add(risk_a3)

    # Transaction B risks
    risk_b = RiskAlert(
        transaction_id=tx_b.id,
        alert_type="fx_risk",
        alert_level="High",
        alert_message="High CNY/USD exposure: CNY 30M supplier payment with USD 5M customer collection, 70-day collection gap.",
        main_factors=["CNY 30M supplier payment paired with USD 5M customer collection", "70-day gap between supplier payment and customer collection", "Large absolute FX exposure amount"],
        positive_factors=["All core documents present and consistent", "Buyer identity consistent across all documents", "Supplier well-established in historical records"],
        explanation="The overall transaction risk is Medium. The primary risk driver is the high FX exposure from the large CNY/USD mismatch and the extended collection period. Document completeness is good (88/100) but logistics documentation remains incomplete.",
        resolved=False,
    )
    session.add(risk_b)

    risk_b2 = RiskAlert(
        transaction_id=tx_b.id,
        alert_type="document_risk",
        alert_level="Medium",
        alert_message="Missing Information: Logistics document (bill of lading) has not been uploaded.",
        main_factors=["Bill of lading not uploaded"],
        positive_factors=["Purchase order, sales contract, and invoice all present and amounts consistent"],
        explanation="Transaction completeness score is 88/100. The missing logistics document prevents full verification of goods shipment. RM should request the bill of lading from the enterprise.",
        resolved=False,
    )
    session.add(risk_b2)
    session.flush()

    # ─── Create Cashflow Items ───
    # Transaction A baseline cashflows
    cashflows_a = [
        ("outflow", "Supplier Payment (Shenzhen ABC)", "CNY", -3600000, date(2026, 10, 15), None, tx_a.id),
        ("inflow", "Customer Collection (ABC International)", "USD", 500000, date(2026, 12, 20), None, tx_a.id),
        ("outflow", "Operating Expenses (Monthly)", "HKD", -500000, date(2026, 10, 31), None, tx_a.id),
        ("outflow", "Operating Expenses (Monthly)", "HKD", -500000, date(2026, 11, 30), None, tx_a.id),
        ("outflow", "Operating Expenses (Monthly)", "HKD", -500000, date(2026, 12, 31), None, tx_a.id),
    ]
    for ft, desc, curr, amt, fd, sid, tid in cashflows_a:
        cf = CashflowItem(
            transaction_id=tid,
            enterprise_id=1,
            flow_type=ft,
            description=desc,
            currency=curr,
            amount=amt,
            flow_date=fd,
            scenario_id=sid,
        )
        session.add(cf)

    # Transaction B baseline cashflows
    cashflows_b = [
        ("outflow", "Supplier Payment (Dongguan XYZ)", "CNY", -30000000, date(2026, 9, 15), None, tx_b.id),
        ("inflow", "Customer Collection (Global Brands)", "USD", 5000000, date(2026, 11, 24), None, tx_b.id),
        ("outflow", "Operating Expenses (Monthly)", "HKD", -500000, date(2026, 9, 30), None, tx_b.id),
        ("outflow", "Operating Expenses (Monthly)", "HKD", -500000, date(2026, 10, 31), None, tx_b.id),
        ("outflow", "Operating Expenses (Monthly)", "HKD", -500000, date(2026, 11, 30), None, tx_b.id),
    ]
    for ft, desc, curr, amt, fd, sid, tid in cashflows_b:
        cf = CashflowItem(
            transaction_id=tid,
            enterprise_id=1,
            flow_type=ft,
            description=desc,
            currency=curr,
            amount=amt,
            flow_date=fd,
            scenario_id=sid,
        )
        session.add(cf)
    session.flush()

    # ─── Create Scenarios ───
    # Transaction A scenarios
    scenarios_a = [
        ("Base Case", "Payment as planned, no FX change", {"delay_days": 0, "fx_change_pct": 0, "supplier_early_days": 0}, 3600000, "CNY", "Timing Mismatch", tx_a.id),
        ("Customer Delay +15 days", "Customer payment delayed by 15 days", {"delay_days": 15, "fx_change_pct": 0, "supplier_early_days": 0}, 3600000, "CNY", "Receivables Risk", tx_a.id),
        ("CNY Appreciation +3%", "CNY appreciates by 3%", {"delay_days": 0, "fx_change_pct": 3, "supplier_early_days": 0}, 3708000, "CNY", "FX Risk", tx_a.id),
        ("Supplier Early Payment", "Supplier requires payment 15 days earlier", {"delay_days": 0, "fx_change_pct": 0, "supplier_early_days": 15}, 3600000, "CNY", "Liquidity Risk", tx_a.id),
        ("Combined Stress Case", "Customer delay + CNY appreciation + supplier early", {"delay_days": 15, "fx_change_pct": 3, "supplier_early_days": 15}, 4500000, "CNY", "Multiple Risks", tx_a.id),
    ]
    scenario_a_ids = []
    for name, desc, params, gap, curr, risk, tid in scenarios_a:
        sc = Scenario(
            transaction_id=tid,
            name=name,
            description=desc,
            parameters=params,
            max_funding_gap=gap,
            gap_currency=curr,
            main_risk=risk,
        )
        session.add(sc)
        session.flush()
        scenario_a_ids.append(sc.id)

    # Transaction B scenarios
    scenarios_b = [
        ("Base Case", "Payment as planned, no FX change", {"delay_days": 0, "fx_change_pct": 0, "supplier_early_days": 0}, 30000000, "CNY", "Timing Mismatch", tx_b.id),
        ("Customer Delay +15 days", "Customer payment delayed by 15 days", {"delay_days": 15, "fx_change_pct": 0, "supplier_early_days": 0}, 30000000, "CNY", "Receivables Risk", tx_b.id),
        ("CNY Appreciation +3%", "CNY appreciates by 3%", {"delay_days": 0, "fx_change_pct": 3, "supplier_early_days": 0}, 30900000, "CNY", "FX Risk", tx_b.id),
        ("Supplier Early Payment", "Supplier requires payment 15 days earlier", {"delay_days": 0, "fx_change_pct": 0, "supplier_early_days": 15}, 30000000, "CNY", "Liquidity Risk", tx_b.id),
        ("Combined Stress Case", "Customer delay + CNY appreciation + supplier early", {"delay_days": 15, "fx_change_pct": 3, "supplier_early_days": 15}, 45000000, "CNY", "Multiple Risks", tx_b.id),
    ]
    scenario_b_ids = []
    for name, desc, params, gap, curr, risk, tid in scenarios_b:
        sc = Scenario(
            transaction_id=tid,
            name=name,
            description=desc,
            parameters=params,
            max_funding_gap=gap,
            gap_currency=curr,
            main_risk=risk,
        )
        session.add(sc)
        session.flush()
        scenario_b_ids.append(sc.id)
    session.flush()

    # ─── Create Funding Gaps ───
    # Transaction A baseline gap
    fg_a = FundingGap(
        transaction_id=tx_a.id,
        gap_currency="CNY",
        gap_amount=3600000,
        gap_duration_days=66,  # Oct 15 to Dec 20
        gap_start_date=date(2026, 10, 15),
        gap_end_date=date(2026, 12, 20),
        primary_cause="Timing mismatch: CNY supplier payment (Oct 15) precedes USD customer collection (Dec 20) by 66 days. Currency mismatch: CNY outflow vs USD inflow.",
        scenario_id=scenario_a_ids[0],
    )
    session.add(fg_a)

    # Transaction B baseline gap
    fg_b = FundingGap(
        transaction_id=tx_b.id,
        gap_currency="CNY",
        gap_amount=30000000,
        gap_duration_days=70,  # Sep 15 to Nov 24
        gap_start_date=date(2026, 9, 15),
        gap_end_date=date(2026, 11, 24),
        primary_cause="Timing mismatch: CNY 30M supplier payment (Sep 15) precedes USD 5M customer collection (Nov 24) by 70 days. Currency mismatch: CNY outflow vs USD inflow creates significant FX exposure.",
        scenario_id=scenario_b_ids[0],
    )
    session.add(fg_b)
    session.flush()

    # ─── Create Recommendations ───
    # Generated with the same matching engine used by the API so the seeded
    # recommendations stay in sync with the current product catalog.
    from app.services.product_matcher import match_products

    product_dicts = [{
        "id": p.id,
        "product_code": p.product_code,
        "product_name": p.product_name,
        "product_name_cn": p.product_name_cn,
        "product_name_tw": p.product_name_tw,
        "category": p.category,
        "description": p.description,
        "applicable_stages": p.applicable_stages,
        "required_materials": p.required_materials,
        "knowledge_base_entry": p.knowledge_base_entry,
    } for p in products]

    def _seed_recommendations(tx, funding_gap):
        tx_dict = {
            "order_currency": tx.order_currency,
            "invoice_currency": tx.invoice_currency,
            "order_amount": tx.order_amount,
            "invoice_amount": tx.invoice_amount,
            "logistics_status": tx.logistics_status,
            "expected_collection_date": tx.expected_collection_date,
            "payment_date": tx.payment_date,
            "order_date": tx.order_date,
        }
        fg_dict = None
        if funding_gap is not None:
            fg_dict = {"gaps": [{
                "gap_amount": funding_gap.gap_amount,
                "gap_currency": funding_gap.gap_currency,
                "gap_duration_days": funding_gap.gap_duration_days,
            }]}
        for rec in match_products(tx_dict, product_dicts, fg_dict, lang="zh-CN"):
            session.add(Recommendation(
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
                transaction_id=tx.id,
                enterprise_id=1,
                status="pending",
            ))

    _seed_recommendations(tx_a, fg_a)
    _seed_recommendations(tx_b, fg_b)
    session.flush()

    # ─── Create Monitoring Events ───
    events = [
        (tx_a.id, 1, "shipment_update", "Supplier Shenzhen ABC has shipped goods. Logistics tracking initiated.", "info", {"shipment_date": "2026-11-05", "origin": "Shenzhen", "destination": "US"}),
        (tx_a.id, 1, "fx_change", "USD/CNY exchange rate has moved by 1.2% in the last week.", "warning", {"pair": "USD/CNY", "change_pct": 1.2}),
        (tx_b.id, 1, "shipment_update", "Supplier Dongguan XYZ has shipped goods. In transit to overseas customer.", "info", {"shipment_date": "2026-11-08", "origin": "Dongguan", "destination": "US"}),
        (tx_b.id, 1, "payment_overdue", "Expected collection date (Nov 24) has not yet arrived. Monitoring in progress.", "info", {"expected_date": "2026-11-24", "status": "pending"}),
    ]
    for tid, eid, etype, desc, sev, meta in events:
        ev = MonitoringEvent(
            transaction_id=tid,
            enterprise_id=eid,
            event_type=etype,
            event_description=desc,
            severity=sev,
            metadata_json=meta,
        )
        session.add(ev)
    session.flush()

    # ─── Create Audit Logs ───
    audit_entries = [
        (1, "system", "seed_data", "database", None, "Initialized database with seed data"),
        (1, "system", "create_transaction", "transaction", tx_a.id, f"Created transaction {tx_a.tx_ref}"),
        (1, "system", "create_transaction", "transaction", tx_b.id, f"Created transaction {tx_b.tx_ref}"),
        (1, "system", "risk_analysis", "transaction", tx_a.id, "Risk analysis completed for TX-A-001"),
        (1, "system", "risk_analysis", "transaction", tx_b.id, "Risk analysis completed for TX-B-001"),
    ]
    for eid, actor, action, ttype, tid, details in audit_entries:
        al = AuditLog(
            enterprise_id=eid,
            actor=actor,
            action=action,
            target_type=ttype,
            target_id=tid,
            details=details,
        )
        session.add(al)

    session.commit()
    return True
