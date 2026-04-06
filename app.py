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
CACHE_TTL_SECONDS = 900  # 15 minutes

KNOWN_BRANDS = [
    "grohe",
    "hansgrohe",
    "geberit",
    "roca",
    "nobili",
    "gessi",
    "axor",
    "dornbracht",
    "paini",
    "ideal standard",
    "jacob delafon",
    "villeroy",
    "laufen",
    "ondyna",
    "fantini",
    "cristina"
]


def normalize_spaces(text: str) -> str:
    return " ".join((text or "").split()).strip()


def normalize_text(text: str) -> str:
    text = normalize_spaces(text).lower()
    return text


def clean_price(price_value):
    """
    Convertit un prix texte en float.
    Exemples :
    "119,99 €" -> 119.99
    "1 729,00 €" -> 1729.00
    """
    if price_value is None:
        return None

    if isinstance(price_value, (int, float)):
        return float(price_value)

    try:
        text = str(price_value)
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
    q = normalize_text(query)
    return any(brand in q for brand in KNOWN_BRANDS)


def has_product_reference(query: str) -> bool:
    q = normalize_text(query)

    patterns = [
        r"\b[a-z]{0,4}\d{3,}[a-z0-9-]*\b",
        r"\b\d{5,}\b",
        r"\b[a-z]+\d+[a-z0-9-]*\b"
    ]

    return any(re.search(pattern, q, re.IGNORECASE) for pattern in patterns)


def is_precise_query(query: str) -> bool:
    q = normalize_text(query)
    words = [w for w in q.split() if w]

    if has_brand(q) and has_product_reference(q):
        return True

    if has_product_reference(q):
        return True

    if has_brand(q) and len(words) <= 5:
        return True

    return False


def fallback_offers(query: str):
    q = normalize_text(query)
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

    return [
        {
            "site": "ManoMano",
            "title": f"Résultat estimé pour {query}",
            "price": round(base * 0.90, 2),
            "url": f"https://www.manomano.fr/recherche/{quote_plus(query)}",
            "estimated": True,
            "review_score": 70,
            "trust_score": 70
        },
        {
            "site": "Leroy Merlin",
            "title": f"Résultat estimé pour {query}",
            "price": round(base * 0.95, 2),
            "url": f"https://www.leroymerlin.fr/recherche?q={quote_plus(query)}",
            "estimated": True,
            "review_score": 74,
            "trust_score": 74
        },
        {
            "site": "Amazon",
            "title": f"Résultat estimé pour {query}",
            "price": round(base * 1.05, 2),
            "url": f"https://www.amazon.fr/s?k={quote_plus(query)}",
            "estimated": True,
            "review_score": 68,
            "trust_score": 68
        }
    ]


def compute_review_score(source: str, title: str) -> int:
    """
    Score simple de confiance / avis.
    Ce n'est pas encore Avobot réel, mais une base propre.
    """
    score = 70
    src = normalize_text(source)
    ttl = normalize_text(title)

    if "amazon" in src:
        score += 2
    elif "leroy" in src:
        score += 6
    elif "manomano" in src:
        score += 4
    elif "cdiscount" in src:
        score -= 3

    if "lot" in ttl:
        score -= 2

    if "promo" in ttl:
        score -= 2

    if "officiel" in ttl:
        score += 4

    if "garantie" in ttl:
        score += 2

    return max(40, min(95, score))


def relevance_score(query: str, title: str) -> int:
    """
    Score de pertinence entre la requête et le titre produit.
    """
    q = normalize_text(query)
    t = normalize_text(title)

    q_tokens = [tok for tok in q.split() if len(tok) >= 3]
    score = 0

    for tok in q_tokens:
        if tok in t:
            score += 10

    if has_brand(q) and has_brand(t):
        score += 10

    if has_product_reference(q) and has_product_reference(t):
        score += 15

    return score


def parse_serpapi_shopping(data: dict, query: str):
    offers = []
    shopping_results = data.get("shopping_results", []) or []

    for item in shopping_results[:20]:
        title = normalize_spaces(item.get("title", ""))
        raw_price = item.get("price", "")
        source = normalize_spaces(item.get("source", "Google Shopping"))
        link = item.get("link") or item.get("product_link") or "#"

        cleaned_price = clean_price(raw_price)

        if not title:
            continue

        rel_score = relevance_score(query, title)
        review_score = compute_review_score(source, title)

        offers.append({
            "site": source or "Google Shopping",
            "title": title,
            "price": cleaned_price,
            "url": link,
            "estimated": False,
            "relevance_score": rel_score,
            "review_score": review_score,
            "trust_score": review_score
        })

    offers = [o for o in offers if o["price"] is not None]

    # On élimine les résultats totalement hors sujet
    offers = [o for o in offers if o["relevance_score"] >= 10]

    return offers


def choose_lowest_offer(offers: list):
    if not offers:
        return None
    valid = [o for o in offers if o.get("price") is not None]
    if not valid:
        return None
    valid.sort(key=lambda x: x["price"])
    return valid[0]


def value_score(offer: dict) -> float:
    """
    Score rapport qualité/prix.
    Plus haut = meilleur.
    """
    price = offer.get("price")
    trust = offer.get("trust_score", 60)
    relevance = offer.get("relevance_score", 0)

    if price is None or price <= 0:
        return -999999

    # Plus le prix est bas, mieux c'est
    price_component = 1000 / price

    # Confiance et pertinence renforcent l'offre
    trust_component = trust * 0.6
    relevance_component = relevance * 0.8

    return price_component + trust_component + relevance_component


def choose_best_value_offer(offers: list):
    if not offers:
        return None

    valid = [o for o in offers if o.get("price") is not None]
    if not valid:
        return None

    valid.sort(key=lambda x: value_score(x), reverse=True)
    return valid[0]


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "service": "Fyndy API",
        "message": "API en ligne"
    })


@app.route("/search", methods=["GET"])
def search():
    query = normalize_spaces(request.args.get("q", ""))

    if not query:
        return jsonify({
            "ok": False,
            "error": "query manquante"
        }), 400

    cached = get_cached(query)
    if cached:
        return jsonify(cached)

    mode = "lowest_price" if is_precise_query(query) else "value"

    if not SERPAPI_KEY:
        offers = fallback_offers(query)
        lowest_offer = choose_lowest_offer(offers)
        best_offer = choose_best_value_offer(offers) if mode == "value" else lowest_offer

        result = {
            "ok": True,
            "query": query,
            "mode": mode,
            "source": "fallback_no_serpapi_key",
            "used_fallback": True,
            "warning": "SERPAPI_KEY absente",
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
            "hl": "fr",
            "gl": "fr",
            "api_key": SERPAPI_KEY
        }

        resp = requests.get("https://serpapi.com/search.json", params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        offers = parse_serpapi_shopping(data, query)

        used_fallback = False
        if not offers:
            offers = fallback_offers(query)
            used_fallback = True

        lowest_offer = choose_lowest_offer(offers)
        best_offer = choose_best_value_offer(offers) if mode == "value" else lowest_offer

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

    except requests.RequestException as e:
        offers = fallback_offers(query)
        lowest_offer = choose_lowest_offer(offers)
        best_offer = choose_best_value_offer(offers) if mode == "value" else lowest_offer

        result = {
            "ok": True,
            "query": query,
            "mode": mode,
            "source": "fallback_request_error",
            "used_fallback": True,
            "warning": f"Erreur SerpAPI: {str(e)}",
            "lowest_offer": lowest_offer,
            "best_offer": best_offer,
            "offers": offers
        }
        set_cached(query, result)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"Erreur serveur: {str(e)}"
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
