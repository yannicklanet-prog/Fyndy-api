from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import re
import time

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

CACHE = {}
CACHE_TTL_SECONDS = 900  # 15 minutes


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


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


def parse_google_shopping_results(html: str, fallback_url: str):
    soup = BeautifulSoup(html, "html.parser")
    offers = []

    # Sélecteurs best effort pour Google Shopping
    items = soup.select("div.sh-dgr__content")[:3]

    for item in items:
        title_el = item.select_one("h3") or item.select_one("h4")
        price_el = item.select_one(".a8Pemb") or item.select_one(".T14wmb")
        link_el = item.select_one("a")

        if not title_el or not price_el:
            continue

        title = normalize_spaces(title_el.get_text(" ", strip=True))
        price = normalize_spaces(price_el.get_text(" ", strip=True))
        url = fallback_url

        if link_el and link_el.get("href"):
            href = link_el.get("href")
            if href.startswith("/"):
                url = "https://www.google.com" + href
            else:
                url = href

        offers.append({
            "site": "Google Shopping",
            "title": title,
            "price": price,
            "url": url,
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

    google_url = f"https://www.google.com/search?q={quote_plus(query)}&tbm=shop"

    try:
        resp = requests.get(google_url, headers=HEADERS, timeout=3.5)
        resp.raise_for_status()

        offers = parse_google_shopping_results(resp.text, google_url)

        used_fallback = False
        if not offers:
            offers = fallback_offers(query)
            used_fallback = True

        result = {
            "ok": True,
            "query": query,
            "source": "google_shopping",
            "used_fallback": used_fallback,
            "offers": offers
        }

        set_cached(query, result)
        return jsonify(result)

    except requests.RequestException as e:
        result = {
            "ok": True,
            "query": query,
            "source": "fallback_only",
            "used_fallback": True,
            "warning": f"Source distante indisponible: {str(e)}",
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
