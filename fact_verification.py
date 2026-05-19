import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote
from functools import lru_cache

from sentence_transformers import SentenceTransformer, util


embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


# ---------------------------------------------------
# Trusted domains that may appear directly in LLM output
# ---------------------------------------------------

TRUSTED_DOMAINS = [
    "who.int",
    "unicef.org",
    "un.org",
    "europa.eu",
    "thelancet.com",
    "nature.com",
    "reuters.com",
    "bbc.com",
    "apnews.com",
    "cdc.gov",
    "nih.gov",
    "gov",
    "edu"
]


# ---------------------------------------------------
# URL extraction
# ---------------------------------------------------

def extract_urls(text):
    pattern = (
        r'https?://[^\s)>\]]+'
        r'|www\.[^\s)>\]]+'
        r'|\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b'
    )

    return re.findall(pattern, text)


def normalize_url(url):
    if not url.startswith("http"):
        return "https://" + url

    return url


def get_domain(url):
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    return parsed.netloc.replace("www.", "").lower()


def is_trusted_domain(domain):
    for trusted_domain in TRUSTED_DOMAINS:
        if (
            domain == trusted_domain
            or domain.endswith("." + trusted_domain)
            or trusted_domain in domain
        ):
            return True

    return False


def get_trusted_urls_from_text(text):
    urls = extract_urls(text)
    trusted_urls = []

    for url in urls:
        domain = get_domain(url)

        if is_trusted_domain(domain):
            trusted_urls.append(normalize_url(url))

    return list(dict.fromkeys(trusted_urls))


# ---------------------------------------------------
# Fetch direct trusted URL content
# ---------------------------------------------------

@lru_cache(maxsize=100)
def fetch_webpage_text(url):
    try:
        response = requests.get(
            url,
            timeout=12,
            headers={
                "User-Agent": "EthicalAnalyserPrototype/1.0"
            }
        )

        if response.status_code != 200:
            return ""

        content_type = response.headers.get("Content-Type", "").lower()

        if "pdf" in content_type:
            return ""

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup([
            "script",
            "style",
            "noscript",
            "header",
            "footer",
            "nav",
            "aside"
        ]):
            tag.decompose()

        text = soup.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()

        return text[:20000]

    except Exception:
        return ""


def collect_direct_trusted_url_evidence(full_text):
    trusted_urls = get_trusted_urls_from_text(full_text)
    evidence_items = []

    for url in trusted_urls[:3]:
        page_text = fetch_webpage_text(url)

        if page_text:
            evidence_items.append({
                "source": url,
                "text": page_text,
                "evidence_type": "Direct cited trusted URL"
            })

    return evidence_items


# ---------------------------------------------------
# Wikipedia Search API fallback
# ---------------------------------------------------

def search_wikipedia(claim):
    search_url = "https://en.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "list": "search",
        "srsearch": claim,
        "format": "json",
        "utf8": 1,
        "srlimit": 1
    }

    try:
        response = requests.get(
            search_url,
            params=params,
            timeout=8,
            headers={
                "User-Agent": "EthicalAnalyserPrototype/1.0"
            }
        )

        if response.status_code == 200:
            data = response.json()
            search_results = data.get("query", {}).get("search", [])

            if search_results:
                return search_results[0]["title"]

    except Exception:
        pass

    return None


def get_wikipedia_summary(title):
    if not title:
        return {
            "source": None,
            "text": ""
        }

    safe_title = quote(title.replace(" ", "_"))
    summary_url = (
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_title}"
    )

    try:
        response = requests.get(
            summary_url,
            timeout=8,
            headers={
                "User-Agent": "EthicalAnalyserPrototype/1.0"
            }
        )

        if response.status_code == 200:
            data = response.json()

            return {
                "source": data.get("content_urls", {})
                              .get("desktop", {})
                              .get("page", ""),
                "text": data.get("extract", "")
            }

    except Exception:
        pass

    return {
        "source": None,
        "text": ""
    }


def retrieve_wikipedia_evidence(claim):
    title = search_wikipedia(claim)
    wiki_data = get_wikipedia_summary(title)

    if not wiki_data["text"]:
        return []

    return [{
        "source": wiki_data["source"],
        "text": wiki_data["text"],
        "evidence_type": "Wikipedia search fallback"
    }]


