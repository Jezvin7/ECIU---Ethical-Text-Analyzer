import streamlit as st
import os
import requests

from analysis_core import analyze_full_text


# ---------------------------------------------------
# PAGE CONFIG — must be before other Streamlit UI calls
# ---------------------------------------------------
st.set_page_config(
    page_title="Ethical Analyser",
    layout="wide"
)


# ---------------------------------------------------
# ENV SETTINGS
# ---------------------------------------------------
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


# ---------------------------------------------------
# REUSABLE RESULT DISPLAY FUNCTION
# ---------------------------------------------------
def display_full_analysis(result, original_text=None, source_links=None):
    if source_links is None:
        source_links = []

    # ---------------------------------------------------
    # Original analyzed text
    # ---------------------------------------------------
    if original_text:
        st.header("Analyzed Text")
        st.write(original_text)

    # ---------------------------------------------------
    # Extracted clickable source links from LLM page
    # ---------------------------------------------------
    if source_links:
        st.header("Extracted Clickable Source Links")

        st.write(
            "These are the actual URLs captured from clickable source labels "
            "inside the LLM response."
        )

        for link in source_links:
            st.write(f"- {link}")

    # ---------------------------------------------------
    # Overall Trust Score
    # ---------------------------------------------------
    st.header("Overall Trust Score")
    st.metric("Trust Score", f"{result['trust_score']} / 100")

    if result["trust_score"] >= 75:
        st.success("High reliability")
    elif result["trust_score"] >= 50:
        st.warning("Medium reliability")
    else:
        st.error("Low reliability")

    # ---------------------------------------------------
    # 1. Claim Classification
    # ---------------------------------------------------
    st.header("1. AI Claim Classification")

    for item in result["classified_claims"]:
        st.write(f"**Sentence:** {item['sentence']}")
        st.write(f"**AI Label:** {item['label']}")
        st.write(f"**Confidence:** {item['confidence']}")
        st.divider()

    # ---------------------------------------------------
    # 2. Fact Verification
    # ---------------------------------------------------
    st.header("2. AI Semantic Fact Verification")

    if result["fact_results"]:
        for item in result["fact_results"]:
            st.write(f"**Claim:** {item['claim']}")
            st.write(f"**Status:** {item['status']}")
            st.write(f"**Similarity:** {item['similarity']}")

            if item.get("evidence_type"):
                st.write(f"**Evidence Route:** {item['evidence_type']}")

            if item.get("source"):
                st.write(f"**Source:** {item['source']}")

            if item.get("summary"):
                st.info(item["summary"])

            st.divider()
    else:
        st.info("No factual claims found for verification.")

    # ---------------------------------------------------
    # 3. Bias / Emotion Detection
    # ---------------------------------------------------
    st.header("3. AI Bias / Emotion Detection")

    bias = result["bias_result"]

    st.write(f"**Top Emotion:** {bias['top_emotion']}")
    st.write(f"**Emotion Confidence:** {bias['emotion_confidence']}")
    st.write(f"**Bias Risk Score:** {bias['bias_risk_score']} / 100")

    if bias["biased_words"]:
        st.warning("Biased words found: " + ", ".join(bias["biased_words"]))
    else:
        st.success("No strong biased keywords detected.")

    # ---------------------------------------------------
    # 4. Citation Quality
    # ---------------------------------------------------
    st.header("4. Citation Quality Scorer")

    citation = result["citation_result"]

    st.write(f"**Citation Score:** {citation['overall_score']} / 100")
    st.write(f"**Level:** {citation['level']}")

    if citation["sources"]:
        for source in citation["sources"]:
            source_type = source.get("type", "unknown")

            if source_type == "url":
                st.write(
                    f"- {source.get('url', 'Unknown URL')} → "
                    f"{source.get('quality', 'unknown quality')} "
                    f"({source.get('score', 0)}/100)"
                )

            elif source_type == "named_source":
                st.write(
                    f"- {source.get('url', 'Trusted named source')} → "
                    f"{source.get('quality', 'unknown quality')} "
                    f"({source.get('score', 0)}/100)"
                )

            else:
                st.write(
                    f"- {source.get('url', 'Detected source')} → "
                    f"{source.get('quality', 'unknown quality')} "
                    f"({source.get('score', 0)}/100)"
                )
    else:
        st.warning("No citations or links were found.")

    # ---------------------------------------------------
    # 5. AI Explanation
    # ---------------------------------------------------
    st.header("5. Generative AI Explanation")
    st.info(result["ai_explanation"])


# ---------------------------------------------------
# PAGE HEADER
# ---------------------------------------------------
st.title("Ethical Analyser: AI-Powered Text Analyser")

st.write(
    "This prototype uses Machine Learning, NLP, semantic embeddings, and Generative AI "
    "to evaluate the reliability of online or AI-generated text."
)

st.markdown("""
### Where AI is used
1. **Claim Classification:** transformer-based zero-shot classification  
2. **Fact Verification:** semantic similarity using sentence embeddings  
3. **Bias Detection:** transformer-based emotion classifier  
4. **Citation Quality:** source reliability scoring  
5. **Explainability:** LLM-generated explanation  
6. **Browser Extension:** real-time AI checking through API  
""")


# ---------------------------------------------------
# DETAILS MODE — when opened from browser extension
# Example:
# http://localhost:8501/?analysis_id=503fa4d9-...
# ---------------------------------------------------
analysis_id = st.query_params.get("analysis_id")

if analysis_id:
    st.subheader("Detailed Analysis from Browser Extension")

    try:
        response = requests.get(
            f"http://127.0.0.1:5000/result/{analysis_id}",
            timeout=10
        )

        if response.status_code == 200:
            stored_data = response.json()

            original_text = stored_data["text"]
            source_links = stored_data.get("source_links", [])
            result = stored_data["result"]

            st.success("Loaded analysis from browser extension.")
            display_full_analysis(
                result=result,
                original_text=original_text,
                source_links=source_links
            )

        else:
            st.error(
                "Analysis result could not be found. "
                "The Flask backend may have been restarted after the analysis."
            )

    except Exception:
        st.error(
            "Could not connect to the browser analysis API. "
            "Make sure browser_api.py is running."
        )

    # Prevent normal manual text input section from appearing
    st.stop()


# ---------------------------------------------------
# NORMAL MANUAL ANALYSIS MODE
# ---------------------------------------------------
text = st.text_area(
    "Paste text to analyze:",
    height=250,
    placeholder="Paste an online article, AI output, or social media post..."
)

if st.button("Analyze with AI"):
    if not text.strip():
        st.warning("Please enter text.")
    else:
        with st.spinner("Running AI analysis..."):
            result = analyze_full_text(
                text=text,
                source_links=[]
            )

        display_full_analysis(
            result=result,
            original_text=text,
            source_links=[]
        )