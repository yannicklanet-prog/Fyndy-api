from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import time
from urllib.parse import quote_plus
import re

app = Flask(__name__)
CORS(app)

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()

CACHE = {}
CACHE_TTL_SECONDS = 900

KNOWN_BRANDS = [
    "grohe", "hansgrohe", "geberit", "roca",
    "nobili", "gessi", "axor", "dornbracht",
    "paini", "ideal standard", "jacob delafon",
    "villeroy", "laufen", "ondyna", "fantini", "cristina"
]


def normalize(text):
    return " ".join((text or "").lower().split())


def clean_price(price):
    if price is None:
        return None
    try:
        text = str(price)
        text = text.replace("€", "")
        text = text.replace("\u20ac", "")
        text = text.replace("\xa0", " ")
        text = text.replace(" ", "")
        text = text.replace(",", ".")
        return float(text)
    except Exception:
        return None


def clean_rating(value):
    if value is None:
        return None
    try:
        text = str(value).replace(",", ".").strip()
        match = re.search(r"\d+(\.\d+)?", text)
        if not match:
            return None
        rating = float(match.group())
        if 0 <= rating <= 5:
            return rating
        return None
    except Exception:
        return None


def clean_reviews_count(value):
    if value is None:
        return 0
    try:
        text = str(value).replace("\xa0", " ").replace(" ", "")
        text = re.sub(r"[^\d]", "", text)
        return int(text) if text else 0
    except Exception:
        return 0


def get_cached(query: str):
    entry = CACHE.get(query)
    if not entry:
        return None

    if time.time() - entry["ts"] > CACHE_TTL_SECONDS:
        CACHE.pop(query, None)
        return None

    return entry["data"]


def set_cached(query: str, data):
    CACHE[query] = {
        "ts": time.time(),
        "data": data
    }


def has_brand(query: str) -> bool:
    q = normalize(query)
    return any(b in q for b in KNOWN_BRANDS)


def has_product_reference(query: str) -> bool:
    q = normalize(query)
    patterns = [
        r"\b[a-z]{0,4}\d{3,}[a-z0-9-]*\b",
        r"\b\d{3,}[a-z-]*\b"
    ]
    return any(re.search(pattern, q, re.IGNORECASE) for pattern in patterns)


def is_precise(query: str) -> bool:
    q = normalize(query)
    words = [w for w in q.split() if w]

    if has_brand(q) and has_product_reference(q):
        return True

    if has_product_reference(q):
        return True

    if has_brand(q) and len(words) <= 5:
        return True

    return False


def relevance(query, title):
    q = normalize(query)
    t = normalize(title)

    score = 0
    for word in q.split():
        if len(word) >= 3 and word in t:
            score += 10

    if has_brand(q) and has_brand(t):
        score += 10

    if has_product_reference(q) and has_product_reference(t):
        score += 15

    return score


def is_comparator_site(site: str, title: str = ""):
    s = normalize(site)
    t = normalize(title)

    keywords = [
        "idealo",
        "klarna",
        "kelkoo",
        "shopalike",
        "google shopping",
        "shopping",
        "comparateur",
        "compare",
        "comparer",
        "prix",
        "offers",
        "offer",
        "deals",
        "deal"
    ]

    for k in keywords:
        if k in s or k in t:
            return True

    return False


def review_signal_from_score(score):
    if score >= 80:
        return "fiable"
    if score >= 65:
        return "correct"
    if score >= 50:
        return "prudence"
    return "douteux"


