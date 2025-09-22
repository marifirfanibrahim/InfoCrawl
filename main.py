# main.py
import streamlit as st

# imports
from sections.news_control import render_news_controls
from sections.search_pipeline import render_search_pipeline
from sections.summaries import render_summaries
from sections.news_feed import render_news_feed
from sections.entity import render_entity_summary
from sections.full_news import render_full_news

# page setup
st.set_page_config(page_title="InfoCrawl", layout="wide")
st.markdown(
    """
    <h1 style='text-align: center;'>
        InfoCrawl
    </h1>
    """,
    unsafe_allow_html=True
)

# search box
search_text = st.text_input("Search", placeholder="e.g. Maybank")

# layout: left = pipeline/summaries, right = controls/feed
left, right = st.columns([2, 1])

# right side: news controls
with right:
    render_news_controls()

# left side: pipeline + summaries
with left:
    render_search_pipeline(search_text)
    render_summaries(search_text)

# right side: feed + entities
with right:
    render_news_feed(search_text)
    render_entity_summary(search_text)

# full width: full news
render_full_news(search_text)
