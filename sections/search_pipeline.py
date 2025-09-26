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
import subprocess

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

def check_model(model: str):
    try:
        # check installed models
        res = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True
        )
        if model not in res.stdout:
            with st.spinner(f"Downloading model '{model}'..."):
                pull = subprocess.run(
                    ["ollama", "pull", model],
                    capture_output=True,
                    text=True
                )
                if pull.returncode == 0:
                    st.success(f"Model '{model}' downloaded successfully")
                else:
                    st.error(f"Failed to download model '{model}': {pull.stderr}")
        else:
            st.caption(f"✅ Model '{model}' already available")
    except Exception as e:
        st.error(f"Could not check/download model: {e}")

def render_search_pipeline(search_text: str):
    # update last_query.txt
    _ensure_parent(last_query_file)
    query = search_text.strip()
    last_query_file.write_text(query, encoding="utf-8")

    col1, _, col2= st.columns([3, 1, 1])
    with col1:
        disabled = not bool(search_text.strip())

        # choose model (make sure to download the model first with ollama pull (model_name))
        model_options = {
            "mistral": "Mistral – Lightweight (~4‑7B), runs well on CPU or modest GPU",
            "llama3.2": "LLaMA 3.2 – Larger (~13B), needs ≥12‑16GB VRAM or lots of RAM",
            "tinyllama": "TinyLLaMA – Tiny (~1B), runs anywhere, very fast but less detailed"

        }

        col_model, _ = st.columns([3,2])
        with col_model:
            model_choice = st.selectbox(
                "Choose summarisation model",
                options=list(model_options.keys()),
                format_func=lambda x: model_options[x]  # shows description in dropdown
            )

        # run full pipeline
        if st.button("Search & Summarise", type="primary", disabled=disabled):
            check_model(model_choice) 
            if not search_text.strip():
                st.warning("Please enter a search term first")
            else:
                with st.status("Running pipeline...", expanded=True) as box:
                    try:
                        box.write("Crawling for links...")
                        crawl_mod.run(query)

                        box.write("Scraping for text...")
                        run_scraper(query) 

                        box.write("Summarising individual files...")
                        sum_mod.run_individual(query=query, model=model_choice)

                        box.write("Compiling files...")
                        comp_mod.run(query=query)

                        box.write("Summarising compiled file...")
                        sum_mod.run_overall(query=query, model=model_choice)

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

    with col2:
        if "show_clear_confirm" not in st.session_state:
            st.session_state.show_clear_confirm = False

        # clear button
        if st.button("Clear Data", type="secondary", use_container_width=True):
            st.session_state.show_clear_confirm = True

        # confirm clear
        if st.session_state.show_clear_confirm:
            st.warning(
                "Are you sure you want to clear pipeline data? "
                "This will remove processed/output data but keep news_feed, news_id, "
                "and their respective prediction JSON files."
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Yes, clear it"):
                    clear_pipeline_data()
                    st.session_state.show_clear_confirm = False
            with c2:
                if st.button("Cancel"):
                    st.session_state.show_clear_confirm = False

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
