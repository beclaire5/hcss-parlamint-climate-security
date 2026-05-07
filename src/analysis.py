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
# ----------------------------------------------------------------------------
# Correlation analysis
# ----------------------------------------------------------------------------

def theme_correlation_over_time(df: pd.DataFrame) -> pd.DataFrame:
    """Compute correlation matrix between climate themes based on their
    monthly co-occurrence rates in the corpus.

    For each month, we compute the share of climate speeches that mention
    each theme. The correlation matrix tells us which themes tend to rise
    and fall together in the parliamentary discourse.
    """
    df_local = df.copy()
    df_local["month"] = pd.to_datetime(df_local["date"]).dt.to_period("M")

    # For each month, fraction of speeches that mention each theme
    monthly_rates = df_local.groupby("month")[THEME_COLS].mean()

    # Pearson correlation matrix
    corr = monthly_rates.corr()
    # Rename to readable labels
    corr = corr.rename(index=THEME_LABELS, columns=THEME_LABELS)
    return corr


# ----------------------------------------------------------------------------
# Cluster analysis (TF-IDF + K-Means)
# ----------------------------------------------------------------------------

def cluster_speeches(
    df: pd.DataFrame,
    n_clusters: int = 6,
    sample_size: int = 5000,
    random_state: int = 42,
) -> tuple[pd.DataFrame, list[list[str]]]:
    """Cluster climate speeches into latent topics using TF-IDF + K-Means.

    Returns:
        - df_with_clusters: input df with extra columns 'cluster' (int) and
          'pca_x', 'pca_y' (2D projection for plotting)
        - top_terms: list of lists, where top_terms[i] contains the top
          distinguishing terms for cluster i
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    from sklearn.decomposition import TruncatedSVD

    # Sample for speed; clustering on 22k speeches with TF-IDF is heavy
    if len(df) > sample_size:
        df_sample = df.sample(sample_size, random_state=random_state).copy().reset_index(drop=True)
    else:
        df_sample = df.copy().reset_index(drop=True)

    # TF-IDF on speech text
    # max_features keeps it fast; min_df removes ultra-rare terms; stop_words removes English filler
    vectorizer = TfidfVectorizer(
        max_features=2000,
        min_df=5,
        max_df=0.5,
        stop_words="english",
        ngram_range=(1, 2),
    )
    X = vectorizer.fit_transform(df_sample["text"].fillna(""))

    # K-Means clustering
    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    df_sample["cluster"] = km.fit_predict(X)

    # 2D projection for plotting (TruncatedSVD = LSA, works on sparse matrices)
    svd = TruncatedSVD(n_components=2, random_state=random_state)
    coords = svd.fit_transform(X)
    df_sample["pca_x"] = coords[:, 0]
    df_sample["pca_y"] = coords[:, 1]

    # Top distinguishing terms per cluster
    feature_names = vectorizer.get_feature_names_out()
    top_terms = []
    for i in range(n_clusters):
        center = km.cluster_centers_[i]
        top_idx = center.argsort()[::-1][:10]
        top_terms.append([feature_names[j] for j in top_idx])

    return df_sample, top_terms
# ----------------------------------------------------------------------------
# Statistical significance: did the Russian invasion shift the discourse?
# ----------------------------------------------------------------------------

def pre_post_invasion_significance(df_climate: pd.DataFrame, df_all: pd.DataFrame) -> pd.DataFrame:
    """For each climate theme, test whether the rate of mention significantly
    changed after the Russian invasion of Ukraine (24 Feb 2022), using a
    chi-square test of independence.

    The test compares two contingency tables:
        Period          | Climate-theme speeches | Other speeches
        Pre-invasion    |        a               |       b
        Post-invasion   |        c               |       d

    A significant chi-square (p < 0.05) means the share of speeches mentioning
    that theme is different before vs after the invasion in a way that is
    unlikely to be due to chance.

    Returns df: theme, pre_share_pct, post_share_pct, chi2, p_value, significant
    """
    from scipy.stats import chi2_contingency

    # Restrict to comparable window: 2021-01-01 → 2022-07-12 (corpus end)
    # for fair comparison of pre vs post invasion.
    WINDOW_START = "2021-01-01"
    WINDOW_END = df_all["date"].max()  # corpus end

    # Filter both dataframes to the comparison window
    all_window = df_all[(df_all["date"] >= WINDOW_START) & (df_all["date"] <= WINDOW_END)]
    climate_window = df_climate[(df_climate["date"] >= WINDOW_START) & (df_climate["date"] <= WINDOW_END)]

    # Total speeches in each period (denominator: ALL speeches, climate or not)
    pre_total = (all_window["date"] < INVASION_DATE).sum()
    post_total = (all_window["date"] >= INVASION_DATE).sum()

    rows = []
    for theme_col in THEME_COLS:
        if theme_col not in df_climate.columns:
            continue

        # Numerator: climate-theme speeches in each period
        pre_theme = ((climate_window["date"] < INVASION_DATE) & climate_window[theme_col]).sum()
        post_theme = ((climate_window["date"] >= INVASION_DATE) & climate_window[theme_col]).sum()

        # Build 2x2 contingency table
        # Rows: pre / post invasion
        # Cols: theme mentioned / not mentioned
        a = int(pre_theme)
        b = int(pre_total - pre_theme)
        c = int(post_theme)
        d = int(post_total - post_theme)
        contingency = [[a, b], [c, d]]

        # Chi-square test
        try:
            chi2, p_value, dof, expected = chi2_contingency(contingency)
        except ValueError:
            chi2, p_value = float("nan"), float("nan")

        pre_share = (a / pre_total * 100) if pre_total else 0
        post_share = (c / post_total * 100) if post_total else 0

        rows.append({
            "theme": THEME_LABELS[theme_col],
            "pre_count": a,
            "post_count": c,
            "pre_share_pct": round(pre_share, 3),
            "post_share_pct": round(post_share, 3),
            "abs_change_pct": round(post_share - pre_share, 3),
            "chi2": round(chi2, 2) if chi2 == chi2 else None,
            "p_value": round(p_value, 4) if p_value == p_value else None,
            "significant_005": (p_value < 0.05) if p_value == p_value else False,
        })

    return pd.DataFrame(rows)
# ----------------------------------------------------------------------------
# Sentiment analysis (VADER)
# ----------------------------------------------------------------------------

def compute_sentiment_scores(df: pd.DataFrame, text_col: str = "text") -> pd.DataFrame:
    """Add VADER sentiment scores to a DataFrame of speeches.

    VADER (Valence Aware Dictionary and sEntiment Reasoner) is a lexicon-based
    sentiment analyzer well-suited for short-to-medium English text. It returns:
        - compound: overall sentiment in [-1, 1] (most useful)
        - pos, neu, neg: individual proportions

    Returns a copy of df with a new 'sentiment' column (the compound score)
    and a categorical 'sentiment_label' column (positive/neutral/negative).
    """
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    analyzer = SentimentIntensityAnalyzer()
    df = df.copy()

    # Compute compound score for each speech
    df["sentiment"] = df[text_col].fillna("").apply(
        lambda t: analyzer.polarity_scores(t)["compound"]
    )

    # Categorize: VADER's standard thresholds
    def categorize(score):
        if score >= 0.05:
            return "positive"
        elif score <= -0.05:
            return "negative"
        else:
            return "neutral"

    df["sentiment_label"] = df["sentiment"].apply(categorize)
    return df


def sentiment_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """Average sentiment per year, plus distribution of pos/neu/neg labels."""
    yearly = df.groupby("year").agg(
        mean_sentiment=("sentiment", "mean"),
        n_speeches=("sentiment", "count"),
        pct_positive=("sentiment_label", lambda s: (s == "positive").mean() * 100),
        pct_neutral=("sentiment_label", lambda s: (s == "neutral").mean() * 100),
        pct_negative=("sentiment_label", lambda s: (s == "negative").mean() * 100),
    ).reset_index()
    return yearly.round(3)


def sentiment_by_party(df: pd.DataFrame, n: int = 12) -> pd.DataFrame:
    """Average sentiment per party (top-N by speech count)."""
    out = df.groupby("party_abbr").agg(
        mean_sentiment=("sentiment", "mean"),
        n_speeches=("sentiment", "count"),
    ).reset_index()
    out = out.dropna(subset=["party_abbr"])
    out = out[out["n_speeches"] >= 100]  # only parties with meaningful sample size
    return out.sort_values("n_speeches", ascending=False).head(n).round(3)


def sentiment_by_theme(df: pd.DataFrame) -> pd.DataFrame:
    """Average sentiment per theme. A speech can belong to multiple themes."""
    rows = []
    for col in THEME_COLS:
        if col not in df.columns:
            continue
        sub = df[df[col]]
        if len(sub) == 0:
            continue
        rows.append({
            "theme": THEME_LABELS[col],
            "n_speeches": len(sub),
            "mean_sentiment": round(sub["sentiment"].mean(), 3),
            "pct_negative": round((sub["sentiment_label"] == "negative").mean() * 100, 1),
        })
    return pd.DataFrame(rows)