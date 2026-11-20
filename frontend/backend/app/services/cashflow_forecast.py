"""
Cash-flow forecasting and financial-product simulation.

This module turns existing transaction / cash-flow records into a daily
forecast and simulates how an ICBC (Asia) product changes that forecast.

Design notes
------------
- Amounts are reported in a single base currency (CNY) using the illustrative
  exchange rates already used elsewhere in the demo. Original amounts and
  currencies are kept in the entry/event payloads.
- Opening balances are the illustrative assumptions used by the existing
  funding-gap calculation; they are surfaced as "assumption" in the API.
- Product interest rates / fees are NEVER invented. When the recommendation or
  product data does not provide them they are returned as `unset`, and the
  simulation treats them as 0 while flagging them to the UI.
- FX hedging adjusts the converted value of the hedged cash flow; the notional
  itself is never added as a cash inflow.
"""
import math
from collections import defaultdict
from datetime import date, timedelta, datetime
from typing import Dict, List, Optional

from app.services.cashflow_service import (
    EXCHANGE_RATES,
    MIN_LIQUIDITY_BUFFER,
    convert_currency,
)

BASE_CURRENCY = "CNY"
HISTORY_DAYS = 30

DEFAULT_OPENING_CASH = {"CNY": 4000000}

# product_code -> simulation family
PRODUCT_SIMULATION_TYPE = {
    # Trade / term lending
    "IF001": "loan",
    "PLO005": "loan",
    "CBR011": "loan",
    "OBL012": "loan",
    "XBL013": "loan",
    "SME014": "loan",
    # Receivables / invoice finance
    "EFI006": "receivable",
    "EXN007": "receivable",
    "FOR008": "receivable",
    "FAC009": "receivable",
    # Letter of credit
    "ILC002": "lc",
    "BBL003": "lc",
    # Guarantees
    "SGR004": "guarantee",
    "BGS010": "guarantee",
    # FX hedging
    "FXF015": "fx",
    "NDF016": "fx",
}

EVENT_LABELS = {
    "loan_drawdown": {"zh-CN": "融资放款到账", "zh-TW": "融資放款到賬", "en": "Loan drawdown"},
    "loan_repayment": {"zh-CN": "贷款本息还款", "zh-TW": "貸款本息還款", "en": "Loan principal + interest repayment"},
    "fee": {"zh-CN": "手续费", "zh-TW": "手續費", "en": "Processing fee"},
    "receivable_advance": {"zh-CN": "应收账款预付款", "zh-TW": "應收賬款預付款", "en": "Receivables advance"},
    "receivable_repayment": {"zh-CN": "融资还款（应收款回款中扣收）", "zh-TW": "融資還款（應收款回款中扣收）", "en": "Financing repayment from collection"},
    "lc_margin": {"zh-CN": "信用证保证金占用", "zh-TW": "信用證保證金佔用", "en": "L/C margin deposit"},
    "lc_fee": {"zh-CN": "信用证手续费", "zh-TW": "信用證手續費", "en": "L/C fee"},
    "lc_settlement": {"zh-CN": "信用证到期付款", "zh-TW": "信用證到期付款", "en": "L/C settlement payment"},
    "lc_margin_release": {"zh-CN": "保证金退回", "zh-TW": "保證金退回", "en": "Margin release"},
    "guarantee_margin": {"zh-CN": "担保保证金占用", "zh-TW": "擔保保證金佔用", "en": "Guarantee margin deposit"},
    "guarantee_fee": {"zh-CN": "担保费", "zh-TW": "擔保費", "en": "Guarantee fee"},
    "guarantee_margin_release": {"zh-CN": "担保保证金退回", "zh-TW": "擔保保證金退回", "en": "Guarantee margin release"},
    "fx_settlement": {"zh-CN": "外汇对冲结算差额", "zh-TW": "外匯對沖結算差額", "en": "FX hedge settlement difference"},
}

STATUS_LABELS = {
    "resolved": {"zh-CN": "缺口已解决", "zh-TW": "缺口已解決", "en": "Shortfall Resolved"},
    "partial": {"zh-CN": "部分缓解", "zh-TW": "部分緩解", "en": "Partially Resolved"},
    "remains": {"zh-CN": "缺口仍存在", "zh-TW": "缺口仍存在", "en": "Shortfall Remains"},
    "none": {"zh-CN": "无缺口", "zh-TW": "無缺口", "en": "No Shortfall"},
}


def _norm_lang(lang: Optional[str]) -> str:
    if lang in ("zh-CN", "zh-TW", "en"):
        return lang
    return "zh-CN"


def _label(labels: Dict[str, str], lang: str) -> str:
    return labels.get(lang) or labels.get("en") or ""


def _as_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def to_base(amount: float, currency: str) -> float:
    """Convert an amount into the reporting base currency (CNY)."""
    return convert_currency(abs(float(amount or 0)), currency or BASE_CURRENCY, BASE_CURRENCY)


def categorize(description: str) -> str:
    """Infer a cash-flow category from an existing record description."""
    text = (description or "").lower()
    if any(k in text for k in ("letter of credit", "l/c", " lc", "credit letter")):
        return "LC"
    if any(k in text for k in ("loan", "repayment", "interest", "borrow")):
        return "LOAN"
    if any(k in text for k in ("customer", "collection", "receivable", "sales proceeds")):
        return "AR"
    if any(k in text for k in ("supplier", "payable", "purchase")):
        return "AP"
    if any(k in text for k in ("expense", "operating", "salary", "payroll", "rent", "overhead")):
        return "OPEX"
    return "OTHER"


