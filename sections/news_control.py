# sections/news_control.py
"""
buttons to fetch news
1. news feed button
2. full news (id) button
"""
import streamlit as st
import subprocess
from pipeline import predict as pred_mod

def render_news_controls():
    st.subheader("Get News")

    # make 2 cols for buttons
    col1, col2 = st.columns(2)

    # button for news feed
    with col1:
        if st.button("Get News Feed"):
            with st.status("Scraping news feed...", expanded=True) as box:
                # run quick scraper
                subprocess.run(["python", "pipeline/scraper_quick.py"], check=True)

                # run preds
                box.write("Predicting labels on news feed...")
                pred_mod.run_news()

                box.success("Feed scraped & labeled")

    # button for full news
    with col2:
        if st.button("Get News Articles"):
            with st.status("Scraping news articles...", expanded=True) as box:
                # run full scraper
                subprocess.run(["python", "pipeline/scraper_full.py"], check=True)

                # run preds
                box.write("Predicting labels on full news...")
                pred_mod.run_fullnews()

                box.success("Full news scraped & labeled")
