"""DeepL Free batch translator for the Next i18n labels.

Scans every `tLang(lang, { en, vi, th, zh, ko })` block in
frontend/app/**.tsx + frontend/components/**.tsx, finds entries where
th/zh/ko are missing or trivially copied from en, calls DeepL's free
API, and rewrites the file in place with the translated value.

Why DeepL Free for this (not Qwen): batch one-time UI strings benefit
from DeepL's deterministic output + 500k free chars/month. Source of
truth stays the en string in the same tLang block.

Setup:
  1. Sign up free.deepl.com → get DEEPL_API_KEY
  2. export DEEPL_API_KEY=...
  3. Dry run:  python scripts/deepl_translate_ui.py --dry
  4. Apply:    python scripts/deepl_translate_ui.py --apply

Notes:
  • Endpoint: https://api-free.deepl.com (free tier).
  • Source language: 'en' (we translate from English, not Vietnamese,
    because DeepL English coverage is highest).
  • Skip entries where th/zh/ko are already non-empty AND non-English
    (assume they were authored).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "frontend"

# DeepL language codes per their API.
DEEPL_LANG = {
    "th": "TH",
    "zh": "ZH",
    "ko": "KO",
}

# Match a `tLang(lang, { en: "...", vi: "...", th: "...", zh: "...", ko: "..." })`
# block. Tolerates trailing commas + multi-line. Uses non-greedy + a stop
# at `})`. Inner content captured into group 1.
TLANG_RE = re.compile(
    r"tLang\s*\(\s*[A-Za-z_][A-Za-z0-9_]*\s*,\s*\{(.*?)\}\s*\)",
    re.DOTALL,
)

# Per-key matchers — the keys are identifier-style.
KEY_RE = {
    "en": re.compile(r"en\s*:\s*(\"[^\"]*\"|`[^`]*`)", re.DOTALL),
    "vi": re.compile(r"vi\s*:\s*(\"[^\"]*\"|`[^`]*`)", re.DOTALL),
    "th": re.compile(r"th\s*:\s*(\"[^\"]*\"|`[^`]*`)", re.DOTALL),
    "zh": re.compile(r"zh\s*:\s*(\"[^\"]*\"|`[^`]*`)", re.DOTALL),
    "ko": re.compile(r"ko\s*:\s*(\"[^\"]*\"|`[^`]*`)", re.DOTALL),
}


def _strip_quotes(s: str) -> tuple[str, str]:
    """Returns (inner_text, quote_char). Quote char is '"' or '`'."""
    if not s:
        return "", '"'
    q = s[0]
    return s[1:-1], q


def _deepl_translate(text: str, target: str) -> str | None:
    """Single DeepL Free API call. Returns translated string or None
    if the API fails (network / quota / auth)."""
    key = os.environ.get("DEEPL_API_KEY")
    if not key:
        return None
    body = urllib.parse.urlencode({
        "auth_key": key,
        "text": text,
        "source_lang": "EN",
        "target_lang": DEEPL_LANG[target],
        "preserve_formatting": "1",
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api-free.deepl.com/v2/translate",
        data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"[deepl] {target}: {type(e).__name__}: {e}")
        return None
    try:
        return data["translations"][0]["text"]
    except (KeyError, IndexError):
        return None


def _looks_english(text: str, en_text: str) -> bool:
    """A th/zh/ko slot 'looks English' if it's empty, identical to the
    en value, or contains > 50% ASCII letters (rough heuristic for
    'translation never written, copied from en')."""
    if not text:
        return True
    if text == en_text:
        return True
    if text.startswith("← "):  # navigation arrows are language-neutral
        return False
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    ascii_ratio = sum(1 for c in letters if ord(c) < 128) / len(letters)
    return ascii_ratio > 0.5


def process_file(path: Path, langs: list[str], dry: bool) -> int:
    """Returns the number of replacements made. Mutates the file when
    dry=False."""
    text = path.read_text()
    original = text
    n_changes = 0

    # Walk every tLang(...) block.
    for m in list(TLANG_RE.finditer(text)):
        block = m.group(1)
        en_match = KEY_RE["en"].search(block)
        if not en_match:
            continue
        en_raw, en_q = _strip_quotes(en_match.group(1))
        if not en_raw or "\\n" in en_raw or len(en_raw) < 2:
            continue

        new_block = block
        block_changed = False
        for lang in langs:
            target_match = KEY_RE[lang].search(block)
            if not target_match:
                continue
            target_raw, target_q = _strip_quotes(target_match.group(1))
            if not _looks_english(target_raw, en_raw):
                continue  # Already translated, skip.
            if dry:
                print(f"  [dry] {path.name}: {lang}={target_raw!r} ← {en_raw!r}")
                n_changes += 1
                continue
            translated = _deepl_translate(en_raw, lang)
            if not translated:
                continue
            print(f"  {path.name}: {lang}={translated!r} ← {en_raw!r}")
            # Replace the value inside the original block. Quote with the
            # same style as before (likely "), escaping any internal " by
            # switching to backtick if " present.
            quote = '"' if '"' not in translated else "`"
            new_value = f"{lang}: {quote}{translated}{quote}"
            new_block = re.sub(
                rf'{lang}\s*:\s*({target_q}[^{target_q}]*{target_q})',
                new_value,
                new_block,
                count=1,
            )
            block_changed = True
            n_changes += 1

        if block_changed:
            text = text[:m.start(1)] + new_block + text[m.end(1):]

    if not dry and text != original:
        path.write_text(text)
    return n_changes


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry", action="store_true",
                   help="Only print what would change; do not call DeepL.")
    p.add_argument("--apply", action="store_true",
                   help="Mutate files (calls DeepL API).")
    p.add_argument("--langs", default="th,zh,ko",
                   help="Comma-separated target language codes.")
    args = p.parse_args()
    if not args.dry and not args.apply:
        print("Pass --dry to preview or --apply to mutate.")
        sys.exit(1)
    langs = [s.strip() for s in args.langs.split(",") if s.strip() in DEEPL_LANG]
    if not langs:
        print("No supported langs in --langs. Pick from th,zh,ko.")
        sys.exit(1)
    if args.apply and not os.environ.get("DEEPL_API_KEY"):
        print("DEEPL_API_KEY env var required for --apply.")
        sys.exit(1)

    files = list((ROOT / "app").rglob("*.tsx")) + list((ROOT / "components").rglob("*.tsx"))
    print(f"Scanning {len(files)} .tsx files for missing {langs} translations…\n")
    total = 0
    for path in files:
        n = process_file(path, langs, args.dry)
        total += n
    print(f"\n{total} translation slot{'s' if total != 1 else ''} {'would be' if args.dry else 'were'} updated.")


if __name__ == "__main__":
    main()
