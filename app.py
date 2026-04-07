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

# ---------------------------
# INIT STORAGE
# ---------------------------
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
# SEARCH AMAZON
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

        if not results:
            return jsonify({"ok": False})

        # on prend le premier produit valable
        best = results[0]

        offer = {
            "title": best.get("title"),
            "price": best.get("price"),
            "url": best.get("link"),
            "site": "Amazon"
        }

        return jsonify({
            "ok": True,
            "best_offer": offer
        })

    except Exception as e:
        print("ERROR SEARCH:", e)
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
                font-family: Arial;
                padding: 40px;
                background: #f9fafb;
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
            }}
            th, td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
                text-align: left;
            }}
            th {{
                background: #2563eb;
                color: white;
            }}
        </style>
    </head>
    <body>

    <h1>📊 Statistiques Fyndy</h1>

    <div class="box">
        <h2>Total clics : {len(clicks)}</h2>
    </div>

    <div class="box">
        <table>
            <tr>
                <th>Produit</th>
                <th>Recherche</th>
                <th>Source</th>
                <th>Date</th>
                <th>Lien</th>
            </tr>
    """

    for c in reversed(clicks):
        html += f"""
        <tr>
            <td>{c.get('product')}</td>
            <td>{c.get('query')}</td>
            <td>{c.get('source')}</td>
            <td>{c.get('date')}</td>
            <td><a href="{c.get('url')}" target="_blank">Voir</a></td>
        </tr>
        """

    html += """
        </table>
    </div>

    </body>
    </html>
    """

    return html


# ---------------------------
# ROOT
# ---------------------------
@app.route("/")
def home():
    return "Fyndy API running"


# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
