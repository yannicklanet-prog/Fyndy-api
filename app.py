from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
DATA_FILE = "clicks.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)

def load_clicks():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_click(click):
    data = load_clicks()
    data.append(click)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------------------------
# SEARCH INTELLIGENTE
# ---------------------------
@app.route("/search")
def search():
    query = request.args.get("q")

    if not query:
        return jsonify({"ok": False})

    try:
        params = {
            "engine": "amazon",
            "amazon_domain": "amazon.fr",
            "search_term": query,
            "api_key": SERPAPI_KEY
        }

        res = requests.get("https://serpapi.com/search", params=params)
        data = res.json()

        results = data.get("organic_results", [])

        prices = []
        offers = []

        for r in results[:5]:
            price = r.get("price")
            if price:
                try:
                    price = float(str(price).replace("€", "").replace(",", "."))
                    prices.append(price)
                    offers.append({
                        "title": r.get("title"),
                        "price": price,
                        "url": r.get("link"),
                        "site": "Amazon"
                    })
                except:
                    pass

        if not prices:
            return jsonify({"ok": False})

        avg_price = sum(prices) / len(prices)
        min_price = min(prices)

        best_offer = min(offers, key=lambda x: x["price"])

        return jsonify({
            "ok": True,
            "best_offer": best_offer,
            "avg_price": round(avg_price, 2),
            "min_price": min_price,
            "all_prices": prices
        })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"ok": False})

# ---------------------------
# TRACK CLICK
# ---------------------------
@app.route("/track_click", methods=["POST"])
def track_click():
    data = request.json

    click = {
        "query": data.get("query"),
        "product": data.get("product"),
        "price": data.get("price"),
        "source": data.get("source"),
        "url": data.get("url"),
        "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    save_click(click)

    return jsonify({"ok": True})

# ---------------------------
# STATS
# ---------------------------
@app.route("/stats")
def stats():
    clicks = load_clicks()

    html = f"""
    <html>
    <body style="font-family:Arial;padding:40px;">
    <h1>Stats Fyndy</h1>
    <h2>Total clics : {len(clicks)}</h2>
    <table border="1" cellpadding="10">
    <tr><th>Produit</th><th>Recherche</th><th>Date</th></tr>
    """

    for c in reversed(clicks):
        html += f"<tr><td>{c['product']}</td><td>{c['query']}</td><td>{c['date']}</td></tr>"

    html += "</table></body></html>"

    return html

@app.route("/")
def home():
    return "Fyndy API running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
