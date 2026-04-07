from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
import json
from urllib.parse import quote_plus

app = Flask(__name__)
CORS(app)

DATA_FILE = "clicks.json"

def ensure_data_file():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)

def load_clicks():
    ensure_data_file()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_click(click):
    clicks = load_clicks()
    clicks.append(click)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(clicks, f, ensure_ascii=False, indent=2)

@app.route("/")
def home():
    return "Fyndy API OK"

# Endpoint utilisé par l’extension
@app.route("/search")
def search():
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({"ok": False, "error": "query manquante"})

    # Prototype vendeur contrôlé :
    # on renvoie une offre fallback propre et toujours valide
    best_offer = {
        "title": f"Offres Amazon pour : {query}",
        "price": None,
        "url": f"https://www.amazon.fr/s?k={quote_plus(query)}",
        "site": "Amazon"
    }

    return jsonify({
        "ok": True,
        "best_offer": best_offer,
        "avg_price": None
    })

# Tracking robuste
@app.route("/track_click", methods=["POST"])
def track_click():
    data = request.get_json(silent=True) or {}

    click = {
        "product": data.get("product"),
        "query": data.get("query"),
        "source": data.get("source"),
        "price": data.get("price"),
        "url": data.get("url"),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    save_click(click)

    return jsonify({"ok": True, "message": "clic enregistré"})

# Stats JSON
@app.route("/stats-data")
def stats_data():
    clicks = load_clicks()
    return jsonify({
        "total_clicks": len(clicks),
        "data": clicks
    })

# Stats HTML propre
@app.route("/stats")
def stats():
    clicks = load_clicks()

    rows = ""
    for c in reversed(clicks):
        rows += f"""
        <tr>
            <td>{c.get('product') or ''}</td>
            <td>{c.get('query') or ''}</td>
            <td>{c.get('source') or ''}</td>
            <td>{c.get('price') if c.get('price') is not None else '-'}</td>
            <td>{c.get('date') or ''}</td>
            <td><a href="{c.get('url') or '#'}" target="_blank">Voir</a></td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="6" style="padding:14px;color:#6b7280;">Aucun clic enregistré.</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Stats Fyndy</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f8fafc;
                color: #111827;
                margin: 0;
                padding: 32px;
            }}
            h1 {{
                margin: 0 0 8px 0;
                font-size: 40px;
            }}
            .sub {{
                color: #6b7280;
                margin-bottom: 24px;
            }}
            .card {{
                background: white;
                border-radius: 14px;
                padding: 20px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.06);
                margin-bottom: 24px;
            }}
            .counter {{
                font-size: 42px;
                font-weight: 800;
                color: #2563eb;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 14px;
                overflow: hidden;
                box-shadow: 0 8px 24px rgba(0,0,0,0.06);
            }}
            th {{
                background: #2563eb;
                color: white;
                text-align: left;
                padding: 12px;
                font-size: 14px;
            }}
            td {{
                padding: 12px;
                border-bottom: 1px solid #e5e7eb;
                font-size: 14px;
            }}
            a {{
                color: #2563eb;
                text-decoration: none;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h1>Stats Fyndy</h1>
        <div class="sub">Suivi des clics enregistrés</div>

        <div class="card">
            <div>Total clics</div>
            <div class="counter">{len(clicks)}</div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Produit</th>
                    <th>Recherche</th>
                    <th>Source</th>
                    <th>Prix</th>
                    <th>Date</th>
                    <th>Lien</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </body>
    </html>
    """

if __name__ == "__main__":
    ensure_data_file()
    app.run(host="0.0.0.0", port=10000, debug=True)
