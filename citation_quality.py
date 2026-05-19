import re
from urllib.parse import urlparse

TRUSTED_DOMAINS = [
    "wikipedia.org",
    "who.int",
    "un.org",
    "europa.eu",
    "gov",
    "edu",
    "nature.com",
    "springer.com",
    "sciencedirect.com",
    "reuters.com",
    "bbc.com",
    "apnews.com"
]

WEAK_DOMAINS = [
    "blogspot",
    "medium.com",
    "reddit.com",
    "facebook.com",
    "x.com",
    "tiktok.com",
    "instagram.com"
]

def extract_urls(text):
    pattern = r'https?://[^\s]+|www\.[^\s]+|\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b'
    return re.findall(pattern, text)


def get_domain(url):
    if not url.startswith("http"):
        url = "https://" + url

    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")


def score_single_source(url):
    domain = get_domain(url)
    lower_domain = domain.lower()

    if any(trusted in lower_domain for trusted in TRUSTED_DOMAINS):
        return {
            "url": url,
            "domain": domain,
            "quality": "trusted",
            "score": 90
        }

    if any(weak in lower_domain for weak in WEAK_DOMAINS):
        return {
            "url": url,
            "domain": domain,
            "quality": "weak",
            "score": 25
        }

    return {
        "url": url,
        "domain": domain,
        "quality": "unknown",
        "score": 50
    }


def score_citations(text):
    urls = extract_urls(text)

    if not urls:
        return {
            "overall_score": 0,
            "level": "No citations found",
            "sources": []
        }

    source_scores = [
        score_single_source(url)
        for url in urls
    ]

    average_score = sum(item["score"] for item in source_scores) / len(source_scores)

    if average_score >= 75:
        level = "High source quality"
    elif average_score >= 45:
        level = "Medium source quality"
    else:
        level = "Low source quality"

    return {
        "overall_score": round(average_score, 2),
        "level": level,
        "sources": source_scores
    }