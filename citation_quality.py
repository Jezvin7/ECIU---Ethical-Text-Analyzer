import re
from urllib.parse import urlparse


TRUSTED_DOMAINS = [
    "wikipedia.org",
    "who.int",
    "un.org",
    "unicef.org",
    "europa.eu",
    "gov",
    "edu",
    "nature.com",
    "springer.com",
    "sciencedirect.com",
    "thelancet.com",
    "reuters.com",
    "bbc.com",
    "apnews.com",
    "cdc.gov",
    "nih.gov"
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

TRUSTED_SOURCE_NAMES = {
    "world health organization": {
        "display_name": "World Health Organization (WHO)",
        "score": 85
    },
    "who": {
        "display_name": "World Health Organization (WHO)",
        "score": 85
    },
    "unicef": {
        "display_name": "UNICEF",
        "score": 82
    },
    "united nations": {
        "display_name": "United Nations",
        "score": 82
    },
    "the lancet": {
        "display_name": "The Lancet",
        "score": 88
    },
    "nature": {
        "display_name": "Nature",
        "score": 88
    },
    "reuters": {
        "display_name": "Reuters",
        "score": 80
    },
    "associated press": {
        "display_name": "Associated Press",
        "score": 80
    },
    "ap news": {
        "display_name": "AP News",
        "score": 80
    },
    "bbc": {
        "display_name": "BBC",
        "score": 75
    },
    "our world in data": {
        "display_name": "Our World in Data",
        "score": 78
    }
}


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


def score_single_url(url):
    normalized_url = normalize_url(url)
    domain = get_domain(normalized_url)

    if any(trusted in domain for trusted in TRUSTED_DOMAINS):
        return {
            "type": "url",
            "url": normalized_url,
            "domain": domain,
            "quality": "trusted URL source",
            "score": 90
        }

    if any(weak in domain for weak in WEAK_DOMAINS):
        return {
            "type": "url",
            "url": normalized_url,
            "domain": domain,
            "quality": "weak URL source",
            "score": 25
        }

    return {
        "type": "url",
        "url": normalized_url,
        "domain": domain,
        "quality": "unknown URL source",
        "score": 50
    }


def extract_named_sources(text):
    lower_text = text.lower()
    found = []

    for alias, metadata in TRUSTED_SOURCE_NAMES.items():
        pattern = rf"\b{re.escape(alias)}\b"

        if re.search(pattern, lower_text):
            found.append({
                "type": "named_source",
                "url": metadata["display_name"],
                "domain": None,
                "quality": "trusted named source detected",
                "score": metadata["score"]
            })

    return found


def deduplicate_sources(sources):
    unique = []
    seen = set()

    for source in sources:
        key = (
            source.get("type"),
            source.get("url"),
            source.get("domain")
        )

        if key not in seen:
            seen.add(key)
            unique.append(source)

    return unique


def score_citations(text, extra_urls=None):
    if extra_urls is None:
        extra_urls = []

    visible_urls = extract_urls(text)

    all_urls = list(dict.fromkeys(
        visible_urls + extra_urls
    ))

    url_sources = [
        score_single_url(url)
        for url in all_urls
    ]

    named_sources = extract_named_sources(text)

    all_sources = deduplicate_sources(
        url_sources + named_sources
    )

    if not all_sources:
        return {
            "overall_score": 0,
            "level": "No citations found",
            "sources": []
        }

    average_score = sum(
        source["score"] for source in all_sources
    ) / len(all_sources)

    if average_score >= 75:
        level = "High source quality"
    elif average_score >= 45:
        level = "Medium source quality"
    else:
        level = "Low source quality"

    return {
        "overall_score": round(average_score, 2),
        "level": level,
        "sources": all_sources
    }