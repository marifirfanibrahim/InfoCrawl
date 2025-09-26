import streamlit as st
from pathlib import Path
from collections import Counter
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
    safe_q = "".join(c if c.isalnum() else "_" for c in search_text).lower()
    newsfeed = load_preds_json(proc_folder / "predictions_newsfeed.json") or {}
    fullnews = load_preds_json(proc_folder / "predictions_fullnews.json") or {}
    search = load_preds_json(proc_folder / f"predictions_search_{safe_q}.json") or {}

    # filter by query
    def filter_by_query(preds: dict, query: str):
        if not isinstance(preds, dict):
            return {}
        filtered = {}
        for k, ents in preds.items():
            if query in k.lower() or any(query in str(e.get("text", "")).lower() for e in ents):
                filtered[k] = ents
        return filtered

    filtered_newsfeed = filter_by_query(newsfeed, cur_q)
    filtered_fullnews = filter_by_query(fullnews, cur_q)
    filtered_search = filter_by_query(search, cur_q)

    # merge
    all_preds = {}
    for src in (filtered_newsfeed, filtered_fullnews, filtered_search):
        all_preds.update(src)

    # collect ORG + PERSON with frequency
    org_counter, person_counter = Counter(), Counter()
    for ents in all_preds.values():
        if not isinstance(ents, list):
            continue
        for e in ents:
            label, txt = e.get("label"), e.get("text")
            if not label or not txt:
                continue
            txt = txt.strip()
            if label == "ORG":
                org_counter[txt] += 1
            elif label == "PERSON":
                person_counter[txt] += 1

    if not org_counter and not person_counter:
        st.caption("No ORG or PERSON found for this query")
        return

    # show counts
    st.caption(f"Found {len(org_counter)} unique ORG entities)")
    st.caption(f"Found {len(person_counter)} unique PERSON entities)")

    # slider for minimum frequency
    min_freq = st.slider("Minimum frequency to display", 1, 10, 2)

    # filter counters by min_freq
    filtered_orgs = {ent: c for ent, c in org_counter.items() if c >= min_freq}
    filtered_persons = {ent: c for ent, c in person_counter.items() if c >= min_freq}

    def show_list(counter: dict, label: str):
        if not counter:
            return
        st.markdown(
            f"""
            <div style="text-align:center; font-weight:bold; font-size:1.05em; margin-top:8px; margin-bottom:4px;">
                {label}
            </div>
            """,
            unsafe_allow_html=True
        )
        # sort by frequency (descending), then alphabetically
        items = sorted(counter.items(), key=lambda x: (-x[1], x[0]))
        preview = items[:10]
        st.markdown("\n".join(f"- {ent} ({count})" for ent, count in preview))
        if len(items) > 10:
            with st.expander("show all"):
                remaining = items[10:]
                st.markdown("\n".join(f"- {ent} ({count})" for ent, count in remaining))

    show_list(filtered_orgs, f"Organizations (ORG) - {len(filtered_orgs)}")
    show_list(filtered_persons, f"Persons (PERSON) - {len(filtered_persons)}")
