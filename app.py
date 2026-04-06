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


def compute_trust(site, title):
    """
    Score de confiance simple.
    Base provisoire avant vrai moteur Avobot.
    """
    s = normalize(site)
    t = normalize(title)

    score = 70

    # score vendeur/source
    if "amazon" in s:
        score += 2
    if "leroy" in s:
        score += 6
    if "manomano" in s:
        score += 4
    if "castorama" in s:
        score += 5
    if "cdiscount" in s:
        score -= 5
    if "marketplace" in s:
        score -= 8
    if "seller" in s:
        score -= 2

    # signaux titre
    if "promo" in t:
        score -= 3
    if "officiel" in t:
        score += 4
    if "garantie" in t:
        score += 2
    if "lot" in t:
        score -= 2
    if "reconditionné" in t:
        score -= 15
    if "occasion" in t:
        score -= 20

    return max(35, min(95, score))


def review_signal_from_score(score):
    if score >= 80:
        return "fiable"
    if score >= 65:
        return "correct"
    if score >= 50:
        return "prudence"
    return "douteux"


def value_score(offer):
    price = offer.get("price")
    trust = offer.get("trust_score", 60)
    relevance_score_val = offer.get("relevance_score", 0)

    if not price or price <= 0:
        return -999999

    # équilibre : prix + confiance + pertinence
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


def choose_best_offer(offers, mode):
    if not offers:
        return None

    valid = [o for o in offers if o.get("price") is not None]
    if not valid:
        return None

    if mode == "lowest_price":
        # pour une recherche précise : priorité au prix, mais on évite le douteux si possible
        safe = [o for o in valid if o.get("trust_score", 0) >= 50]
        target = safe if safe else valid
        target.sort(key=lambda x: x["price"])
        return target[0]

    # recherche vague = meilleur rapport qualité/prix
    valid.sort(key=lambda x: value_score(x), reverse=True)
    return valid[0]


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
            "estimated": True
        },
        {
            "site": "Leroy Merlin",
            "title": f"Résultat estimé pour {query}",
            "price": round(base * 0.95, 2),
            "url": f"https://www.leroymerlin.fr/recherche?q={quote_plus(query)}",
            "estimated": True
        },
        {
            "site": "Amazon",
            "title": f"Résultat estimé pour {query}",
            "price": round(base * 1.05, 2),
            "url": f"https://www.amazon.fr/s?k={quote_plus(query)}",
            "estimated": True
        }
    ]

    final = []
    for offer in offers:
        trust = compute_trust(offer["site"], offer["title"])
        offer["relevance_score"] = 20
        offer["trust_score"] = trust
        offer["review_score"] = trust
        offer["review_signal"] = review_signal_from_score(trust)
        final.append(offer)

    return final


def parse_serpapi_shopping(data, query):
    results = []

    for item in data.get("shopping_results", [])[:20]:
        title = item.get("title", "")
        price = clean_price(item.get("price"))
        site = item.get("source", "Google")
        link = item.get("link") or item.get("product_link") or "#"

        if not title or price is None:
            continue

        rel = relevance(query, title)
        if rel < 10:
            continue

        trust = compute_trust(site, title)

        results.append({
            "site": site,
            "title": title,
            "price": price,
            "url": link,
            "estimated": False,
            "relevance_score": rel,
            "review_score": trust,
            "trust_score": trust,
            "review_signal": review_signal_from_score(trust)
        })

    return results


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

        result = {
            "ok": True,
            "query": query,
            "mode": mode,
            "source": "fallback_no_serpapi_key",
            "used_fallback": True,
            "lowest_offer": lowest_offer,
            "best_offer": best_offer,
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

        result = {
            "ok": True,
            "query": query,
            "mode": mode,
            "source": "serpapi_google_shopping",
            "used_fallback": used_fallback,
            "lowest_offer": lowest_offer,
            "best_offer": best_offer,
            "offers": offers
        }

        set_cached(query, result)
        return jsonify(result)

    except Exception as e:
        offers = fallback_offers(query)
        lowest_offer = choose_lowest_offer(offers)
        best_offer = choose_best_offer(offers, mode)

        result = {
            "ok": True,
            "query": query,
            "mode": mode,
            "source": "fallback_request_error",
            "used_fallback": True,
            "warning": str(e),
            "lowest_offer": lowest_offer,
            "best_offer": best_offer,
            "offers": offers
        }
        set_cached(query, result)
        return jsonify(result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
