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
    "villeroy", "laufen"
]


def normalize(text):
    return " ".join((text or "").lower().split())


def clean_price(price):
    if price is None:
        return None
    try:
        text = str(price).replace("€", "").replace(",", ".").replace(" ", "")
        return float(text)
    except:
        return None


def is_precise(query):
    q = normalize(query)

    has_brand = any(b in q for b in KNOWN_BRANDS)
    has_ref = re.search(r"\d{3,}", q)

    return has_brand or has_ref


def compute_trust(site, title):
    s = normalize(site)
    t = normalize(title)

    score = 70

    if "amazon" in s:
        score += 2
    if "leroy" in s:
        score += 6
    if "manomano" in s:
        score += 4
    if "cdiscount" in s:
        score -= 5

    if "promo" in t:
        score -= 3
    if "officiel" in t:
        score += 4

    return max(40, min(95, score))


def relevance(query, title):
    q = normalize(query)
    t = normalize(title)

    score = 0
    for word in q.split():
        if word in t:
            score += 10

    return score


# 🔥 NOUVEL ALGO ÉQUILIBRÉ
def value_score(offer):
    price = offer.get("price")
    trust = offer.get("trust_score", 60)
    relevance_score_val = offer.get("relevance_score", 0)

    if not price:
        return -999999

    price_score = max(0, 100 - price / 5)
    trust_score = trust * 1.2
    relevance_score_val = relevance_score_val * 1.5

    return price_score + trust_score + relevance_score_val


def choose_best(offers, mode):
    if not offers:
        return None

    valid = [o for o in offers if o["price"]]

    if not valid:
        return None

    if mode == "lowest_price":
        valid.sort(key=lambda x: x["price"])
        return valid[0]

    if mode == "value":
        valid.sort(key=lambda x: value_score(x), reverse=True)
        return valid[0]


def parse_results(data, query):
    results = []

    for item in data.get("shopping_results", [])[:20]:
        title = item.get("title", "")
        price = clean_price(item.get("price"))
        site = item.get("source", "Google")
        link = item.get("link") or "#"

        if not title or not price:
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
            "relevance_score": rel,
            "trust_score": trust
        })

    return results


@app.route("/search")
def search():
    query = request.args.get("q", "")

    if not query:
        return jsonify({"error": "query manquante"}), 400

    mode = "lowest_price" if is_precise(query) else "value"

    try:
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": SERPAPI_KEY,
            "hl": "fr",
            "gl": "fr"
        }

        r = requests.get("https://serpapi.com/search.json", params=params, timeout=5)
        data = r.json()

        offers = parse_results(data, query)

        best_offer = choose_best(offers, mode)

        lowest_offer = None
        if offers:
            lowest_offer = sorted(offers, key=lambda x: x["price"])[0]

        return jsonify({
            "query": query,
            "mode": mode,
            "best_offer": best_offer,
            "lowest_offer": lowest_offer,
            "offers": offers
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def home():
    return "Fyndy API OK"