def compute_review_score(site, title, rating=None, reviews_count=0, price=None, median_price=None):
    """
    Détecteur d'avis amélioré :
    - note moyenne
    - volume d'avis
    - vendeur/source
    - signaux suspects
    - prix anormalement bas
    """
    s = normalize(site)
    t = normalize(title)

    score = 60

    # Source / vendeur
    if "amazon" in s:
        score += 4
    if "leroy" in s:
        score += 7
    if "manomano" in s:
        score += 4
    if "castorama" in s:
        score += 6
    if "darty" in s:
        score += 6
    if "lapeyre" in s:
        score += 5
    if "bricoman" in s:
        score += 3
    if "marketplace" in s:
        score -= 10
    if "seller" in s:
        score -= 4
    if "cdiscount" in s:
        score -= 5

    # Comparateurs = pas vendeur direct
    if is_comparator_site(site, title):
        score -= 14

    # Signaux titre
    if "promo" in t:
        score -= 3
    if "officiel" in t:
        score += 4
    if "garantie" in t:
        score += 2
    if "lot" in t:
        score -= 2
    if "reconditionné" in t:
        score -= 18
    if "occasion" in t:
        score -= 20
    if "compatible" in t:
        score -= 8

    # Note moyenne
    if rating is not None:
        if rating >= 4.7:
            score += 12
        elif rating >= 4.5:
            score += 9
        elif rating >= 4.2:
            score += 5
        elif rating >= 4.0:
            score += 2
        elif rating >= 3.7:
            score -= 4
        else:
            score -= 10

    # Nombre d'avis
    if reviews_count >= 500:
        score += 10
    elif reviews_count >= 200:
        score += 8
    elif reviews_count >= 100:
        score += 6
    elif reviews_count >= 30:
        score += 3
    elif reviews_count >= 10:
        score += 1
    elif reviews_count > 0:
        score -= 3

    # Signaux suspects : très bonne note avec très peu d'avis
    if rating is not None and reviews_count > 0:
        if rating >= 4.8 and reviews_count < 10:
            score -= 10
        if rating >= 4.7 and reviews_count < 5:
            score -= 12

    # Prix anormalement bas par rapport au marché détecté
    if price is not None and median_price is not None and median_price > 0:
        ratio = price / median_price
        if ratio < 0.75:
            score -= 12
        elif ratio < 0.85:
            score -= 7
        elif ratio < 0.92:
            score -= 3

    return max(25, min(95, round(score)))


def value_score(offer):
    price = offer.get("price")
    trust = offer.get("trust_score", 60)
    relevance_score_val = offer.get("relevance_score", 0)

    if not price or price <= 0:
        return -999999

    price_score = max(0, 100 - price / 5)
    trust_score = trust * 1.2
    relevance_component = relevance_score_val * 1.5

    return price_score + trust_score + relevance_component


def choose_lowest_offer(offers):
    if not offers:
        return None

    valid = [o for o in offers if o.get("price") is not None]
    if not valid:
        return None

    valid.sort(key=lambda x: x["price"])
    return valid[0]


def choose_cheaper_comparator_offer(offers, best_offer):
    if not offers or not best_offer:
        return None

    comparators = [
        o for o in offers
        if o.get("price") is not None
        and is_comparator_site(o.get("site", ""), o.get("title", ""))
    ]

    if not comparators:
        return None

    comparators.sort(key=lambda x: x["price"])
    cheapest = comparators[0]

    if cheapest["price"] < best_offer["price"]:
        return cheapest

    return None


def choose_best_offer(offers, mode):
    if not offers:
        return None

    valid = [o for o in offers if o.get("price") is not None]
    if not valid:
        return None

    direct_sellers = [
        o for o in valid
        if not is_comparator_site(o.get("site", ""), o.get("title", ""))
    ]

    if mode == "lowest_price":
        target = direct_sellers if direct_sellers else valid
        safe = [o for o in target if o.get("trust_score", 0) >= 50]
        final_target = safe if safe else target
        final_target.sort(key=lambda x: x["price"])
        return final_target[0]

    target = direct_sellers if direct_sellers else valid
    target.sort(key=lambda x: value_score(x), reverse=True)
    return target[0]


