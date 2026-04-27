import streamlit as st
from analyzer import analyze_text

st.set_page_config(page_title="Ethical Text Analyzer", layout="centered")

st.title("Ethical Text Analyzer")
st.write("Analyze text for ethical information quality issues.")

text_input = st.text_area("Paste your text here:", height=200)

if st.button("Analyze"):
    if text_input.strip() == "":
        st.warning("Please enter some text.")
    else:
        result = analyze_text(text_input)

        st.subheader("Analysis Report")

        # Claims
        st.write(f"Claims detected: {len(result['claims'])}")
        if result['claims']:
            with st.expander("View Claims"):
                for c in result['claims']:
                    st.write(f"- {c}")

        # Missing citations
        st.write(f"Missing citations: {len(result['missing_citations'])}")
        if result['missing_citations']:
            with st.expander("View Missing Citations"):
                for m in result['missing_citations']:
                    st.write(f"- {m}")

        # Bias words
        st.write(f"Bias words found: {len(result['bias_words'])}")
        if result['bias_words']:
            st.write(", ".join(result['bias_words']))

        # Sources
        if result['has_sources']:
            st.success("Sources detected")
        else:
            st.error("No sources found")

        # Score
        st.subheader(f"Trust Score: {result['score']} / 100")

        # Color feedback
        if result['score'] > 75:
            st.success("High reliability")
        elif result['score'] > 50:
            st.warning("Moderate reliability")
        else:
            st.error("Low reliability")