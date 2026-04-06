from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from urllib.parse import quote_plus

app = Flask(__name__)
CORS(app)

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()


def search_amazon(query):
    return {
        "site": "Amazon",
        "title": query,
        "price": None,
        "url": f"https://www.amazon.fr/s?k={quote_plus(query)}",
        "estimated": False,
        "review_score": None,
        "trust_score": 75
    }


def search_leroy(query):
    return {
        "site": "Leroy Merlin",
        "title": query,
        "price": None,
        "url": f"https://www.leroymerlin.fr/recherche?q={quote_plus(query)}",
        "estimated": False,
        "review_score": None,
        "trust_score": 80
    }


def search_manomano(query):
    return {
        "site": "ManoMano",
        "title": query,
        "price": None,
        "url": f"https://www.manomano.fr/recherche/{quote_plus(query)}",
        "estimated": False,
        "review_score": None,
        "trust_score": 70
    }


def fallback_real(query):
    return [
        search_leroy(query),
        search_amazon(query),
        search_manomano(query)
    ]


def parse_google(data):
    results = []

    for item in data.get("shopping_results", []):
        price = item.get("price")
        title = item.get("title")
        link = item.get("link")
        site = item.get("source")

        if not price or not title:
            continue

        results.append({
            "site": site,
            "title": title,
            "price": price,
            "url": link,
            "estimated": False,
            "review_score": None,
            "trust_score": 70
        })

    return results


@app.route("/search")
def search():
    query = request.args.get("q", "")

    if not query:
        return jsonify({"ok": False})

    # 🔥 GOOGLE SHOPPING
    if SERPAPI_KEY:
        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": SERPAPI_KEY,
                "hl": "fr",
                "gl": "fr"
            }

            r = requests.get("https://serpapi.com/search.json", params=params, timeout=5)
            data = r.json()

            offers = parse_google(data)

            if offers:
                best = sorted(offers, key=lambda x: float(str(x["price"]).replace(",", ".").replace("€", "")))[0]

                return jsonify({
                    "ok": True,
                    "best_offer": best,
                    "offers": offers,
                    "source": "google"
                })

        except:
            pass

    # 🔥 FALLBACK RÉEL (IMPORTANT)
    offers = fallback_real(query)

    return jsonify({
        "ok": True,
        "best_offer": offers[0],
        "offers": offers,
        "source": "fallback_real"
    })


if __name__ == "__main__":
    app.run(port=10000)