def build_entries(cashflow_items: List[Dict], transaction=None) -> List[Dict]:
    """Normalize existing cash-flow records into signed forecast entries.

    Records come from the `cashflow_items` table. If the transaction carries a
    supplier payment / customer collection that is not represented yet, it is
    added once (deduplicated by date + currency + amount + direction).
    """
    entries: List[Dict] = []
    seen = set()

    def add(flow_date, flow_type, description, currency, amount, source, status):
        flow_date = _as_date(flow_date)
        if not flow_date:
            return
        amount = float(amount or 0)
        if amount == 0:
            return
        key = (flow_date.isoformat(), currency, round(abs(amount), 2), flow_type)
        if key in seen:
            return
        seen.add(key)
        entries.append({
            "date": flow_date.isoformat(),
            "type": flow_type,
            "category": categorize(description),
            "description": description,
            "currency": currency,
            "amount": abs(amount),
            "signed_amount": abs(amount) if flow_type == "inflow" else -abs(amount),
            "amount_base": round(to_base(amount, currency), 2),
            "source": source,
            "status": status,
        })

    for item in cashflow_items:
        add(item.get("flow_date"), item.get("flow_type"), item.get("description"),
            item.get("currency"), item.get("amount"), "cashflow_item", "committed")

    if transaction:
        has_inflow = any(e["type"] == "inflow" for e in entries)
        has_outflow = any(e["type"] == "outflow" for e in entries)
        infos = transaction if isinstance(transaction, dict) else {
            "buyer": transaction.buyer,
            "supplier": transaction.supplier,
            "order_amount": transaction.order_amount,
            "order_currency": transaction.order_currency,
            "invoice_amount": transaction.invoice_amount,
            "invoice_currency": transaction.invoice_currency,
            "payment_date": transaction.payment_date,
            "expected_collection_date": transaction.expected_collection_date,
            "order_date": transaction.order_date,
        }
        if (not has_inflow and infos.get("expected_collection_date")
                and infos.get("order_amount")):
            add(infos["expected_collection_date"], "inflow",
                f"Customer Collection ({infos.get('buyer', 'buyer')})",
                infos.get("order_currency") or BASE_CURRENCY,
                infos.get("order_amount"), "transaction", "forecast")
        if (not has_outflow and infos.get("payment_date")
                and infos.get("invoice_amount")):
            add(infos["payment_date"], "outflow",
                f"Supplier Payment ({infos.get('supplier', 'supplier')})",
                infos.get("invoice_currency") or BASE_CURRENCY,
                infos.get("invoice_amount"), "transaction", "forecast")

    entries.sort(key=lambda e: e["date"])
    return entries


def _date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def build_forecast(entries: List[Dict], as_of: Optional[date] = None,
                   horizon_days: int = 90,
                   opening_cash: Optional[Dict[str, float]] = None,
                   history_days: int = HISTORY_DAYS) -> Dict:
    """Build a daily historical + forecast cash-flow series in base currency."""
    as_of = as_of or date.today()
    horizon_days = max(1, min(int(horizon_days or 90), 365))
    opening_cash = opening_cash or dict(DEFAULT_OPENING_CASH)
    opening_base = round(sum(to_base(v, c) for c, v in opening_cash.items()), 2)

    history_start = as_of - timedelta(days=history_days)
    forecast_end = as_of + timedelta(days=horizon_days)

    daily = {d: {"inflow": 0.0, "outflow": 0.0} for d in _date_range(history_start, forecast_end)}
    sources = []
    for e in entries:
        d = _as_date(e["date"])
        if not d or d < history_start or d > forecast_end:
            continue
        status = "actual" if d < as_of else "forecast"
        e = dict(e)
        e["status"] = status
        sources.append(e)
        bucket = daily[d]
        if e["type"] == "inflow":
            bucket["inflow"] += e["amount_base"]
        else:
            bucket["outflow"] += e["amount_base"]

    buffer = float(MIN_LIQUIDITY_BUFFER.get(BASE_CURRENCY, 0))
    balance = opening_base
    series = []
    min_balance = None
    min_date = None
    shortfall_days = 0
    below_buffer_days = 0
    gap_start = None
    gap_end = None
    total_inflow = 0.0
    total_outflow = 0.0

    for d in _date_range(history_start, forecast_end):
        inflow = round(daily[d]["inflow"], 2)
        outflow = round(daily[d]["outflow"], 2)
        net = round(inflow - outflow, 2)
        is_forecast = d >= as_of
        row = {
            "date": d.isoformat(),
            "is_forecast": is_forecast,
            "inflow": inflow,
            "outflow": outflow,
            "net": net,
            "balance": None,
        }
        if is_forecast:
            balance = round(balance + net, 2)
            row["balance"] = balance
            total_inflow += inflow
            total_outflow += outflow
            if min_balance is None or balance < min_balance:
                min_balance = balance
                min_date = d
            if balance < 0 and gap_start is None:
                gap_start = d
            if balance >= 0 and gap_start is not None and gap_end is None:
                gap_end = d
            if balance < 0:
                shortfall_days += 1
            if balance < buffer:
                below_buffer_days += 1
        series.append(row)

    lowest = round(min_balance if min_balance is not None else opening_base, 2)
    closing = round(balance, 2)
    cash_deficit = round(max(0.0, -lowest), 2)
    buffer_gap = round(max(0.0, buffer - lowest), 2)
    gap_start_date = gap_start.isoformat() if gap_start else None
    gap_end_date = gap_end.isoformat() if gap_end else None
    if gap_start:
        gap_duration_days = max(1, ((gap_end or forecast_end) - gap_start).days)
    else:
        gap_duration_days = 0

    kpis = {
        "base_currency": BASE_CURRENCY,
        "opening_balance_base": opening_base,
        "opening_balance": {c: round(v, 2) for c, v in opening_cash.items()},
        "projected_closing_balance": closing,
        "total_inflow": round(total_inflow, 2),
        "total_outflow": round(total_outflow, 2),
        "net_change": round(total_inflow - total_outflow, 2),
        "lowest_balance": lowest,
        "lowest_balance_date": min_date.isoformat() if min_date else None,
        "min_liquidity_buffer": buffer,
        "shortfall_amount": cash_deficit,
        "buffer_shortfall_amount": buffer_gap,
        "shortfall_days": shortfall_days,
        "below_buffer_days": below_buffer_days,
        "has_shortfall": cash_deficit > 0,
        "gap_start_date": gap_start_date,
        "gap_end_date": gap_end_date,
        "gap_duration_days": gap_duration_days,
    }

    return {
        "as_of": as_of.isoformat(),
        "horizon_days": horizon_days,
        "history_days": history_days,
        "base_currency": BASE_CURRENCY,
        "series": series,
        "sources": sources,
        "kpis": kpis,
        "assumptions": {
            "exchange_rates": dict(EXCHANGE_RATES),
            "opening_balance": {c: round(v, 2) for c, v in opening_cash.items()},
            "min_liquidity_buffer": dict(MIN_LIQUIDITY_BUFFER),
            "note": "opening_balance_illustrative",
        },
    }


