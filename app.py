from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
import json

app = Flask(__name__)
CORS(app)

DATA_FILE = "clicks.json"


def ensure_data_file():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_clicks():
    ensure_data_file()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_clicks(clicks):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(clicks, f, ensure_ascii=False, indent=2)


def escape_html(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


@app.route("/")
def home():
    return "Fyndy API OK"


@app.route("/health")
def health():
    return jsonify({"ok": True, "service": "fyndy-api"})


@app.route("/track-click", methods=["POST"])
def track_click():
    data = request.get_json(silent=True) or {}

    entry = {
        "product": data.get("product", ""),
        "recherche": data.get("recherche", ""),
        "source": data.get("source", ""),
        "prix": data.get("prix", ""),
        "lien": data.get("lien", ""),
        "page_url": data.get("page_url", ""),
        "date": data.get("date", datetime.now().isoformat())
    }

    clicks = load_clicks()
    clicks.insert(0, entry)
    save_clicks(clicks)

    return jsonify({
        "ok": True,
        "message": "Clic enregistré",
        "entry": entry
    })


@app.route("/stats-data")
def stats_data():
    clicks = load_clicks()
    return jsonify({
        "total": len(clicks),
        "clicks": clicks
    })


@app.route("/stats")
def stats():
    clicks = load_clicks()

    if clicks:
        rows = ""
        for item in clicks:
            product = escape_html(item.get("product", ""))
            recherche = escape_html(item.get("recherche", ""))
            source = escape_html(item.get("source", ""))
            prix = escape_html(item.get("prix", ""))
            date = escape_html(item.get("date", ""))
            lien = item.get("lien", "")

            if lien:
                safe_link = escape_html(lien)
                link_html = f'<a href="{safe_link}" target="_blank">Voir</a>'
            else:
                link_html = "-"

            rows += f"""
            <tr>
                <td>{product}</td>
                <td>{recherche}</td>
                <td>{source}</td>
                <td>{prix}</td>
                <td>{date}</td>
                <td>{link_html}</td>
            </tr>
            """
    else:
        rows = """
        <tr>
            <td colspan="6">Aucun clic enregistré.</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta http-equiv="refresh" content="3" />
        <title>Stats Fyndy</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 30px;
                background: #f8fafc;
                color: #111827;
            }}

            h1 {{
                font-size: 42px;
                margin-bottom: 10px;
            }}

            .card {{
                background: white;
                padding: 20px;
                border-radius: 14px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.08);
                margin-bottom: 24px;
            }}

            .big {{
                font-size: 52px;
                font-weight: 700;
                color: #1d4ed8;
            }}

            .refresh {{
                font-size: 14px;
                color: #64748b;
                margin-bottom: 18px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 14px;
                overflow: hidden;
                box-shadow: 0 8px 24px rgba(0,0,0,0.08);
            }}

            thead {{
                background: #1d4ed8;
                color: white;
            }}

            th, td {{
                padding: 14px;
                text-align: left;
                border-bottom: 1px solid #e5e7eb;
                vertical-align: top;
            }}

            a {{
                color: #1d4ed8;
                text-decoration: none;
                font-weight: 700;
            }}
        </style>
    </head>
    <body>
        <h1>Stats Fyndy</h1>
        <div class="refresh">Rafraîchissement automatique toutes les 3 secondes</div>

        <div class="card">
            <div>Total clics</div>
            <div class="big">{len(clicks)}</div>
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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
