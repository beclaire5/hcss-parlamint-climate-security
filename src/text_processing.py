"""
text_processing.py
==================
Functions for filtering and processing text content of parliamentary speeches.

Main functions:
    clean_tokenized_text(text)    -> str    # fix punctuation spacing
    contains_keywords(text, kws)  -> bool   # case-insensitive keyword check
    matched_keywords(text, kws)   -> list   # which keywords matched
    filter_by_keywords(df, kws)   -> df     # filter dataframe to matching speeches
    add_keyword_flags(df, themes) -> df     # add boolean columns per theme
"""

from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


# ----------------------------------------------------------------------------
# Keyword themes
# ----------------------------------------------------------------------------
# We organize keywords by theme so we can analyze sub-topics separately and
# also see how speakers/parties frame climate (purely environmental vs security).

CLIMATE_KEYWORDS = {
    "core": [
        "climate change", "climate", "global warming",
        "greenhouse gas", "greenhouse",
        "co2", "carbon dioxide", "carbon emission", "carbon",
        "emission", "emissions",
    ],
    "energy_transition": [
        "energy transition", "renewable energy", "renewable", "renewables",
        "fossil fuel", "fossil fuels", "fossil",
        "wind energy", "solar energy", "solar power", "wind power",
        "hydrogen",
        "sustainability", "sustainable",
    ],
    "policy": [
        "paris agreement", "paris accord", "paris climate",
        "climate law", "climate act", "climate agreement",
        "klimaatwet", "klimaatakkoord",  # Dutch terms surviving translation
        "ipcc", "cop21", "cop26", "cop27",
        "european green deal", "green deal",
    ],
    "security_nexus": [
        # The HCSS angle: where climate meets security
        "climate security", "climate risk", "climate threat",
        "energy security", "food security", "water security",
        "climate migration", "climate refugee", "climate refugees",
        "resource scarcity", "resource conflict",
        "drought", "flooding", "sea level",
    ],
    "arctic": [
        # Arctic-specific dimension
        "arctic", "polar", "antarctic",
        "ice cap", "ice sheet", "melting ice", "sea ice",
        "northern sea route", "arctic council",
        "greenland", "spitsbergen", "svalbard",
        "permafrost",
    ],
}

# Flat list of all climate-related keywords across themes
ALL_CLIMATE_KEYWORDS = sorted({kw for kws in CLIMATE_KEYWORDS.values() for kw in kws})


# ----------------------------------------------------------------------------
# Text cleaning
# ----------------------------------------------------------------------------

def clean_tokenized_text(text: str) -> str:
    """ParlaMint .ana files have one token per line, which after concatenation
    leaves spaces before punctuation (e.g. 'Mr. Chairman . I 'll file').
    This function reattaches punctuation to the previous word for readability.
    """
    if not isinstance(text, str):
        return ""
    # Remove space before punctuation
    text = re.sub(r"\s+([.,;:!?\)\]])", r"\1", text)
    # Remove space after opening brackets
    text = re.sub(r"([\(\[])\s+", r"\1", text)
    # Reattach contractions: "I 'll" -> "I'll", "do n't" -> "don't"
    text = re.sub(r"\s+'(s|re|ve|ll|d|m|t)\b", r"'\1", text)
    text = re.sub(r"\bn 't\b", "n't", text)
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ----------------------------------------------------------------------------
# Keyword matching
# ----------------------------------------------------------------------------

def _build_keyword_pattern(keywords: Iterable[str]) -> re.Pattern:
    """Build a single compiled regex matching any of the keywords as whole words,
    case-insensitive. Multi-word keywords are matched as exact phrases."""
    # Sort by length DESC so longer phrases match first ("climate change" > "climate")
    sorted_kws = sorted(set(keywords), key=len, reverse=True)
    escaped = [re.escape(kw) for kw in sorted_kws]
    pattern = r"\b(" + "|".join(escaped) + r")\b"
    return re.compile(pattern, flags=re.IGNORECASE)


def contains_keywords(text: str, keywords: Iterable[str]) -> bool:
    """True if at least one keyword is found in the text (case-insensitive)."""
    if not isinstance(text, str) or not text:
        return False
    pattern = _build_keyword_pattern(keywords)
    return bool(pattern.search(text))


def matched_keywords(text: str, keywords: Iterable[str]) -> list[str]:
    """Return the list of distinct keywords found in the text (lowercase)."""
    if not isinstance(text, str) or not text:
        return []
    pattern = _build_keyword_pattern(keywords)
    return sorted({m.group(0).lower() for m in pattern.finditer(text)})


# ----------------------------------------------------------------------------
# DataFrame-level operations
# ----------------------------------------------------------------------------

def filter_by_keywords(df: pd.DataFrame, keywords: Iterable[str], text_col: str = "text") -> pd.DataFrame:
    """Return rows of df whose text contains at least one of the keywords."""
    pattern = _build_keyword_pattern(keywords)
    mask = df[text_col].fillna("").str.contains(pattern, regex=True)
    return df[mask].copy()


def add_keyword_flags(df: pd.DataFrame, themes: dict[str, list[str]] = None, text_col: str = "text") -> pd.DataFrame:
    """Add boolean columns to df, one per theme, indicating whether each speech
    mentions any keyword from that theme.

    Returns a copy of df with extra columns named e.g. 'is_climate_core',
    'is_climate_security_nexus', etc.
    """
    if themes is None:
        themes = CLIMATE_KEYWORDS
    df = df.copy()
    for theme, kws in themes.items():
        pattern = _build_keyword_pattern(kws)
        col = f"is_climate_{theme}"
        df[col] = df[text_col].fillna("").str.contains(pattern, regex=True)
    # Aggregate flag: any climate theme matched
    theme_cols = [f"is_climate_{t}" for t in themes]
    df["is_climate_any"] = df[theme_cols].any(axis=1)
    return df