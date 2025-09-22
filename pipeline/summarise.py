# pipeline/summarise.py
"""
summarise search csv
1. load ollama (llama3.2)
2. set prompt
3. summarise from individual data (csv files)
4. summarise from compiled data (txt file)
4. save as txt files into data/output
"""
from pathlib import Path
from tqdm import tqdm
import pandas as pd
import subprocess

# folders
raw_folder = Path("data/raw/search")
out_folder = Path("data/output")
out_indiv = out_folder / "summary_individual"

# make sure folders exist
out_folder.mkdir(parents=True, exist_ok=True)
out_indiv.mkdir(parents=True, exist_ok=True)

# call ollama
def ollama_generate(prompt: str, model: str = "llama3.2") -> str:
    try:
        res = subprocess.run(
            ["ollama", "run", model],
            input=prompt.encode("utf-8"),
            capture_output=True,
            check=True
        )
        return res.stdout.decode("utf-8").strip()
    except Exception as e:
        print("ollama call failed:", e)
        return ""

# summarise
def summarise(txt: str, query: str = "") -> str:
    if not txt.strip():
        return ""

    if query:
        prompt = (
            f"Write a concise summary of the following article. "
            f"The summary must start with the exact '{query}' "
            f"The summary must clearly mention the exact '{query}' at least once "
            f"and explain how the article relates to it. "
            f"Do not include any introductory phrases like "
            f"'Here is the summary' or 'Berikut adalah ringkasan artikel'.\n\n{txt}"
        )
    else:
        prompt = (
            f"Write a concise summary of the following article. "
            f"Do not include any introductory phrases like "
            f"'Here is the summary' or 'Berikut adalah ringkasan artikel'.\n\n{txt}"
        )

    summary = ollama_generate(prompt, model="llama3.2").strip()

    # make sure query is mentioned
    if query and query.lower() not in summary.lower():
        summary = f"{summary} This article is related to {query}."

    # remove unwanted boilerplate
    for bad in [
        "Berikut adalah ringkasan artikel:",
        "Here is the summary of the article:",
        "Ringkasan artikel:"
    ]:
        if summary.lower().startswith(bad.lower()):
            summary = summary[len(bad):].strip()

    return summary

# summarise each article
def run_individual(query: str = ""):
    csvs = sorted(raw_folder.glob("*.csv"))
    if not csvs:
        print("no csv files in data/raw/search/")
        return

    for f in csvs:
        try:
            df = pd.read_csv(f)
        except Exception as e:
            print("could not read", f, e)
            continue

        # check for content col
        content_col = next((c for c in df.columns if c.lower() == "content"), None)
        if not content_col:
            print("no 'Content' col in", f)
            continue

        for idx, row in tqdm(df.iterrows(), total=len(df), desc=f"summarising {f.name}"):
            title = str(row.get("Title", f"row{idx}"))
            content = str(row.get(content_col, "")).strip()
            if not content:
                continue

            summary = summarise(content, query=query)
            if not summary:
                continue

            safe_title = "".join(c if c.isalnum() else "_" for c in title)[:40]
            out_path = out_indiv / f"{safe_title}_{idx}.txt"
            try:
                out_path.write_text(summary, encoding="utf-8")
            except Exception as e:
                print("could not write summary for", title, e)

# summarise compiled file
def run_overall(query: str = "") -> Path | None:
    compiled = Path("data/processed/compiled.txt")
    if compiled.exists():
        txt = compiled.read_text(encoding="utf-8", errors="ignore")
        summary = summarise(txt, query=query)
        if not summary:
            return None
        out_path = out_folder / "summary_overall.txt"
        try:
            out_path.write_text(summary, encoding="utf-8")
            return out_path
        except Exception as e:
            print("could not write overall summary:", e)
            return None
    else:
        print("no compiled.txt in data/processed/")
    return None

# run both
if __name__ == "__main__":
    q = "maybank"
    run_individual(query=q)
    run_overall(query=q)
