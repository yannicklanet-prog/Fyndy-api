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
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

def load_clicks():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_click(click):
    data = load_clicks()
    data.append(click)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

@app.route("/")
def home():
    return "Fyndy API running"

# ---------------------------
# SEARCH AMAZON INTELLIGENT
# ---------------------------
@app.route("/search")
def search():
    query = request.args.get("q")

    if not query:
        return jsonify({"ok": False, "error": "query manquante"})

    if not SERPAPI_KEY:
        return jsonify({"ok": False, "error": "SERPAPI_KEY manquante sur Render"})

    try:
        params = {
            "engine": "amazon",
            "amazon_domain": "amazon.fr",
            "search_term": query,
            "api_key": SERPAPI_KEY
        }

        res = requests.get("https://serpapi.com/search", params=params, timeout=30)
        data = res.json()

        results = data.get("organic_results", [])

        prices = []
        offers = []

        for r in results[:5]:
            price_data = r.get("price")
            price = None

            if isinstance(price_data, dict):
                value = price_data.get("value")
                try:
                    if value is not None:
                        price = float(value)
                except:
                    price = None

            elif isinstance(price_data, str):
                try:
                    cleaned = (
                        price_data.replace("€", "")
                        .replace("\u202f", "")
                        .replace("\xa0", "")
                        .replace(" ", "")
                        .replace(",", ".")
                        .strip()
                    )
                    price = float(cleaned)
                except:
                    price = None

            elif isinstance(price_data, (int, float)):
                try:
                    price = float(price_data)
                except:
                    price = None

            if price is not None:
                prices.append(price)
                offers.append({
                    "title": r.get("title"),
                    "price": round(price, 2),
                    "url": r.get("link"),
                    "site": "Amazon"
                })

        # fallback si SerpAPI ne renvoie pas de prix exploitables
        if not offers:
            fallback_offer = {
                "title": f"Offres Amazon pour : {query}",
                "price": None,
                "url": f"https://www.amazon.fr/s?k={query.replace(' ', '+')}",
                "site": "Amazon"
            }

            return jsonify({
                "ok": True,
                "best_offer": fallback_offer,
                "avg_price": None,
                "min_price": None,
                "all_prices": []
            })

        avg_price = round(sum(prices) / len(prices), 2)
        min_price = round(min(prices), 2)

        best_offer = min(offers, key=lambda x: x["price"])

        return jsonify({
            "ok": True,
            "best_offer": best_offer,
            "avg_price": avg_price,
            "min_price": min_price,
            "all_prices": prices
        })

    except Exception as e:
        print("ERROR SEARCH:", e)
        return jsonify({"ok": False, "error": str(e)})

# ---------------------------
# TRACK CLICK
# ---------------------------
@app.route("/track_click", methods=["POST"])
def track_click():
    data = request.get_json(silent=True) or {}

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
# STATS PAGE
# ---------------------------
@app.route("/stats")
def stats():
    clicks = load_clicks()

    html = f"""
    <html>
    <head>
        <title>Fyndy Stats</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 40px;
                background: #f9fafb;
                color: #111827;
            }}
            h1 {{
                margin-bottom: 20px;
            }}
            .box {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 20px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            }}
            th, td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
                text-align: left;
                font-size: 14px;
            }}
            th {{
                background: #2563eb;
                color: white;
            }}
            a {{
                color: #2563eb;
                text-decoration: none;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>

    <h1>📊 Stats Fyndy</h1>

    <div class="box">
        <h2>Total clics : {len(clicks)}</h2>
    </div>

    <div class="box">
        <table>
            <tr>
                <th>Produit</th>
                <th>Recherche</th>
                <th>Source</th>
                <th>Prix</th>
                <th>Date</th>
                <th>Lien</th>
            </tr>
    """

    for c in reversed(clicks):
        html += f"""
        <tr>
            <td>{c.get('product', '')}</td>
            <td>{c.get('query', '')}</td>
            <td>{c.get('source', '')}</td>
            <td>{c.get('price', '-') if c.get('price') is not None else '-'}</td>
            <td>{c.get('date', '')}</td>
            <td><a href="{c.get('url', '#')}" target="_blank">Voir</a></td>
        </tr>
        """

    html += """
        </table>
    </div>

    </body>
    </html>
    """

    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
