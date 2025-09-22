# pipeline/scraper_full.py
import requests
import pandas as pd
from bs4 import BeautifulSoup
from lxml import html
import random, time
from requests.exceptions import RequestException
from datetime import datetime
from pathlib import Path

# folder to save csv
save_folder = Path("data/raw/news_id")
save_folder.mkdir(parents=True, exist_ok=True)

# settings for Utusan
UTUSAN = {
    "name": "Utusan Malaysia",
    "base_url": "https://www.utusan.com.my",
    "id_param": "p",
    "id_range": (100000, 900000),
    "num_ids_to_check": 100,
    "content_xpath": '//*[@id="content"]/div/div/section[3]/div/div/div[1]/div/div/div[5]/div',
    "title_selectors": ["h1.jeg_post_title", "h1.entry-title", "title"],
    "date_selectors": [
        ".jeg_meta_date a", "time.jeg_date", "span.jeg_date", ".date",
        "time.entry-date", "span.posted-on",
        "meta[property='article:published_time']", "meta[name='date']"
    ],
    "category_selectors": [
        ".jeg_meta_category a", "a.jeg_meta_category", ".category",
        "a[rel='category tag']", ".post-categories a", "span.cat-links a",
        "meta[property='article:section']"
    ]
}

# get current date/time
def get_now():
    now = datetime.now()
    return {"date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M:%S")}

# grab article text
def get_text(soup: BeautifulSoup, tree: html.HtmlElement, settings: dict) -> str:
    txt = ""
    try:
        box = tree.xpath(settings["content_xpath"])
        if box:
            ps = box[0].xpath(".//p")
            for p in ps:
                bits = p.xpath(".//text()")
                para = " ".join(t.strip() for t in bits if t.strip())
                if para:
                    txt += para + "\n\n"
    except Exception as e:
        print("xpath failed:", e)

    if not txt.strip():
        fallbacks = ['.jeg_post_content', '.entry-content', '.article-content', '.post-content', '.content']
        for sel in fallbacks:
            try:
                block = soup.select_one(sel)
                if block:
                    for p in block.find_all("p"):
                        para = p.get_text(strip=True)
                        if para:
                            txt += para + "\n\n"
                    if txt.strip():
                        break
            except Exception:
                continue
    return txt.strip()

# main scrape
def scrape_utusan(settings: dict, num_articles: int | None = None):
    if num_articles:
        settings = {**settings, "num_ids_to_check": num_articles}

    now_info = get_now()
    articles = []
    found = 0
    skipped = 0

    ids = random.sample(range(settings["id_range"][0], settings["id_range"][1]), settings["num_ids_to_check"])
    print("trying", settings["num_ids_to_check"], "random IDs from", settings["name"])

    for aid in ids:
        try:
            url = f"{settings['base_url']}/?{settings['id_param']}={aid}"
            r = requests.get(url, timeout=20)
            r.raise_for_status()

            if r.url.rstrip("/") == settings["base_url"].rstrip("/"):
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            tree = html.fromstring(r.content)

            # title
            title = ""
            for sel in settings["title_selectors"]:
                try:
                    el = soup.select_one(sel)
                    if el:
                        t = el.get_text().strip()
                        if t and t != settings["name"]:
                            title = t
                            break
                except Exception:
                    continue
            if not title:
                continue

            # date
            pub_date = ""
            for sel in settings["date_selectors"]:
                try:
                    if sel.startswith("meta["):
                        el = soup.select_one(sel)
                        if el and el.has_attr("content"):
                            val = el["content"]
                            pub_date = str(val).strip()
                            if "T" in pub_date:
                                pub_date = pub_date.split("T")[0]
                            if pub_date:
                                break
                    else:
                        el = soup.select_one(sel)
                        if el:
                            val = el.get_text()
                            pub_date = str(val).strip()
                            if pub_date:
                                break
                except Exception:
                    continue

            # category
            cat = ""
            for sel in settings["category_selectors"]:
                try:
                    if sel.startswith("meta["):
                        el = soup.select_one(sel)
                        if el and el.has_attr("content"):
                            val = el["content"]
                            cat = str(val).strip()
                            if cat:
                                break
                    else:
                        el = soup.select_one(sel)
                        if el:
                            val = el.get_text()
                            cat = str(val).strip()
                            if cat:
                                break
                except Exception:
                    continue

            # content
            content = get_text(soup, tree, settings)
            if not content:
                skipped += 1
                print("skip ID", aid, "- no content")
                continue

            # summary
            last = max(content.rfind("."), content.rfind("!"), content.rfind("?"))
            summary = content[:last+1] if last != -1 else content

            articles.append({
                "News_Source": settings["name"],
                "Title": title,
                "Source_URL": r.url,
                "Publish_Date": pub_date,
                "Category": cat,
                "Summary": summary,
                "Scrape_Date": now_info["date"]
            })

            found += 1
            print("found:", aid, "-", title[:50], "...")
            time.sleep(random.uniform(1.0, 2.5))

        except RequestException as e:
            print("request failed for", aid, e)
            time.sleep(3)
        except Exception as e:
            print("error with", aid, e)
            time.sleep(1.5)

    df = pd.DataFrame(articles) if articles else pd.DataFrame()
    return {"dataframe": df, "articles_found": found, "articles_excluded": skipped}

# run directly
if __name__ == "__main__":
    res = scrape_utusan(UTUSAN)
    if not res["dataframe"].empty:
        print("\nscraped", res["articles_found"], "articles")
        fname = save_folder / f"malay_news_{get_now()['date']}.csv"
        res["dataframe"].to_csv(fname, index=False)
        print("saved to", fname)
    else:
        print("no articles found")
