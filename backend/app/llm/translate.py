"""Qwen-powered translation for match stories.

Source language is Vietnamese (the original generate_story output).
Targets: en, th, zh, ko. Translations cached in
`match_story_translations` so each story gets translated at most once
per target language.
"""

from __future__ import annotations

import asyncpg

from app.llm.reasoning import _call_qwen


SUPPORTED_LANGS = ("en", "th", "zh", "ko")

LANG_NAMES = {
    "en": "English",
    "th": "Thai (ภาษาไทย)",
    "zh": "Simplified Chinese (简体中文)",
    "ko": "Korean (한국어)",
}

TRANSLATE_SYSTEM = (
    "You are a professional sports translator. Preserve every fact, "
    "number, team name and player name exactly. Keep the tone "
    "(slightly informal but professional). Output ONLY the translation, "
    "no quotes, no preamble, no language tag. Keep paragraph breaks."
)


def _build_prompt(source_text: str, target_lang: str) -> str:
    return (
        f"Translate the following Vietnamese football match narrative into "
        f"{LANG_NAMES[target_lang]}. Keep team names + player names + "
        f"numbers exact (do not localize 'Real Madrid' to anything else). "
        f"Maintain the 3-paragraph structure if present.\n\n"
        f"--- SOURCE (Vietnamese) ---\n"
        f"{source_text}\n"
        f"--- END SOURCE ---\n"
    )


async def translate_story(
    pool: asyncpg.Pool,
    match_id: int,
    target_lang: str,
    *,
    model: str = "dashscope/qwen-plus-latest",
) -> str | None:
    """Translate a stored story to `target_lang` and persist to
    match_story_translations. Idempotent: returns cached translation
    if already present. Returns None on LLM failure.
    """
    if target_lang not in SUPPORTED_LANGS:
        return None

    async with pool.acquire() as conn:
        cached = await conn.fetchrow(
            "SELECT story FROM match_story_translations "
            "WHERE match_id = $1 AND lang = $2",
            match_id, target_lang,
        )
        if cached:
            return cached["story"]
        src = await conn.fetchval(
            "SELECT story FROM matches WHERE id = $1",
            match_id,
        )
    if not src:
        return None

    prompt = _build_prompt(src, target_lang)
    try:
        translated = _call_qwen(
            prompt, model, system=TRANSLATE_SYSTEM,
            max_tokens=1500, temperature=0.3,
        )
    except Exception as e:
        print(f"[translate] {match_id} {target_lang} failed: {type(e).__name__}: {e}")
        return None
    if not translated or len(translated) < 100:
        return None

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO match_story_translations
                (match_id, lang, story, model)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (match_id, lang) DO UPDATE
                SET story = EXCLUDED.story,
                    model = EXCLUDED.model,
                    translated_at = NOW()
            """,
            match_id, target_lang, translated, model,
        )
    return translated


async def get_localized_story(
    pool: asyncpg.Pool,
    match_id: int,
    lang: str,
) -> str | None:
    """Return the story in the requested language: original Vietnamese
    if lang == 'vi' or unsupported, else the cached translation.
    Returns None if neither exists. Read-only — translation generation
    happens via the daily cron, not on read."""
    if lang == "vi" or lang not in SUPPORTED_LANGS:
        async with pool.acquire() as conn:
            row = await conn.fetchval(
                "SELECT story FROM matches WHERE id = $1",
                match_id,
            )
        return row
    async with pool.acquire() as conn:
        row = await conn.fetchval(
            "SELECT story FROM match_story_translations "
            "WHERE match_id = $1 AND lang = $2",
            match_id, lang,
        )
    return row
