# pipeline/compile.py
"""
compile search data into a single txt file
1. get all csv files in data/raw/search
2. get only content column
3. save as compiled.txt into data/processed
"""
from pathlib import Path
import pandas as pd

# raw csv file location
raw_folder = Path("data/raw/search")

# compiled file location
processed_folder = Path("data/processed")
processed_folder.mkdir(parents=True, exist_ok=True)

def run(output_name="compiled.txt"):
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
            # get title if exists, else just row number
            title = row.get("Title", f"row{i}")
            content = str(row.get("Content", "")).strip()
            if content == "":
                continue
            # add title, then content, then separator
            texts.append(f"# {title}\n\n{content}\n\n---\n")

    # if nothing was added, just say empty
    if texts:
        final = "\n".join(texts)
    else:
        final = "# Empty\n"

    # save the file
    out_path = processed_folder / output_name
    out_path.write_text(final, encoding="utf-8")

    return out_path

if __name__ == "__main__":
    print(run())
