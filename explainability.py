from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

model_name = "google/flan-t5-small"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)


def generate_ai_explanation(
    trust_score,
    classified_claims,
    fact_results,
    bias_result,
    citation_result
):
    factual_claims = [
        item for item in classified_claims
        if item["label"] == "factual claim"
    ]

    unsupported_claims = [
        item for item in fact_results
        if item["status"] != "Likely supported"
    ]

    biased_words = bias_result.get("biased_words", [])
    top_emotion = bias_result.get("top_emotion", "unknown")
    bias_score = bias_result.get("bias_risk_score", 0)

    citation_level = citation_result.get("level", "unknown")
    citation_score = citation_result.get("overall_score", 0)

    prompt = f"""
Write a short explanation.

Trust score: {trust_score}/100.
Factual claims: {len(factual_claims)}.
Unsupported claims: {len(unsupported_claims)}.
Bias emotion: {top_emotion}.
Bias score: {bias_score}/100.
Biased words: {biased_words}.
Citation quality: {citation_level}.
Citation score: {citation_score}/100.

Explain whether the content should be trusted.
"""

    try:
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )

        outputs = model.generate(
            **inputs,
            max_new_tokens=150,
            num_beams=4,
            do_sample=False
        )

        ai_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

    except Exception:
        ai_text = ""

    # Reliable fallback explanation
    explanation = f"""
The content received a trust score of {trust_score}/100.

The system detected {len(factual_claims)} factual claim(s), and {len(unsupported_claims)} of them were not clearly supported by the available reference source.

The AI bias detector identified the dominant emotional tone as "{top_emotion}" with a bias risk score of {bias_score}/100.
"""

    if biased_words:
        explanation += f'\nEmotionally or biased language was detected, including: {", ".join(biased_words)}.'
    else:
        explanation += "\nNo strong biased keywords were detected."

    explanation += f"""

The citation quality was rated as "{citation_level}" with a citation score of {citation_score}/100.

Overall recommendation: """

    if trust_score >= 75:
        explanation += "the content appears mostly reliable, but important claims should still be checked."
    elif trust_score >= 50:
        explanation += "the content should be trusted with caution because some claims, citations, or emotional language may need review."
    else:
        explanation += "the content should not be fully trusted without further verification."

    if ai_text and len(ai_text.split()) > 8:
        explanation += f"\n\nAI-generated summary: {ai_text}"

    return explanation