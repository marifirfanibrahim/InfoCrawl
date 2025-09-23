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
                box.write("Running news feed scraper...")
                try:
                    subprocess.run(["python", "pipeline/scraper_quick.py"], check=True)
                    box.write("Scraping completed!")
                except subprocess.CalledProcessError as e:
                    box.error(f"Scraping failed: {e}")
                    return

                # run preds
                box.write("Predicting labels on news feed...")
                try:
                    pred_mod.run_news()
                    box.write("Prediction completed!")
                except Exception as e:
                    box.error(f"Prediction failed: {e}")
                    return

                box.success("Feed scraped & labeled")

    # button for full news
    with col2:
        if st.button("Get News Articles"):
            with st.status("Scraping news articles...", expanded=True) as box:
                # run full scraper
                box.write("Running full news scraper...")
                try:
                    subprocess.run(["python", "pipeline/scraper_full.py"], check=True)
                    box.write("Scraping completed!")
                except subprocess.CalledProcessError as e:
                    box.error(f"Scraping failed: {e}")
                    return

                # run preds
                box.write("Predicting labels on full news...")
                try:
                    pred_mod.run_fullnews()
                    box.write("Prediction completed!")
                except Exception as e:
                    box.error(f"Prediction failed: {e}")
                    return

                box.success("Full news scraped & labeled")