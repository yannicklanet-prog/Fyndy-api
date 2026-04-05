from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import time
from urllib.parse import quote_plus

app = Flask(__name__)
CORS(app)

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()

CACHE = {}
CACHE_TTL_SECONDS = 900  # 15 minutes


def normalize_spaces(text: str) -> str:
    return " ".join((text or "").split()).strip()


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


def fallback_offers(query: str):
    q = (query or "").lower()
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

    return [
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


def parse_serpapi_shopping(data: dict):
    offers = []

    shopping_results = data.get("shopping_results", []) or []

    for item in shopping_results[:3]:
        title = normalize_spaces(item.get("title", ""))
        price = item.get("price", "")
        source = normalize_spaces(item.get("source", "Google Shopping"))
        link = item.get("link") or item.get("product_link") or "#"

        if not title:
            continue

        offers.append({
            "site": source or "Google Shopping",
            "title": title,
            "price": price,
            "url": link,
            "estimated": False
        })

    return offers


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

    if not SERPAPI_KEY:
        result = {
            "ok": True,
            "query": query,
            "source": "fallback_no_serpapi_key",
            "used_fallback": True,
            "warning": "SERPAPI_KEY absente",
            "offers": fallback_offers(query)
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

        offers = parse_serpapi_shopping(data)

        used_fallback = False
        if not offers:
            offers = fallback_offers(query)
            used_fallback = True

        result = {
            "ok": True,
            "query": query,
            "source": "serpapi_google_shopping",
            "used_fallback": used_fallback,
            "offers": offers
        }

        set_cached(query, result)
        return jsonify(result)

    except requests.RequestException as e:
        result = {
            "ok": True,
            "query": query,
            "source": "fallback_request_error",
            "used_fallback": True,
            "warning": f"Erreur SerpAPI: {str(e)}",
            "offers": fallback_offers(query)
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
