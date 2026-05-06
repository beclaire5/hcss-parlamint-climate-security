# Climate & Security in Dutch Parliamentary Debates (2015–2022)

An interactive analysis tool exploring how the Dutch parliament's framing of climate has evolved between 2015 and 2022, with a focus on the intersection of climate and security. Aligned with the HCSS research pillar **Climate, Energy, Materials & Food (Climate and Security)**.

Built using the [ParlaMint](https://www.clarin.eu/parlamint) corpus.

## Project Goals

- Identify trends in climate-related parliamentary debate over time
- Analyze how climate is framed: environmental issue vs. security/geopolitical issue
- Surface the most active speakers, parties, and topics in climate debates
- Provide an interactive Streamlit interface for non-technical users to explore the data

## Project Structure

```
hcss-parlamint-nl/
├── app/             # Streamlit application
├── data/            # Raw and processed data (excluded from git)
│   ├── raw/         # Original ParlaMint XML files
│   └── processed/   # Cleaned, filtered datasets
├── notebooks/       # Jupyter notebooks for exploration
├── src/             # Reusable Python modules
├── requirements.txt # Python dependencies
└── README.md
```

## Installation

```bash
# Clone the repository
git clone https://github.com/beclaire5/hcss-parlamint-nl.git
cd hcss-parlamint-nl

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Data

This project uses the ParlaMint-NL corpus. Due to its size (~2.65 GB), the data is not included in this repository.

## Usage

```bash
streamlit run app/main.py
```

## HCSS Research Pillar

This project addresses the **Climate and Security** theme within the broader pillar of *Climate, Energy, Materials & Food*.

## Author

Chiara Barontini — Internship Application, HCSS Datalab (May 2026)