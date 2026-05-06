# Climate in Dutch Parliamentary Discourse (2014–2022)

> An interactive analytical tool exploring how the Dutch parliament has discussed climate over an eight-year period, with a particular focus on the climate–security nexus which is a research priority of HCSS.
>
> Built for the **HCSS Datalab Internship Test**, May 2026.

---

## Overview

This project analyses **609,209 parliamentary speeches** from the Dutch Tweede Kamer (Lower House) and Eerste Kamer (Upper House) between April 2014 and July 2022, drawn from the [ParlaMint-NL-en v4.1 corpus](https://www.clarin.si/repository/xmlui/handle/11356/1910). Of these, **22,088 speeches (3.6%)** mention climate-related topics. A subset of **718 speeches (3.2% of climate speeches)** explicitly bridges climate to security, the angle most relevant to HCSS's research priorities.

The deliverable is a Streamlit application that allows analysts and non-technical users to explore the corpus across multiple dimensions: trends over time, actors (speakers and parties), thematic framing, the impact of the Russian invasion of Ukraine, and an Arctic deep-dive case study.

## Research question

**How has the Dutch parliament's framing of climate evolved between 2014 and 2022, and to what extent has the climate–security nexus emerged as a distinct strand of discourse?**

Sub-questions explored in the tool:
- Which speakers and parties have led climate debates, and with what intensity?
- How is climate framed — purely environmental, or as a security/geopolitical issue?
- Did the Russian invasion of Ukraine (24 February 2022) shift the discourse toward energy security?
- How visible is the Arctic dimension — relevant despite the Netherlands being a non-Arctic country and an Arctic Council observer?

## Live application

Launch the app locally:

```bash
streamlit run app/main.py
```

The app provides six analytical tabs:

| Tab | What it shows |
|-----|---------------|
| 📈 **Trends over time** | Annual volume of climate speeches and breakdown by sub-theme |
| 👥 **Actors** | Top speakers, top parties, and a "climate intensity" metric correcting for party size |
| 🎯 **Themes** | Distribution across five sub-themes: core climate, energy transition, policy, climate–security nexus, Arctic |
| 🇷🇺 **Pre/Post invasion** | Comparison of climate discourse before vs. after 24 February 2022 |
| ❄️ **Arctic deep-dive** | A focused case study on the Arctic dimension, including sample speeches |
| 🔍 **Explore speeches** | Random sampling of individual speeches matching the active filters |

All views respond to a global filter set in the sidebar: **year range**, **parties**, **chamber**, and **theme**.

## Data pipeline

```
ParlaMint-NL-en.ana.tgz  (2.65 GB, 6112 XML files)
        │
        ▼  src/data_loader.py  (lxml + custom TEI parser)
        │
all_speeches.csv  (609,209 rows × 14 columns, 517 MB)
        │
        ▼  src/text_processing.py  (regex keyword filtering, 5 themes)
        │
climate_speeches.csv  (22,088 rows × 19 columns)
        │
        ▼  src/analysis.py + app/main.py
        │
Interactive Streamlit dashboard
```

## Project structure

```
hcss-parlamint-climate-security/
├── app/
│   └── main.py                    # Streamlit application
├── src/
│   ├── data_loader.py             # XML parsing, speaker/party metadata
│   ├── text_processing.py         # Keyword filtering, theme tagging, text cleaning
│   ├── analysis.py                # Analytical functions (trends, actors, comparisons)
│   └── config.py                  # (Reserved)
├── notebooks/
│   ├── 01_explore_data.ipynb      # Initial data exploration and full-corpus parsing
│   └── 02_climate_filtering.ipynb # Keyword validation and climate subset creation
├── data/
│   ├── raw/                       # ParlaMint XML (excluded from git)
│   └── processed/                 # Generated CSVs (excluded from git)
├── requirements.txt
└── README.md
```

## Installation

**Prerequisites**: Python 3.10+, ~5 GB free disk space.

```bash
# 1. Clone the repository
git clone https://github.com/beclaire5/hcss-parlamint-climate-security.git
cd hcss-parlamint-climate-security

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download the data
# Download ParlaMint-NL-en.ana.tgz (2.65 GB) from:
# https://www.clarin.si/repository/xmlui/handle/11356/1910
# Place the .tgz file in data/raw/, then extract:
python -c "import tarfile; tarfile.open('data/raw/ParlaMint-NL-en.ana.tgz').extractall('data/raw/')"

# 5. Build the processed CSVs (~15 minutes for parsing, ~1 minute for filtering)
# Run the notebooks in order: 01_explore_data.ipynb then 02_climate_filtering.ipynb

# 6. Launch the app
streamlit run app/main.py
```

## Key design decisions

**Choice of corpus version (4.1, not 5.0)** — The task brief explicitly references the v4.1 file with its MD5 checksum. Even though v5.0 is now available with an additional "war" subcorpus, fidelity to the brief was prioritised; the war/post-invasion split is reconstructed manually from the date attribute.

**Thematic taxonomy** — Five themes were defined (core, energy transition, policy, climate–security nexus, Arctic) rather than a single "climate" flag. This allows users to distinguish between different framings and to spot where climate enters security-coded language. Themes can overlap, which is intentional: a single speech can simultaneously mention CO2 emissions and food security.

**Keyword curation** — Initial Arctic keywords included "polar", which produced many false positives ("polar opposites", "polar freezing" used metaphorically). After validation on real speeches, "polar" was removed, reducing Arctic mentions from 106 to 72 but improving precision substantially.

**Language** — The corpus chosen is the **machine-translated English version** (`ParlaMint-NL-en`) rather than the original Dutch. This makes the interface and analysis accessible to a wider HCSS audience and aligns with the task brief, which specifies this exact file.

**Lxml over BeautifulSoup** — The TEI XML files are large (up to 16 MB each) and deeply nested. `lxml` provides 5–10× the parsing speed of BeautifulSoup and supports XPath queries, which makes navigating the TEI schema cleaner.

**Streamlit + Plotly** — Streamlit was the framework explicitly suggested in the brief, and Plotly was chosen over Matplotlib because its interactivity (hover, zoom, legend toggling) is well-suited to an exploratory dashboard.

## Limitations

- The English text is **machine-translated**: nuances of Dutch political vocabulary may be lost, especially idiomatic expressions and party-specific framing.
- **Keyword-based filtering** is a coarse instrument. A speech that discusses climate without using a keyword from the list is missed; a speech that mentions a keyword in a tangential way is included. More sophisticated approaches (semantic similarity, classifier trained on labelled examples) would improve recall and precision.
- **Speech length is not normalised**: short procedural utterances by chairs are counted equally to substantive 10-minute speeches.
- **No causality is claimed**: shifts in discourse correlate with external events (Paris Agreement, COVID, invasion of Ukraine) but the tool does not establish causal links.

## Possible extensions

- **Sentiment analysis** of climate speeches over time, by party, to detect polarisation
- **Topic modelling (LDA or BERTopic)** to discover latent sub-themes within the climate corpus instead of relying solely on pre-defined keywords
- **Named entity analysis** using the existing NER annotations to track which countries, organisations, and persons appear most often in climate-security speeches
- **Network analysis** of speaker interactions: who responds to whom on climate matters, and how those networks evolved
- **Migration to v5.0** which adds a third subcorpus ("war") and improved language tagging
- **HCSS-style visual identity**: full integration of the HCSS brand palette and typography for a polished demo

## Tech stack

- **Python 3.13**
- **lxml** — TEI XML parsing
- **pandas, numpy** — data manipulation
- **Streamlit** — interactive web interface
- **Plotly Express** — interactive visualisations
- **scikit-learn, NLTK** — text processing utilities (used selectively)
- **tqdm** — progress bars during corpus parsing

## Author

**Chiara Barontini** — applying for the Data Internship at HCSS Datalab.
[GitHub](https://github.com/beclaire5) · [LinkedIn](https://www.linkedin.com/in/chiara-barontini-4535803a9/)

## Data attribution

ParlaMint-NL-en v4.1 by Tomaž Erjavec et al., distributed via CLARIN.SI under CC BY 4.0.