def build_summary(forecast: Dict, lang: str = "zh-CN") -> str:
    lang = _norm_lang(lang)
    k = forecast["kpis"]
    days = forecast["horizon_days"]
    cur = BASE_CURRENCY
    gap = ""
    if k.get("has_shortfall"):
        if lang == "zh-TW":
            gap = (f"預計有 {k['shortfall_days']} 天現金餘額為負，"
                   f"缺口區間 {k.get('gap_start_date')} 至 {k.get('gap_end_date') or '期末'}，"
                   f"最大缺口 {cur} {k['shortfall_amount']:,.0f}。")
        elif lang == "en":
            gap = (f"Cash balance turns negative on {k['shortfall_days']} day(s), "
                   f"from {k.get('gap_start_date')} to {k.get('gap_end_date') or 'the end of the horizon'}, "
                   f"with a maximum shortfall of {cur} {k['shortfall_amount']:,.0f}.")
        else:
            gap = (f"预计有 {k['shortfall_days']} 天现金余额为负，"
                   f"缺口区间 {k.get('gap_start_date')} 至 {k.get('gap_end_date') or '期末'}，"
                   f"最大缺口 {cur} {k['shortfall_amount']:,.0f}。")
    if lang == "zh-TW":
        parts = [f"未來 {days} 天預計現金流入 {cur} {k['total_inflow']:,.0f}，流出 {cur} {k['total_outflow']:,.0f}，"
                 f"期末餘額約 {cur} {k['projected_closing_balance']:,.0f}。"]
        parts.append(f"最低餘額 {cur} {k['lowest_balance']:,.0f}"
                     + (f"（{k['lowest_balance_date']}）" if k.get("lowest_balance_date") else "") + "。")
        parts.append(gap if gap else "預計期內現金餘額保持為正。")
    elif lang == "en":
        parts = [f"Over the next {days} days, expected inflow is {cur} {k['total_inflow']:,.0f} and outflow "
                 f"{cur} {k['total_outflow']:,.0f}, with a projected closing balance of {cur} "
                 f"{k['projected_closing_balance']:,.0f}."]
        parts.append(f"Lowest balance {cur} {k['lowest_balance']:,.0f}"
                     + (f" on {k['lowest_balance_date']}" if k.get("lowest_balance_date") else "") + ".")
        parts.append(gap if gap else "Cash balance is expected to stay positive.")
    else:
        parts = [f"未来 {days} 天预计现金流入 {cur} {k['total_inflow']:,.0f}，流出 {cur} {k['total_outflow']:,.0f}，"
                 f"期末余额约 {cur} {k['projected_closing_balance']:,.0f}。"]
        parts.append(f"最低余额 {cur} {k['lowest_balance']:,.0f}"
                     + (f"（{k['lowest_balance_date']}）" if k.get("lowest_balance_date") else "") + "。")
        parts.append(gap if gap else "预计期内现金余额保持为正。")
    return " ".join(parts)


# ─── Product simulation ───

def simulation_type_for(product) -> str:
    code = getattr(product, "product_code", "") or ""
    if code in PRODUCT_SIMULATION_TYPE:
        return PRODUCT_SIMULATION_TYPE[code]
    category = (getattr(product, "category", "") or "").lower()
    if "guarantee" in category:
        return "guarantee"
    if "treasury" in category:
        return "fx"
    if "trade finance" in category:
        return "loan"
    return "loan"


def _parse_tenor_days(text: Optional[str]) -> Optional[int]:
    """Parse a product's indicative tenor string into days.

    Handles ranges ("30-90 days", "1-3 years") by taking the upper bound and
    applying the unit present in the text.
    """
    if not text:
        return None
    lower = text.lower()
    digits = "".join(ch if ch.isdigit() else " " for ch in lower).split()
    if not digits:
        return None
    try:
        values = [int(d) for d in digits]
    except ValueError:
        return None
    value = max(values)
    if "year" in lower:
        return value * 365
    if "month" in lower:
        return value * 30
    if "day" in lower:
        return value
    return None


def _param(key, value, unit, editable=True, source="derived", options=None):
    return {
        "key": key,
        "value": value,
        "unit": unit,
        "editable": editable,
        "source": source,  # user | recommendation | product | derived | assumption | unset
        "options": options or [],
    }


def _num(params: Dict, key: str) -> Optional[float]:
    value = params.get(key)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _event(events: List[Dict], day: date, code: str, signed_amount: float,
           lang: str, currency: str = BASE_CURRENCY, note: str = ""):
    desc = _label(EVENT_LABELS.get(code, {}), lang) or code
    events.append({
        "date": day.isoformat(),
        "code": code,
        "description": desc,
        "currency": currency,
        "amount": round(signed_amount, 2),
        "note": note,
    })


