"""Bet-tax adjustments per jurisdiction.

Applied to ROI readouts so users see what their P&L looks like AFTER
typical local taxation. Rates are rough (jurisdictions vary by bookmaker
licence); they round to the most common retail-consumer scenario.
"""

from __future__ import annotations


# (tax on winnings), (tax on stake), (label)
_TAX_TABLE: dict[str, tuple[float, float, str]] = {
    "none": (0.00, 0.00, "no tax"),
    "eu":   (0.00, 0.05, "EU — 5% stake tax (e.g. France, Germany)"),
    "vn":   (0.10, 0.00, "Vietnam — 10% winnings tax"),
    "en":   (0.00, 0.00, "UK — no point-of-consumption tax on punter"),
    "us":   (0.24, 0.00, "US — 24% withholding on winnings over threshold"),
}


def apply_tax(
    *, pnl: float, total_staked: float, jurisdiction: str = "none",
) -> float:
    """Return adjusted P&L after applying the jurisdiction's tax rule.

    Stake tax = (stake_tax_rate × total_staked), always deducted from P&L.
    Winnings tax = (wins_tax_rate × positive_gross_winnings), applied only
    when net P&L is positive — rough proxy since we don't have per-bet
    gross here.
    """
    wins_tax, stake_tax, _ = _TAX_TABLE.get(jurisdiction, _TAX_TABLE["none"])
    out = pnl - stake_tax * total_staked
    if out > 0:
        out = out * (1 - wins_tax)
    return out


def jurisdictions() -> list[dict]:
    return [
        {"key": k, "wins_tax": w, "stake_tax": s, "label": label}
        for k, (w, s, label) in _TAX_TABLE.items()
    ]
