"""
data_loader.py
==============
Functions to parse the ParlaMint-NL-en TEI XML corpus into structured data.

The corpus has 6100 XML files organized by year (2014-2022).
Each file contains one parliamentary meeting with multiple utterances.

Main pipeline:
    parse_speaker_metadata(list_person_path) -> dict[speaker_id -> info]
    parse_party_metadata(list_org_path)      -> dict[party_id -> info]
    parse_meeting_file(xml_path)             -> list[speech dicts]
    build_corpus_dataframe(corpus_root)      -> pd.DataFrame of all speeches
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import re

import pandas as pd
from lxml import etree
from tqdm import tqdm

# TEI namespace map for XPath queries
NS = {"tei": "http://www.tei-c.org/ns/1.0"}
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


# ----------------------------------------------------------------------------
# Speaker / party metadata
# ----------------------------------------------------------------------------

def parse_speaker_metadata(list_person_path: Path) -> dict[str, dict]:
    """Parse listPerson.xml into a dict mapping speaker_id -> info.

    For speakers with multiple party affiliations over time, we keep all of them
    so the caller can resolve the party at the date of the meeting.
    """
    tree = etree.parse(str(list_person_path))
    root = tree.getroot()
    persons = root.findall(".//tei:person", NS)

    speakers = {}
    for p in persons:
        pid = p.attrib.get(XML_ID)
        if not pid:
            continue

        # Name
        surname_elem = p.find(".//tei:surname", NS)
        forename_elem = p.find(".//tei:forename", NS)
        surname = surname_elem.text.strip() if surname_elem is not None and surname_elem.text else ""
        forename = forename_elem.text.strip() if forename_elem is not None and forename_elem.text else ""
        full_name = f"{forename} {surname}".strip()

        # Sex
        sex_elem = p.find("tei:sex", NS)
        sex = sex_elem.attrib.get("value") if sex_elem is not None else None

        # Birth year
        birth_elem = p.find("tei:birth", NS)
        birth_year = None
        if birth_elem is not None:
            when = birth_elem.attrib.get("when", "")
            if when[:4].isdigit():
                birth_year = int(when[:4])

        # Affiliations (party memberships over time)
        affiliations = []
        for aff in p.findall("tei:affiliation", NS):
            ref = aff.attrib.get("ref", "")
            role = aff.attrib.get("role", "")
            from_date = aff.attrib.get("from", "")
            to_date = aff.attrib.get("to", "")
            # We're mainly interested in party memberships
            if ref.startswith("#party.") or role == "MP":
                affiliations.append(
                    {"ref": ref.lstrip("#"), "role": role, "from": from_date, "to": to_date}
                )

        speakers[pid] = {
            "speaker_id": pid,
            "name": full_name,
            "sex": sex,
            "birth_year": birth_year,
            "affiliations": affiliations,
        }

    return speakers


def parse_party_metadata(list_org_path: Path) -> dict[str, dict]:
    """Parse listOrg.xml into a dict mapping party_id -> info.

    Only parliamentary groups (= political parties) are kept.
    """
    tree = etree.parse(str(list_org_path))
    root = tree.getroot()
    orgs = root.findall(".//tei:org", NS)

    parties = {}
    for o in orgs:
        if o.attrib.get("role") != "parliamentaryGroup":
            continue
        pid = o.attrib.get(XML_ID)
        if not pid:
            continue

        info = {"party_id": pid, "abbr": None, "name_en": None, "name_nl": None}
        for name_elem in o.findall("tei:orgName", NS):
            full_attr = name_elem.attrib.get("full")
            lang = name_elem.attrib.get(XML_LANG)
            text = (name_elem.text or "").strip()
            if full_attr == "abb":
                info["abbr"] = text
            elif full_attr == "yes" and lang == "en":
                info["name_en"] = text
            elif full_attr == "yes" and lang == "nl":
                info["name_nl"] = text
        parties[pid] = info

    return parties


def resolve_party_at_date(speaker: dict, date_str: str) -> str | None:
    """Given a speaker's affiliations and a date (YYYY-MM-DD), return the party ID active then."""
    if not speaker:
        return None
    for aff in speaker.get("affiliations", []):
        ref = aff.get("ref", "")
        if not ref.startswith("party."):
            continue
        from_date = aff.get("from") or "0000-00-00"
        to_date = aff.get("to") or "9999-99-99"
        if from_date <= date_str <= to_date:
            return ref
    # Fallback: return first party affiliation if any
    for aff in speaker.get("affiliations", []):
        if aff.get("ref", "").startswith("party."):
            return aff["ref"]
    return None


# ----------------------------------------------------------------------------
# Meeting file parsing
# ----------------------------------------------------------------------------