# ---------------------------------------------------
# Evidence chunking and semantic matching
# ---------------------------------------------------

def split_into_evidence_chunks(text, max_chars=450):
    if not text:
        return []

    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        if len(current) + len(sentence) + 1 <= max_chars:
            current += " " + sentence if current else sentence
        else:
            if current:
                chunks.append(current)

            current = sentence

    if current:
        chunks.append(current)

    return chunks[:120]


def best_semantic_match(claim, evidence_items):
    all_chunks = []

    for item in evidence_items:
        chunks = split_into_evidence_chunks(item["text"])

        for chunk in chunks:
            all_chunks.append({
                "source": item["source"],
                "chunk": chunk,
                "evidence_type": item["evidence_type"]
            })

    if not all_chunks:
        return None

    claim_embedding = embedding_model.encode(
        claim,
        convert_to_tensor=True
    )

    chunk_texts = [item["chunk"] for item in all_chunks]

    chunk_embeddings = embedding_model.encode(
        chunk_texts,
        convert_to_tensor=True
    )

    similarities = util.cos_sim(
        claim_embedding,
        chunk_embeddings
    )[0]

    best_index = int(similarities.argmax())
    best_similarity = float(similarities[best_index])

    best_chunk = all_chunks[best_index]

    return {
        "source": best_chunk["source"],
        "summary": best_chunk["chunk"],
        "similarity": round(best_similarity, 3),
        "evidence_type": best_chunk["evidence_type"]
    }


def similarity_to_status(similarity):
    if similarity >= 0.66:
        return "Likely supported"

    if similarity >= 0.45:
        return "Partially related / needs review"

    return "Not clearly supported"


# ---------------------------------------------------
# Skip citation-only fragments
# ---------------------------------------------------

def should_skip_claim_for_verification(claim):
    lower = claim.lower().strip()

    citation_prefixes = [
        "source:",
        "available at:",
        "citation:",
        "references:"
    ]

    if any(lower.startswith(prefix) for prefix in citation_prefixes):
        return True

    if len(claim.split()) <= 3 and extract_urls(claim):
        return True

    return False


# ---------------------------------------------------
# Main single-claim verification
# ---------------------------------------------------

def verify_claim_semantically(claim, full_text):
    # 1. Try evidence from direct trusted URLs included in the LLM answer
    direct_url_evidence = collect_direct_trusted_url_evidence(full_text)

    direct_match = best_semantic_match(
        claim,
        direct_url_evidence
    )

    if direct_match and direct_match["similarity"] >= 0.45:
        return {
            "claim": claim,
            "status": similarity_to_status(direct_match["similarity"]),
            "similarity": direct_match["similarity"],
            "source": direct_match["source"],
            "summary": direct_match["summary"],
            "evidence_type": direct_match["evidence_type"]
        }

    # 2. Fall back to free Wikipedia search
    wikipedia_evidence = retrieve_wikipedia_evidence(claim)

    wikipedia_match = best_semantic_match(
        claim,
        wikipedia_evidence
    )

    if wikipedia_match:
        return {
            "claim": claim,
            "status": similarity_to_status(wikipedia_match["similarity"]),
            "similarity": wikipedia_match["similarity"],
            "source": wikipedia_match["source"],
            "summary": wikipedia_match["summary"],
            "evidence_type": wikipedia_match["evidence_type"]
        }

    # 3. No evidence retrieved
    return {
        "claim": claim,
        "status": "No reference source found",
        "similarity": 0,
        "source": None,
        "summary": "",
        "evidence_type": "No evidence retrieved"
    }


# ---------------------------------------------------
# Verify all factual claims
# ---------------------------------------------------

def verify_factual_claims(classified_claims, full_text):
    factual_claims = [
        item["sentence"]
        for item in classified_claims
        if item["label"] == "factual claim"
    ]

    verified_results = []

    for claim in factual_claims[:5]:
        if should_skip_claim_for_verification(claim):
            continue

        verified_results.append(
            verify_claim_semantically(claim, full_text)
        )

    return verified_results