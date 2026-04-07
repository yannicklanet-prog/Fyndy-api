from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from datetime import datetime
from urllib.parse import quote_plus

app = Flask(__name__)
CORS(app)

# Stockage simple en mémoire
clicks = []

CONTROLLED_RESULTS = {
    "hansgrohe ecostat 1001cl": {
        "mode": "lowest_price",
        "best_offer": {
            "site": "Amazon",
            "title": "Hansgrohe Ecostat 1001 CL Mitigeur thermostatique",
            "price": 119.99,
            "url": "https://www.amazon.fr/s?k=hansgrohe+ecostat+1001",
            "review_score": 91
        }
    },
    "grohe grohtherm 800": {
        "mode": "lowest_price",
        "best_offer": {
            "site": "Leroy Merlin",
            "title": "Grohe Grohtherm 800 Mitigeur thermostatique",
            "price": 139.00,
            "url": "https://www.leroymerlin.fr/recherche?q=grohe+grohtherm+800",
            "review_score": 88
        }
    },
    "geberit duofix": {
        "mode": "lowest_price",
        "best_offer": {
            "site": "Amazon",
            "title": "Geberit Duofix bâti-support WC",
            "price": 189.00,
            "url": "https://www.amazon.fr/s?k=geberit+duofix",
            "review_score": 90
        }
    },
    "mitigeur grohe start": {
        "mode": "lowest_price",
        "best_offer": {
            "site": "Amazon",
            "title": "Grohe Start Mitigeur lavabo",
            "price": 59.99,
            "url": "https://www.amazon.fr/s?k=grohe+start",
            "review_score": 87
        }
    },
    "colonne de douche hansgrohe": {
        "mode": "lowest_price",
        "best_offer": {
            "site": "Leroy Merlin",
            "title": "Colonne de douche Hansgrohe Crometta",
            "price": 199.00,
            "url": "https://www.leroymerlin.fr/recherche?q=hansgrohe+colonne+douche",
            "review_score": 89
        }
    },
    "mitigeur douche": {
        "mode": "value",
        "best_offer": {
            "site": "Amazon",
            "title": "Mitigeur douche Grohe Precision Trend",
            "price": 89.00,
            "url": "https://www.amazon.fr/s?k=mitigeur+douche",
            "review_score": 85
        }
    },
    "colonne de douche": {
        "mode": "value",
        "best_offer": {
            "site": "Leroy Merlin",
            "title": "Colonne de douche thermostatique",
            "price": 179.00,
            "url": "https://www.leroymerlin.fr/recherche?q=colonne+de+douche",
            "review_score": 86
        }
    },
    "receveur douche": {
        "mode": "value",
        "best_offer": {
            "site": "Leroy Merlin",
            "title": "Receveur de douche extra plat",
            "price": 129.00,
            "url": "https://www.leroymerlin.fr/recherche?q=receveur+douche",
            "review_score": 82
        }
    }
}


def normalize_query(query: str) -> str:
    return " ".join((query or "").strip().lower().split())


def is_precise_query(query: str) -> bool:
    q = normalize_query(query)
    words = q.split()

    if len(words) >= 3:
        return True

    has_digit = any(char.isdigit() for char in q)
    if has_digit:
        return True

    return False


def build_amazon_offer(query: str):
    return {
        "site": "Amazon",
        "title": f"Offres Amazon pour : {query}",
        "price": None,
        "url": f"https://www.amazon.fr/s?k={quote_plus(query)}",
        "review_score": None
    }


def build_leroy_offer(query: str):
    return {
        "site": "Leroy Merlin",
        "title": f"Offres Leroy Merlin pour : {query}",
        "price": None,
        "url": f"https://www.leroymerlin.fr/recherche?q={quote_plus(query)}",
        "review_score": None
    }


def build_fallback_offer(query: str):
    q = normalize_query(query)

    habitat_keywords = [
        "douche", "mitigeur", "receveur", "wc", "lavabo", "robinet",
        "chauffe", "plomberie", "bain", "vasque", "paroi", "meuble",
        "colonne", "sanitaire", "robinetterie"
    ]

    if any(k in q for k in habitat_keywords):
        return {
            "mode": "fallback_habitat",
            "best_offer": build_leroy_offer(query)
        }

    if is_precise_query(q):
        return {
            "mode": "fallback_precise",
            "best_offer": build_amazon_offer(query)
        }

    return {
        "mode": "fallback_general",
        "best_offer": build_amazon_offer(query)
    }


@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "service": "Fyndy API",
        "message": "API en ligne"
    })


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    normalized_query = normalize_query(query)

    if not normalized_query:
        return jsonify({
            "ok": False,
            "error": "query manquante"
        }), 400

    if normalized_query in CONTROLLED_RESULTS:
        return jsonify({
            "ok": True,
            "query": query,
            "mode": CONTROLLED_RESULTS[normalized_query]["mode"],
            "best_offer": CONTROLLED_RESULTS[normalized_query]["best_offer"]
        })

    fallback = build_fallback_offer(query)

    return jsonify({
        "ok": True,
        "query": query,
        "mode": fallback["mode"],
        "best_offer": fallback["best_offer"]
    })


@app.route("/track_click", methods=["POST"])
def track_click():
    data = request.get_json(silent=True) or {}

    click = {
        "query": data.get("query"),
        "product": data.get("product"),
        "price": data.get("price"),
        "source": data.get("source"),
        "url": data.get("url"),
        "timestamp": datetime.now().isoformat()
    }

    clicks.append(click)
    print("CLICK:", click)

    return jsonify({
        "status": "ok",
        "message": "clic enregistré"
    })


@app.route("/stats-data")
def stats_data():
    return jsonify({
        "total_clicks": len(clicks),
        "data": clicks
    })


@app.route("/stats")
def stats_page():
    with open("stats.html", "r", encoding="utf-8") as f:
        html = f.read()
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