def _compute_kpis(series: List[Dict], opening_base: float, buffer: float,
                  lang: str, key: str = "balance") -> Dict:
    forecast_rows = [r for r in series if r["is_forecast"]]
    balances = [r[key] for r in forecast_rows if r.get(key) is not None]
    lowest = round(min(balances), 2) if balances else opening_base
    lowest_row = next((r for r in forecast_rows if r.get(key) == lowest), None)
    closing = round(balances[-1], 2) if balances else opening_base
    deficit = round(max(0.0, -lowest), 2)
    buffer_gap = round(max(0.0, buffer - lowest), 2)
    shortfall_days = sum(1 for b in balances if b < 0)
    below_buffer_days = sum(1 for b in balances if b < buffer)

    gap_start = next((r["date"] for r in forecast_rows if (r.get(key) or 0) < 0), None)
    gap_end = None
    if gap_start:
        seen = False
        for r in forecast_rows:
            if r["date"] == gap_start:
                seen = True
                continue
            if seen and (r.get(key) or 0) >= 0:
                gap_end = r["date"]
                break
    gap_duration = 0
    if gap_start:
        start_d = _as_date(gap_start)
        end_d = _as_date(gap_end) if gap_end else _as_date(forecast_rows[-1]["date"])
        gap_duration = max(1, (end_d - start_d).days)

    return {
        "projected_closing_balance": closing,
        "lowest_balance": lowest,
        "lowest_balance_date": lowest_row["date"] if lowest_row else None,
        "shortfall_amount": deficit,
        "buffer_shortfall_amount": buffer_gap,
        "shortfall_days": shortfall_days,
        "below_buffer_days": below_buffer_days,
        "has_shortfall": deficit > 0,
        "gap_start_date": gap_start,
        "gap_end_date": gap_end,
        "gap_duration_days": gap_duration,
    }


