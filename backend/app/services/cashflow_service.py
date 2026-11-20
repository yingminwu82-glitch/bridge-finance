"""
Multi-currency cash flow forecasting service.
Handles cash flow timeline, funding gap calculation, scenario simulation.
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

# Demo exchange rates (illustrative assumptions)
EXCHANGE_RATES = {
    "USD_CNY": 7.2,
    "USD_HKD": 7.8,
    "CNY_HKD": 1.08,
    "EUR_USD": 1.08,
    "EUR_CNY": 7.78,
    "EUR_HKD": 8.42,
}

# Minimum liquidity buffer (illustrative)
MIN_LIQUIDITY_BUFFER = {
    "CNY": 1000000,
    "USD": 100000,
    "HKD": 500000,
}


def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """Convert amount from one currency to another using demo exchange rates."""
    if from_currency == to_currency:
        return amount

    rate_key = f"{from_currency}_{to_currency}"
    if rate_key in EXCHANGE_RATES:
        return amount * EXCHANGE_RATES[rate_key]

    # Try reverse
    reverse_key = f"{to_currency}_{from_currency}"
    if reverse_key in EXCHANGE_RATES:
        return amount / EXCHANGE_RATES[reverse_key]

    # Via USD
    if from_currency != "USD" and to_currency != "USD":
        usd_amount = convert_currency(amount, from_currency, "USD")
        return convert_currency(usd_amount, "USD", to_currency)

    logger.warning(f"No exchange rate for {from_currency} to {to_currency}")
    return amount


def build_cashflow_timeline(cashflow_items: List[Dict]) -> List[Dict]:
    """Build a chronological cash flow timeline."""
    timeline = []
    for item in cashflow_items:
        flow_date = item.get("flow_date")
        if isinstance(flow_date, str):
            flow_date = date.fromisoformat(flow_date)
        timeline.append({
            "date": flow_date.isoformat() if flow_date else None,
            "type": item.get("flow_type"),
            "description": item.get("description"),
            "currency": item.get("currency"),
            "amount": item.get("amount"),
        })

    timeline.sort(key=lambda x: x["date"] or "9999-12-31")
    return timeline


def calculate_future_cash_position(cashflow_items: List[Dict],
                                    opening_cash: Dict[str, float] = None,
                                    target_date: date = None) -> Dict:
    """
    Calculate future cash position by currency.
    Future Cash Position = Opening Cash + Expected Inflows - Expected Outflows
    """
    if opening_cash is None:
        opening_cash = {"CNY": 4000000}

    positions = defaultdict(float)
    for curr, amount in opening_cash.items():
        positions[curr] += amount

    for item in cashflow_items:
        curr = item.get("currency", "USD")
        amount = item.get("amount", 0)
        if item.get("flow_type") == "inflow":
            positions[curr] += amount
        else:
            positions[curr] += amount  # amount is already negative for outflows

    return {
        "opening_cash": dict(opening_cash),
        "positions": dict(positions),
        "target_date": target_date.isoformat() if target_date else None,
    }


def calculate_funding_gap(cashflow_items: List[Dict],
                           opening_cash: Dict[str, float] = None) -> Dict:
    """
    Calculate funding gap for each currency.
    If Future Cash Position < Minimum Liquidity Buffer, there is a Potential Funding Gap.
    """
    if opening_cash is None:
        opening_cash = {"CNY": 4000000}

    # Build running balance by currency and date
    def _sort_key(x):
        fd = x.get("flow_date")
        if fd is None:
            return date.max
        if isinstance(fd, str):
            try:
                return date.fromisoformat(fd)
            except:
                return date.max
        return fd
    items_by_date = sorted(cashflow_items, key=_sort_key)

    gaps = {}
    running_balance = dict(opening_cash)

    for item in items_by_date:
        curr = item.get("currency", "USD")
        amount = item.get("amount", 0)

        if curr not in running_balance:
            running_balance[curr] = 0

        running_balance[curr] += amount

        # Check against minimum buffer
        buffer = MIN_LIQUIDITY_BUFFER.get(curr, 0)
        if running_balance[curr] < buffer:
            gap_amount = buffer - running_balance[curr]
            if curr not in gaps or gap_amount > gaps[curr]["gap_amount"]:
                gaps[curr] = {
                    "gap_currency": curr,
                    "gap_amount": round(gap_amount, 2),
                    "gap_start_date": item.get("flow_date"),
                    "running_balance": round(running_balance[curr], 2),
                }

    # Calculate gap duration
    for curr, gap in gaps.items():
        # Find when balance recovers
        gap_start = gap["gap_start_date"]
        if isinstance(gap_start, str):
            gap_start = date.fromisoformat(gap_start)

        # Find recovery date
        temp_balance = dict(opening_cash)
        for item in items_by_date:
            c = item.get("currency", "USD")
            if c != curr:
                continue
            fd = item.get("flow_date")
            if isinstance(fd, str):
                fd = date.fromisoformat(fd)
            if fd and fd > gap_start:
                temp_balance[curr] = temp_balance.get(curr, 0) + item.get("amount", 0)
                if temp_balance[curr] >= MIN_LIQUIDITY_BUFFER.get(curr, 0):
                    gap["gap_end_date"] = fd.isoformat()
                    gap["gap_duration_days"] = (fd - gap_start).days
                    break

        if "gap_duration_days" not in gap:
            gap["gap_end_date"] = None
            gap["gap_duration_days"] = 90  # Default assumption

    # Determine primary cause
    primary_cause = "No funding gap detected."
    if gaps:
        first_gap = list(gaps.values())[0]
        gap_curr = first_gap["gap_currency"]
        primary_cause = (
            f"Timing mismatch: {gap_curr} supplier payment precedes customer collection. "
            f"This creates a temporary liquidity gap that may require short-term financing."
        )

    return {
        "gaps": list(gaps.values()) if gaps else [],
        "primary_cause": primary_cause,
        "opening_cash": dict(opening_cash),
        "min_liquidity_buffer": dict(MIN_LIQUIDITY_BUFFER),
    }


def simulate_scenario(baseline_cashflows: List[Dict],
                      scenario_name: str,
                      parameters: Dict) -> Dict:
    """
    Simulate a scenario by modifying baseline cash flows.
    Parameters: delay_days, fx_change_pct, supplier_early_days
    """
    modified_cashflows = []

    delay_days = parameters.get("delay_days", 0)
    fx_change_pct = parameters.get("fx_change_pct", 0)
    supplier_early_days = parameters.get("supplier_early_days", 0)

    for item in baseline_cashflows:
        modified = dict(item)
        flow_date = item.get("flow_date")
        if isinstance(flow_date, str):
            flow_date = date.fromisoformat(flow_date)

        if flow_date:
            if item.get("flow_type") == "inflow" and delay_days > 0:
                # Delay customer collection
                modified["flow_date"] = (flow_date + timedelta(days=delay_days)).isoformat()
            elif item.get("flow_type") == "outflow" and supplier_early_days > 0:
                # Advance supplier payment
                modified["flow_date"] = (flow_date - timedelta(days=supplier_early_days)).isoformat()

        # Apply FX change to CNY outflows
        if fx_change_pct != 0 and item.get("currency") == "CNY" and item.get("flow_type") == "outflow":
            modified["amount"] = item["amount"] * (1 + fx_change_pct / 100)

        modified_cashflows.append(modified)

    # Calculate funding gap for modified scenario
    gap_result = calculate_funding_gap(modified_cashflows)

    # Determine main risk for scenario
    main_risks = {
        "Base Case": "Timing Mismatch",
        "Customer Delay +15 days": "Receivables Risk",
        "CNY Appreciation +3%": "FX Risk",
        "Supplier Early Payment": "Liquidity Risk",
        "Combined Stress Case": "Multiple Risks",
    }
    main_risk = main_risks.get(scenario_name, "Scenario Risk")

    # Calculate max funding gap
    max_gap = 0
    gap_currency = "CNY"
    if gap_result["gaps"]:
        for g in gap_result["gaps"]:
            if abs(g["gap_amount"]) > abs(max_gap):
                max_gap = g["gap_amount"]
                gap_currency = g["gap_currency"]

    return {
        "scenario_name": scenario_name,
        "parameters": parameters,
        "modified_cashflows": modified_cashflows,
        "max_funding_gap": max_gap,
        "gap_currency": gap_currency,
        "main_risk": main_risk,
        "gap_details": gap_result,
    }


def get_default_scenarios() -> List[Dict]:
    """Return the default scenario definitions."""
    return [
        {"name": "Base Case", "description": "Payment as planned, no FX change",
         "parameters": {"delay_days": 0, "fx_change_pct": 0, "supplier_early_days": 0}},
        {"name": "Customer Delay +15 days", "description": "Customer payment delayed by 15 days",
         "parameters": {"delay_days": 15, "fx_change_pct": 0, "supplier_early_days": 0}},
        {"name": "CNY Appreciation +3%", "description": "CNY appreciates by 3%",
         "parameters": {"delay_days": 0, "fx_change_pct": 3, "supplier_early_days": 0}},
        {"name": "Supplier Early Payment", "description": "Supplier requires payment 15 days earlier",
         "parameters": {"delay_days": 0, "fx_change_pct": 0, "supplier_early_days": 15}},
        {"name": "Combined Stress Case", "description": "Customer delay + CNY appreciation + supplier early",
         "parameters": {"delay_days": 15, "fx_change_pct": 3, "supplier_early_days": 15}},
    ]


def generate_cashflow_summary(cashflow_items: List[Dict], funding_gap: Dict) -> str:
    """Generate a text summary of the cash flow analysis."""
    inflows = defaultdict(float)
    outflows = defaultdict(float)

    for item in cashflow_items:
        curr = item.get("currency", "USD")
        amount = abs(item.get("amount", 0))
        if item.get("flow_type") == "inflow":
            inflows[curr] += amount
        else:
            outflows[curr] += amount

    parts = []
    for curr in set(list(inflows.keys()) + list(outflows.keys())):
        parts.append(f"{curr}: Inflow {inflows[curr]:,.0f} / Outflow {outflows[curr]:,.0f}")

    if funding_gap.get("gaps"):
        for g in funding_gap["gaps"]:
            parts.append(f"Funding Gap: {g['gap_currency']} {g['gap_amount']:,.0f} for {g.get('gap_duration_days', 0)} days")
    else:
        parts.append("No funding gap detected.")

    return " | ".join(parts)
