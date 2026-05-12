"""
HCSS Datalab — Climate in Dutch Parliamentary Discourse (2014–2022)
====================================================================

A Streamlit application for exploring how the Dutch parliament has
discussed climate, with a particular focus on the climate-security nexus, a research priority of HCSS.

Run from the project root:
    streamlit run app/main.py
"""

from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Make sure we can import from src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.text_processing import clean_tokenized_text, CLIMATE_KEYWORDS
from src import analysis as A


# ----------------------------------------------------------------------------
# Page configuration
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Climate in Dutch Parliament — HCSS",
    layout="wide",
    initial_sidebar_state="expanded",
)
# Custom CSS for headers and titles — HCSS-inspired styling
st.markdown("""
<style>
    /* Main page title */
    h1 {
        color: #1f3a5f !important;
        font-weight: 700 !important;
        border-bottom: 3px solid #1f3a5f;
        padding-bottom: 0.3em;
        margin-bottom: 0.8em;
    }
    /* Section headers */
    h2 {
        color: #1f3a5f !important;
        font-weight: 600 !important;
        margin-top: 1.5em;
    }
    /* Subsection headers */
    h3 {
        color: #1f3a5f !important;
        font-weight: 600 !important;
    }
    /* Sidebar title */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {
        color: #1f3a5f !important;
        border-bottom: none;
    }
    /* Metric labels */
    [data-testid="stMetricLabel"] {
        color: #5d6d7e !important;
        font-weight: 600 !important;
    }
    /* Metric values */
    [data-testid="stMetricValue"] {
        color: #1f3a5f !important;
        font-weight: 700 !important;
    }
    /* Tab labels */
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 1rem !important;
        font-weight: 500 !important;
    }
    /* Active tab */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #1f3a5f !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Data loading (cached so we only load once per session)
# ----------------------------------------------------------------------------
@st.cache_data
def load_climate_speeches() -> pd.DataFrame:
    path = PROJECT_ROOT / "data" / "processed" / "climate_speeches.csv"
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data
def load_all_speeches_metadata() -> pd.DataFrame:
    """Load only metadata columns (no full text) from the full corpus.
    Used for computing party-level baselines (e.g., share of speeches
    that are climate-related)."""
    path = PROJECT_ROOT / "data" / "processed" / "all_speeches.csv"
    df = pd.read_csv(path, usecols=["date", "year", "house", "subcorpus", "party_abbr"])
    return df


# ----------------------------------------------------------------------------
# Sidebar (filters)
# ----------------------------------------------------------------------------
def sidebar_filters(df: pd.DataFrame) -> dict:
    st.sidebar.title("Filters")
    st.sidebar.markdown("Refine the analysis by year, party, and theme.")

    # Year range slider
    min_year = int(df["year"].min())
    max_year = int(df["year"].max())
    year_range = st.sidebar.slider(
        "Year range",
        min_value=min_year, max_value=max_year,
        value=(min_year, max_year),
        step=1,
    )

    # Parties multiselect
    all_parties = sorted(df["party_abbr"].dropna().unique())
    selected_parties = st.sidebar.multiselect(
        "Parties (leave empty for all)",
        options=all_parties,
        default=[],
    )

    # House
    house = st.sidebar.radio(
        "House",
        options=["Both", "Lower (Tweede Kamer)", "Upper (Eerste Kamer)"],
        index=0,
    )

    # Themes
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Climate themes**")
    selected_themes = []
    for theme_col, label in A.THEME_LABELS.items():
        if st.sidebar.checkbox(label, value=True, key=theme_col):
            selected_themes.append(theme_col)

    return {
        "year_range": year_range,
        "parties": selected_parties,
        "house": house,
        "themes": selected_themes,
    }


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    out = df.copy()
    out = out[(out["year"] >= filters["year_range"][0]) & (out["year"] <= filters["year_range"][1])]
    if filters["parties"]:
        out = out[out["party_abbr"].isin(filters["parties"])]
    if filters["house"] == "Lower (Tweede Kamer)":
        out = out[out["house"] == "Lower"]
    elif filters["house"] == "Upper (Eerste Kamer)":
        out = out[out["house"] == "Upper"]
    if filters["themes"]:
        # Keep speeches matching AT LEAST one selected theme
        theme_mask = out[filters["themes"]].any(axis=1)
        out = out[theme_mask]
    return out


# ----------------------------------------------------------------------------
# Main app
# ----------------------------------------------------------------------------
def main():
    # Header with HCSS logo (rendered via HTML for crisper display)
    LOGO_PATH = PROJECT_ROOT / "assets" / "hcss_logo.png"

    if LOGO_PATH.exists():
        import base64
        with open(LOGO_PATH, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 24px; margin-bottom: 16px;">
                <img src="data:image/png;base64,{logo_b64}" width="90" height="90"
                     style="image-rendering: -webkit-optimize-contrast; image-rendering: crisp-edges;" />
                <div>
                    <h1 style="margin: 0; padding: 0; border: none; color: #1f3a5f; font-weight: 700;">
                        Climate in Dutch Parliamentary Discourse
                    </h1>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.title("Climate in Dutch Parliamentary Discourse")

    st.markdown(
        "**An exploratory analysis of how the Dutch parliament discussed climate "
        "between 2014 and 2022, with a focus on the climate-security nexus.**"
    )
    st.caption(
        "Submission for the HCSS Datalab Internship Test, May 2026. "
        "Source: [ParlaMint-NL-en v4.1](https://www.clarin.si/repository/xmlui/handle/11356/1910). "
        "This is a candidate application; not an official HCSS product."
    )

    # Load data
    with st.spinner("Loading climate speeches..."):
        df = load_climate_speeches()
        df_all_meta = load_all_speeches_metadata()

    # Sidebar filters
    filters = sidebar_filters(df)
    df_filtered = apply_filters(df, filters)

    # ------------------------------------------------------------------------
    # Top metrics
    # ------------------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Climate speeches", f"{len(df_filtered):,}")
    col2.metric("Unique speakers", f"{df_filtered['speaker_name'].nunique():,}")
    col3.metric("Parties", f"{df_filtered['party_abbr'].nunique()}")
    col4.metric(
        "Security-nexus speeches",
        f"{int(df_filtered.get('is_climate_security_nexus', pd.Series(dtype=bool)).sum()):,}"
    )

    st.markdown("---")

    # ------------------------------------------------------------------------
    # Tabs for different views
    # ------------------------------------------------------------------------
    (tab_overview, tab_actors, tab_themes, tab_war, tab_arctic,
     tab_patterns, tab_sentiment, tab_explore) = st.tabs([
        "Trends over time",
        "Actors",
        "Themes",
        "Pre/Post invasion",
        "Arctic deep-dive",
        "Patterns",
        "Sentiment",
        "Explore speeches",
    ])

    # --- Trends ---
    with tab_overview:
        st.subheader("Climate-related speeches per year")
        st.caption(
            "Annual count of parliamentary speeches that mention at least one "
            "climate-related keyword. The 2014 figure is partial (corpus starts in April). "
            "The 2019 peak coincides with the Dutch Climate Act (Klimaatwet) and global "
            "climate mobilisation; the 2020 dip reflects COVID-19 dominating parliamentary "
            "agenda; the 2022 figure covers only January–July."
        )
        yearly = A.speeches_per_year(df_filtered)
        fig = px.bar(yearly, x="year", y="count",
                     labels={"count": "Number of speeches"},
                     color_discrete_sequence=["#1f3a5f"])
        fig.update_layout(showlegend=False, xaxis=dict(tickmode="linear"))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Climate themes over time")
        st.caption(
            "Breakdown of climate speeches by sub-theme. Note that themes can overlap "
            "(a speech can mention both 'core' climate language and 'energy transition'). "
            "The climate-security nexus and Arctic dimension remain consistently smaller in volume "
            "but show distinct dynamics."
        )
        themed = A.speeches_per_year_by_theme(df_filtered)
        if not themed.empty:
            fig2 = px.line(themed, x="year", y="count", color="theme",
                           markers=True,
                           labels={"count": "Speeches", "theme": "Theme"})
            fig2.update_layout(xaxis=dict(tickmode="linear"))
            st.plotly_chart(fig2, use_container_width=True)

    # --- Actors ---
    with tab_actors:
        st.caption(
            "Two complementary views: absolute climate speech counts (left and right) "
            "highlight which actors dominate by volume; **climate intensity** (bottom) "
            "shows the *share* of each party's total speeches that mention climate, "
            "correcting for party size. A small party can have very high climate "
            "intensity even with few absolute speeches. This often reveals the true "
            "climate prioritisers in the parliament."
        )
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Top 10 speakers")
            top_sp = A.top_speakers(df_filtered, n=10)
            if not top_sp.empty:
                top_sp["label"] = top_sp["speaker_name"] + " (" + top_sp["party_abbr"].fillna("?") + ")"
                fig = px.bar(top_sp, x="count", y="label", orientation="h",
                             labels={"count": "Speeches", "label": ""},
                             color_discrete_sequence=["#1f3a5f"])
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.subheader("Top parties by climate speech count")
            top_p = A.top_parties(df_filtered, n=15)
            if not top_p.empty:
                fig = px.bar(top_p, x="count", y="party_abbr", orientation="h",
                             labels={"count": "Speeches", "party_abbr": ""},
                             color_discrete_sequence=["#3a8a5f"])
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Climate intensity — share of each party's speeches that are climate-related")
        st.caption("This corrects for party size: small parties may speak proportionally more about climate.")
        intensity = A.party_climate_intensity(df_all_meta, df_filtered, n=15)
        if not intensity.empty:
            fig = px.bar(intensity, x="climate_share_pct", y="party_abbr", orientation="h",
                         labels={"climate_share_pct": "% of speeches that mention climate",
                                 "party_abbr": ""},
                         color_discrete_sequence=["#3a6ea5"])
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)

    # --- Themes ---
    with tab_themes:
        st.subheader("Distribution of climate themes")
        st.caption(
            "Each climate speech is tagged with one or more of five sub-themes "
            "based on a curated keyword dictionary. Themes intentionally overlap: "
            "a single speech can mention both 'core' climate language (CO2, emissions) "
            "and 'security nexus' language (food security, drought). The overlap is "
            "itself analytically interesting."
        )
        theme_dist = A.theme_distribution(df_filtered)
        if not theme_dist.empty:
            fig = px.bar(theme_dist.sort_values("count"), x="count", y="theme",
                         orientation="h",
                         labels={"count": "Speeches", "theme": ""},
                         color_discrete_sequence=["#1f3a5f"])
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("What words dominate the climate discourse?")
        st.caption(
            "A word cloud of the most frequent terms in the filtered speeches, "
            "excluding parliamentary boilerplate (chairman, minister, member). "
            "Filter by theme in the sidebar to see which words dominate each "
            "framing, for example, the climate-security theme surfaces words "
            "like 'security', 'energy', 'crisis', 'water', while the energy "
            "transition theme emphasises 'gas', 'wind', 'renewable', 'hydrogen'."
        )

        with st.spinner("Generating word cloud..."):
            wc_fig = A.generate_wordcloud_image(df_filtered, max_words=80)
            if wc_fig is not None:
                st.pyplot(wc_fig, use_container_width=True)
            else:
                st.info("Not enough data to generate a word cloud with the current filters.")

    # --- Pre/Post invasion ---
    with tab_war:
        st.subheader("Did the Russian invasion of Ukraine (Feb 2022) shift the climate discourse?")
        st.caption(
            "This view tests whether the share of speeches mentioning each climate theme "
            "significantly changed between the period **before** and **after** "
            "24 February 2022, using a **chi-square test of independence**. "
            "The comparison window is restricted to 2021-01-01 → corpus end for fair baseline."
        )

        sig = A.pre_post_invasion_significance(df_filtered, df_all_meta)

        if not sig.empty:
            # Display summary table
            display_df = sig[["theme", "pre_count", "post_count",
                              "pre_share_pct", "post_share_pct",
                              "abs_change_pct", "chi2", "p_value", "significant_005"]].copy()
            display_df.columns = ["Theme", "Pre count", "Post count",
                                   "Pre share (%)", "Post share (%)",
                                   "Δ (pp)", "χ²", "p-value", "Significant (p<0.05)"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Visualization: change in share with significance highlighted
            sig_plot = sig.copy()
            sig_plot["Significance"] = sig_plot["significant_005"].map(
                {True: "Significant (p<0.05)", False: "Not significant"}
            )
            fig = px.bar(
                sig_plot,
                x="theme", y="abs_change_pct",
                color="Significance",
                color_discrete_map={
                    "Significant (p<0.05)": "#1f3a5f",
                    "Not significant": "#bdbdbd",
                },
                labels={"abs_change_pct": "Change in share (percentage points)",
                        "theme": ""},
                title="Change in share of climate-theme speeches after the invasion",
            )
            fig.update_layout(legend_title="")
            st.plotly_chart(fig, use_container_width=True)

            # Narrative interpretation
            sig_themes = sig[sig["significant_005"]]
            if not sig_themes.empty:
                significant_list = ", ".join(f"**{t}**" for t in sig_themes["theme"])
                st.success(
                    f"The chi-square test indicates a statistically significant shift "
                    f"(p<0.05) in: {significant_list}. "
                    f"For these themes, the change in discourse share before vs. after "
                    f"the invasion is unlikely to be explained by random fluctuation alone."
                )
            else:
                st.info(
                    "No theme shows a statistically significant shift at the p<0.05 threshold "
                    "in the chosen filter selection. This could mean the discourse was relatively "
                    "stable, or that the comparison window contains too few post-invasion observations."
                )

            with st.expander("How to read this analysis"):
                st.markdown("""
                The **chi-square test of independence** compares two periods (pre/post invasion)
                and asks: *is the share of speeches mentioning theme X significantly different
                between the two periods, beyond what we would expect by chance?*

                - **χ² (chi-square statistic)** — larger means bigger gap between observed and
                  expected counts
                - **p-value** — probability of observing this gap if the two periods truly
                  had the same underlying rate. p < 0.05 means we reject that hypothesis
                - **Δ (pp)** — change in the share of speeches mentioning the theme,
                  expressed in percentage points (e.g., 0.5pp = 0.5%)

                **Caveats**: parliamentary speech rates are influenced by many concurrent
                factors (election cycles, COVID, agenda setting). Significance here is
                association, not causation.
                """)


    # --- Arctic ---
    with tab_arctic:
        st.subheader("The Arctic in Dutch parliamentary debate")
        df_arctic = df[df.get("is_climate_arctic", pd.Series(False, index=df.index))]
        st.write(
            f"Despite the Netherlands being a non-Arctic country, the Dutch parliament "
            f"mentioned the Arctic in **{len(df_arctic)} climate-related speeches** between 2014 and 2022. "
            f"This reflects the country's status as an Arctic Council observer and its broader engagement "
            f"in climate-security discussions."
        )
        st.caption(
            "The Arctic is a paradigmatic case of the climate-security nexus: melting ice "
            "opens new shipping routes, strategic resource access shifts, and great-power "
            "competition (Russia, China, NATO) intensifies. Although volume is small "
            "(72 speeches), the temporal pattern and the speakers involved offer a "
            "qualitative window into how climate-security thinking surfaces in Dutch debate."
        )
        if not df_arctic.empty:
            yearly_arc = df_arctic.groupby("year").size().reset_index(name="count")
            fig = px.bar(yearly_arc, x="year", y="count",
                         labels={"count": "Arctic mentions"},
                         color_discrete_sequence=["#1f3a5f"])
            fig.update_layout(xaxis=dict(tickmode="linear"))
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("**Sample speeches mentioning the Arctic:**")
            samples = A.get_speech_samples(df_arctic, n=5)
            for _, row in samples.iterrows():
                with st.expander(f"{row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else row['date']} — {row['speaker_name']} ({row['party_abbr']})"):
                    st.write(clean_tokenized_text(row["text"]))
    # --- Patterns (correlation + clustering) ---
    with tab_patterns:
        st.subheader("Theme correlation over time")
        st.caption(
            "Pearson correlation between the monthly rates of each climate theme. "
            "Themes that rise and fall together appear in red; those that move "
            "independently or inversely appear lighter or blue. "
            "This reveals which strands of climate discourse are coupled and which evolve separately."
        )
        corr = A.theme_correlation_over_time(df_filtered)
        if not corr.empty:
            fig = px.imshow(
                corr,
                text_auto=".2f",
                aspect="auto",
                color_continuous_scale="RdBu_r",
                color_continuous_midpoint=0,
                zmin=-1, zmax=1,
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        st.subheader("Latent topic clusters (TF-IDF + K-Means)")
        st.caption(
            "Beyond the pre-defined keyword themes, an unsupervised clustering of "
            "climate speeches reveals emergent topics. Each speech is encoded as "
            "TF-IDF vectors; K-Means groups them into 6 latent clusters; the 2D "
            "projection (Truncated SVD) shows their separation."
        )
        n_clusters = st.slider("Number of clusters", min_value=3, max_value=10, value=6)

        with st.spinner("Clustering speeches (this takes ~10 seconds)..."):
            df_clusters, top_terms = A.cluster_speeches(df_filtered, n_clusters=n_clusters)

        # 2D scatter
        df_clusters["cluster_label"] = "Cluster " + df_clusters["cluster"].astype(str)
        fig = px.scatter(
            df_clusters,
            x="pca_x", y="pca_y",
            color="cluster_label",
            hover_data=["speaker_name", "party_abbr", "year"],
            opacity=0.6,
            labels={"pca_x": "Dimension 1", "pca_y": "Dimension 2"},
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Top distinguishing terms per cluster**")
        for i, terms in enumerate(top_terms):
            st.write(f"**Cluster {i}**: {', '.join(terms)}")
    # --- Sentiment ---
    with tab_sentiment:
        st.subheader("Sentiment of climate speeches over time")
        st.caption(
            "Each speech is scored using **VADER** (Valence Aware Dictionary and "
            "sEntiment Reasoner), a lexicon-based method calibrated on social and "
            "political English text. The compound score ranges from -1 (most "
            "negative) to +1 (most positive). VADER tends to skew positive on long "
            "formal text, so absolute values should be read with caution; the "
            "**relative comparisons** below (across years, parties, and themes) "
            "are the meaningful signal."
        )

        if "sentiment" not in df_filtered.columns:
            st.warning(
                "Sentiment scores are not available in the loaded dataset. "
                "Re-run the sentiment computation cell in `notebooks/02_climate_filtering.ipynb` "
                "to populate them."
            )
        else:
            # Yearly trend
            st.markdown("**Average sentiment per year**")
            yearly_sent = A.sentiment_by_year(df_filtered)
            if not yearly_sent.empty:
                fig = px.line(
                    yearly_sent, x="year", y="mean_sentiment",
                    markers=True,
                    labels={"mean_sentiment": "Mean compound sentiment", "year": "Year"},
                    color_discrete_sequence=["#1f3a5f"],
                )
                fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
                fig.update_layout(xaxis=dict(tickmode="linear"))
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("Yearly breakdown table"):
                    st.dataframe(yearly_sent, use_container_width=True, hide_index=True)

            # By party
            st.markdown("---")
            st.markdown("**Sentiment by party**")
            st.caption(
                "Mean sentiment for parties with at least 100 climate speeches. "
                "More negative scores suggest a more critical or alarmist framing of climate."
            )
            party_sent = A.sentiment_by_party(df_filtered, n=12)
            if not party_sent.empty:
                fig = px.bar(
                    party_sent.sort_values("mean_sentiment"),
                    x="mean_sentiment", y="party_abbr",
                    orientation="h",
                    labels={"mean_sentiment": "Mean compound sentiment", "party_abbr": ""},
                    color="mean_sentiment",
                    color_continuous_scale="RdYlGn",
                    color_continuous_midpoint=party_sent["mean_sentiment"].median(),
                )
                fig.update_layout(showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)

            # By theme
            st.markdown("---")
            st.markdown("**Sentiment by climate theme**")
            st.caption(
                "Different framings carry different emotional registers. "
                "Climate-security speeches, for example, may use more alarmist or "
                "urgent language than core environmental policy speeches."
            )
            theme_sent = A.sentiment_by_theme(df_filtered)
            if not theme_sent.empty:
                fig = px.bar(
                    theme_sent.sort_values("mean_sentiment"),
                    x="mean_sentiment", y="theme",
                    orientation="h",
                    labels={"mean_sentiment": "Mean compound sentiment", "theme": ""},
                    color_discrete_sequence=["#1f3a5f"],
                )
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("Theme breakdown with negative-share details"):
                    st.dataframe(theme_sent, use_container_width=True, hide_index=True)

            # Methodology disclaimer
            with st.expander("Methodology and caveats"):
                st.markdown("""
                **Method**: VADER (Hutto & Gilbert, 2014) is a rule-based sentiment
                analyzer using a curated lexicon and grammatical heuristics. It produces
                a compound score in [-1, +1].

                **Caveats specific to this dataset**:
                - The text is **machine-translated** from Dutch. Sentiment-bearing
                  nuances may be lost or distorted in translation.
                - VADER was trained on English **social media** text. Parliamentary
                  prose contains ritual courtesies ("Mr. Chairman", "I thank the
                  member") that inflate positive scores artificially.
                - Long speeches (200+ words) tend to skew positive due to additive
                  scoring. Comparisons across **equally long** units mitigate this.

                **As future work**, fine-tuning a Dutch sentiment model (e.g., BERTje)
                on the original Dutch text, with a small manually-labelled validation
                set, would yield more reliable scores.
                """)
    # --- Explore ---
    with tab_explore:
        st.subheader("Browse individual speeches")
        st.caption("A random sample from your current filter selection.")
        n = st.slider("Number of samples", 1, 20, 5)
        if len(df_filtered) > 0:
            samples = A.get_speech_samples(df_filtered, n=n, random_state=None)
            for _, row in samples.iterrows():
                date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                with st.expander(f"{date_str} — {row['speaker_name']} ({row['party_abbr']}) [{row['house']}]"):
                    st.write(clean_tokenized_text(row["text"]))
        else:
            st.info("No speeches match your filters.")

    # Footer
    # Footer
    st.markdown("---")
    st.caption(
        "**Chiara Barontini** · HCSS Datalab Internship Test · May 2026  \n"
        "Code: [github.com/beclaire5/hcss-parlamint-climate-security]"
        "(https://github.com/beclaire5/hcss-parlamint-climate-security) · "
        "Data: [ParlaMint-NL-en v4.1](https://www.clarin.si/repository/xmlui/handle/11356/1910) (CC BY 4.0)  \n"
        "*This is a candidate application; not an official HCSS product.*"
    )


if __name__ == "__main__":
    main()