"""
OCR service - handles document text extraction and field identification.
Supports Tesseract OCR when available, falls back to structured data parsing.
"""
import os
import re
import json
import logging
from typing import Dict, Tuple, Optional, List

logger = logging.getLogger(__name__)

# Try importing OCR-related libraries
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract/PIL not available")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


# Document type classification patterns
DOC_TYPE_PATTERNS = {
    "Purchase Order": [
        r"purchase\s+order", r"po\s*no", r"order\s*no", r"p\.o\.", r"订单", r"采购订单"
    ],
    "Sales Contract": [
        r"sales\s+contract", r"contract\s+no", r"sales\s+agreement", r"销售合同", r"合约"
    ],
    "Purchase Contract": [
        r"purchase\s+contract", r"procurement\s+contract", r"采购合同"
    ],
    "Commercial Invoice": [
        r"commercial\s+invoice", r"invoice\s*no", r"invoice\s*date", r"发票", r"商业发票"
    ],
    "Payment Schedule": [
        r"payment\s+schedule", r"payment\s+plan", r"付款计划", r"付款安排"
    ],
    "Bill of Lading": [
        r"bill\s+of\s+lading", r"b/l\s*no", r"提单", r"装箱单", r"packing\s+list"
    ],
    "Payment Notice": [
        r"payment\s+notice", r"payment\s+advice", r"付款通知"
    ],
}

# Field extraction patterns by document type
FIELD_PATTERNS = {
    "Purchase Order": {
        "Buyer": [r"(?:buyer|customer|to)\s*[:：]\s*(.+)", r"(?:买方|客户)\s*[:：]\s*(.+)"],
        "Seller": [r"(?:seller|supplier|from)\s*[:：]\s*(.+)", r"(?:卖方|供应商)\s*[:：]\s*(.+)"],
        "Order No.": [r"(?:order\s*no|po\s*no|p\.o\.)\s*[:：]\s*(\S+)", r"订单号\s*[:：]\s*(\S+)"],
        "Order Amount": [r"(?:amount|total|order\s*value)\s*[:：]\s*([\d,.]+)", r"金额\s*[:：]\s*([\d,.]+)"],
        "Currency": [r"(usd|cny|hkd|eur|gbp|jpy)", r"(美元|人民币|港币|欧元)"],
        "Order Date": [r"(?:date|order\s*date)\s*[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})", r"日期\s*[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"],
        "Delivery Date": [r"(?:delivery\s*date|ship\s*date|expected\s*delivery)\s*[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"],
        "Delivery Terms": [r"(?:delivery\s*terms|trade\s*terms|incoterms)\s*[:：]\s*(\S+)"],
    },
    "Sales Contract": {
        "Buyer": [r"(?:buyer|party\s*a|customer)\s*[:：]\s*(.+)", r"买方\s*[:：]\s*(.+)"],
        "Seller": [r"(?:seller|party\s*b|vendor)\s*[:：]\s*(.+)", r"卖方\s*[:：]\s*(.+)"],
        "Contract No.": [r"(?:contract\s*no|ref\s*no)\s*[:：]\s*(\S+)", r"合同号\s*[:：]\s*(\S+)"],
        "Contract Value": [r"(?:total\s*value|contract\s*value|amount)\s*[:：]\s*([\d,.]+)", r"合同金额\s*[:：]\s*([\d,.]+)"],
        "Currency": [r"(usd|cny|hkd|eur|gbp|jpy)"],
        "Payment Terms": [r"(?:payment\s*terms|terms\s*of\s*payment)\s*[:：]\s*(.+)", r"付款条件\s*[:：]\s*(.+)"],
        "Contract Date": [r"(?:date|contract\s*date|signed\s*date)\s*[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"],
    },
    "Commercial Invoice": {
        "Supplier": [r"(?:supplier|seller|from)\s*[:：]\s*(.+)", r"供应商\s*[:：]\s*(.+)"],
        "Invoice No.": [r"(?:invoice\s*no|inv\s*no)\s*[:：]\s*(\S+)", r"发票号\s*[:：]\s*(\S+)"],
        "Invoice Date": [r"(?:invoice\s*date|date)\s*[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})", r"开票日期\s*[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"],
        "Amount": [r"(?:total\s*amount|invoice\s*amount|amount)\s*[:：]\s*([\d,.]+)", r"金额\s*[:：]\s*([\d,.]+)"],
        "Currency": [r"(usd|cny|hkd|eur|gbp|jpy)"],
        "Payment Due Date": [r"(?:payment\s*due|due\s*date|payment\s*date)\s*[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})", r"付款日期\s*[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"],
        "Buyer": [r"(?:buyer|customer|bill\s*to)\s*[:：]\s*(.+)", r"买方\s*[:：]\s*(.+)"],
    },
    "Payment Schedule": {
        "Payment Date": [r"(?:payment\s*date|due\s*date|date)\s*[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"],
        "Amount": [r"(?:amount|total)\s*[:：]\s*([\d,.]+)"],
        "Currency": [r"(usd|cny|hkd|eur|gbp|jpy)"],
        "Account": [r"(?:account|acct|bank\s*account)\s*[:：]\s*([\d\-]+)"],
        "Beneficiary": [r"(?:beneficiary|payee|to)\s*[:：]\s*(.+)"],
    },
    "Bill of Lading": {
        "Shipment No.": [r"(?:b/l\s*no|shipment\s*no|bl\s*no)\s*[:：]\s*(\S+)"],
        "Origin": [r"(?:port\s*of\s*loading|origin|from)\s*[:：]\s*(.+)"],
        "Destination": [r"(?:port\s*of\s*discharge|destination|to)\s*[:：]\s*(.+)"],
        "Shipment Date": [r"(?:shipment\s*date|date\s*of\s*loading|date)\s*[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"],
        "Quantity": [r"(?:quantity|qty|packages)\s*[:：]\s*([\d,.]+)"],
    },
}

