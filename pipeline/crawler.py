# pipeline/crawler.py
"""
crawl and parse for links (pending update - selenium error if tried on other links)
1. set template links
2. set parsing for each template (beautifulsoup)
3. set duckduckgo crawl (selenium)
4. save as search_*.csv into data/raw/search
"""
from urllib.parse import quote_plus
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
import time, requests
from bs4 import BeautifulSoup

# path to edge driver
edge_driver = r"C:\WebDrivers\msedgedriver.exe"

# folder to save stuff
crawl_folder = Path("data/crawl")
crawl_folder.mkdir(parents=True, exist_ok=True)

# make search urls for different sites
def build_search_pages(text: str) -> dict[str, str]:
    q = text.strip()
    plus_q = quote_plus(q)
    under_q = q.replace(" ", "_")
    percent_q = q.replace(" ", "%20")

    return {
        "wikipedia": f"https://ms.wikipedia.org/wiki/{under_q}",
        "sinar": f"https://www.sinarharian.com.my/carian?query={plus_q}",
        "hmetro": f"https://www.hmetro.com.my/search?keywords={under_q}",
        "astroawani": f"https://www.astroawani.com/search?keywords={percent_q}",    
        "gempak": f"https://www.gempak.com/search?keywords={percent_q}",
        "prpm": f"https://prpm.dbp.gov.my/Cari1?keyword={plus_q}",
        "pnm": f"https://www.pnm.gov.my/index.php/pages/module_search?search={plus_q}"
    }

# get article links from html
def extract_article_links(url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []

    if "sinarharian.com.my" in url:
        for a in soup.select("div.article-title a"):
            h = a.get("href")
            if h and h.startswith("http"):
                links.append(h)

    elif "hmetro.com.my" in url:
        for a in soup.select("#main div.col h3 a, #main div.col div.content h3 a"):
            h = a.get("href")
            if h:
                links.append(h)

    elif "astroawani.com" in url:
        for a in soup.select("div.Article_title__agIb8 a"):
            h = a.get("href")
            if h:
                if h.startswith("/"):
                    h = "https://www.astroawani.com" + h
                links.append(h)

    elif "gempak.com" in url:
        for h5 in soup.select("h5"):
            a = h5.find("a")
            if a:
                h = a.get("href")
                if h:
                    links.append(h)

    else:
        # wikipedia, prpm, pnm just use the url itself
        links.append(url)

    return links

# duckduckgo
def duckduckgo_links(query: str, max_results: int = 10, delay: float = 2.0) -> list[str]:
    opts = Options()
    opts.add_argument("--headless")
    service = Service(edge_driver)
    driver = webdriver.Edge(service=service, options=opts)

    urls = []
    try:
        driver.get("https://html.duckduckgo.com/html/")
        box = driver.find_element(By.NAME, "q")
        box.send_keys(query)
        box.submit()
        time.sleep(delay)

        results = driver.find_elements(By.CSS_SELECTOR, "div.result a.result__a")
        for r in results[:max_results]:
            h = r.get_attribute("href")
            if h:
                urls.append(h)
    finally:
        driver.quit()

    return urls

# save all links into a file
def save_links(links: list[str]) -> Path:
    f = crawl_folder / "link_list.txt"
    f.write_text("\n".join(links), encoding="utf-8")
    return f

# main function
def run(search_text: str) -> Path:
    pages = build_search_pages(search_text)
    all_links = []

    for name, url in pages.items():
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            links = extract_article_links(url, r.text)
            all_links.extend(links)
        except Exception as e:
            print("failed to fetch", url, e)

    # add duckduckgo links too
    all_links.extend(duckduckgo_links(search_text))

    return save_links(all_links)
