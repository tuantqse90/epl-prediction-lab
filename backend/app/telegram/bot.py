"""Telegram bot — interactive command handler.

Webhook flow:
    POST /api/telegram/webhook → parse_update → dispatch → format + sendMessage

All pure functions live here. DB access goes through fetchers in the
router. Splitting like this keeps the core testable without a pool.
"""

from __future__ import annotations

import os
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class ParsedCommand:
    chat_id: int
    command: str
    args: list[str] = field(default_factory=list)
    user_id: int | None = None
    username: str | None = None


def parse_update(update: dict) -> ParsedCommand | None:
    """Extract command + args from a Telegram Update JSON.

    Supports:
      - direct /command [args] from message.text
      - /command@botname [args] from group chats (strip the @suffix)
      - callback_query.data that starts with / (inline buttons)
    """
    # Inline button callback — carries .data which we treat like text.
    cb = update.get("callback_query")
    if cb:
        text = (cb.get("data") or "").strip()
        chat = ((cb.get("message") or {}).get("chat") or {})
        user = cb.get("from") or {}
    else:
        msg = update.get("message") or update.get("edited_message") or {}
        text = (msg.get("text") or "").strip()
        chat = msg.get("chat") or {}
        user = msg.get("from") or {}
    if not text.startswith("/"):
        return None
    chat_id = chat.get("id")
    if not isinstance(chat_id, int):
        return None
    parts = text.split()
    head = parts[0]
    # /pick@worldcup_predictor_bot → /pick
    if "@" in head:
        head = head.split("@", 1)[0]
    command = head.lstrip("/").lower()
    if not command:
        return None
    args = parts[1:]
    return ParsedCommand(
        chat_id=chat_id,
        command=command,
        args=args,
        user_id=user.get("id") if isinstance(user.get("id"), int) else None,
        username=user.get("username"),
    )


# ---------------------------------------------------------------------------
# Pure formatters — take already-fetched rows, produce Telegram Markdown
# ---------------------------------------------------------------------------


def format_help() -> str:
    return (
        "*Prediction Lab bot*\n"
        "\n"
        "• `/pick today` — model's top picks for today\n"
        "• `/pick PSG` — pick for a specific team's next match\n"
        "• `/edge` — fixtures with edge ≥ 5% right now\n"
        "• `/clv` — closing-line value (model vs closing market)\n"
        "• `/roi [7d|30d|90d]` — historical ROI window\n"
        "• `/subscribe TEAM` — goal + FT pings for that team\n"
        "• `/unsubscribe TEAM` · `/subs` — list yours\n"
        "• `/help` — this message"
    )


def _league_emoji(league_code: str | None) -> str:
    return {
        "ENG-Premier League": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "ESP-La Liga": "🇪🇸",
        "ITA-Serie A": "🇮🇹",
        "GER-Bundesliga": "🇩🇪",
        "FRA-Ligue 1": "🇫🇷",
    }.get(league_code or "", "⚽")


SITE = "https://predictor.nullshift.sh"


def format_pick(rows: Iterable, *, window_label: str = "today") -> str:
    """Render the model's top picks for a window. Each row needs:
        home_short, away_short, league_code, kickoff_time,
        pick_side (H|D|A), pick_conf, best_odds, edge_pp,
        match_id (optional — renders a deep-link when present)
    """
    rows = list(rows)
    if not rows:
        return f"*No matches in {window_label}* — check back when the fixture list fills in."
    lines = [f"*Top picks · {window_label}*"]
    for r in rows[:8]:
        side_label = (
            r.home_short if r.pick_side == "H"
            else r.away_short if r.pick_side == "A"
            else "Draw"
        )
        ko = str(r.kickoff_time)[11:16] if r.kickoff_time else ""
        edge_str = (
            f"· {r.edge_pp:+.1f}% edge" if r.edge_pp is not None else ""
        )
        odds_str = f"@ {r.best_odds:.2f}" if r.best_odds else ""
        conf = int(round(r.pick_conf * 100))
        mid = getattr(r, "match_id", None)
        # Markdown link wraps the fixture name — Telegram renders it as a
        # tappable deep-link straight to /match/:id (43.4).
        fixture = (
            f"[*{r.home_short}* vs *{r.away_short}*]({SITE}/match/{int(mid)})"
            if mid is not None
            else f"*{r.home_short}* vs *{r.away_short}*"
        )
        lines.append(
            f"{_league_emoji(r.league_code)} {ko}  {fixture}\n"
            f"   → {side_label} · {conf}% {odds_str} {edge_str}"
        )
    return "\n\n".join(lines)


def format_roi(*, total_bets: int, roi_pct: float, pnl: float, window: str) -> str:
    if total_bets == 0:
        return (
            f"*ROI · {window}*\n"
            f"No graded bets in this window."
        )
    arrow = "📈" if roi_pct > 0 else "📉" if roi_pct < 0 else "➖"
    sign = "+" if roi_pct >= 0 else ""
    return (
        f"*ROI · {window}* {arrow}\n"
        f"Bets: {total_bets}\n"
        f"P&L: {sign}{pnl:.2f}u\n"
        f"ROI: {sign}{roi_pct:.1f}%"
    )


def format_edge(rows: Iterable, *, threshold_pp: float = 5.0) -> str:
    rows = list(rows)
    if not rows:
        return f"*No current edges* ≥ {threshold_pp:.1f}%."
    lines = [f"*Edges ≥ {threshold_pp:.1f}%*"]
    for r in rows[:10]:
        side_label = (
            r.home_short if r.pick_side == "H"
            else r.away_short if r.pick_side == "A"
            else "Draw"
        )
        ko = str(r.kickoff_time)[5:16] if r.kickoff_time else ""
        lines.append(
            f"{_league_emoji(r.league_code)} {ko} "
            f"*{r.home_short}*-*{r.away_short}* → {side_label} "
            f"@ {r.best_odds:.2f} (+{r.edge_pp:.1f}%)"
        )
    return "\n".join(lines)


def format_clv(*, total: int, mean_clv: float, window: str = "season") -> str:
    if total == 0:
        return f"*CLV · {window}*\nNo closing odds snapshots yet."
    arrow = "📈" if mean_clv > 0 else "📉"
    return (
        f"*Closing-line value · {window}* {arrow}\n"
        f"Sample: {total} bets\n"
        f"Mean CLV: {mean_clv:+.2f}%"
    )


def format_subscribe_ok(team_name: str) -> str:
    return f"🔔 Subscribed to *{team_name}* — I'll ping you on goals + HT/FT."


def format_unsubscribe_ok(team_name: str) -> str:
    return f"🔕 Unsubscribed from *{team_name}*."


def format_unknown_team(query: str) -> str:
    return (
        f"Couldn't find a team matching *{query}*. "
        f"Try the full short name (e.g., `ARS`, `PSG`, `Bayern`)."
    )


def format_error(msg: str = "Something went wrong.") -> str:
    return f"⚠️ {msg}"


# ---------------------------------------------------------------------------
# Telegram API — side-effectful, guarded against missing creds
# ---------------------------------------------------------------------------


def send_message(chat_id: int, text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print(f"[telegram-bot] no TELEGRAM_BOT_TOKEN; would send to {chat_id}: {text[:60]}")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[telegram-bot] send_message failed: {type(e).__name__}: {e}")
        return False
