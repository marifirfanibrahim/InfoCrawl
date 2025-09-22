# ui_helpers.py
"""
smaller functions for various other files
1. text/file/call handling
2. highlights/colours
"""
from pathlib import Path
import json
import pandas as pd
from urllib.parse import urlparse
import re

# basic helpers
def s(val):
    # safe string (no NaN, None)
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    return str(val)

def join_meta(parts):
    # join meta fields with bullet
    clean = [s(p).strip() for p in parts]
    clean = [p for p in clean if p and p.lower() != "nan"]
    return " • ".join(clean)

def trim_source(src):
    # shorten source (remove www if url)
    txt = s(src).strip()
    if txt.startswith("http"):
        return urlparse(txt).netloc.replace("www.", "")
    return txt

# search helpers
def exact_mask(series: pd.Series, query: str) -> pd.Series:
    # exact word match mask
    if not query.strip():
        return series.astype(bool) & False
    pattern = rf"(?i)(?<!\w){re.escape(query)}(?!\w)"
    return series.astype(str).str.contains(pattern, na=False, regex=True)

# title color helpers 
def get_title_color(srcfile: str) -> str:
    # pick color based on file name
    src = srcfile.lower()
    if "search" in src:
        return "green"
    if "news_id" in src:
        return "gold"
    return "red"

# json helpers 
def load_preds_json(path: Path):
    # load json if exists else {}
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

# entity color + highlight 
def build_colors(labels: list[str]) -> dict[str, str]:
    # assign colors from palette
    palette = [
        "#b30000", "#006400", "#b36b00", "#00008b", "#8b4513",
        "#4b0082", "#008b8b", "#8b008b", "#556b2f", "#8b0000",
        "#2f4f4f", "#483d8b", "#800000", "#191970", "#ff8c00",
        "#228b22", "#9932cc", "#cd5c5c", "#4682b4", "#708090"
    ]
    return {lbl: palette[i % len(palette)] for i, lbl in enumerate(labels)}

def highlight_ents(txt: str, ents: list[dict], colors: dict[str, str]) -> str:
    # highlight entities with bg color
    safe_txt = s(txt).replace("<", "&lt;").replace(">", "&gt;")
    if not ents:
        return safe_txt

    # sort by start pos
    ents_sorted = sorted(ents, key=lambda e: (int(e.get("start", 0)), -int(e.get("end", 0))))
    out = []
    pos = 0
    n = len(safe_txt)

    for e in ents_sorted:
        start = max(0, min(int(e.get("start", 0)), n))
        end = max(0, min(int(e.get("end", 0)), n))
        if start < pos or start >= end:
            continue
        out.append(safe_txt[pos:start])
        snippet = safe_txt[start:end]
        color = colors.get(e.get("label", ""), "#f58231")
        out.append(
            f'<span style="background:{color};padding:0.1em;border-radius:3px;" '
            f'title="{e.get("label","")}">{snippet}</span>'
        )
        pos = end

    out.append(safe_txt[pos:])
    return "".join(out)

# prediction helpers 
def needs_prediction(path: Path) -> bool:
    # check if json missing or empty
    if not path.exists():
        return True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return True
    if isinstance(data, dict):
        return not bool(data)
    if isinstance(data, list):
        return not bool(data)
    return True
