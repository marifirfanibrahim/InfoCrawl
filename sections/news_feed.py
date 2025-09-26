# sections/news_feed.py
"""
display news feed
1. appearance
2. check predictions from *.json files from data/processed
3. set filter to only query
4. set highlights (from ui_helpers.py)
6. news rendering (csv files)
"""
import streamlit as st
import pandas as pd
from pathlib import Path

# helpers from ui_helpers.py
from ui_helpers import (
    s, join_meta, trim_source, exact_mask,
    load_preds_json, build_colors, highlight_ents
)

# paths
data_folder = Path("data")
proc_folder = data_folder / "processed"
feed_folder = data_folder / "raw" / "news_feed"

def render_news_feed(search_text: str):
    # title box
    st.markdown(
        """
        <div style="
            background-color:#2c3e50;
            color:white;
            padding:6px 20px;
            border-radius:6px;
            font-size:20px;
            font-weight:bold;
            margin-bottom:10px;
            text-align:center;
        ">
            News Feed
        </div>
        """,
        unsafe_allow_html=True
    )

    # session toggles
    show_ents = st.session_state.get("show_ents", False)
    active_labels = st.session_state.get("active_labels", [])
    colors = st.session_state.get("entity_colors", {})

    # load preds
    feed_preds = load_preds_json(proc_folder / "predictions_newsfeed.json")

    # build colors if not set
    colors = st.session_state.get("entity_colors")
    if not colors:
        indiv_preds = load_preds_json(proc_folder / "predictions_individual.json")
        full_preds = load_preds_json(proc_folder / "predictions_fullnews.json")

        labels = sorted({
            e.get("label", "")
            for src in (indiv_preds, feed_preds, full_preds)
            if isinstance(src, dict)
            for ents in src.values()
            for e in ents
        } - {""})

        colors = build_colors(labels)
        st.session_state["entity_colors"] = colors

    # load csvs
    csvs = sorted(feed_folder.glob("*.csv"))
    if not csvs:
        st.caption("No feed csvs available")
        return

    dfs = []
    for f in csvs:
        try:
            df = pd.read_csv(f)
            df["__srcfile__"] = f.name
            dfs.append(df)
        except Exception:
            continue

    if not dfs:
        st.caption("No readable feed csvs")
        return

    # combine
    df_all = pd.concat(dfs, ignore_index=True)

    # filter by query
    if search_text.strip():
        mask = exact_mask(df_all["Title"], search_text) | exact_mask(df_all["Summary"], search_text)
        df_filt = df_all[mask]
    else:
        df_filt = df_all.iloc[0:0]

    st.caption(f"{len(df_filt)} of {len(df_all)} feed articles")

    if df_filt.empty:
        st.caption("No news feed available")
        return

    # show up to 30
    for idx, row in df_filt.head(30).iterrows():
        title = s(row.get("Title"))
        url = s(row.get("Source_URL"))
        meta = join_meta([
            trim_source(row.get("News_Source")),
            row.get("Publish_Date"),
            row.get("Category")
        ])

        # title + link
        st.markdown(
            f"<div style='text-align:center; font-weight:bold; font-size:1.05em;'>"
            f"{title} (<a href='{url}' target='_blank'>link</a>)"
            f"</div>",
            unsafe_allow_html=True
        )

        # meta info
        if meta:
            st.markdown(
                f"<div style='text-align:center; color:gray; font-size:0.9em;'>"
                f"{meta}</div>",
                unsafe_allow_html=True
            )

        # summary + ents
        summ = s(row.get("Summary"))
        fallback = f"{s(row.get('__srcfile__'))}:{s(idx)}"
        ents = (feed_preds or {}).get(url) or (feed_preds or {}).get(fallback) or []

        if show_ents and active_labels and ents:
            filt_ents = [e for e in ents if e.get("label") in active_labels]
            if filt_ents:
                html_sum = highlight_ents(summ, filt_ents, colors)
            else:
                html_sum = s(summ)
            st.markdown(f"<div class='summary-text'>{html_sum}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='summary-text'>{s(summ)}</div>", unsafe_allow_html=True)

        st.divider()
