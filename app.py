from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from datetime import datetime
from urllib.parse import quote_plus

app = Flask(__name__)
CORS(app)

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

    if any(char.isdigit() for char in q):
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
    html = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Fyndy - Statistiques</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background: #f8fafc;
      margin: 0;
      padding: 24px;
      color: #111827;
    }
    h1 {
      margin: 0 0 10px 0;
      font-size: 28px;
    }
    .sub {
      color: #6b7280;
      margin-bottom: 20px;
    }
    .card {
      background: white;
      border-radius: 14px;
      padding: 18px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.08);
      margin-bottom: 20px;
    }
    .counter {
      font-size: 32px;
      font-weight: 800;
      color: #2563eb;
    }
    .refresh {
      color: #6b7280;
      font-size: 13px;
      margin-top: 6px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: white;
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    }
    th {
      background: #2563eb;
      color: white;
      text-align: left;
      font-size: 14px;
      padding: 12px;
    }
    td {
      padding: 12px;
      border-bottom: 1px solid #e5e7eb;
      font-size: 14px;
      vertical-align: top;
    }
    tr:hover td {
      background: #f8fafc;
    }
    a {
      color: #2563eb;
      text-decoration: none;
      font-weight: 600;
    }
    a:hover {
      text-decoration: underline;
    }
    .empty {
      padding: 16px;
      color: #6b7280;
    }
  </style>
</head>
<body>
  <h1>📊 Statistiques Fyndy</h1>
  <div class="sub">Suivi automatique des clics</div>

  <div class="card">
    <div>Total clics</div>
    <div class="counter" id="totalClicks">0</div>
    <div class="refresh">Mise à jour automatique toutes les 3 secondes</div>
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
    <tbody id="tableBody">
      <tr><td colspan="6" class="empty">Chargement...</td></tr>
    </tbody>
  </table>

  <script>
    async function loadStats() {
      try {
        const res = await fetch("/stats-data");
        const data = await res.json();

        document.getElementById("totalClicks").innerText = data.total_clicks || 0;

        const tbody = document.getElementById("tableBody");
        tbody.innerHTML = "";

        const rows = [...(data.data || [])].reverse();

        if (rows.length === 0) {
          tbody.innerHTML = '<tr><td colspan="6" class="empty">Aucun clic enregistré pour le moment.</td></tr>';
          return;
        }

        rows.forEach(item => {
          const tr = document.createElement("tr");

          const price = (item.price !== null && item.price !== undefined && item.price !== "")
            ? `${item.price} €`
            : "-";

          const date = item.timestamp
            ? new Date(item.timestamp).toLocaleString("fr-FR")
            : "-";

          const link = item.url
            ? `<a href="${item.url}" target="_blank" rel="noopener noreferrer">Voir</a>`
            : "-";

          tr.innerHTML = `
            <td>${item.product || "-"}</td>
            <td>${item.query || "-"}</td>
            <td>${item.source || "-"}</td>
            <td>${price}</td>
            <td>${date}</td>
            <td>${link}</td>
          `;

          tbody.appendChild(tr);
        });
      } catch (error) {
        console.error("Erreur chargement stats :", error);
        document.getElementById("tableBody").innerHTML =
          '<tr><td colspan="6" class="empty">Erreur de chargement.</td></tr>';
      }
    }

    loadStats();
    setInterval(loadStats, 3000);
  </script>
</body>
</html>
"""
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
