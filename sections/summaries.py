# sections/summaries.py
"""
display summaries
1. check last query (for loading)
2. get source
3. appearance
4. set highlights (from ui_helpers.py)
5. render individual and overall summaries (txt files)
"""
from pathlib import Path
import streamlit as st
import pandas as pd
from ui_helpers import s, load_preds_json, highlight_ents, needs_prediction
from pipeline import predict as pred_mod

# paths
data_folder = Path("data")
proc_folder = data_folder / "processed"
out_folder = data_folder / "output"
out_indiv = out_folder / "summary_individual"
last_query_file = proc_folder / "last_query.txt"
raw_folder = data_folder / "raw" / "search"

def get_last_query() -> str:
    if last_query_file.exists():
        return last_query_file.read_text(encoding="utf-8").strip()
    return ""

def make_safe_filename(title: str, idx: int) -> str:
    safe = "".join(c if c.isalnum() else "_" for c in (title or ""))[:40]
    return f"{safe}_{idx}.txt"

# source link
def build_source_map():
    src_map = {}
    for csv_file in raw_folder.glob("*.csv"):
        try:
            df = pd.read_csv(csv_file)
        except Exception:
            continue
        if "Title" not in df.columns or "Source_URL" not in df.columns:
            continue
        for idx, row in df.iterrows():
            title = str(row.get("Title", "")).strip()
            url = str(row.get("Source_URL", "")).strip()
            if not title:
                continue
            fname = make_safe_filename(title, idx)
            src_map[fname] = (title, url)
    return src_map

def banner(title: str):
    st.markdown(
        f"""
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
            {title}
        </div>
        """,
        unsafe_allow_html=True
    )

def render_summaries(search_text: str):
    # overall summary
    if not search_text.strip():
        banner("Overall Summary")
        st.caption("No summary available")
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
        banner("Individual Summaries")
        st.caption("No summaries available")
        return

    overall_file = out_folder / "summary_overall.txt"
    summary_files = sorted(out_indiv.glob("*.txt"))
    summaries_exist = overall_file.exists() or bool(summary_files)
    last_q = get_last_query()
    query_ok = (search_text.strip() == last_q)

    banner("Overall Summary")
    if not summaries_exist or not query_ok:
        st.caption("No summary for this query")
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
        banner("Individual Summaries")
        st.caption("No individual summaries for this query")
        return

    show_ents = st.session_state.get("show_ents", False)
    active_labels = st.session_state.get("active_labels", [])
    colors = st.session_state.get("entity_colors", {})

    if show_ents:
        if needs_prediction(proc_folder / "predictions_individual.json"):
            pred_mod.run_individual()
        if needs_prediction(proc_folder / "predictions_overall.json"):
            pred_mod.run_overall()
        if needs_prediction(proc_folder / "predictions_newsfeed.json"):
            pred_mod.run_news()
        if needs_prediction(proc_folder / "predictions_fullnews.json"):
            pred_mod.run_fullnews()

    st.markdown("<style>.summary-text{ text-align:justify; line-height:1.5; }</style>", unsafe_allow_html=True)

    overall_txt = overall_file.read_text(encoding="utf-8") if overall_file.exists() else ""
    overall_json = load_preds_json(proc_folder / "predictions_overall.json")
    overall_ents = overall_json.get("entities", []) if isinstance(overall_json, dict) else []

    if overall_txt:
        if show_ents and active_labels:
            ents_to_show = [e for e in overall_ents if e.get("label") in active_labels]
            html_sum = highlight_ents(overall_txt, ents_to_show, colors)
            st.markdown(f"<div class='summary-text'>{html_sum}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='summary-text'>{s(overall_txt)}</div>", unsafe_allow_html=True)
    else:
        st.caption("No overall summary available")

    # individual summaries
    st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
    banner("Individual Summaries")
    if not summary_files:
        st.caption("No individual summaries available")
        st.caption(f"query: {search_text}")
        return

    st.caption(f"{len(summary_files)} individual summaries generated")

    src_map = build_source_map()
    indiv_preds = load_preds_json(proc_folder / "predictions_individual.json")

    for f in summary_files:
        txt = f.read_text(encoding="utf-8")
        file_ents = (indiv_preds or {}).get(f.name, [])
        if show_ents and active_labels:
            ents_to_show = [e for e in file_ents if e.get("label") in active_labels]
            html_sum = highlight_ents(txt, ents_to_show, colors) if ents_to_show else s(txt)
            st.markdown(f"<div class='summary-text'>{html_sum}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='summary-text'>{s(txt)}</div>", unsafe_allow_html=True)

        # show source
        title, link = src_map.get(f.name, (f.stem, ""))
        if link:
            st.markdown(f"**source:** [{title}]({link})")
        else:
            st.markdown(f"**source:** {title}")

        st.divider()

    st.caption(f"query: {search_text}")
