"""
analysis.py
===========
Analytical functions for the climate speeches subset.

Each function takes a DataFrame and returns a DataFrame ready for
plotting in Streamlit. Functions are pure and stateless.
"""

from __future__ import annotations
import pandas as pd
from collections import Counter

# Date of the Russian invasion of Ukraine — used as a comparison breakpoint
INVASION_DATE = "2022-02-24"

THEME_COLS = [
    "is_climate_core",
    "is_climate_energy_transition",
    "is_climate_policy",
    "is_climate_security_nexus",
    "is_climate_arctic",
]
THEME_LABELS = {
    "is_climate_core": "Core (climate, CO2, emissions)",
    "is_climate_energy_transition": "Energy transition",
    "is_climate_policy": "Policy (Paris, IPCC, COP)",
    "is_climate_security_nexus": "Climate-security nexus",
    "is_climate_arctic": "Arctic dimension",
}


# ----------------------------------------------------------------------------
# Descriptive analytics
# ----------------------------------------------------------------------------

def speeches_per_year(df: pd.DataFrame) -> pd.DataFrame:
    """Count speeches per year. Returns df with columns: year, count."""
    out = df.groupby("year").size().reset_index(name="count")
    return out.sort_values("year")


def speeches_per_year_by_theme(df: pd.DataFrame) -> pd.DataFrame:
    """Count of speeches per year for each climate theme.
    Returns long-format df with columns: year, theme, count."""
    rows = []
    for col in THEME_COLS:
        if col not in df.columns:
            continue
        sub = df[df[col]]
        yearly = sub.groupby("year").size().reset_index(name="count")
        yearly["theme"] = THEME_LABELS[col]
        rows.append(yearly)
    if not rows:
        return pd.DataFrame(columns=["year", "theme", "count"])
    return pd.concat(rows, ignore_index=True).sort_values(["year", "theme"])


def speeches_per_month(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly time series. Returns df with columns: month (date), count."""
    out = df.copy()
    out["month"] = pd.to_datetime(out["date"]).dt.to_period("M").dt.to_timestamp()
    return out.groupby("month").size().reset_index(name="count").sort_values("month")


def top_speakers(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N speakers by number of climate speeches.
    Returns df: speaker_name, party_abbr, count."""
    out = (
        df.groupby(["speaker_name", "party_abbr"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(n)
    )
    return out


def top_parties(df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    """Top N parties by climate speech count."""
    return (
        df.groupby("party_abbr")
        .size()
        .reset_index(name="count")
        .dropna(subset=["party_abbr"])
        .sort_values("count", ascending=False)
        .head(n)
    )


def party_climate_intensity(df_all: pd.DataFrame, df_climate: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    """For each party, compute share of speeches that are climate-related.
    This corrects for party size (PvdD looks small in absolute counts but talks
    about climate proportionally more)."""
    total = df_all.groupby("party_abbr").size().rename("total")
    climate = df_climate.groupby("party_abbr").size().rename("climate")
    out = pd.concat([total, climate], axis=1).fillna(0)
    out["climate_share_pct"] = (out["climate"] / out["total"] * 100).round(2)
    out = out[out["total"] >= 1000]  # only meaningful parties
    return out.sort_values("climate_share_pct", ascending=False).reset_index().head(n)


def theme_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Count of speeches per theme (themes can overlap)."""
    rows = []
    for col in THEME_COLS:
        if col in df.columns:
            rows.append({"theme": THEME_LABELS[col], "count": int(df[col].sum())})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Inferential / comparative analytics
# ----------------------------------------------------------------------------

def pre_post_invasion_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Compare climate-related speech volume per theme, before and after the
    Russian invasion of Ukraine (2022-02-24).
    Restricted to 2021-2022 for fair comparison (similar baseline window).
    Returns df: theme, pre_count, post_count, pct_change."""
    df_recent = df[df["year"].isin([2021, 2022])].copy()
    pre = df_recent[df_recent["date"] < INVASION_DATE]
    post = df_recent[df_recent["date"] >= INVASION_DATE]

    rows = []
    for col in THEME_COLS:
        if col not in df.columns:
            continue
        pre_count = int(pre[col].sum())
        post_count = int(post[col].sum())
        # Normalize by number of days in each period for fair comparison
        pre_days = (pd.Timestamp(INVASION_DATE) - pd.Timestamp("2021-01-01")).days
        post_days = (df["date"].max() and pd.Timestamp(df["date"].max()) - pd.Timestamp(INVASION_DATE)).days or 1
        pre_rate = pre_count / pre_days
        post_rate = post_count / post_days
        pct = ((post_rate - pre_rate) / pre_rate * 100) if pre_rate > 0 else 0
        rows.append({
            "theme": THEME_LABELS[col],
            "pre_count": pre_count,
            "post_count": post_count,
            "pre_per_day": round(pre_rate, 2),
            "post_per_day": round(post_rate, 2),
            "pct_change": round(pct, 1),
        })
    return pd.DataFrame(rows)


def keyword_frequency(df: pd.DataFrame, keywords: list[str], text_col: str = "text") -> pd.DataFrame:
    """Count occurrences of each keyword (sum across all speeches).
    Returns df: keyword, count."""
    rows = []
    text_lower = df[text_col].fillna("").str.lower()
    for kw in keywords:
        # Whole-word, case-insensitive count
        pattern = r"\b" + pd.Series([kw]).str.replace(r"([\\.\^\$\*\+\?\(\)\[\]\{\}\|])", r"\\\1", regex=True).iloc[0] + r"\b"
        count = int(text_lower.str.count(pattern).sum())
        rows.append({"keyword": kw, "count": count})
    return pd.DataFrame(rows).sort_values("count", ascending=False)


# ----------------------------------------------------------------------------
# Sample retrieval (for showing example speeches in the app)
# ----------------------------------------------------------------------------

def get_speech_samples(df: pd.DataFrame, n: int = 5, random_state: int = 42) -> pd.DataFrame:
    """Return a random sample of speeches with key columns, ready to display."""
    cols = ["date", "speaker_name", "party_abbr", "house", "subcorpus", "text"]
    cols = [c for c in cols if c in df.columns]
    sample = df.sample(min(n, len(df)), random_state=random_state)
    return sample[cols].reset_index(drop=True)