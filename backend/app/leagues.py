"""Static multi-league registry.

All league-scoped scripts and APIs accept a `league_code` matching one of the
keys here. Adding a new league = one entry + checking the team metadata
coverage in `frontend/lib/team-{logos,colors}.ts`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class League:
    code: str               # soccerdata key (e.g. "ENG-Premier League")
    slug: str               # URL-friendly id (e.g. "epl")
    short: str              # display abbreviation (e.g. "EPL")
    name_en: str
    name_vi: str
    emoji: str              # flag / identifier for UI + Telegram
    # source ids per external provider:
    football_data_code: str        # football-data.co.uk: E0 / SP1 / I1 / D1 / F1
    api_football_id: int           # v3.football.api-sports.io
    the_odds_api_key: str          # the-odds-api.com sport key


LEAGUES: list[League] = [
    League(
        code="ENG-Premier League", slug="epl", short="EPL",
        name_en="Premier League", name_vi="Ngoại hạng Anh",
        emoji="🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        football_data_code="E0", api_football_id=39,
        the_odds_api_key="soccer_epl",
    ),
    League(
        code="ESP-La Liga", slug="laliga", short="LaLiga",
        name_en="La Liga", name_vi="La Liga",
        emoji="🇪🇸",
        football_data_code="SP1", api_football_id=140,
        the_odds_api_key="soccer_spain_la_liga",
    ),
    League(
        code="ITA-Serie A", slug="seriea", short="Serie A",
        name_en="Serie A", name_vi="Serie A",
        emoji="🇮🇹",
        football_data_code="I1", api_football_id=135,
        the_odds_api_key="soccer_italy_serie_a",
    ),
    League(
        code="GER-Bundesliga", slug="bundesliga", short="Bundesliga",
        name_en="Bundesliga", name_vi="Bundesliga",
        emoji="🇩🇪",
        football_data_code="D1", api_football_id=78,
        the_odds_api_key="soccer_germany_bundesliga",
    ),
    League(
        code="FRA-Ligue 1", slug="ligue1", short="Ligue 1",
        name_en="Ligue 1", name_vi="Ligue 1",
        emoji="🇫🇷",
        football_data_code="F1", api_football_id=61,
        the_odds_api_key="soccer_france_ligue_one",
    ),
]

BY_CODE: dict[str, League] = {lg.code: lg for lg in LEAGUES}
BY_SLUG: dict[str, League] = {lg.slug: lg for lg in LEAGUES}

DEFAULT_LEAGUE = "ENG-Premier League"


def get_league(code_or_slug: str) -> League:
    if code_or_slug in BY_CODE:
        return BY_CODE[code_or_slug]
    if code_or_slug in BY_SLUG:
        return BY_SLUG[code_or_slug]
    raise KeyError(f"unknown league: {code_or_slug!r}")
