# pipeline/compile.py
"""
compile search data into a single txt file
1. get all csv files in data/raw/search
2. get only content column
3. save as compiled_<query>.txt into data/processed
"""
from pathlib import Path
import pandas as pd

# raw csv file location
raw_folder = Path("data/raw/search")

# compiled file location
processed_folder = Path("data/processed")
processed_folder.mkdir(parents=True, exist_ok=True)

def run(query: str = "", output_name: str | None = None) -> Path:
    texts = []  # keep all the text here

    # get all csv files and sort them
    csvs = sorted(raw_folder.glob("*.csv"))

    for f in csvs:
        try:
            df = pd.read_csv(f)
        except Exception as e:
            print("could not read", f, e)
            continue

        if "Content" not in df.columns:
            print("no Content column in", f)
            continue

        for i, row in df.iterrows():
            title = row.get("Title", f"row{i}")
            content = str(row.get("Content", "")).strip()
            if not content:
                continue
            texts.append(f"# {title}\n\n{content}\n\n---\n")

    final = "\n".join(texts) if texts else "# Empty\n"

    # build output filename
    if output_name:
        out_file = processed_folder / output_name
    else:
        safe_q = "".join(c if c.isalnum() else "_" for c in query) if query else "compiled"
        out_file = processed_folder / f"compiled_{safe_q}.txt"

    out_file.write_text(final, encoding="utf-8")
    return out_file

if __name__ == "__main__":
    print(run(query="maybank"))
