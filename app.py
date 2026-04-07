from flask import Flask, request, jsonify
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
            "site": "ManoMano",
            "title": "Geberit Duofix bâti-support WC",
            "price": 189.00,
            "url": "https://www.manomano.fr/recherche/geberit+duofix",
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
            "site": "ManoMano",
            "title": "Colonne de douche Hansgrohe Crometta",
            "price": 179.00,
            "url": "https://www.manomano.fr/recherche/colonne+douche",
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


def build_fallback_offer(query: str):
    q = query.lower().strip()

    # Si la recherche ressemble à quelque chose de déco / maison / bricolage
    if any(word in q for word in [
        "douche", "mitigeur", "robinet", "receveur", "wc",
        "lavabo", "baignoire", "colonne", "meuble", "vasque"
    ]):
        return {
            "site": "Leroy Merlin",
            "title": f"Résultats pour : {query}",
            "price": None,
            "url": f"https://www.leroymerlin.fr/recherche?q={quote_plus(query)}",
            "review_score": None
        }

    # Si ça ressemble à un achat généraliste
    if any(word in q for word in [
        "iphone", "samsung", "tv", "télé", "casque", "ordinateur",
        "bague", "bijou", "chaussure", "montre", "parfum", "cadeau"
    ]):
        return {
            "site": "Google",
            "title": f"Résultats pour : {query}",
            "price": None,
            "url": f"https://www.google.com/search?q={quote_plus(query)}",
            "review_score": None
        }

    # fallback par défaut
    return {
        "site": "Google",
        "title": f"Résultats pour : {query}",
        "price": None,
        "url": f"https://www.google.com/search?q={quote_plus(query)}",
        "review_score": None
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
    query = request.args.get("q", "").lower().strip()

    if query in CONTROLLED_RESULTS:
        return jsonify({
            "ok": True,
            "query": query,
            "mode": CONTROLLED_RESULTS[query]["mode"],
            "best_offer": CONTROLLED_RESULTS[query]["best_offer"]
        })

    fallback_offer = build_fallback_offer(query)

    return jsonify({
        "ok": True,
        "query": query,
        "mode": "fallback",
        "best_offer": fallback_offer
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


@app.route("/stats", methods=["GET"])
def stats():
    return jsonify({
        "total_clicks": len(clicks),
        "data": clicks
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
