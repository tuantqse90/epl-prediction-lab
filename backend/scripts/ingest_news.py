"""RSS football-news aggregator.

Pulls headlines from a handful of well-known public feeds, keyword-matches
each title against the teams we already track, and upserts. Stores title +
summary + URL only — no full-text scraping, no copyright surface.

Sources (all public RSS):
    BBC Sport football · Guardian football · ESPN soccer · Goal.com

Usage:
    python scripts/ingest_news.py
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings


@dataclass(frozen=True)
class Feed:
    source: str
    url: str
    # True = feed URL is football-gated upstream, so we trust all items
    # even if the item URL doesn't contain /football/ (e.g. Metro uses
    # /YYYY/MM/DD/slug paths; 90min uses /slug directly but the feed
    # itself is football-only).
    trusted_football: bool = False


FEEDS: list[Feed] = [
    Feed("bbc",          "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    Feed("guardian",     "https://www.theguardian.com/football/rss"),
    # Sky Sports catch-all (some non-football; path filter strips those).
    Feed("sky",          "https://www.skysports.com/rss/12040"),
    Feed("independent",  "https://www.independent.co.uk/sport/football/rss"),
    Feed("mirror",       "https://www.mirror.co.uk/sport/football/rss.xml"),
    Feed("dailymail",    "https://www.dailymail.co.uk/sport/football/index.rss"),
    Feed("thesun",       "https://www.thesun.co.uk/sport/football/feed/",
         trusted_football=True),
    # Non-/football/ article URLs — feed itself is football-gated.
    Feed("metro",        "https://metro.co.uk/sport/football/feed/",
         trusted_football=True),
    Feed("90min",        "https://www.90min.com/posts.rss",
         trusted_football=True),
    Feed("football-italia", "https://www.football-italia.net/rss.xml",
         trusted_football=True),
    Feed("cbssports",    "https://www.cbssports.com/rss/headlines/soccer/",
         trusted_football=True),
    # Notes: ESPN /rss/soccer/news returns a bot-challenge (202 + empty
    # body) in datacenter IPs as of 2026-04. Telegraph returns 403 for
    # any non-interactive UA. Both dropped rather than fight it.
]

_STRIP_TAGS = re.compile(r"<[^>]+>")

# Sky's `rss/12040` turned out to be general Sky Sports (tennis, boxing, golf)
# rather than football-only, and other feeds occasionally leak non-football
# items too. Gate on the URL path since every publisher uses /football/ or
# /soccer/ for football stories — far cleaner than keyword-guessing titles.
_FOOTBALL_PATH_RE = re.compile(r"/(?:football|soccer)(?:/|$)", re.IGNORECASE)


def _is_football_url(url: str) -> bool:
    return bool(_FOOTBALL_PATH_RE.search(url))


def _fetch(url: str) -> str | None:
    # Telegraph (and similar) return 403 to non-browser user agents.
    req = urllib.request.Request(url, headers={
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        ),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[news] fetch failed {url}: {type(e).__name__}: {e}")
        return None


def _parse_pubdate(s: str | None) -> datetime:
    if not s:
        return datetime.now(tz=timezone.utc)
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(tz=timezone.utc)


def _parse_rss(xml_text: str) -> list[dict]:
    """Extract {title, url, summary, published_at} tuples from an RSS 2.0 feed."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    items = []
    # RSS 2.0: <rss><channel><item>... · Atom fallback: <feed><entry>...
    for item in root.iter():
        tag = item.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        title = None
        url = None
        summary = None
        published = None
        for child in item:
            ctag = child.tag.split("}")[-1]
            if ctag == "title" and child.text:
                title = child.text.strip()
            elif ctag == "link":
                # Atom: <link href="..."/> · RSS: <link>url</link>
                href = child.attrib.get("href")
                url = href or (child.text.strip() if child.text else None)
            elif ctag in ("description", "summary") and child.text:
                summary = _STRIP_TAGS.sub("", child.text).strip()[:600]
            elif ctag in ("pubDate", "published", "updated") and child.text:
                published = child.text.strip()
        if title and url:
            items.append({
                "title": title,
                "url": url,
                "summary": summary,
                "published_at": _parse_pubdate(published),
            })
    return items


def _detect_teams(title: str, summary: str | None, team_index: list[tuple[str, str, str]]) -> tuple[list[str], str | None]:
    """Return (team_slugs, first_league_code) matching the article text.

    team_index = [(name_lower, slug, league_code), ...]
    """
    hay = f"{title} {summary or ''}".lower()
    slugs: list[str] = []
    league: str | None = None
    for name, slug, lg in team_index:
        # Require word-boundary ish match to avoid "Ars" matching "Arsenal"-adjacent noise.
        # Simple containment works for fully qualified names (“Manchester United”).
        if name in hay:
            slugs.append(slug)
            if league is None:
                league = lg
    return list(dict.fromkeys(slugs)), league


async def run() -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        # Pull team index for keyword linking.
        async with pool.acquire() as conn:
            team_rows = await conn.fetch(
                """
                SELECT DISTINCT ON (t.slug)
                       t.slug, t.name,
                       m.league_code
                FROM teams t
                JOIN matches m ON (m.home_team_id = t.id OR m.away_team_id = t.id)
                WHERE m.season >= '2024-25'
                ORDER BY t.slug, m.kickoff_time DESC
                """
            )
        # Case-folded "Manchester United" → slug+league lookup. Also add each
        # team's short_name later if space is worth it (skip for now).
        team_index = [
            (r["name"].lower(), r["slug"], r["league_code"])
            for r in team_rows
        ]
        # Longer names first so "Manchester United" wins over "Manchester".
        team_index.sort(key=lambda t: -len(t[0]))

        total = 0
        inserted = 0
        for feed in FEEDS:
            body = _fetch(feed.url)
            if not body:
                continue
            items = _parse_rss(body)
            total += len(items)
            kept = (
                items if feed.trusted_football
                else [it for it in items if _is_football_url(it["url"])]
            )
            skipped = len(items) - len(kept)
            async with pool.acquire() as conn:
                for it in kept:
                    teams, league = _detect_teams(it["title"], it["summary"], team_index)
                    res = await conn.execute(
                        """
                        INSERT INTO news_items (
                            source, url, title, summary, published_at,
                            teams, league_code
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (url) DO NOTHING
                        """,
                        feed.source, it["url"], it["title"],
                        it["summary"], it["published_at"],
                        teams, league,
                    )
                    if res.endswith("1"):
                        inserted += 1
            print(f"[news] {feed.source}: {len(items)} items ({skipped} non-football skipped)")

        # Prune ancient stories — 30-day window keeps the side panel current.
        pruned = await pool.execute(
            "DELETE FROM news_items WHERE published_at < NOW() - INTERVAL '30 days'",
        )
        print(f"[news] total fetched={total} inserted={inserted} pruned={pruned}")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    argparse.ArgumentParser().parse_args()
    asyncio.run(run())


if __name__ == "__main__":
    main()