def simulate_product(product, recommendation, transaction, entries: List[Dict],
                     forecast: Dict, params: Optional[Dict] = None,
                     horizon_days: int = 90, lang: str = "zh-CN") -> Dict:
    """Simulate a product's effect on the forecast.

    Different product families apply genuinely different cash-flow logic;
    see the module docstring.
    """
    lang = _norm_lang(lang)
    params = params or {}
    as_of = date.fromisoformat(forecast["as_of"])
    forecast_end = as_of + timedelta(days=forecast["horizon_days"])
    base_kpis = forecast["kpis"]
    buffer = float(base_kpis.get("min_liquidity_buffer") or 0)
    sim_type = simulation_type_for(product)

    rec_amount = getattr(recommendation, "estimated_amount", None) if recommendation else None
    rec_tenor = getattr(recommendation, "estimated_tenor_days", None) if recommendation else None
    gap_default = float(base_kpis.get("shortfall_amount") or 0)
    tx_invoice_base = to_base(getattr(transaction, "invoice_amount", 0) or 0,
                              getattr(transaction, "invoice_currency", BASE_CURRENCY) or BASE_CURRENCY)
    amount_default = round(rec_amount or gap_default or tx_invoice_base, 2)
    tenure_default = int(rec_tenor or _parse_tenor_days(getattr(product, "typical_tenor", "")) or 90)

    events: List[Dict] = []
    schema: List[Dict] = []
    unconfigured: List[str] = []
    assumptions: List[Dict] = []
    notes: List[Dict] = []
    financing_cost = 0.0
    receivable_info = None

    interest = _num(params, "interest_rate_pct")
    fee_pct = _num(params, "processing_fee_pct")

    user_amount = _num(params, "amount")
    amount = user_amount if user_amount is not None else amount_default
    amount_source = "user" if user_amount is not None else ("recommendation" if rec_amount else "derived")

    user_tenure = _num(params, "tenure_days")
    tenure = int(user_tenure) if user_tenure is not None else tenure_default
    tenure_source = "user" if user_tenure is not None else ("recommendation" if rec_tenor else "product")

    def amount_param():
        return _param("amount", round(amount, 2), BASE_CURRENCY, True, amount_source)

    if sim_type == "loan":
        if interest is None:
            unconfigured.append("interest_rate_pct")
        if fee_pct is None:
            unconfigured.append("processing_fee_pct")
        repayment = params.get("repayment_method") or "bullet"
        repayment_source = "user" if params.get("repayment_method") else "assumption"
        rate = interest or 0.0
        fee = amount * (fee_pct or 0.0) / 100.0
        _event(events, as_of, "loan_drawdown", amount, lang)
        if fee:
            _event(events, as_of, "fee", -fee, lang)
        if repayment == "amortizing":
            n = max(1, math.ceil(tenure / 30))
            monthly_rate = rate / 100.0 / 12.0
            if monthly_rate > 0:
                installment = amount * monthly_rate / (1 - (1 + monthly_rate) ** -n)
            else:
                installment = amount / n
            for i in range(1, n + 1):
                day = as_of + timedelta(days=30 * i)
                _event(events, day, "loan_repayment", -installment, lang)
            total_interest = installment * n - amount
        else:
            total_interest = amount * rate / 100.0 * tenure / 365.0
            _event(events, as_of + timedelta(days=tenure), "loan_repayment",
                   -(amount + total_interest), lang)
        financing_cost = round(total_interest + fee, 2)
        schema = [
            amount_param(),
            _param("tenure_days", tenure, "days", True, tenure_source),
            _param("interest_rate_pct", interest, "% p.a.", True,
                   "user" if interest is not None else "unset"),
            _param("processing_fee_pct", fee_pct, "%", True,
                   "user" if fee_pct is not None else "unset"),
            _param("repayment_method", repayment, "", True, repayment_source,
                   options=["bullet", "amortizing"]),
        ]
        if interest is None:
            assumptions.append({"key": "interest_rate_pct", "note": "unset_treated_as_zero"})
        if fee_pct is None:
            assumptions.append({"key": "processing_fee_pct", "note": "unset_treated_as_zero"})
        if repayment == "amortizing":
            assumptions.append({"key": "repayment_method", "note": "equal_monthly_installments"})

    elif sim_type == "receivable":
        if interest is None:
            unconfigured.append("interest_rate_pct")
        if fee_pct is None:
            unconfigured.append("processing_fee_pct")
        eligible = [e for e in entries
                    if e["type"] == "inflow" and e.get("category") == "AR"
                    and _as_date(e["date"]) and _as_date(e["date"]) >= as_of
                    and _as_date(e["date"]) <= forecast_end]
        eligible.sort(key=lambda e: e["amount_base"], reverse=True)
        idx_raw = params.get("receivable_index")
        try:
            idx = int(idx_raw) if idx_raw is not None else 0
        except (TypeError, ValueError):
            idx = 0
        idx = max(0, min(idx, len(eligible) - 1)) if eligible else 0
        recv = eligible[idx] if eligible else None
        recv_base = float(recv["amount_base"]) if recv else 0.0
        due = _as_date(recv["date"]) if recv else forecast_end
        if user_amount is None and recv_base:
            amount = round(min(amount_default if amount_default > 0 else recv_base, recv_base), 2)
            amount_source = "derived"
        advance_rate = round(amount / recv_base * 100, 2) if recv_base else 0.0
        days = max(1, (due - as_of).days)
        rate = interest or 0.0
        fee = amount * (fee_pct or 0.0) / 100.0
        total_interest = amount * rate / 100.0 * days / 365.0
        _event(events, as_of, "receivable_advance", amount, lang)
        if fee:
            _event(events, as_of, "fee", -fee, lang)
        _event(events, due, "receivable_repayment", -(amount + total_interest), lang)
        financing_cost = round(total_interest + fee, 2)
        receivable_info = {
            "eligible_receivables": [{
                "index": i,
                "date": e["date"],
                "description": e["description"],
                "currency": e["currency"],
                "amount": e["amount"],
                "amount_base": e["amount_base"],
            } for i, e in enumerate(eligible)],
            "selected_index": idx,
            "advance_rate_pct": advance_rate,
            "receivable_amount_base": recv_base,
        }
        schema = [
            amount_param(),
            _param("receivable_index", idx, "", True,
                   "user" if idx_raw is not None else "derived",
                   options=[str(i) for i in range(len(eligible))]),
            _param("advance_rate_pct", advance_rate, "%", False, "derived"),
            _param("interest_rate_pct", interest, "% p.a.", True,
                   "user" if interest is not None else "unset"),
            _param("processing_fee_pct", fee_pct, "%", True,
                   "user" if fee_pct is not None else "unset"),
        ]
        if interest is None:
            assumptions.append({"key": "interest_rate_pct", "note": "unset_treated_as_zero"})
        if fee_pct is None:
            assumptions.append({"key": "processing_fee_pct", "note": "unset_treated_as_zero"})

    elif sim_type == "lc":
        if fee_pct is None:
            unconfigured.append("processing_fee_pct")
        margin_pct = _num(params, "margin_pct")
        margin_source = "user" if margin_pct is not None else "assumption"
        if margin_pct is None:
            margin_pct = 30.0
        margin = amount * margin_pct / 100.0
        fee = amount * (fee_pct or 0.0) / 100.0
        _event(events, as_of, "lc_margin", -margin, lang)
        if fee:
            _event(events, as_of, "lc_fee", -fee, lang)
        settle = as_of + timedelta(days=tenure)
        _event(events, settle, "lc_settlement", -amount, lang)
        _event(events, settle, "lc_margin_release", margin, lang)
        financing_cost = round(fee, 2)
        schema = [
            amount_param(),
            _param("margin_pct", margin_pct, "%", True, margin_source),
            _param("tenure_days", tenure, "days", True, tenure_source),
            _param("processing_fee_pct", fee_pct, "%", True,
                   "user" if fee_pct is not None else "unset"),
        ]
        if fee_pct is None:
            assumptions.append({"key": "processing_fee_pct", "note": "unset_treated_as_zero"})
        assumptions.append({"key": "margin_pct", "note": "illustrative_default"})
        notes.append({"code": "lc_margin_lockup",
                      "text": _label({"zh-CN": "保证金为占用资金，到期退回；手续费为实际成本。",
                                      "zh-TW": "保證金為佔用資金，到期退回；手續費為實際成本。",
                                      "en": "Margin is a temporary lock-up released at maturity; the fee is the real cost."}, lang)})

    elif sim_type == "guarantee":
        if fee_pct is None:
            unconfigured.append("processing_fee_pct")
        margin_pct = _num(params, "margin_pct")
        margin_source = "user" if margin_pct is not None else "assumption"
        if margin_pct is None:
            margin_pct = 30.0
        margin = amount * margin_pct / 100.0
        fee = amount * (fee_pct or 0.0) / 100.0
        _event(events, as_of, "guarantee_margin", -margin, lang)
        if fee:
            _event(events, as_of, "guarantee_fee", -fee, lang)
        _event(events, as_of + timedelta(days=tenure), "guarantee_margin_release", margin, lang)
        financing_cost = round(fee, 2)
        schema = [
            amount_param(),
            _param("margin_pct", margin_pct, "%", True, margin_source),
            _param("tenure_days", tenure, "days", True, tenure_source),
            _param("processing_fee_pct", fee_pct, "%", True,
                   "user" if fee_pct is not None else "unset"),
        ]
        assumptions.append({"key": "margin_pct", "note": "illustrative_default"})
        if fee_pct is None:
            assumptions.append({"key": "processing_fee_pct", "note": "unset_treated_as_zero"})

    elif sim_type == "fx":
        foreign_recv = [e for e in entries
                        if e["type"] == "inflow" and e.get("currency") != BASE_CURRENCY
                        and _as_date(e["date"]) and _as_date(e["date"]) >= as_of
                        and _as_date(e["date"]) <= forecast_end]
        foreign_recv.sort(key=lambda e: e["amount_base"], reverse=True)
        recv = foreign_recv[0] if foreign_recv else None

        tx_currency = None
        tx_amount = 0.0
        tx_collection_date = None
        if transaction is not None:
            if isinstance(transaction, dict):
                tx_currency = transaction.get("order_currency")
                tx_amount = float(transaction.get("order_amount") or 0)
                tx_collection_date = _as_date(transaction.get("expected_collection_date"))
            else:
                tx_currency = getattr(transaction, "order_currency", None)
                tx_amount = float(getattr(transaction, "order_amount", 0) or 0)
                tx_collection_date = _as_date(
                    getattr(transaction, "expected_collection_date", None))

        if recv:
            currency = recv["currency"]
            hedged_default = float(recv["amount"])
            exposure_date = _as_date(recv["date"])
            exposure_source = "cashflow"
        elif tx_currency and tx_currency != BASE_CURRENCY and tx_amount > 0:
            # The forecast itself is single-currency (CNY), but the underlying
            # order is foreign-currency; hedge the conversion of that exposure.
            currency = tx_currency
            hedged_default = tx_amount
            exposure_date = tx_collection_date or (as_of + timedelta(days=30))
            exposure_source = "transaction"
        else:
            currency = "USD"
            hedged_default = 0.0
            exposure_date = None
            exposure_source = "none"

        user_hedged = _num(params, "hedged_amount")
        hedged = user_hedged if user_hedged is not None else hedged_default
        forward_rate = _num(params, "forward_rate")
        spot = EXCHANGE_RATES.get(f"{currency}_{BASE_CURRENCY}")
        if forward_rate is None:
            unconfigured.append("forward_rate")
        delta = 0.0
        if forward_rate is not None and spot and hedged > 0 and exposure_date:
            delta = hedged * (forward_rate - spot)
            _event(events, exposure_date, "fx_settlement", delta, lang,
                   currency=BASE_CURRENCY,
                   note=f"{currency}: forward {forward_rate} vs spot {spot}")
        schema = [
            _param("hedged_amount", round(hedged, 2), currency, True,
                   "user" if user_hedged is not None else "derived"),
            _param("forward_rate", forward_rate, f"{currency}/{BASE_CURRENCY}", True,
                   "user" if forward_rate is not None else "unset"),
            _param("spot_rate", spot, f"{currency}/{BASE_CURRENCY}", False, "assumption"),
        ]
        financing_cost = 0.0
        if exposure_source == "transaction":
            notes.append({"code": "fx_transaction_exposure",
                          "text": _label({"zh-CN": f"现金流预测已统一为 CNY；对冲敞口来自订单的 {currency} {hedged:,.0f} 应收，按远期汇率折算差额调整人民币回款。",
                                          "zh-TW": f"現金流預測已統一為 CNY；對沖敞口來自訂單的 {currency} {hedged:,.0f} 應收，按遠期匯率折算差額調整人民幣回款。",
                                          "en": f"The forecast is in CNY; the hedge applies to the {currency} {hedged:,.0f} order receivable and adjusts the CNY collection by the forward-vs-spot difference."}, lang)})
        notes.append({"code": "fx_notional_not_cash",
                      "text": _label({"zh-CN": "外汇对冲名义本金不直接作为现金流入，仅体现按远期汇率折算后的结算差额。",
                                      "zh-TW": "外匯對沖名義本金不直接作為現金流入，僅體現按遠期匯率折算後的結算差額。",
                                      "en": "The FX notional is not counted as cash inflow; only the difference between forward and spot conversion is recognised."}, lang)})
        assumptions.append({"key": "spot_rate", "note": "illustrative_exchange_rate"})

    else:
        schema = [amount_param()]

    # Merge events into the base series
    events_by_date = defaultdict(float)
    for ev in events:
        if ev["date"] < forecast["as_of"]:
            continue
        events_by_date[ev["date"]] += ev["amount"]

    series = []
    sim_balance = base_kpis["opening_balance_base"]
    for row in forecast["series"]:
        new_row = dict(row)
        if row["is_forecast"]:
            delta = round(events_by_date.get(row["date"], 0.0), 2)
            sim_inflow = round(row["inflow"] + max(delta, 0.0), 2)
            sim_outflow = round(row["outflow"] + abs(min(delta, 0.0)), 2)
            sim_net = round(sim_inflow - sim_outflow, 2)
            sim_balance = round(sim_balance + sim_net, 2)
            new_row.update({
                "sim_inflow": sim_inflow,
                "sim_outflow": sim_outflow,
                "sim_net": sim_net,
                "sim_balance": sim_balance,
            })
        else:
            new_row.update({"sim_inflow": None, "sim_outflow": None,
                            "sim_net": None, "sim_balance": None})
        series.append(new_row)

    sim_kpis = _compute_kpis(series, base_kpis["opening_balance_base"], buffer, lang,
                             key="sim_balance")

    base_lowest = base_kpis["lowest_balance"]
    additional_liquidity = round(max(0.0, sim_kpis["lowest_balance"] - base_lowest), 2)
    improvement = round(sim_kpis["lowest_balance"] - base_lowest, 2)

    base_deficit = round(base_kpis["shortfall_amount"], 2)
    sim_deficit = round(sim_kpis["shortfall_amount"], 2)
    if base_deficit > 0 and sim_deficit <= 0:
        resolution = "resolved"
    elif base_deficit > 0 and sim_deficit < base_deficit:
        resolution = "partial"
    elif base_deficit > 0:
        resolution = "remains"
    else:
        resolution = "none"

    outside = [e for e in events if e["date"] > forecast_end.isoformat()]
    if outside:
        notes.append({"code": "events_outside_horizon",
                      "text": _label({"zh-CN": f"有 {len(outside)} 笔产品现金流发生在预测窗口之外，未计入期末余额，但计入了融资成本。",
                                      "zh-TW": f"有 {len(outside)} 筆產品現金流發生在預測窗口之外，未計入期末餘額，但計入了融資成本。",
                                      "en": f"{len(outside)} product cash flow(s) fall outside the forecast window; they are excluded from the closing balance but included in financing cost."}, lang)})

    summary = _simulation_summary(lang, sim_type, sim_kpis, base_kpis,
                                  financing_cost, additional_liquidity)

    return {
        "simulation_type": sim_type,
        "as_of": forecast["as_of"],
        "horizon_days": forecast["horizon_days"],
        "base_currency": BASE_CURRENCY,
        "params": {p["key"]: p["value"] for p in schema},
        "parameter_schema": schema,
        "unconfigured": sorted(set(unconfigured)),
        "assumptions": assumptions,
        "notes": notes,
        "events": events,
        "receivable": receivable_info,
        "series": series,
        "kpis": {
            "base": base_kpis,
            "simulation": sim_kpis,
            "financing_cost": financing_cost,
            "additional_liquidity": additional_liquidity,
            "cash_flow_improvement": improvement,
            "shortfall_risk": {
                "status": resolution,
                "resolution": resolution,
                "label": _label(STATUS_LABELS[resolution], lang),
                "base_shortfall_amount": base_deficit,
                "simulation_shortfall_amount": sim_deficit,
                "base_shortfall_days": base_kpis["shortfall_days"],
                "simulation_shortfall_days": sim_kpis["shortfall_days"],
                "base_gap_start_date": base_kpis.get("gap_start_date"),
                "base_gap_end_date": base_kpis.get("gap_end_date"),
                "simulation_gap_start_date": sim_kpis.get("gap_start_date"),
                "simulation_gap_end_date": sim_kpis.get("gap_end_date"),
            },
        },
        "summary": summary,
    }


