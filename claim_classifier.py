from transformers import pipeline

claim_model = pipeline(
    "zero-shot-classification",
    model="typeform/distilbert-base-uncased-mnli"
)

LABELS = [
    "factual claim",
    "opinion",
    "speculation"
]


FACTUAL_SIGNALS = [
    "states that",
    "research published",
    "data from",
    "according to",
    "study",
    "studies",
    "report",
    "reports",
    "evidence",
    "prevented",
    "reducing",
    "increases",
    "decreases",
    "causes",
    "leads to",
    "shows",
    "support",
    "supports",
    "has",
    "have",
    "is",
    "are",
    "was",
    "were"
]


def classify_claim(sentence):
    lower = sentence.lower()

    # Strong factual override
    if any(signal in lower for signal in FACTUAL_SIGNALS):
        return {
            "sentence": sentence,
            "label": "factual claim",
            "confidence": 0.90
        }

    result = claim_model(sentence, LABELS)

    return {
        "sentence": sentence,
        "label": result["labels"][0],
        "confidence": round(result["scores"][0], 3)
    }


def classify_all_claims(sentences):
    return [classify_claim(sentence) for sentence in sentences]