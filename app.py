import streamlit as st
import google.generativeai as genai
import langextract as lx
from pypdf import PdfReader
import os
import tempfile
import streamlit.components.v1 as components

# --- CONFIG ---
st.set_page_config(page_title="DocuTrace", layout="wide", page_icon="📜")

# Load Key
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    os.environ["LANGEXTRACT_API_KEY"] = api_key

# --- UI HEADER ---
st.title("📜 DocuTrace: The Verifiable AI Auditor")
st.markdown("Extract structured data from documents with **Source Grounding** (Evidence).")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Configuration")
    model_choice = st.selectbox("Model", ["gemini-2.5-flash", "gemini-1.5-flash"])
    uploaded_file = st.file_uploader("Upload Document (PDF)", type=["pdf"])
    
    st.divider()
    st.info("Powered by **Google LangExtract**")

# --- MAIN LOGIC ---
if uploaded_file:
    # 1. READ PDF
    with st.spinner("Reading Document..."):
        try:
            reader = PdfReader(uploaded_file)
            # Limit to first 5 pages to prevent timeouts on free tier
            text = ""
            for i in range(min(5, len(reader.pages))):
                text += reader.pages[i].extract_text() + "\n"
            st.success(f"Loaded {len(reader.pages)} pages. (Analyzing first 5)")
        except Exception as e:
            st.error(f"Error reading PDF: {e}")
            st.stop()

    # 2. DEFINE SCHEMA
    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input("What are you looking for?", "Risk Factors")
    with col2:
        fields = st.text_input("Fields to extract (comma separated)", "category, summary, impact")

    # 3. RUN EXTRACTION
    if st.button("🚀 Run Audit", type="primary"):
        if not api_key:
            st.error("Missing API Key.")
        else:
            with st.status("🕵️‍♂️ Auditing Document...", expanded=True) as status:
                try:
                    # Construct Prompt
                    prompt = f"Extract '{topic}'. Fields: {fields}."
                    
                    # Dummy Example (Required by Library)
                    examples = [
                        lx.data.ExampleData(
                            text="The company faces regulatory risks.", 
                            extractions=[lx.data.Extraction(extraction_class="item", extraction_text="The company faces regulatory risks", attributes={"category": "Legal"})]
                        )
                    ]

                    # Run Engine
                    status.write("AI is analyzing text...")
                    result = lx.extract(
                        text_or_documents=text,
                        prompt_description=prompt,
                        examples=examples,
                        model_id=model_choice
                    )
                    
                    status.write(f"✅ Found {len(result.extractions)} items.")
                    
                    # Generate HTML
                    status.write("Generating Visualization...")
                    lx.io.save_annotated_documents([result], output_name="data.jsonl", output_dir=".")
                    html_obj = lx.visualize("data.jsonl")
                    
                    # Save HTML string for rendering
                    html_content = html_obj.data
                    status.update(label="Audit Complete", state="complete")
                    
                    # 4. RENDER RESULT
                    st.markdown("### 🔍 Verified Evidence")
                    st.caption("Click highlights to see source text.")
                    components.html(html_content, height=800, scrolling=True)

                except Exception as e:
                    st.error(f"Extraction Failed: {e}")

else:
    st.info("👈 Upload a PDF to begin.")