def _clean_text(raw: str) -> str:
    """Collapse whitespace into single spaces. ParlaMint .ana files have
    one token per line; we want a normal sentence."""
    return re.sub(r"\s+", " ", raw).strip()


def parse_meeting_file(xml_path: Path) -> list[dict]:
    """Parse one meeting XML file into a list of speech (utterance) dicts."""
    try:
        tree = etree.parse(str(xml_path))
    except etree.XMLSyntaxError:
        return []

    root = tree.getroot()

    # File-level metadata
    file_id = root.attrib.get(XML_ID, xml_path.stem)
    ana_root = root.attrib.get("ana", "")
    # Subcorpus tag: #covid or #reference
    subcorpus = "covid" if "#covid" in ana_root else "reference" if "#reference" in ana_root else "unknown"

    header = root.find("tei:teiHeader", NS)
    text_elem = root.find("tei:text", NS)
    if header is None or text_elem is None:
        return []

    # Date
    date_elem = header.find(".//tei:settingDesc//tei:date", NS)
    date_str = date_elem.attrib.get("when") if date_elem is not None else None

    # Title (also identifies Upper/Lower house)
    title_elem = header.find(".//tei:titleStmt/tei:title[@type='main']", NS)
    title = title_elem.text if title_elem is not None and title_elem.text else ""

    # Determine house from filename (more reliable than title)
    if "tweedekamer" in xml_path.name.lower():
        house = "Lower"  # Tweede Kamer
    elif "eerstekamer" in xml_path.name.lower():
        house = "Upper"  # Eerste Kamer
    else:
        house = "Unknown"

    # Walk all utterances
    speeches = []
    for u in text_elem.findall(".//tei:u", NS):
        u_id = u.attrib.get(XML_ID, "")
        speaker_ref = u.attrib.get("who", "").lstrip("#")
        role_ana = u.attrib.get("ana", "")
        # role can be #chair, #regular, etc.
        role = role_ana.replace("#", "").strip() if role_ana else "unknown"

        # Concatenate all <seg> text in this utterance
        seg_texts = []
        for seg in u.findall("tei:seg", NS):
            seg_texts.append("".join(seg.itertext()))
        full_text = _clean_text(" ".join(seg_texts))

        # Skip empty utterances
        if not full_text:
            continue

        speeches.append({
            "speech_id": u_id,
            "file_id": file_id,
            "date": date_str,
            "year": int(date_str[:4]) if date_str else None,
            "house": house,
            "subcorpus": subcorpus,
            "speaker_id": speaker_ref,
            "role": role,
            "title": title,
            "text": full_text,
            "n_words": len(full_text.split()),
        })

    return speeches


# ----------------------------------------------------------------------------
# Build the full corpus DataFrame
# ----------------------------------------------------------------------------

def build_corpus_dataframe(
    corpus_root: Path,
    list_person_path: Path,
    list_org_path: Path,
    limit: int | None = None,
) -> pd.DataFrame:
    """Parse all meeting files into a single DataFrame, enriched with speaker
    and party metadata.

    Args:
        corpus_root: Path to ParlaMint-NL-en.TEI.ana/
        list_person_path: Path to ParlaMint-NL-listPerson.xml
        list_org_path:    Path to ParlaMint-NL-listOrg.xml
        limit: Optional cap on number of files (for quick testing)
    """
    # Load metadata
    print("Loading speaker metadata...")
    speakers = parse_speaker_metadata(list_person_path)
    print(f"  {len(speakers)} speakers")

    print("Loading party metadata...")
    parties = parse_party_metadata(list_org_path)
    print(f"  {len(parties)} parties")

    # Find all meeting XML files
    year_dirs = sorted([d for d in corpus_root.iterdir() if d.is_dir() and d.name.isdigit()])
    xml_files = []
    for d in year_dirs:
        xml_files.extend(sorted(d.glob("*.xml")))
    if limit:
        xml_files = xml_files[:limit]
    print(f"\nFound {len(xml_files)} meeting files. Parsing...")

    # Parse all files
    all_speeches = []
    for xml_path in tqdm(xml_files):
        all_speeches.extend(parse_meeting_file(xml_path))

    df = pd.DataFrame(all_speeches)
    print(f"\nTotal speeches: {len(df):,}")

    # Enrich with speaker name + party (at the date of the meeting)
    print("Resolving speaker → party at meeting date...")
    df["speaker_name"] = df["speaker_id"].map(
        lambda sid: speakers.get(sid, {}).get("name", "")
    )
    df["party_id"] = df.apply(
        lambda row: resolve_party_at_date(speakers.get(row["speaker_id"], {}), row["date"] or ""),
        axis=1,
    )
    df["party_abbr"] = df["party_id"].map(
        lambda pid: parties.get(pid, {}).get("abbr") if pid else None
    )

    return df