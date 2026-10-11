"""
Streamlit UI for Question Generator + Duplicate Detector.
Runs alongside FastAPI backend.

Run: streamlit run streamlit_app.py
"""
import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Question Generator", page_icon="🧠", layout="wide")

st.title("🧠 Question Generator + Duplicate Detector")
st.caption("AI-powered exam question generation with semantic duplicate prevention")

# Sidebar
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown(
        "This app generates new exam questions while avoiding duplicates "
        "using sentence embeddings + cosine similarity."
    )
    st.markdown("**Stack:** FastAPI · sentence-transformers · SQLite")
    try:
        h = requests.get(f"{API_URL}/health", timeout=2).json()
        st.success(f"Backend: {h.get('status', 'unknown')}")
    except Exception:
        st.error("Backend not reachable. Start uvicorn first.")

tab1, tab2, tab3 = st.tabs(["➕ Add Question", "🔍 Detect Duplicate", "✨ Generate"])

# ---------- TAB 1: Add ----------
with tab1:
    st.subheader("Add a question to the catalog")
    with st.form("add_form"):
        content = st.text_area("Question text", height=80)
        tags = st.text_input("Tags (comma-separated)", value="physics")
        submitted = st.form_submit_button("Add Question", type="primary")

    if submitted:
        if len(content.strip()) < 5:
            st.error("Question too short.")
        else:
            r = requests.post(
                f"{API_URL}/questions",
                json={"content": content, "tags": tags},
                timeout=30,
            )
            if r.status_code == 200:
                st.success(f"✅ Added with id {r.json()['id']}")
            else:
                st.error(f"Error: {r.text}")

    st.divider()
    st.subheader("Current Catalog")
    try:
        qs = requests.get(f"{API_URL}/questions", timeout=5).json()
        if qs:
            st.dataframe(
                [{"id": q["id"], "content": q["content"], "tags": q["tags"]} for q in qs],
                use_container_width=True,
            )
        else:
            st.info("No questions yet.")
    except Exception:
        st.warning("Could not load catalog.")

# ---------- TAB 2: Detect ----------
with tab2:
    st.subheader("Check if a question is a duplicate")
    with st.form("detect_form"):
        text = st.text_area("Question to check", height=80)
        threshold = st.slider("Similarity threshold", 0.5, 1.0, 0.85, 0.01)
        check = st.form_submit_button("Check Duplicate", type="primary")

    if check:
        if len(text.strip()) < 5:
            st.error("Text too short.")
        else:
            r = requests.post(
                f"{API_URL}/detect-duplicate",
                json={"content": text, "threshold": threshold},
                timeout=30,
            )
            if r.status_code == 200:
                body = r.json()
                if body["is_duplicate"]:
                    st.error(f"🚫 DUPLICATE ({body['match_type']})")
                    tm = body["top_match"]
                    st.markdown(f"**Top match:** {tm['content']}")
                    st.metric("Similarity", f"{tm['similarity']:.4f}")
                else:
                    st.success("✅ NOT a duplicate")
                    if body.get("top_match"):
                        tm = body["top_match"]
                        st.markdown(f"**Closest match:** {tm['content']}")
                        st.metric("Similarity", f"{tm['similarity']:.4f}")

                if body.get("all_matches"):
                    st.markdown("### All matches above 0.5")
                    st.dataframe(
                        [{"id": m["id"], "content": m["content"], "similarity": m["similarity"]}
                         for m in body["all_matches"]],
                        use_container_width=True,
                    )
            else:
                st.error(f"Error: {r.text}")

# ---------- TAB 3: Generate ----------
with tab3:
    st.subheader("Generate a new question (with duplicate avoidance)")
    with st.form("gen_form"):
        topic = st.text_input("Topic", value="reflection of light")
        max_attempts = st.slider("Max attempts", 1, 10, 5)
        gen_threshold = st.slider("Avoidance threshold", 0.5, 1.0, 0.85, 0.01)
        gen = st.form_submit_button("Generate", type="primary")

    if gen:
        if len(topic.strip()) < 3:
            st.error("Topic too short.")
        else:
            with st.spinner("Generating..."):
                r = requests.post(
                    f"{API_URL}/generate",
                    json={
                        "topic": topic,
                        "max_attempts": max_attempts,
                        "threshold": gen_threshold,
                    },
                    timeout=60,
                )
            if r.status_code == 200:
                body = r.json()
                if body["success"]:
                    st.success(f"✅ Generated in {body['total_attempts']} attempt(s)")
                    st.markdown(f"### {body['question']}")
                    st.text_input("Copy this:", value=body["question"], label_visibility="collapsed")
                else:
                    st.error(f"❌ {body.get('reason', 'Failed')}")

                st.markdown("### Attempt log")
                st.dataframe(body["attempts"], use_container_width=True)
            else:
                st.error(f"Error: {r.text}")