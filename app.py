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

# Petit cache mémoire pour éviter de taper la source à chaque clic
CACHE = {}
CACHE_TTL_SECONDS = 600  # 10 minutes


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def extract_price(text: str):
    """
    Extrait un prix depuis une chaîne.
    Exemples gérés :
    - 132,90 €
    - 132.90€
    - 132 €
    """
    if not text:
        return None

    text = text.replace("\xa0", " ")
    match = re.search(r"(\d{1,5}(?:[.,]\d{1,2})?)\s*€", text)
    if not match:
        return None

    value = match.group(1).replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


def build_manomano_search_url(query: str) -> str:
    return f"https://www.manomano.fr/recherche/{quote_plus(query)}"


def parse_manomano_results(html: str):
    """
    Parsing best effort.
    ManoMano peut changer son HTML. On essaie plusieurs stratégies.
    """
    soup = BeautifulSoup(html, "html.parser")
    offers = []

    # 1) Première stratégie : tous les liens produits plausibles
    candidate_links = soup.select('a[href*="/p/"], a[href*="/fr/p/"], a[data-testid], a')

    seen = set()

    for link in candidate_links:
        href = link.get("href", "")
        if not href:
            continue

        # Filtre grossier pour éviter trop de bruit
        href_ok = (
            "/p/" in href
            or "/fr/p/" in href
            or "manomano.fr/" in href
        )
        if not href_ok:
            continue

        title = normalize_spaces(link.get_text(" ", strip=True))
        if not title or len(title) < 8:
            continue

        # Cherche un prix proche dans le texte du lien puis du parent
        price = extract_price(link.get_text(" ", strip=True))
        if price is None:
            parent_text = ""
            if link.parent:
                parent_text = normalize_spaces(link.parent.get_text(" ", strip=True))
            price = extract_price(parent_text)

        if price is None:
            # On tente un niveau au-dessus
            grandparent_text = ""
            if link.parent and link.parent.parent:
                grandparent_text = normalize_spaces(link.parent.parent.get_text(" ", strip=True))
            price = extract_price(grandparent_text)

        if price is None:
            continue

        if href.startswith("/"):
            href = "https://www.manomano.fr" + href

        key = (title.lower(), round(price, 2), href)
        if key in seen:
            continue
        seen.add(key)

        offers.append({
            "site": "ManoMano",
            "title": title,
            "price": round(price, 2),
            "url": href
        })

        if len(offers) >= 5:
            break

    # Tri par prix
    offers.sort(key=lambda x: x["price"])
    return offers[:3]


def fallback_offers(query: str):
    """
    Fallback si ManoMano ne renvoie rien.
    On reste honnête en marquant ces résultats comme estimés.
    """
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
            "url": build_manomano_search_url(query),
            "estimated": True,
        },
        {
            "site": "Leroy Merlin",
            "title": f"Résultat estimé pour {query}",
            "price": round(base * 0.95, 2),
            "url": f"https://www.leroymerlin.fr/recherche?q={quote_plus(query)}",
            "estimated": True,
        },
        {
            "site": "Amazon",
            "title": f"Résultat estimé pour {query}",
            "price": round(base * 1.05, 2),
            "url": f"https://www.amazon.fr/s?k={quote_plus(query)}",
            "estimated": True,
        }
    ]


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


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "service": "Fyndy API",
        "message": "API en ligne"
    })


@app.route("/search", methods=["POST"])
def search():
    payload = request.get_json(silent=True) or {}
    query = normalize_spaces(payload.get("query", ""))

    if not query:
        return jsonify({
            "ok": False,
            "error": "query manquante"
        }), 400

    cached = get_cached(query)
    if cached:
        return jsonify(cached)

    try:
        url = build_manomano_search_url(query)
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        offers = parse_manomano_results(resp.text)

        used_fallback = False
        if not offers:
            offers = fallback_offers(query)
            used_fallback = True

        result = {
            "ok": True,
            "query": query,
            "source": "manomano_search",
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