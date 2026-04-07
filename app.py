from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# stockage simple (simulation base)
data_store = []

@app.route("/")
def home():
    return "Fyndy API running"

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    query = data.get("query", "")

    url = f"https://www.amazon.fr/s?k={query}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        price = None

        # extraction prix Amazon (basique)
        price_tag = soup.select_one(".a-price .a-offscreen")
        if price_tag:
            price = price_tag.text.replace("€", "").replace(",", ".")

        result = {
            "score": 75,
            "message": "Prix correct",
            "price_detected": price if price else "indisponible",
            "average_price": "indisponible",
            "best_offer": "https://www.amazon.fr/s?k=" + query
        }

        # stockage pour stats
        data_store.append({
            "product": query,
            "price": price,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "link": result["best_offer"]
        })

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "error": str(e)
        })


@app.route("/stats")
def stats():
    return jsonify(data_store)


if __name__ == "__main__":
    app.run(debug=True)
