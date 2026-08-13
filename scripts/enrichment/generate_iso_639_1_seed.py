"""Generates dbt_project/seeds/iso_639_1.csv, the ISO 639-1 code -> English
name reference table dim_language.sql joins against for its display name.

Not part of the ingestion/cleaning/dbt pipeline -- run once, by hand,
whenever the seed needs regenerating (the ISO 639-1 standard essentially
never changes, so in practice this is a write-once script). The pipeline
itself never imports or calls this; `dbt seed` just reads the committed CSV.

Source is `pycountry` (bundles Debian's `iso-codes` project, itself sourced
from the Library of Congress/SIL ISO 639 maintenance registries) -- a
verifiable, non-live reference dataset, as opposed to hand-typing names from
memory or calling a live enrichment API (this dataset already draws from
TMDB elsewhere; the point of this seed is an independent authority).

Two codes have no `alpha_2` entry in pycountry and are filled in manually:
- `bh` (Bihari languages) -- a collective/group code, not an individual
  language, so it's absent from the alpha_2-keyed index.
- `mo` (Moldavian) -- deprecated from the ISO 639-1 registry in 2008
  (merged into `ro`), so current lookups don't carry it, but it's still a
  code TMDB's source data actually uses.

`cn` (Cantonese) and `xx` (TMDB's "no language" placeholder) are NOT ISO
639-1 codes at all -- they're TMDB-specific conventions -- so they're
deliberately excluded here and named explicitly in dim_language.sql instead.

Run: python -m scripts.enrichment.generate_iso_639_1_seed
"""

import csv
from pathlib import Path

import pycountry

SEED_PATH = (
    Path(__file__).resolve().parent.parent.parent / "dbt_project" / "seeds" / "iso_639_1.csv"
)

# Every ISO 639-1 alpha-2 code in current use across this project's data,
# plus `mo` -- the full standard is otherwise not needed here.
CODES = [
    "aa", "ab", "ae", "af", "ak", "am", "an", "ar", "as", "av", "ay", "az",
    "ba", "be", "bg", "bh", "bi", "bm", "bn", "bo", "br", "bs",
    "ca", "ce", "ch", "co", "cr", "cs", "cu", "cv", "cy",
    "da", "de", "dv", "dz",
    "ee", "el", "en", "eo", "es", "et", "eu",
    "fa", "ff", "fi", "fj", "fo", "fr", "fy",
    "ga", "gd", "gl", "gn", "gu", "gv",
    "ha", "he", "hi", "ho", "hr", "ht", "hu", "hy", "hz",
    "ia", "id", "ie", "ig", "ii", "ik", "io", "is", "it", "iu",
    "ja", "jv",
    "ka", "kg", "ki", "kj", "kk", "kl", "km", "kn", "ko", "kr", "ks", "ku", "kv", "kw", "ky",
    "la", "lb", "lg", "li", "ln", "lo", "lt", "lu", "lv",
    "mg", "mh", "mi", "mk", "ml", "mn", "mo", "mr", "ms", "mt", "my",
    "na", "nb", "nd", "ne", "ng", "nl", "nn", "no", "nr", "nv", "ny",
    "oc", "oj", "om", "or", "os",
    "pa", "pi", "pl", "ps", "pt",
    "qu",
    "rm", "rn", "ro", "ru", "rw",
    "sa", "sc", "sd", "se", "sg", "sh", "si", "sk", "sl", "sm", "sn", "so", "sq", "sr", "ss",
    "st", "su", "sv", "sw",
    "ta", "te", "tg", "th", "ti", "tk", "tl", "tn", "to", "tr", "ts", "tt", "tw", "ty",
    "ug", "uk", "ur", "uz",
    "ve", "vi", "vo",
    "wa", "wo",
    "xh",
    "yi", "yo",
    "za", "zh", "zu",
]

MANUAL_OVERRIDES = {
    "bh": "Bihari languages",
    "mo": "Moldavian",
}


def build_rows() -> dict[str, str]:
    rows = {}
    unresolved = []
    for code in CODES:
        if code in MANUAL_OVERRIDES:
            rows[code] = MANUAL_OVERRIDES[code]
            continue
        lang = pycountry.languages.get(alpha_2=code)
        if lang is None:
            unresolved.append(code)
            continue
        rows[code] = lang.name

    if unresolved:
        # Every code in CODES is expected to resolve via MANUAL_OVERRIDES
        # or pycountry -- an unresolved code here means CODES drifted from
        # what's actually in analytics.dim_language and needs updating.
        raise RuntimeError(f"no pycountry entry and no manual override for: {unresolved}")

    return rows


def main():
    rows = build_rows()
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SEED_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["code", "name"])
        for code in sorted(rows):
            writer.writerow([code, rows[code]])
    print(f"Wrote {len(rows)} rows to {SEED_PATH}")


if __name__ == "__main__":
    main()
