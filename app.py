from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

CONTROLLED_RESULTS = {

    # ===== PRODUITS PRÉCIS =====
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

    # ===== RECHERCHES VAGUES =====
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

    return jsonify({
        "ok": True,
        "query": query,
        "mode": "unsupported",
        "best_offer": {
            "site": "Fyndy",
            "title": "Recherche non prise en charge dans cette démo",
            "price": None,
            "url": "https://www.google.com/search?q=" + query,
            "review_score": None
        }
    })


if __name__ == "__main__":
    app.run(debug=True)
