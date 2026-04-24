"""Derby / rivalry tagging.

Static pair list per league. When the model predicts a derby fixture,
we surface the tag on the match page and (later) inflate the scoreline
variance to reflect the well-documented "anything happens" effect in
heated rivalries.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DerbyTag:
    name: str
    description: str
    variance_multiplier: float   # 1.0 = neutral, >1 = more spread out scorelines


_DERBIES: dict[frozenset[str], DerbyTag] = {
    # EPL
    frozenset({"arsenal", "tottenham"}): DerbyTag(
        "North London Derby",
        "Arsenal vs Tottenham — heated London rivalry, historically low draw share.",
        1.15,
    ),
    frozenset({"liverpool", "everton"}): DerbyTag(
        "Merseyside Derby",
        "Liverpool vs Everton — the only Merseyside derby. High yellow-card rate.",
        1.15,
    ),
    frozenset({"manchester-united", "manchester-city"}): DerbyTag(
        "Manchester Derby",
        "United vs City — biggest derby in England by global viewership.",
        1.15,
    ),
    frozenset({"arsenal", "chelsea"}): DerbyTag(
        "London Derby",
        "Arsenal vs Chelsea — top-4 rivalry across the Thames.",
        1.10,
    ),
    frozenset({"tottenham", "chelsea"}): DerbyTag(
        "London Derby",
        "Tottenham vs Chelsea — physical, high-pressing matchup.",
        1.10,
    ),
    frozenset({"liverpool", "manchester-united"}): DerbyTag(
        "North-West Derby",
        "Liverpool vs Manchester United — England's most decorated clubs.",
        1.15,
    ),

    # La Liga
    frozenset({"real-madrid", "barcelona"}): DerbyTag(
        "El Clásico",
        "Real Madrid vs Barcelona — the biggest club match in world football.",
        1.25,
    ),
    frozenset({"real-madrid", "atletico-madrid"}): DerbyTag(
        "Madrid Derby",
        "Real vs Atlético — the city is split two ways.",
        1.15,
    ),
    frozenset({"barcelona", "espanyol"}): DerbyTag(
        "Barcelona Derby",
        "Barça vs Espanyol — Catalonia's city rivals.",
        1.10,
    ),
    frozenset({"sevilla", "real-betis"}): DerbyTag(
        "Seville Derby",
        "Sevilla vs Real Betis — Andalusia's fiercest matchup.",
        1.15,
    ),

    # Serie A
    frozenset({"juventus", "inter"}): DerbyTag(
        "Derby d'Italia",
        "Juventus vs Inter — Italy's biggest rivalry.",
        1.15,
    ),
    frozenset({"inter", "ac-milan"}): DerbyTag(
        "Derby della Madonnina",
        "Inter vs Milan — one stadium, two clubs.",
        1.20,
    ),
    frozenset({"ac-milan", "juventus"}): DerbyTag(
        "Classic Italian",
        "Milan vs Juventus — vintage scudetto battle.",
        1.10,
    ),
    frozenset({"roma", "lazio"}): DerbyTag(
        "Derby della Capitale",
        "Roma vs Lazio — the Rome derby, notoriously low-scoring.",
        1.20,
    ),

    # Bundesliga
    frozenset({"bayern-munich", "borussia-dortmund"}): DerbyTag(
        "Der Klassiker",
        "Bayern vs Dortmund — Germany's premier modern rivalry.",
        1.15,
    ),
    frozenset({"borussia-dortmund", "schalke-04"}): DerbyTag(
        "Revierderby",
        "Dortmund vs Schalke — Ruhr Valley's oldest rivalry.",
        1.20,
    ),
    frozenset({"hamburger-sv", "werder-bremen"}): DerbyTag(
        "Nordderby",
        "Hamburg vs Bremen — North German classic.",
        1.10,
    ),

    # Ligue 1
    frozenset({"paris-saint-germain", "marseille"}): DerbyTag(
        "Le Classique",
        "PSG vs Marseille — France's biggest club rivalry.",
        1.20,
    ),
    frozenset({"lyon", "saint-etienne"}): DerbyTag(
        "Rhône-Alpes Derby",
        "Lyon vs Saint-Étienne — historic neighbours.",
        1.15,
    ),
    frozenset({"lyon", "marseille"}): DerbyTag(
        "OL vs OM",
        "Lyon vs Marseille — contested top-3 spots.",
        1.10,
    ),
}


def derby_tag(home_slug: str, away_slug: str) -> DerbyTag | None:
    return _DERBIES.get(frozenset({home_slug, away_slug}))
