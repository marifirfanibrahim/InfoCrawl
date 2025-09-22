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
import pandas as pd
from gliner import GLiNER

# folders
data_folder = Path("data")
out_folder = data_folder / "output"
indiv_summaries = out_folder / "summary_individual"
proc_folder = data_folder / "processed"
news_feed_folder = data_folder / "raw" / "news_feed"
news_id_folder = data_folder / "raw" / "news_id"
search_folder = data_folder / "raw" / "search"

proc_folder.mkdir(parents=True, exist_ok=True)

# labels + model
labels = [
    "GPE", "PERSON", "ORG", "FAC", "MONEY", "NORP", "LOC", "PRODUCT", "EVENT",
    "PERCENT", "WORK_OF_ART", "TIME", "ORDINAL", "CARDINAL", "QUANTITY", "LAW"
]

model = GLiNER.from_pretrained("urchade/gliner_multi")

def predict_entities(txt: str):
    txt = (txt or "").strip()
    if not txt:
        return []
    return model.predict_entities(txt, labels=labels, threshold=0.5)

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

# individual summaries
def run_individual() -> Path:
    out_file = proc_folder / "predictions_individual.json"
    res = {}
    for f in sorted(indiv_summaries.glob("*.txt")):
        try:
            txt = f.read_text(encoding="utf-8")
        except Exception:
            txt = f.read_text(errors="ignore")
        res[f.name] = predict_entities(txt)
    out_file.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_file

# overall summary
def run_overall() -> Path | None:
    sum_file = out_folder / "summary_overall.txt"
    if not sum_file.exists():
        return None
    try:
        txt = sum_file.read_text(encoding="utf-8")
    except Exception:
        txt = sum_file.read_text(errors="ignore")
    ents = predict_entities(txt)
    out_file = proc_folder / "predictions_overall.json"
    out_file.write_text(
        json.dumps({"file": sum_file.name, "entities": ents}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return out_file

# news feed csvs
def run_news() -> Path:
    df = read_all_csvs(news_feed_folder)
    out_file = proc_folder / "predictions_newsfeed.json"
    if df.empty:
        out_file.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_file

    preds = {}
    for i, row in df.iterrows():
        title = safe_str(row.get("Title"))
        summ = safe_str(row.get("Summary"))
        txt = summ if summ else title
        if not txt:
            continue
        key = safe_str(row.get("Source_URL")).strip()
        if not key:
            key = f"{safe_str(row.get('__srcfile__'))}:{safe_str(i)}"
        preds[key] = predict_entities(txt)

    out_file.write_text(json.dumps(preds, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_file

# full news csvs
def run_fullnews() -> Path:
    df = read_all_csvs(news_id_folder)
    out_file = proc_folder / "predictions_fullnews.json"
    if df.empty:
        out_file.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_file

    preds = {}
    for i, row in df.iterrows():
        title = safe_str(row.get("Title"))
        summ = safe_str(row.get("Summary"))
        txt = summ if summ else title
        if not txt:
            continue
        key = safe_str(row.get("Source_URL")).strip()
        if not key:
            key = f"{safe_str(row.get('__srcfile__'))}:{safe_str(i)}"
        preds[key] = predict_entities(txt)

    out_file.write_text(json.dumps(preds, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_file

# search csvs
def run_search() -> Path:
    df = read_all_csvs(search_folder)
    out_file = proc_folder / "predictions_search.json"
    if df.empty:
        out_file.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_file

    preds = {}
    for i, row in df.iterrows():
        content = safe_str(row.get("Content"))
        title = safe_str(row.get("Title"))
        txt = content if content else title
        if not txt:
            continue
        key = safe_str(row.get("Source_URL")).strip()
        if not key:
            key = f"{safe_str(row.get('__srcfile__'))}:{safe_str(i)}"
        preds[key] = predict_entities(txt)

    out_file.write_text(json.dumps(preds, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_file

if __name__ == "__main__":
    run_individual()
    run_overall()
    run_news()
    run_fullnews()
    run_search()
