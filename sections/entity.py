# sections/entity.py
"""
key entities
1. appearance
2. check last query (for loading)
3. check predictions_*.json from data/processed
4. get ORG and PERSON labels
5. display list
"""
import streamlit as st
from pathlib import Path
from ui_helpers import load_preds_json

# paths
data_folder = Path("data")
proc_folder = data_folder / "processed"
last_query_file = proc_folder / "last_query.txt"

def render_entity_summary(search_text: str = ""):
    # title box
    st.markdown(
        """
        <div style="
            background-color:#34495e;
            color:white;
            padding:6px 20px;
            border-radius:6px;
            font-size:20px;
            font-weight:bold;
            margin-bottom:4px;
            text-align:center;
        ">
            Key Entities
        </div>
        """,
        unsafe_allow_html=True
    )

    # check last query
    if not last_query_file.exists():
        st.caption("No entities available")
        return

    last_q = last_query_file.read_text(encoding="utf-8").strip().lower()
    cur_q = search_text.strip().lower()

    if not cur_q or cur_q != last_q:
        st.caption("No entities available")
        return

    # load predictions
    newsfeed = load_preds_json(proc_folder / "predictions_newsfeed.json") or {}
    fullnews = load_preds_json(proc_folder / "predictions_fullnews.json") or {}
    search = load_preds_json(proc_folder / "predictions_search.json") or {}

    # merge all
    all_preds = {}
    for src in (newsfeed, fullnews, search):
        if isinstance(src, dict):
            all_preds.update(src)

    # collect ORG + PERSON
    orgs = set()
    persons = set()

    for ents in all_preds.values():
        if not isinstance(ents, list):
            continue
        for e in ents:
            label = e.get("label")
            txt = e.get("text")
            if not label or not txt:
                continue
            if label == "ORG":
                orgs.add(txt.strip())
            elif label == "PERSON":
                persons.add(txt.strip())

    orgs = sorted(orgs)
    persons = sorted(persons)

    if not orgs and not persons:
        st.caption("No ORG or PERSON found")
        return

    # show counts
    st.caption(f"Found {len(orgs)} ORG entities")
    st.caption(f"Found {len(persons)} PERSON entities")

    def show_list(items, label):
        if not items:
            return
        st.markdown(f"**{label}:**")
        preview = items[:10]
        st.markdown("\n".join(f"- {i}" for i in preview))
        if len(items) > 10:
            with st.expander("show all"):
                st.markdown("\n".join(f"- {i}" for i in items))

    show_list(orgs, "Organizations (ORG)")
    show_list(persons, "Persons (PERSON)")
