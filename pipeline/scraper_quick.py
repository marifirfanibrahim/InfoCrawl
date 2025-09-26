# pipeline/scraper_quick.py
"""
scrape news based on news feed
1. set links
2. set scrape
3. set parse
4. scrape and parse
5. save as malay_news_*.csv file into data/raw/news_feed
"""
import requests
import pandas as pd
import xml.etree.ElementTree as ET
import re, time
from datetime import datetime
from pathlib import Path

# folder to save csv
save_folder = Path("data/raw/news_feed")
save_folder.mkdir(parents=True, exist_ok=True)

# rss feeds
news = [
    {"name": "Utusan Malaysia", "url": "https://www.utusan.com.my/feed/"},
    {"name": "Berita Harian", "url": "https://www.bharian.com.my/feed/"},
    {"name": "Harian Metro", "url": "https://www.hmetro.com.my/feed/"},
    {"name": "Kosmo", "url": "https://www.kosmo.com.my/feed/"},
    {"name": "Astro Awani", "url": "https://www.astroawani.com/feeds/posts/default?alt=rss"}
]

# get date/time now
def get_now():
    now = datetime.now()
    return {"date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M:%S")}

# clean up summary text
def clean_summary(txt):
    if not txt:
        return "No summary available"
    txt = re.sub(r'<[^>]+>', '', txt)  # remove html tags
    txt = re.sub(r'<!\[CDATA\[|\]\]>', '', txt)  # remove cdata
    txt = re.sub(r'\b(img|width|height)="\d+"', '', txt)  # remove img attrs
    txt = re.sub(r'The post .* appeared first on .*\.', '', txt)
    txt = re.sub(r'\.\.\.\s*(Read More).*', '', txt, flags=re.IGNORECASE)
    txt = txt.strip()
    # cut after last sentence
    last = max(txt.rfind("."), txt.rfind("!"), txt.rfind("?"))
    if last != -1:
        txt = txt[:last+1]
    return txt

# scrape all feeds
def scrape_news(sources=None):
    if sources is None:
        sources = news

    now_info = get_now()
    articles = []
    failed = []

    for src in sources:
        try:
            print("fetching from", src["name"])
            r = requests.get(src["url"], timeout=10)
            r.raise_for_status()
            content = r.content

            root = None
            try:
                root = ET.fromstring(content)
            except ET.ParseError:
                for enc in ["utf-8"]:
                    try:
                        decoded = content.decode(enc)
                        root = ET.fromstring(decoded)
                        break
                    except (UnicodeDecodeError, ET.ParseError):
                        continue

            if root is None:
                print("could not parse xml for", src["name"])
                failed.append(src["name"])
                continue

            for item in root.findall(".//item"):
                try:
                    title_el = item.find("title")
                    title = title_el.text.strip() if title_el is not None and title_el.text else "No Title"

                    link_el = item.find("link")
                    link = link_el.text.strip() if link_el is not None and link_el.text else ""

                    pub_date = None
                    for tag in ["pubDate", "dc:date", "date"]:
                        d = item.find(tag)
                        if d is not None and d.text:
                            pub_date = d.text.strip()
                            break

                    cat = None
                    for tag in ["category", "dc:subject"]:
                        c = item.find(tag)
                        if c is not None and c.text:
                            cat = c.text.strip()
                            break

                    summary = ""
                    for tag in ["description", "content:encoded", "content"]:
                        s = item.find(tag)
                        if s is not None and s.text:
                            summary = s.text
                            break

                    clean_sum = clean_summary(summary)

                    articles.append({
                        "News_Source": src["name"],
                        "Title": title,
                        "Source_URL": link,
                        "Publish_Date": pub_date,
                        "Category": cat,
                        "Summary": clean_sum,
                        "Scrape_Date": now_info["date"]
                    })
                except Exception as e:
                    print("error processing item from", src["name"], e)

            print("done with", src["name"])
            time.sleep(1)

        except Exception as e:
            print("error with", src["name"], e)
            failed.append(src["name"])

    df = pd.DataFrame(articles) if articles else pd.DataFrame()
    return {"dataframe": df, "failed_sources": failed}

if __name__ == "__main__":
    res = scrape_news()
    if not res["dataframe"].empty:
        print("\nscraped", len(res["dataframe"]), "articles")
        fname = save_folder / f"malay_news_{get_now()['date']}.csv"
        res["dataframe"].to_csv(fname, index=False)
        print("saved to", fname)
    else:
        print("no articles scraped")
