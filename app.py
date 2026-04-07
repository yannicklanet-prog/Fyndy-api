from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# stockage simple
data_store = []

@app.route("/")
def home():
    return "Fyndy API OK"

# 🔍 ENDPOINT UTILISÉ PAR TON EXTENSION
@app.route("/search")
def search():
    query = request.args.get("q", "")

    if not query:
        return jsonify({"ok": False})

    # simulation (pour prototype vendable)
    best_offer = {
        "title": f"Offres Amazon pour : {query}",
        "price": None,
        "url": f"https://www.amazon.fr/s?k={query}",
        "site": "Amazon"
    }

    avg_price = None

    return jsonify({
        "ok": True,
        "best_offer": best_offer,
        "avg_price": avg_price
    })

# 📊 TRACK CLIC
@app.route("/track_click", methods=["POST"])
def track_click():
    data = request.json

    data_store.append({
        "product": data.get("product"),
        "price": data.get("price"),
        "source": data.get("source"),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "url": data.get("url")
    })

    return jsonify({"status": "ok"})

# 📈 STATS JSON
@app.route("/stats")
def stats():
    return jsonify(data_store)

if __name__ == "__main__":
    app.run(debug=True)