def _simulation_summary(lang: str, sim_type: str, sim_kpis: Dict,
                        base_kpis: Dict, cost: float, liquidity: float) -> str:
    cur = BASE_CURRENCY
    if lang == "zh-TW":
        return (f"使用該產品後，預計期末餘額 {cur} {sim_kpis['projected_closing_balance']:,.0f}，"
                f"新增可用流動性 {cur} {liquidity:,.0f}，預計融資成本 {cur} {cost:,.0f}；"
                f"最低餘額 {cur} {sim_kpis['lowest_balance']:,.0f}。")
    if lang == "en":
        return (f"With this product, projected closing balance is {cur} "
                f"{sim_kpis['projected_closing_balance']:,.0f}, additional available liquidity "
                f"{cur} {liquidity:,.0f}, estimated financing cost {cur} {cost:,.0f}; "
                f"lowest balance {cur} {sim_kpis['lowest_balance']:,.0f}.")
    return (f"使用该产品后，预计期末余额 {cur} {sim_kpis['projected_closing_balance']:,.0f}，"
            f"新增可用流动性 {cur} {liquidity:,.0f}，预计融资成本 {cur} {cost:,.0f}；"
            f"最低余额 {cur} {sim_kpis['lowest_balance']:,.0f}。")


# ─── Cash-flow-specific recommendations ───