def enrich_offers_with_review_score(offers):
    priced = [o["price"] for o in offers if o.get("price") is not None]
    median_price = None

    if priced:
        priced_sorted = sorted(priced)
        n = len(priced_sorted)
        if n % 2 == 1:
            median_price = priced_sorted[n // 2]
        else:
            median_price = (priced_sorted[n // 2 - 1] + priced_sorted[n // 2]) / 2

    final = []
    for offer in offers:
        score = compute_review_score(
            site=offer.get("site", ""),
            title=offer.get("title", ""),
            rating=offer.get("rating"),
            reviews_count=offer.get("reviews_count", 0),
            price=offer.get("price"),
            median_price=median_price
        )
        offer["review_score"] = score
        offer["trust_score"] = score
        offer["review_signal"] = review_signal_from_score(score)
        final.append(offer)

    return final


def fallback_offers(query):
    q = normalize(query)
    base = 150

    if "mitigeur" in q:
        base = 120
    elif "colonne" in q:
        base = 250
    elif "robinet" in q:
        base = 90
    elif "wc" in q:
        base = 300
    elif "receveur" in q:
        base = 220
    elif "iphone" in q:
        base = 900

    offers = [
        {
            "site": "ManoMano",
            "title": f"Résultat estimé pour {query}",
            "price": round(base * 0.90, 2),
            "url": f"https://www.manomano.fr/recherche/{quote_plus(query)}",
            "estimated": True,
            "relevance_score": 20,
            "rating": None,
            "reviews_count": 0,
            "is_comparator": False
        },
        {
            "site": "Leroy Merlin",
            "title": f"Résultat estimé pour {query}",
            "price": round(base * 0.95, 2),
            "url": f"https://www.leroymerlin.fr/recherche?q={quote_plus(query)}",
            "estimated": True,
            "relevance_score": 20,
            "rating": None,
            "reviews_count": 0,
            "is_comparator": False
        },
        {
            "site": "Amazon",
            "title": f"Résultat estimé pour {query}",
            "price": round(base * 1.05, 2),
            "url": f"https://www.amazon.fr/s?k={quote_plus(query)}",
            "estimated": True,
            "relevance_score": 20,
            "rating": None,
            "reviews_count": 0,
            "is_comparator": False
        }
    ]

    return enrich_offers_with_review_score(offers)


def parse_serpapi_shopping(data, query):
    results = []

    for item in data.get("shopping_results", [])[:20]:
        title = item.get("title", "")
        price = clean_price(item.get("price"))
        site = item.get("source", "Google")
        link = item.get("link") or item.get("product_link") or "#"
        rating = clean_rating(item.get("rating"))
        reviews_count = clean_reviews_count(item.get("reviews"))

        if not title or price is None:
            continue

        rel = relevance(query, title)
        if rel < 10:
            continue

        results.append({
            "site": site,
            "title": title,
            "price": price,
            "url": link,
            "estimated": False,
            "relevance_score": rel,
            "rating": rating,
            "reviews_count": reviews_count,
            "is_comparator": is_comparator_site(site, title)
        })

    return enrich_offers_with_review_score(results)


@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "service": "Fyndy API",
        "message": "API en ligne"
    })


@app.route("/search")
def search():
    query = request.args.get("q", "")

    if not query:
        return jsonify({"ok": False, "error": "query manquante"}), 400

    cached = get_cached(query)
    if cached:
        return jsonify(cached)

    mode = "lowest_price" if is_precise(query) else "value"

    if not SERPAPI_KEY:
        offers = fallback_offers(query)
        lowest_offer = choose_lowest_offer(offers)
        best_offer = choose_best_offer(offers, mode)
        cheaper_comparator_offer = choose_cheaper_comparator_offer(offers, best_offer)

        result = {
            "ok": True,
            "query": query,
            "mode": mode,
            "source": "fallback_no_serpapi_key",
            "used_fallback": True,
            "lowest_offer": lowest_offer,
            "best_offer": best_offer,
            "cheaper_comparator_offer": cheaper_comparator_offer,
            "has_cheaper_comparator": cheaper_comparator_offer is not None,
            "offers": offers
        }
        set_cached(query, result)
        return jsonify(result)

    try:
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": SERPAPI_KEY,
            "hl": "fr",
            "gl": "fr"
        }

        r = requests.get("https://serpapi.com/search.json", params=params, timeout=5)
        r.raise_for_status()
        data = r.json()

        offers = parse_serpapi_shopping(data, query)

        used_fallback = False
        if not offers:
            offers = fallback_offers(query)
            used_fallback = True

        lowest_offer = choose_lowest_offer(offers)
        best_offer = choose_best_offer(offers, mode)
        cheaper_comparator_offer = choose_cheaper_comparator_offer(offers, best_offer)

        result = {
            "ok": True,
            "query": query,
            "mode": mode,
            "source": "serpapi_google_shopping",
            "used_fallback": used_fallback,
            "lowest_offer": lowest_offer,
            "best_offer": best_offer,
            "cheaper_comparator_offer": cheaper_comparator_offer,
            "has_cheaper_comparator": cheaper_comparator_offer is not None,
            "offers": offers
        }

        set_cached(query, result)
        return jsonify(result)

    except Exception as e:
        offers = fallback_offers(query)
        lowest_offer = choose_lowest_offer(offers)
        best_offer = choose_best_offer(offers, mode)
        cheaper_comparator_offer = choose_cheaper_comparator_offer(offers, best_offer)

        result = {
            "ok": True,
            "query": query,
            "mode": mode,
            "source": "fallback_request_error",
            "used_fallback": True,
            "warning": str(e),
            "lowest_offer": lowest_offer,
            "best_offer": best_offer,
            "cheaper_comparator_offer": cheaper_comparator_offer,
            "has_cheaper_comparator": cheaper_comparator_offer is not None,
            "offers": offers
        }
        set_cached(query, result)
        return jsonify(result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