# Confidence thresholds
LOW_CONFIDENCE_THRESHOLD = 0.85
DEFAULT_CONFIDENCE = 0.95


def classify_document(text: str) -> Tuple[str, float]:
    """Classify document type based on text content."""
    if not text:
        return "Unknown", 0.0

    text_lower = text.lower()
    best_type = "Unknown"
    best_score = 0.0

    for doc_type, patterns in DOC_TYPE_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += 1
        # Normalize score to confidence
        confidence = min(score / max(len(patterns), 1), 1.0) * 0.95 + 0.05
        if confidence > best_score:
            best_score = confidence
            best_type = doc_type

    return best_type, round(best_score, 2)


def extract_fields(text: str, doc_type: str) -> Dict[str, Tuple[str, float]]:
    """Extract structured fields from document text based on document type.
    Returns dict of field_name -> (value, confidence).
    """
    result = {}

    patterns = FIELD_PATTERNS.get(doc_type, {})
    for field_name, field_patterns in patterns.items():
        found = False
        for pattern in field_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip() if match.lastindex else match.group(0).strip()
                # Simulate confidence based on match quality
                confidence = DEFAULT_CONFIDENCE
                # Lower confidence for fuzzy matches
                if len(value) < 3:
                    confidence = 0.75
                # Simulate occasional low confidence for certain fields
                if field_name in ("Payment Due Date", "Payment Terms", "Account"):
                    confidence = min(confidence, 0.82)
                result[field_name] = (value, round(confidence, 2))
                found = True
                break
        if not found:
            # Field not found - don't include it
            pass

    return result


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    text = ""

    # Try pdfplumber first
    if PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                return text
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")

    # Try PyMuPDF
    if PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            if text.strip():
                return text
        except Exception as e:
            logger.warning(f"PyMuPDF failed: {e}")

    return text


def extract_text_from_image(file_path: str) -> str:
    """Extract text from image using Tesseract OCR."""
    if not TESSERACT_AVAILABLE:
        return ""

    try:
        # Check if tesseract binary is available
        import shutil
        if not shutil.which("tesseract"):
            logger.warning("Tesseract binary not found in PATH")
            return ""

        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang="eng+chi_sim")
        return text
    except Exception as e:
        logger.warning(f"Tesseract OCR failed: {e}")
        return ""


def extract_text_from_excel(file_path: str) -> str:
    """Extract text from Excel file."""
    if not OPENPYXL_AVAILABLE:
        return ""

    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        text_parts = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                row_text = " | ".join([str(c) for c in row if c is not None])
                if row_text.strip():
                    text_parts.append(row_text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.warning(f"Excel extraction failed: {e}")
        return ""


def extract_text(file_path: str, file_type: str) -> str:
    """Extract text from any supported file type."""
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    elif file_type in ("image", "png", "jpg", "jpeg", "tiff", "bmp"):
        return extract_text_from_image(file_path)
    elif file_type in ("excel", "xlsx", "xls"):
        return extract_text_from_excel(file_path)
    else:
        # Try reading as text
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except:
            return ""


def get_file_type(filename: str) -> str:
    """Determine file type from filename."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return "pdf"
    elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
        return "image"
    elif ext in (".xlsx", ".xls"):
        return "excel"
    elif ext == ".csv":
        return "csv"
    else:
        return "unknown"


def process_document(file_path: str, filename: str) -> Dict:
    """
    Full OCR processing pipeline for a document.
    Returns: {
        doc_type, doc_type_confidence, ocr_text,
        structured_data, ocr_confidence, low_confidence_fields
    }
    """
    file_type = get_file_type(filename)

    # Extract raw text
    text = extract_text(file_path, file_type)

    if not text.strip():
        # If no text extracted (e.g., scanned PDF without OCR engine),
        # generate placeholder text from filename for demo purposes
        text = f"Document: {filename}\nFile type: {file_type}\n(Status: Text extraction unavailable - OCR engine may not be installed)"

    # Classify document type
    doc_type, doc_confidence = classify_document(text)

    # Extract fields
    fields = extract_fields(text, doc_type)

    structured_data = {}
    ocr_confidence = {}
    low_confidence_fields = []

    for field_name, (value, confidence) in fields.items():
        structured_data[field_name] = value
        ocr_confidence[field_name] = confidence
        if confidence < LOW_CONFIDENCE_THRESHOLD:
            low_confidence_fields.append(field_name)

    return {
        "doc_type": doc_type,
        "doc_type_confidence": doc_confidence,
        "ocr_text": text[:5000],  # Limit stored text
        "structured_data": structured_data,
        "ocr_confidence": ocr_confidence,
        "low_confidence_fields": low_confidence_fields,
        "file_type": file_type,
    }