def _display_name(product, lang: str) -> str:
    cn = getattr(product, "product_name_cn", None) or getattr(product, "product_name", "") or ""
    tw = getattr(product, "product_name_tw", None) or cn
    en = getattr(product, "product_name", "") or cn
    if lang == "en":
        return en
    if lang == "zh-TW":
        return tw
    return cn


def _gap_window_text(lang: str, start: str, end: Optional[str]) -> str:
    end_txt = end or ("期末" if lang == "zh-CN" else "期末" if lang == "zh-TW" else "the end of the horizon")
    return f"{start} ~ {end_txt}"


def recommend_cashflow_products(products: List, forecast: Dict,
                                entries: List[Dict], transaction=None,
                                lang: str = "zh-CN", limit: int = 5) -> List[Dict]:
    """Pick existing ICBC (Asia) products that can address the forecast gap.

    Only liquidity-providing products are returned when a cash deficit exists:
    receivables finance (backed by a future receivable) and term/working-capital
    loans. Guarantees / LCs are excluded because they consume margin rather than
    inject cash.
    """
    lang = _norm_lang(lang)
    k = forecast["kpis"]
    deficit = float(k.get("shortfall_amount") or 0)
    if deficit <= 0:
        return []

    as_of = date.fromisoformat(forecast["as_of"])
    horizon_end = as_of + timedelta(days=forecast["horizon_days"])
    gap_start = k.get("gap_start_date") or as_of.isoformat()
    gap_end = k.get("gap_end_date")
    gap_days = int(k.get("gap_duration_days") or 30)

    future_ar = []
    for e in entries:
        d = _as_date(e.get("date"))
        if (e.get("type") == "inflow" and e.get("category") == "AR"
                and d and as_of <= d <= horizon_end):
            future_ar.append((d, e))
    future_ar.sort(key=lambda item: item[0])
    next_ar_date, next_ar = future_ar[0] if future_ar else (None, None)
    ar_amount = float(next_ar["amount_base"]) if next_ar else 0.0

    receivable, loans = [], []
    for product in products:
        sim_type = simulation_type_for(product)
        if sim_type == "receivable" and next_ar:
            amount = round(min(deficit, ar_amount), 2) if ar_amount else deficit
            tenure = max(1, (next_ar_date - as_of).days)
            if lang == "zh-CN":
                reason = (f"预计 {_gap_window_text(lang, gap_start, gap_end)} 出现 "
                          f"CNY {deficit:,.0f} 现金缺口；{_display_name(product, lang)} 可基于 "
                          f"{next_ar_date.isoformat()} 到账的应收账款（CNY {ar_amount:,.0f}）提前回笼资金，缓解该缺口。")
            elif lang == "zh-TW":
                reason = (f"預計 {_gap_window_text(lang, gap_start, gap_end)} 出現 "
                          f"CNY {deficit:,.0f} 現金缺口；{_display_name(product, lang)} 可基於 "
                          f"{next_ar_date.isoformat()} 到賬的應收賬款（CNY {ar_amount:,.0f}）提前回籠資金，緩解該缺口。")
            else:
                reason = (f"A CNY {deficit:,.0f} cash gap is projected for "
                          f"{_gap_window_text(lang, gap_start, gap_end)}. "
                          f"{_display_name(product, lang)} can advance funds against the "
                          f"CNY {ar_amount:,.0f} receivable due on {next_ar_date.isoformat()}.")
            confidence = 0.9
        elif sim_type == "loan":
            amount = deficit
            tenure = max(60, gap_days + 30)
            if lang == "zh-CN":
                reason = (f"预计 {_gap_window_text(lang, gap_start, gap_end)} 出现 "
                          f"CNY {deficit:,.0f} 现金缺口；{_display_name(product, lang)} 可提供约 "
                          f"{tenure} 天短期营运资金，用于支付供应商与物流费用。")
            elif lang == "zh-TW":
                reason = (f"預計 {_gap_window_text(lang, gap_start, gap_end)} 出現 "
                          f"CNY {deficit:,.0f} 現金缺口；{_display_name(product, lang)} 可提供約 "
                          f"{tenure} 天短期營運資金，用於支付供應商與物流費用。")
            else:
                reason = (f"A CNY {deficit:,.0f} cash gap is projected for "
                          f"{_gap_window_text(lang, gap_start, gap_end)}. "
                          f"{_display_name(product, lang)} can provide around {tenure} days of "
                          f"short-term working capital for supplier and logistics payments.")
            confidence = 0.82
        else:
            continue

        use_of_funds = _label({
            "zh-CN": "填补预测期现金流缺口",
            "zh-TW": "填補預測期現金流缺口",
            "en": "Bridge the forecast cash gap",
        }, lang)
        item = {
            "product_id": getattr(product, "id", None),
            "product_code": getattr(product, "product_code", None),
            "product_name": _display_name(product, lang),
            "product_name_cn": getattr(product, "product_name_cn", None),
            "product_name_tw": getattr(product, "product_name_tw", None),
            "product_category": getattr(product, "category", None),
            "category": getattr(product, "category", None),
            "transaction_stage": "CashFlow",
            "reason": reason,
            "estimated_amount": round(amount, 2),
            "estimated_currency": BASE_CURRENCY,
            "estimated_tenor_days": int(tenure),
            "use_of_funds": use_of_funds,
            "required_materials": getattr(product, "required_materials", []) or [],
            "knowledge_reference": (
                f"{getattr(product, 'product_code', '')}: "
                f"{(getattr(product, 'knowledge_base_entry', '') or '')[:160]}"
            ),
            "confidence": confidence,
        }
        (receivable if sim_type == "receivable" else loans).append(item)

    return (receivable[:2] + loans[: max(0, limit - min(2, len(receivable)))])[:limit]


