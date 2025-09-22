# sections/full_news.py
"""
display full news
1. title
2. check predictions from *.json files from data/processed
3. set filter to only query
4. set title colors (for search and full news)
5. set highlights (from ui_helpers.py)
6. news rendering (csv files)
"""
import streamlit as st
import pandas as pd
from pathlib import Path

# helper functions from ui_helpers.py
from ui_helpers import (
    s,                # safe string conversion
    join_meta,        # join metadata fields
    trim_source,      # shorten source name
    exact_mask,       # exact match filter
    load_preds_json,  # load predictions from JSON
    build_colors,     # assign colors to entity labels
    highlight_ents    # highlight entities in text
)

# paths
data_folder = Path("data")
processed_folder = data_folder / "processed"
full_news_folder = data_folder / "raw" / "news_id"
search_folder = data_folder / "raw" / "search"

def render_full_news(search_text: str):
    st.markdown(
        """
        <div style="
            background-color:#2c3e50;
            color:white;
            padding:12px 20px;
            border-radius:6px;
            font-size:20px;
            font-weight:bold;
            margin-bottom:10px;
            text-align:center;
        ">
            Full News
        </div>
        """,
        unsafe_allow_html=True
    )

    show_entities = st.session_state.get("show_ents", False)
    active_labels = st.session_state.get("active_labels", [])
    colors = st.session_state.get("entity_colors", {})

    # load predictions
    full_predictions = load_preds_json(processed_folder / "predictions_fullnews.json") or {}
    search_predictions = load_preds_json(processed_folder / "predictions_search.json") or {}
    if isinstance(search_predictions, dict):
        full_predictions.update(search_predictions)

    # build colors if not already in session
    if not colors:
        labels = sorted({
            e.get("label", "")
            for src in (search_predictions, full_predictions)
            if isinstance(src, dict)
            for ents in src.values()
            for e in ents
        } - {""})
        colors = build_colors(labels)
        st.session_state["entity_colors"] = colors

    # helper to load CSVs into a dataframe
    def load_csvs(folder: Path):
        frames = []
        for file in sorted(folder.glob("*.csv")):
            try:
                df = pd.read_csv(file)
                df["__srcfile__"] = file.name
                frames.append(df)
            except Exception:
                continue
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # Load separately
    df_search = load_csvs(search_folder)
    df_news = load_csvs(full_news_folder)

    # filter by query
    def filter_df(df, text):
        if df.empty:
            return df
        if text.strip():
            if "Summary" in df.columns:
                mask = exact_mask(df["Title"], text) | exact_mask(df["Summary"], text)
            elif "Content" in df.columns:
                mask = exact_mask(df["Title"], text) | exact_mask(df["Content"], text)
            else:
                mask = exact_mask(df["Title"], text)
            return df[mask]
        return df.iloc[0:0]

    
    df_search_filtered = filter_df(df_search, search_text)  # for search
    df_news_filtered = filter_df(df_news, search_text)  # for news

    total_articles = len(df_search_filtered) + len(df_news_filtered)
    st.caption(f"{total_articles} of {len(df_search) + len(df_news)} articles")

    if total_articles == 0:
        st.caption("No news articles available.")
        return

    # render helper
    def render_rows(df, title_color: str):
        for idx, row in df.head(30).iterrows():
            title = s(row.get("Title"))
            url = s(row.get("Source_URL"))

            meta_info = join_meta([
                trim_source(row.get("News_Source", "")),
                row.get("Publish_Date"),
                row.get("Category")
            ])

            # title + link
            st.markdown(
                f"<div style='text-align:center; font-weight:bold; font-size:1.1em; color:{title_color};'>"
                f"{title} (<a href='{url}' target='_blank'>link</a>)"
                f"</div>",
                unsafe_allow_html=True
            )

            # meta info
            if meta_info:
                st.markdown(
                    f"<div style='text-align:center; color:gray; font-size:0.9em;'>"
                    f"{meta_info}"
                    f"</div>",
                    unsafe_allow_html=True
                )

            # summary / content + highlighting
            summary_text = s(row.get("Summary") or row.get("Content"))
            fallback_key = f"{s(row.get('__srcfile__'))}:{s(idx)}"
            entities = (full_predictions or {}).get(url) or (full_predictions or {}).get(fallback_key) or []

            if show_entities and active_labels and entities:
                filtered_entities = [e for e in entities if e.get("label") in active_labels]
                if filtered_entities:
                    html_summary = highlight_ents(summary_text, filtered_entities, colors)
                else:
                    html_summary = s(summary_text)
                st.markdown(f"<div class='summary-text'>{html_summary}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='summary-text'>{s(summary_text)}</div>", unsafe_allow_html=True)

            st.markdown("---")

    # render search (search first)
    render_rows(df_search_filtered, "green")
    render_rows(df_news_filtered, "gold")
