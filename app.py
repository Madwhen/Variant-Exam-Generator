import streamlit as st
from pdf_parser import extract_text
from docx import Document
from llm_client import call_llm
from prompts import SPLIT_SYSTEM, VARIANT_SYSTEM
from word_export import export_paper, export_answers
from datetime import datetime

st.set_page_config(page_title="Variant Exam Generator", layout="wide")
st.title("Variant Exam Generator")
st.caption("Upload a past paper PDF and generate a structurally similar variant paper with answer key.")

with st.sidebar:
    st.subheader("API Configuration")
    api_key = st.text_input("ELM API Key", type="password")
    base_url = st.text_input("Base URL", value="https://elm.edina.ac.uk/api/v1")
    
    MODEL_OPTIONS = {
        "Qwen 3.5 397B (Default)": "Qwen/Qwen3.5-397B-A17B-FP8",
        "EuroLLM 22B": "utter-project/EuroLLM-22B-Instruct-2512",
        "Mistral Small 4": "mistralai/Mistral-Small-4-119B-2603",
        "Llama 3.3 70B": "meta-llama/Llama-3.3-70B-Instruct"
    }
    selected_model_name = st.selectbox(
        "Select Model",
        options=list(MODEL_OPTIONS.keys()),
        index=0
    )
    model = MODEL_OPTIONS[selected_model_name]

uploaded = st.file_uploader("Upload exam paper (PDF or DOCX)", type=["pdf", "docx"])

full_text = ""
if uploaded:
    with st.spinner("Extracting text..."):
        if uploaded.name.endswith(".docx"):
            doc = Document(uploaded)
            full_text = "\n".join([p.text for p in doc.paragraphs])
        else:
            full_text = extract_text(uploaded)

    if not full_text.strip():
        st.error("No text could be extracted. Please upload a digital PDF or Word file.")
    else:
        MAX_CHARS = 8000
        if len(full_text) > MAX_CHARS:
            full_text = full_text[:MAX_CHARS]
            st.warning(f"⚠️ Input text is too long. Truncated to first {MAX_CHARS} characters for faster processing.")
        
        st.success(f"Extracted {len(full_text)} characters (after truncation)")

        with st.expander("View extracted text"):
            st.text_area("Text", full_text, height=300)

        if st.button("Generate Variant Paper", type="primary"):
            if not api_key:
                st.error("Please enter your ELM API Key in the sidebar.")
            else:
                try:
                    with st.spinner("Step 1/2: Splitting questions..."):
                        split_result = call_llm(
                            api_key, base_url, model, SPLIT_SYSTEM, full_text
                        )
                        questions = split_result.get("questions", [])
                        st.write(f"Extracted {len(questions)} questions")

                    meta = split_result.get("meta", {})
                    if meta.get("note"):
                        st.warning(f"⚠️ {meta['note']}")

                    if not questions:
                        st.error("No questions were extracted. Please try a cleaner PDF.")
                    else:
                        with st.spinner("Step 2/2: Generating variant questions..."):
                            variant_result = call_llm(
                                api_key, base_url, model,
                                VARIANT_SYSTEM, str(split_result)
                            )
                            items = variant_result.get("items", [])

                        if not items:
                            st.error("Variant generation failed. The model returned no items.")
                        else:
                            for it in items:
                                changed = it.get("changed_fields", [])
                                if "table data" not in changed and "table" not in str(changed).lower():
                                    st.warning(
                                        f"Question {it.get('source_id')}: table data may not have been varied. Please verify manually."
                                    )

                            paper_path = export_paper(items)
                            answer_path = export_answers(items)

                            st.session_state["items"] = items  
                            with open(paper_path, "rb") as f:
                                st.session_state["paper_bytes"] = f.read()
                            with open(answer_path, "rb") as f:
                                st.session_state["answer_bytes"] = f.read()

                            st.success(f"Done. {len(items)} questions generated. Download below.")
                except Exception as e:
                    st.error(f"Generation failed: {e}")

if "paper_bytes" in st.session_state:
    st.divider()
    
    st.subheader("Preview")
    saved_items = st.session_state.get("items", [])  # 👈 从 session 取
    for i, it in enumerate(saved_items, 1):
        st.markdown(f"**Question {i}:** {it.get('new_question', '')}")
        for opt in it.get("new_options", []):
            if opt:
                st.markdown(f"- {opt}")
        st.divider()

    st.subheader("Download")
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    
    st.download_button(
        "Download Variant Paper (.docx)",
        st.session_state["paper_bytes"],
        file_name=f"variant_paper_{ts}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key="download_paper",
    )
    
    st.download_button(
        "Download Answer Key (.docx)",
        st.session_state["answer_bytes"],
        file_name=f"answer_key_{ts}.docx",    
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key="download_answer",
    )