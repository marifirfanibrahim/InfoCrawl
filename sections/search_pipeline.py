# sections/search_pipeline.py
"""
make search and summarise pipeline with clear button
1. set layout
2. make clear button (DON'T REMOVE ALL DATA)
3. make search and summarise button
4. trigger pipeline (crawl.py -> scraper_search.py -> summarise.py -> compile.py -> summarise.py)
5. make label prediction button
6. trigger prediction (predict.py)
"""
import streamlit as st
import shutil
from pathlib import Path
from ui_helpers import load_preds_json, build_colors

from pipeline import crawler as crawl_mod
from pipeline import summarise as sum_mod
from pipeline import compile as comp_mod
from pipeline.scraper_search import run_scraper
from pipeline import predict as pred_mod

last_query_file = Path("data/processed/last_query.txt")

def _ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

# clear pipeline data except some files
def clear_pipeline_data():
    keep_dirs = {
        Path("data/raw/news_feed").resolve(),
        Path("data/raw/news_id").resolve()
    }
    keep_files = {
        Path("data/processed/predictions_fullnews.json").resolve(),
        Path("data/processed/predictions_newsfeed.json").resolve()
    }
    folders = [Path("data/raw"), Path("data/output"), Path("data/processed")]
    for f in folders:
        if f.exists():
            for item in f.iterdir():
                item_path = item.resolve()
                if any(str(item_path).startswith(str(k)) for k in keep_dirs) or item_path in keep_files:
                    continue
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    try:
                        item.unlink()
                    except FileNotFoundError:
                        pass
    st.success("Pipeline data cleared (except news_feed, news_id, and two prediction json files)")

def render_search_pipeline(search_text: str):
    col1, col2 = st.columns(2)
    with col1:
        disabled = not bool(search_text.strip())

        # run full pipeline
        if st.button("Search & Summarise", type="primary", disabled=disabled):
            if not search_text.strip():
                st.warning("Please enter a search term first")
            else:
                with st.status("Running pipeline...", expanded=True) as box:
                    try:
                        query = search_text.strip()

                        box.write("Crawling for links...")
                        crawl_mod.run(query)

                        _ensure_parent(last_query_file)
                        last_query_file.write_text(query, encoding="utf-8")

                        box.write("Scraping for text...")
                        run_scraper(query) 

                        box.write("Summarising individual files...")
                        sum_mod.run_individual(query=query)

                        box.write("Compiling files...")
                        comp_mod.run(query=query)

                        box.write("Summarising compiled file...")
                        sum_mod.run_overall(query=query)

                        box.success("Search summarised")
                    except Exception as e:
                        box.update(label="pipeline failed", state="error")
                        st.error(f"unexpected error: {e}")

        # run label prediction only
        if st.button("Predict Labels", type="secondary", disabled=disabled):
            try:
                with st.status("running label prediction...", expanded=True) as box:
                    query = last_query_file.read_text(encoding="utf-8").strip()

                    box.write("predicting labels...")
                    pred_mod.run_individual(query=query)
                    pred_mod.run_overall(query=query)
                    pred_mod.run_search(query=query)
                    pred_mod.run_news()
                    pred_mod.run_fullnews()
                    box.success("label prediction complete")
            except Exception as e:
                st.error(f"Label prediction failed: {e}")

        # toggle + picker + legend
        show_ents = st.checkbox("Show predicted labels", key="show_ents")

        if show_ents:
            proc_folder = Path("data/processed")
            indiv_preds = load_preds_json(proc_folder / "predictions_individual.json")
            feed_preds = load_preds_json(proc_folder / "predictions_newsfeed.json")
            full_preds = load_preds_json(proc_folder / "predictions_fullnews.json")
            search_preds = load_preds_json(proc_folder / "predictions_search.json")

            labels = sorted({
                e.get("label", "")
                for src in (indiv_preds, feed_preds, full_preds, search_preds)
                if isinstance(src, dict)
                for ents in src.values()
                for e in ents
            } - {""})

            colors = build_colors(labels)
            st.session_state["entity_colors"] = colors

            if "active_labels" not in st.session_state:
                st.session_state.active_labels = labels[:]

            if labels:
                st.multiselect("entity types", options=labels, key="active_labels")
                legend = "  ".join(
                    f'<span style="background:{colors[lbl]};display:inline-block;width:0.8em;height:0.8em;'
                    f'margin-right:0.3em;border-radius:3px;"></span>{lbl}'
                    for lbl in st.session_state.active_labels
                )
                st.markdown(legend, unsafe_allow_html=True)

    with col2:
        # clear button
        if st.button("Clear Data", type="secondary"):
            clear_pipeline_data()
