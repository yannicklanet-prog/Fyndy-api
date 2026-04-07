from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# stockage simple (temporaire)
clicks = []

@app.route("/")
def home():
    return "Fyndy API OK"

@app.route("/track_click", methods=["POST"])
def track_click():
    data = request.json

    click = {
        "query": data.get("query"),
        "product": data.get("product"),
        "price": data.get("price"),
        "source": data.get("source"),
        "timestamp": datetime.now().isoformat()
    }

    clicks.append(click)

    print("CLICK:", click)

    return jsonify({"status": "ok"})

@app.route("/stats", methods=["GET"])
def stats():
    return jsonify({
        "total_clicks": len(clicks),
        "data": clicks
    })

if __name__ == "__main__":
    app.run(debug=True)
