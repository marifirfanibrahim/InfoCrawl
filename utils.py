# utils.py
"""
cache handling
"""
from pathlib import Path
import json
from functools import lru_cache

# main data folder
data_folder = Path("data")

# cache folder inside data
cache_folder = data_folder / ".cache"
cache_folder.mkdir(parents=True, exist_ok=True)

# write to cache
def cache_write(fname: str, obj):
    # save dict/list as json, else just text
    fpath = cache_folder / fname
    if isinstance(obj, (dict, list)):
        fpath.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    else:
        fpath.write_text(str(obj), encoding="utf-8")
    return fpath

# read json from cache
def cache_read_json(fname: str):
    fpath = cache_folder / fname
    if fpath.exists():
        return json.loads(fpath.read_text(encoding="utf-8"))
    return None

# get all links_*.txt files
@lru_cache(maxsize=32)
def get_links_files():
    crawl_folder = data_folder / "crawl"
    return sorted(crawl_folder.glob("links_*.txt"))
