from flask import Flask, request, jsonify
from analysis_core import analyze_full_text
import uuid

app = Flask(__name__)
ANALYSIS_RESULTS = {}


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "No text provided"}), 400

    result = analyze_full_text(text)

    analysis_id = str(uuid.uuid4())

    ANALYSIS_RESULTS[analysis_id] = {
        "text": text,
        "result": result
    }

    return jsonify({
        "analysis_id": analysis_id,
        "trust_score": result["trust_score"],
        "explanation": result["ai_explanation"],
        "bias": result["bias_result"],
        "citations": result["citation_result"]
    })


@app.route("/result/<analysis_id>", methods=["GET"])
def get_result(analysis_id):
    stored = ANALYSIS_RESULTS.get(analysis_id)

    if not stored:
        return jsonify({"error": "Analysis not found"}), 404

    return jsonify(stored)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)