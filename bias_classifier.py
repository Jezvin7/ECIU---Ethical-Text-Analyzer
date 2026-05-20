from transformers import pipeline

emotion_model = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    top_k=None
)

BIAS_KEYWORDS = [
    "shocking", "disaster", "obviously", "clearly",
    "worst", "best", "always", "never",
    "dangerous", "fake", "corrupt", "evil",
    "panic", "threat", "destroy"
]


def detect_bias(text):
    emotions = emotion_model(text[:512])[0]
    emotions = sorted(emotions, key=lambda x: x["score"], reverse=True)

    top_emotion = emotions[0]

    found_keywords = [
        word for word in BIAS_KEYWORDS
        if word in text.lower()
    ]

    emotional_risk = 0

    if (top_emotion["label"].lower() in ["anger", "fear", "disgust"]
    and found_keywords):
        emotional_risk += 30
        
    emotional_risk += len(found_keywords) * 10
    emotional_risk = min(emotional_risk, 100)

    return {
        "top_emotion": top_emotion["label"],
        "emotion_confidence": round(top_emotion["score"], 3),
        "biased_words": found_keywords,
        "bias_risk_score": emotional_risk
    }