# pipeline/scraper_search.py
"""
scrape news based on id
1. set scrape
2. set parse
3. scrape and parse
4. save as search_*.csv file into data/raw/news_search (work on the naming)
"""
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import time, random, re

# folders
crawl_folder = Path("data/crawl")
save_folder = Path("data/raw/search")
proc_folder = Path("data/processed")
last_query_file = proc_folder / "last_query.txt"

# make sure folders exist
save_folder.mkdir(parents=True, exist_ok=True)
proc_folder.mkdir(parents=True, exist_ok=True)

# load links from file
def load_links() -> list[str]:
    f = crawl_folder / "link_list.txt"
    if not f.exists():
        raise FileNotFoundError("no links file found")
    return f.read_text(encoding="utf-8").splitlines()

# clean filename part
def clean_name(txt: str, max_len: int = 50) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", txt).strip("_")[:max_len] or "default"

# get last query
def get_last_query() -> str:
    if last_query_file.exists():
        q = last_query_file.read_text(encoding="utf-8").strip()
        if q:
            return q
    return "default"

# scrape one page
def scrape_page(url: str) -> dict | None:
    try:
        headers = {
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Mozilla/5.0 (X11; Linux x86_64)"
            ])
        }
        r = requests.get(url, timeout=20, headers=headers)
        r.raise_for_status()
    except Exception as e:
        print("fail to fetch", url, e)
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # title
    title = ""
    for sel in ["h1", "title"]:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(strip=True)
            break

    # date
    pub_date = ""
    for sel in ["time", ".date", "span.posted-on",
                "meta[property='article:published_time']",
                "meta[name='date']"]:
        el = soup.select_one(sel)
        if el:
            pub_date = el.get("content", "").strip() if el.has_attr("content") else el.get_text(strip=True)
            if pub_date:
                break

    # category
    cat = ""
    for sel in [".category", "a[rel='category tag']", "meta[property='article:section']"]:
        el = soup.select_one(sel)
        if el:
            cat = el.get("content", "").strip() if el.has_attr("content") else el.get_text(strip=True)
            if cat:
                break

    # content
    content = ""
    for sel in [".article-content", ".entry-content", ".post-content", "article", ".content",
                "#mw-content-text", "#\\31"]:
        block = soup.select_one(sel)
        if block:
            ps = [p.get_text(strip=True) for p in block.find_all("p")]
            if not ps:
                txt = block.get_text(" ", strip=True)
                if txt:
                    content = txt
                    break
            else:
                content = "\n\n".join(p for p in ps if p)
                if content:
                    break

    if not content:
        print("no content from", url)
        return None

    return {
        "Title": title,
        "Source_URL": url,
        "Publish_Date": pub_date,
        "Category": cat,
        "Content": content
    }

# main run
def run_scraper():
    query = get_last_query()
    links = load_links()
    print("loaded", len(links), "links")

    articles = []
    today = datetime.now().strftime("%Y-%m-%d")

    for i, url in enumerate(links, start=1):
        data = scrape_page(url)
        if data:
            articles.append(data)
        time.sleep(random.uniform(1.0, 2.5))

    df = pd.DataFrame(articles)
    if not df.empty:
        safe_q = clean_name(query)
        out_path = save_folder / f"search_{safe_q}_{today}.csv"
        df.to_csv(out_path, index=False, encoding="utf-8")
        print("saved", len(df), "articles to", out_path)
    else:
        print("no articles scraped")

if __name__ == "__main__":
    run_scraper()
    