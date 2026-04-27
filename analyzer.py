import re
from word_lists import BIASED_WORDS, CLAIM_INDICATORS


def split_sentences(text):
    sentences = re.split(r'[.!?]', text)
    return [s.strip() for s in sentences if s.strip()]


# Claim Detection
def detect_claims(sentences):
    claims = []

    for sentence in sentences:
        if any(word in sentence.lower() for word in CLAIM_INDICATORS) or re.search(r'\d', sentence):
            claims.append(sentence)

    return claims


# Citation Checker
def detect_missing_citations(sentences):
    missing = []

    for sentence in sentences:
        has_claim = any(word in sentence.lower() for word in CLAIM_INDICATORS) or re.search(r'\d', sentence)

        has_citation = re.search(r'\(\d{4}\)|\[\d+\]|http', sentence)

        if has_claim and not has_citation:
            missing.append(sentence)

    return missing


# ias Detection
def detect_bias(text):
    found_words = []

    for word in BIASED_WORDS:
        if word in text.lower():
            found_words.append(word)

    return found_words


# Source Checker
def check_sources(text):
    if re.search(r'http|www|\[\d+\]|\(\d{4}\)', text):
        return True
    return False


# 📊 Trust Score
def calculate_score(num_missing, num_bias, has_sources):
    score = 100

    score -= num_missing * 10
    score -= num_bias * 5

    if has_sources:
        score += 5

    return max(score, 0)


# 🎯 Main Analysis Function
def analyze_text(text):
    sentences = split_sentences(text)

    claims = detect_claims(sentences)
    missing_citations = detect_missing_citations(sentences)
    bias_words = detect_bias(text)
    has_sources = check_sources(text)

    score = calculate_score(len(missing_citations), len(bias_words), has_sources)

    return {
        "claims": claims,
        "missing_citations": missing_citations,
        "bias_words": bias_words,
        "has_sources": has_sources,
        "score": score
    }