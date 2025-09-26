# pipeline/predict.py
"""
label prediction
1. set labels
2. load model (urchade/gliner_multi)
3. get csv files
4. predict individual and overall summaries (txt files)
5. predict news feed, full news, and search data (csv files)
6. save predictions as *.json files into data/processed
"""
from pathlib import Path
import json
import time
import pandas as pd
from collections import defaultdict
from gliner import GLiNER
import hashlib
import re

# config
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# folders
data_folder = Path("data")
out_folder = data_folder / "output"
indiv_summaries = out_folder / "summary_individual"
proc_folder = data_folder / "processed"
news_feed_folder = data_folder / "raw" / "news_feed"
news_id_folder = data_folder / "raw" / "news_id"
search_folder = data_folder / "raw" / "search"

proc_folder.mkdir(parents=True, exist_ok=True)

# labels
labels = [
    "GPE", "PERSON", "ORG", "FAC", "MONEY", "NORP", "LOC", "PRODUCT", "EVENT",
    "PERCENT", "WORK_OF_ART", "TIME", "ORDINAL", "CARDINAL", "QUANTITY", "LAW"
]

_model = None

def get_model():
    global _model
    if _model is None:
        print("Loading GLiNER model...")
        _model = GLiNER.from_pretrained("model/gliner_multi", local_files_only=True)
        print("Model loaded successfully!")
    return _model

# helpers
def safe_str(x) -> str:
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x)

def clean_name(txt: str, max_len: int = 50) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", txt).strip("_")[:max_len]

def read_all_csvs(folder: Path) -> pd.DataFrame:
    files = sorted(folder.glob("*.csv"))
    if not files:
        return pd.DataFrame()
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            df["__srcfile__"] = f.name
            dfs.append(df)
        except Exception:
            continue
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def deduplicate_entities(entities: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for ent in entities:
        key = (ent.get("label"), ent.get("text"), ent.get("start"), ent.get("end"))
        if key not in seen:
            seen.add(key)
            unique.append(ent)
    return unique

def file_hash(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

# batch prediction
def predict_entities_in_chunks(texts, batch_size=32):
    model = get_model()
    results = []
    total = len(texts)
    start_time = time.time()
    for i in range(0, total, batch_size):
        batch = texts[i:i+batch_size]
        try:
            out = model.predict_entities(batch, labels=labels, threshold=0.5)
        except Exception:
            out = [model.predict_entities(t, labels=labels, threshold=0.5) for t in batch]
        results.extend(out)
        elapsed = time.time() - start_time
        done = i + len(batch)
        print(f"Processed {done}/{total} rows in {elapsed:.1f}s")
    return results

# individual summaries
def run_individual(query: str = "") -> Path:
    safe_q = clean_name(query) if query else "default"
    out_file = proc_folder / f"predictions_individual_{safe_q}.json"

    print(f"Running individual summaries prediction for query '{query}'...")
    texts, keys = [], []
    for f in sorted(indiv_summaries.glob("*.txt")):
        try:
            txt = f.read_text(encoding="utf-8")
        except Exception:
            txt = f.read_text(errors="ignore")
        if txt.strip():
            texts.append(txt)
            keys.append(f.name)

    preds = predict_entities_in_chunks(texts)
    res = {k: deduplicate_entities(p) for k, p in zip(keys, preds)}

    new_content = json.dumps(res, ensure_ascii=False, indent=2)
    new_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()

    if out_file.exists():
        old_hash = file_hash(out_file)
        if old_hash == new_hash:
            print(f"Skipping individual summaries — {out_file} already up to date")
            return out_file

    out_file.write_text(new_content, encoding="utf-8")
    print(f"Individual predictions saved to {out_file}")
    return out_file

# overall summary
def run_overall(query: str = "") -> Path | None:
    safe_q = clean_name(query) if query else "default"
    out_file = proc_folder / f"predictions_overall_{safe_q}.json"

    print(f"Running overall summary prediction for query '{query}'...")
    sum_file = out_folder / f"summary_overall_{safe_q}.txt"
    if not sum_file.exists():
        print("Overall summary file not found")
        return None

    try:
        txt = sum_file.read_text(encoding="utf-8")
    except Exception:
        txt = sum_file.read_text(errors="ignore")

    if not txt.strip():
        print("Overall summary is empty")
        return None

    ents = predict_entities_in_chunks([txt])[0]
    ents = deduplicate_entities(ents)

    new_content = json.dumps({"file": sum_file.name, "entities": ents}, ensure_ascii=False, indent=2)
    new_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()

    if out_file.exists():
        old_hash = file_hash(out_file)
        if old_hash == new_hash:
            print(f"Skipping overall summary — {out_file} already up to date")
            return out_file

    out_file.write_text(new_content, encoding="utf-8")
    print(f"Overall predictions saved to {out_file}")
    return out_file

# predict csvs
def run_csv(folder: Path, out_name: str, text_cols: list[str], batch_size: int = 32, query: str = "") -> Path:
    safe_q = clean_name(query) if query else ""
    # only add suffix if a query is provided
    suffix = f"_{safe_q}" if safe_q else ""
    out_file = proc_folder / f"predictions_{out_name}{suffix}.json"

    # load existing predictions if available
    if out_file.exists():
        try:
            existing = json.loads(out_file.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    else:
        existing = {}

    msg = f"Running {out_name} prediction" + (f" for query '{query}'..." if query else "...")
    print(msg)

    df = read_all_csvs(folder)
    if df.empty:
        print(f"No {out_name} data found")
        out_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_file

    texts, keys, starts = [], [], []
    for i, row in df.iterrows():
        txt = ""
        for col in text_cols:
            txt = safe_str(row.get(col))
            if txt:
                break
        if not txt:
            continue

        key = safe_str(row.get("Source_URL")).strip()
        if not key:
            key = f"{safe_str(row.get('__srcfile__'))}:{i}"

        if key in existing and existing.get(key):
            continue

        start = 0
        while start < len(txt):
            end = min(start + CHUNK_SIZE, len(txt))
            chunk = txt[start:end]
            texts.append(chunk)
            keys.append(f"{key}__part{len(starts)}")
            starts.append(start)
            start += CHUNK_SIZE - CHUNK_OVERLAP

    if texts:
        preds = predict_entities_in_chunks(texts, batch_size=batch_size)

        merged = defaultdict(list)
        for k, p, cstart in zip(keys, preds, starts):
            doc, _, _ = k.partition("__part")
            for ent in p:
                try:
                    ent["start"] = int(ent.get("start", 0)) + cstart
                    ent["end"] = int(ent.get("end", 0)) + cstart
                except Exception:
                    pass
                merged[doc].append(ent)

        # deduplicate and merge
        for doc, ents in merged.items():
            combined = (existing.get(doc, []) or []) + ents
            existing[doc] = deduplicate_entities(combined)

    new_content = json.dumps(existing, ensure_ascii=False, indent=2)
    new_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()

    if out_file.exists():
        old_hash = file_hash(out_file)
        if old_hash == new_hash:
            print(f"Skipping {out_name} — {out_file} already up to date")
            return out_file

    out_file.write_text(new_content, encoding="utf-8")
    print(f"{out_name.capitalize()} predictions saved to {out_file}")
    return out_file

# respective runs
def run_news(): 
    return run_csv(news_feed_folder, "newsfeed", ["Summary", "Title"])

def run_fullnews(): 
    return run_csv(news_id_folder, "fullnews", ["Summary", "Title"])

def run_search(query: str = ""): 
    return run_csv(search_folder, "search", ["Content", "Title"], query=query)