def build_legacy_gap(forecast: Dict, lang: str = "zh-CN") -> Dict:
    """Funding-gap view derived from the same forecast used by the chart."""
    lang = _norm_lang(lang)
    k = forecast["kpis"]
    gaps = []
    if k.get("has_shortfall"):
        gaps.append({
            "gap_currency": BASE_CURRENCY,
            "gap_amount": k["shortfall_amount"],
            "gap_start_date": k.get("gap_start_date"),
            "gap_end_date": k.get("gap_end_date"),
            "gap_duration_days": k.get("gap_duration_days"),
            "running_balance": k.get("lowest_balance"),
        })
    start = k.get("gap_start_date") or ""
    end = k.get("gap_end_date") or ("期末" if lang != "en" else "the end of the horizon")
    if gaps:
        if lang == "zh-TW":
            cause = (f"供應商付款與物流費用集中在客戶回款之前，導致 {start} 至 {end} 出現短期現金缺口。")
        elif lang == "en":
            cause = (f"Supplier and logistics payments fall due before customer collections, "
                     f"creating a short-term cash gap from {start} to {end}.")
        else:
            cause = (f"供应商付款与物流费用集中在客户回款之前，导致 {start} 至 {end} 出现短期现金缺口。")
    else:
        cause = {"zh-CN": "未检测到未来现金余额为负的缺口。",
                 "zh-TW": "未檢測到未來現金餘額為負的缺口。",
                 "en": "No negative cash balance is projected."}[lang if lang in ("zh-CN", "zh-TW", "en") else "zh-CN"]
    return {
        "gaps": gaps,
        "primary_cause": cause,
        "opening_cash": k.get("opening_balance", {}),
        "min_liquidity_buffer": dict(MIN_LIQUIDITY_BUFFER),
    }
