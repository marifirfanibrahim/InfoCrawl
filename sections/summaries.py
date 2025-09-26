# sections/summaries.py
"""
display summaries
1. check last query (for loading)
2. get source
3. appearance
4. set highlights (from ui_helpers.py)
5. render individual and overall summaries (txt files)
6. filter summaries by query
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

def get_query_from_filename(filename: str) -> str:
    if "_query_" in filename:
        parts = filename.split("_query_")
        if len(parts) > 1:
            return parts[1].split("_")[0]
    return ""

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

def get_summaries_for_query(current_query: str):
    last_query = get_last_query()
    
    # if current query matches last query
    if current_query.strip().lower() == last_query.strip().lower():
        overall_file = out_folder / "summary_overall.txt"
        summary_files = sorted(out_indiv.glob("*.txt"))
        return overall_file, summary_files
    
    return None, []

def check_and_regenerate_summaries(current_query: str):
    last_query = get_last_query()
    
    if current_query.strip().lower() != last_query.strip().lower():
        return False
    return True

def banner(title: str):
    st.markdown(
        f"""
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
            {title}
        </div>
        """,
        unsafe_allow_html=True
    )

def render_overall_summary(overall_file: Path, show_ents: bool, active_labels: list, colors: dict):
    if not overall_file.exists():
        st.caption("No overall summary available")
        return
    
    try:
        overall_txt = overall_file.read_text(encoding="utf-8", errors="ignore").strip()
        if not overall_txt:
            st.caption("Overall summary file is empty")
            return
        
        overall_json = load_preds_json(proc_folder / "predictions_overall.json")
        overall_ents = overall_json.get("entities", []) if isinstance(overall_json, dict) else []
        
        st.markdown("<style>.summary-text{ text-align:justify; line-height:1.5; }</style>", unsafe_allow_html=True)
        
        if show_ents and active_labels and overall_ents:
            ents_to_show = [e for e in overall_ents if e.get("label") in active_labels]
            if ents_to_show:
                html_sum = highlight_ents(overall_txt, ents_to_show, colors)
                st.markdown(f"<div class='summary-text'>{html_sum}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='summary-text'>{s(overall_txt)}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='summary-text'>{s(overall_txt)}</div>", unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Error reading overall summary: {e}")

def render_individual_summaries(summary_files: list, show_ents: bool, active_labels: list, colors: dict, current_query: str):
    if not summary_files:
        st.caption("No individual summaries available")
        st.caption(f"Query: {current_query}")
        return
    
    st.caption(f"{len(summary_files)} individual summaries generated for query: {current_query}")
    
    src_map = build_source_map()
    indiv_preds = load_preds_json(proc_folder / "predictions_individual.json")
    
    for i, f in enumerate(summary_files):
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore").strip()
            if not txt:
                continue
                
            file_ents = (indiv_preds or {}).get(f.name, [])
            
            # summary text
            if show_ents and active_labels and file_ents:
                ents_to_show = [e for e in file_ents if e.get("label") in active_labels]
                if ents_to_show:
                    html_sum = highlight_ents(txt, ents_to_show, colors)
                    st.markdown(f"<div class='summary-text'>{html_sum}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='summary-text'>{s(txt)}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='summary-text'>{s(txt)}</div>", unsafe_allow_html=True)
            
            # source information
            title, link = src_map.get(f.name, (f.stem, ""))
            if link:
                st.markdown(f"**Source:** [{title}]({link})")
            else:
                st.markdown(f"**Source:** {title}")
            
            # divider
            if i < len(summary_files) - 1:
                st.divider()
                st.markdown("<br>", unsafe_allow_html=True) 
                    
        except Exception as e:
            st.error(f"Error reading summary {f.name}: {e}")
            continue

def render_summaries(search_text: str):
    if not search_text.strip():
        banner("Overall Summary")
        st.caption("Search to get summaries")
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

        banner("Individual Summaries")
        st.caption("Search to get summaries")
        return
    
    # check if summaries match current query
    if not check_and_regenerate_summaries(search_text):
        banner("Overall Summary")
        st.caption("No summary available for current query")
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

        banner("Individual Summaries")
        st.caption("No individual summaries available for current query")
        return
    
    # get summaries for current query
    overall_file, summary_files = get_summaries_for_query(search_text)
    
    # check for summaries
    has_overall = overall_file and overall_file.exists()
    has_individual = bool(summary_files)
    
    if not has_overall and not has_individual:
        banner("Overall Summary")
        st.info("No summaries available. Click 'Summarise' to generate summaries for this query.")
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

        banner("Individual Summaries")
        st.info("No individual summaries available. Click 'Summarise' to generate summaries.")
        return
    
    # get entity highlighting settings
    show_ents = st.session_state.get("show_ents", False)
    active_labels = st.session_state.get("active_labels", [])
    colors = st.session_state.get("entity_colors", {})
    
    # run predictions if entity highlighting is enabled
    if show_ents:
        with st.spinner("Loading entity predictions..."):
            if needs_prediction(proc_folder / "predictions_individual.json"):
                pred_mod.run_individual()
            if needs_prediction(proc_folder / "predictions_overall.json"):
                pred_mod.run_overall()
    
    # overall summary
    banner("Overall Summary")
    if has_overall:
        render_overall_summary(overall_file, show_ents, active_labels, colors)
    else:
        st.caption("No overall summary available for this query")
    
    # individual summaries
    st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
    banner("Individual Summaries")
    
    if has_individual:
        render_individual_summaries(summary_files, show_ents, active_labels, colors, search_text)
    else:
        st.caption("No individual summaries available for this query")
        st.caption(f"Query: {search_text}")

# summary status
def get_summary_status(search_text: str) -> dict:
    last_query = get_last_query()
    overall_file = out_folder / "summary_overall.txt"
    summary_files = sorted(out_indiv.glob("*.txt"))
    
    return {
        "current_query": search_text,
        "last_generated_query": last_query,
        "queries_match": search_text.strip().lower() == last_query.strip().lower(),
        "has_overall": overall_file.exists(),
        "has_individual": bool(summary_files),
        "individual_count": len(summary_files),
        "overall_exists": overall_file.exists()
    }