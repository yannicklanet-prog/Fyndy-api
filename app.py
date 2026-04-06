from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import time
import re
from urllib.parse import quote_plus

app = Flask(__name__)
CORS(app)

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()

CACHE = {}
CACHE_TTL_SECONDS = 900

KNOWN_BRANDS = [
    "grohe", "hansgrohe", "geberit", "roca",
    "nobili", "gessi", "axor", "dornbracht",
    "paini", "ideal standard", "jacob delafon",
    "villeroy", "laufen", "ondyna", "fantini", "cristina"
]


def normalize(text):
    return " ".join((text or "").lower().split())


def clean_price(price):
    if price is None:
        return None

    try:
        text = str(price)
        text = text.replace("€", "")
        text = text.replace("\u20ac", "")
        text = text.replace("\xa0", " ")
        text = text.replace(" ", "")
        text = text.replace(",", ".")
        match = re.search(r"\d+(\.\d+)?", text)
        if not match:
            return None
        return float(match.group())
    except Exception:
        return None


def clean_rating(value):
    if value is None:
        return None

    try:
        text = str(value).replace(",", ".").strip()
        match = re.search(r"\d+(\.\d+)?", text)
        if not match:
            return None

        rating = float(match.group())
        if 0 <= rating <= 5:
            return rating
        return None
    except Exception:
        return None


def clean_reviews_count(value):
    if value is None:
        return 0

    try:
        text = str(value).replace("\xa0", " ").replace(" ", "")
        text = re.sub(r"[^\d]", "", text)
        return int(text) if text else 0
    except Exception:
        return 0


def get_cached(query: str):
    entry = CACHE.get(query)
    if not entry:
        return None

    if time.time() - entry["ts"] > CACHE_TTL_SECONDS:
        CACHE.pop(query, None)
        return None

    return entry["data"]


def set_cached(query: str, data):
    CACHE[query] = {
        "ts": time.time(),
        "data": data
    }


def has_brand(query: str) -> bool:
    q = normalize(query)
    return any(b in q for b in KNOWN_BRANDS)


def has_product_reference(query: str) -> bool:
    q = normalize(query)
    patterns = [
        r"\b[a-z]{0,4}\d{3,}[a-z0-9-]*\b",
        r"\b\d{3,}[a-z-]*\b"
    ]
    return any(re.search(pattern, q, re.IGNORECASE) for pattern in patterns)


def is_precise(query: str) -> bool:
    q = normalize(query)
    words = [w for w in q.split() if w]

    if has_brand(q) and has_product_reference(q):
        return True

    if has_product_reference(q):
        return True

    if has_brand(q) and len(words) <= 5:
        return True

    return False


def relevance(query, title):
    q = normalize(query)
    t = normalize(title)

    score = 0
    for word in q.split():
        if len(word) >= 3 and word in t:
            score += 10

    if has_brand(q) and has_brand(t):
        score += 10

    if has_product_reference(q) and has_product_reference(t):
        score += 15

    return score


def is_comparator_site(site: str, title: str = ""):
    s = normalize(site)
    t = normalize(title)

    keywords = [
        "idealo",
        "klarna",
        "kelkoo",
        "shopalike",
        "google shopping",
        "shopping",
        "comparateur",
        "compare",
        "comparer",
        "prix",
        "offers",
        "offer",
        "deals",
        "deal"
    ]

    for k in keywords:
        if k in s or k in t:
            return True

    return False


def review_signal_from_score(score):
    if score is None:
        return "inconnu"
    if score >= 85:
        return "fiable"
    if score >= 68:
        return "correct"
    if score >= 50:
        return "prudence"
    return "douteux"


def extract_google_reviews(data):
    candidates = []

    knowledge_graph = data.get("knowledge_graph", {}) or {}
    if knowledge_graph:
        candidates.append(knowledge_graph)

    answer_box = data.get("answer_box", {}) or {}
    if answer_box:
        candidates.append(answer_box)

    product_result = data.get("product_result", {}) or {}
    if product_result:
        candidates.append(product_result)

    inline_products = data.get("inline_products", []) or []
    if inline_products:
        candidates.extend(inline_products[:5])

    shopping_results = data.get("shopping_results", []) or []
    if shopping_results:
        candidates.extend(shopping_results[:5])

    for block in candidates:
        rating = clean_rating(
            block.get("rating")
            or block.get("reviews_rating")
            or block.get("stars")
        )

        reviews = clean_reviews_count(
            block.get("reviews")
            or block.get("reviews_count")
            or block.get("rating_count")
            or block.get("user_reviews")
        )

        if rating is not None or reviews > 0:
            return rating, reviews

    return None, 0


def compute_review_score(site, title, rating=None, reviews_count=0, price=None, median_price=None):
    s = normalize(site)
    t = normalize(title)

    score = 58

    if "amazon" in s:
        score += 4
    if "leroy" in s:
        score += 7
    if "manomano" in s:
        score += 4
    if "castorama" in s:
        score += 6
    if "darty" in s:
        score += 6
    if "lapeyre" in s:
        score += 5
    if "bricoman" in s:
        score += 3
    if "cdiscount" in s:
        score -= 5
    if "marketplace" in s:
        score -= 10
    if "seller" in s:
        score -= 4

    if is_comparator_site(site, title):
        score -= 14

    if "promo" in t:
        score -= 3
    if "officiel" in t:
        score += 4
    if "garantie" in t:
        score += 2
    if "lot" in t:
        score -= 2
    if "reconditionné" in t:
        score -= 18
    if "occasion" in t:
        score -= 20
    if "compatible" in t:
        score -= 8

    if rating is not None:
        if rating >= 4.8:
            score += 14
        elif rating >= 4.6:
            score += 11
        elif rating >= 4.4:
            score += 8
        elif rating >= 4.2:
            score += 5
        elif rating >= 4.0:
            score += 2
        elif rating >= 3.7:
            score -= 4
        else:
            score -= 10

    if reviews_count >= 1000:
        score += 12
    elif reviews_count >= 500:
        score += 10
    elif reviews_count >= 200:
        score += 8
    elif reviews_count >= 100:
        score += 6
    elif reviews_count >= 30:
        score += 3
    elif reviews_count >= 10:
        score += 1
    elif reviews_count > 0:
        score -= 3

    if rating is not None and reviews_count > 0:
        if rating >= 4.8 and reviews_count < 10:
            score -= 12
        elif rating >= 4.7 and reviews_count < 20:
            score -= 8

    if price is not None and median_price is not None and median_price > 0:
        ratio = price / median_price
        if ratio < 0.75:
            score -= 12
        elif ratio < 0.85:
            score -= 7
        elif ratio < 0.92:
            score -= 3

    # priorité aux vrais excellents avis
    if rating is not None and reviews_count > 0:
        if rating >= 4.7 and reviews_count >= 500:
            score = max(score, 92)
        elif rating >= 4.6 and reviews_count >= 100:
            score = max(score, 88)
        elif rating >= 4.4 and reviews_count >= 50:
            score = max(score, 80)

    return max(25, min(95, round(score)))


def enrich_offers_with_review_score(offers):
    priced = [o["price"] for o in offers if o.get("price") is not None]
    median_price = None

    if priced:
        priced_sorted = sorted(priced)
        n = len(priced_sorted)
        if n % 2 == 1:
            median_price = priced_sorted[n // 2]
        else:
            median_price = (priced_sorted[n // 2 - 1] + priced_sorted[n // 2]) / 2

    final = []
    for offer in offers:
        if offer.get("estimated"):
            offer["review_score"] = None
            offer["trust_score"] = None
            offer["review_signal"] = "inconnu"
        else:
            score = compute_review_score(
                site=offer.get("site", ""),
                title=offer.get("title", ""),
                rating=offer.get("rating"),
                reviews_count=offer.get("reviews_count", 0),
                price=offer.get("price"),
                median_price=median_price
            )
            offer["review_score"] = score
            offer["trust_score"] = score
            offer["review_signal"] = review_signal_from_score(score)

        final.append(offer)

    return final


def build_real_fallback_offers(query):
    # liens réels, sans inventer ni prix ni avis
    return [
        {
            "site": "Leroy Merlin",
            "title": query,
            "price": None,
            "url": f"https://www.leroymerlin.fr/recherche?q={quote_plus(query)}",
            "estimated": True,
            "rating": None,
            "reviews_count": 0,
            "relevance_score": 20,
            "is_comparator": False
        },
        {
            "site": "Amazon",
            "title": query,
            "price": None,
            "url": f"https://www.amazon.fr/s?k={quote_plus(query)}",
            "estimated": True,
            "rating": None,
            "reviews_count": 0,
            "relevance_score": 20,
            "is_comparator": False
        },
        {
            "site": "ManoMano",
            "title": query,
            "price": None,
            "url": f"https://www.manomano.fr/recherche/{quote_plus(query)}",
            "estimated": True,
            "rating": None,
            "reviews_count": 0,
            "relevance_score": 20,
            "is_comparator": False
        }
    ]


def parse_google_results(data, query):
    global_rating, global_reviews = extract_google_reviews(data)
    results = []

    shopping_results = data.get("shopping_results", []) or []

    for item in shopping_results:
        title = item.get("title", "")
        price = clean_price(item.get("price"))
        site = item.get("source", "Google")
        link = item.get("link") or item.get("product_link") or "#"

        if not title:
            continue

        rel = relevance(query, title)
        if rel < 5:
            continue

        if price is None:
            continue

        item_rating = clean_rating(item.get("rating"))
        item_reviews = clean_reviews_count(item.get("reviews"))

        rating = item_rating if item_rating is not None else global_rating
        reviews_count = item_reviews if item_reviews > 0 else global_reviews

        results.append({
            "site": site,
            "title": title,
            "price": price,
            "url": link,
            "estimated": False,
            "relevance_score": rel,
            "rating": rating,
            "reviews_count": reviews_count,
            "is_comparator": is_comparator_site(site, title)
        })

    return enrich_offers_with_review_score(results)


def choose_best_offer(offers, mode):
    if not offers:
        return None

    valid = [o for o in offers]
    if not valid:
        return None

    direct_sellers = [
        o for o in valid
        if not is_comparator_site(o.get("site", ""), o.get("title", ""))
    ]

    target = direct_sellers if direct_sellers else valid

    # pour recherche précise :
    # 1) on privilégie prix réel si dispo
    # 2) sinon meilleur vendeur direct
    if mode == "lowest_price":
        priced = [o for o in target if o.get("price") is not None]
        if priced:
            safe = [
                o for o in priced
                if (o.get("trust_score") or 0) >= 50 or o.get("trust_score") is None
            ]
            final_target = safe if safe else priced
            final_target.sort(key=lambda x: x["price"])
            return final_target[0]

        return target[0]

    # recherche vague : on peut garder simple et stable
    priced = [o for o in target if o.get("price") is not None]
    if priced:
        priced.sort(
            key=lambda x: (
                -(x.get("trust_score") or 0),
                x.get("price") if x.get("price") is not None else 999999
            )
        )
        return priced[0]

    return target[0]


def choose_lowest_offer(offers):
    if not offers:
        return None

    valid = [o for o in offers if o.get("price") is not None]
    if not valid:
        return None

    valid.sort(key=lambda x: x["price"])
    return valid[0]


def choose_cheaper_comparator_offer(offers, best_offer):
    if not offers or not best_offer or best_offer.get("price") is None:
        return None

    comparators = [
        o for o in offers
        if o.get("price") is not None
        and is_comparator_site(o.get("site", ""), o.get("title", ""))
    ]

    if not comparators:
        return None

    comparators.sort(key=lambda x: x["price"])
    cheapest = comparators[0]

    if cheapest["price"] < best_offer["price"]:
        return cheapest

    return None


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

    if not query:
        return jsonify({"ok": False, "error": "query manquante"}), 400

    cached = get_cached(query)
    if cached:
        return jsonify(cached)

    mode = "lowest_price" if is_precise(query) else "value"

    # 1. tentative Google / SerpAPI
    if SERPAPI_KEY:
        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": SERPAPI_KEY,
                "hl": "fr",
                "gl": "fr"
            }

            r = requests.get(
                "https://serpapi.com/search.json",
                params=params,
                timeout=6
            )
            r.raise_for_status()
            data = r.json()

            offers = parse_google_results(data, query)

            if offers:
                best_offer = choose_best_offer(offers, mode)
                lowest_offer = choose_lowest_offer(offers)
                cheaper_comparator_offer = choose_cheaper_comparator_offer(offers, best_offer)

                result = {
                    "ok": True,
                    "query": query,
                    "mode": mode,
                    "source": "serpapi_google",
                    "used_fallback": False,
                    "best_offer": best_offer,
                    "lowest_offer": lowest_offer,
                    "cheaper_comparator_offer": cheaper_comparator_offer,
                    "has_cheaper_comparator": cheaper_comparator_offer is not None,
                    "offers": offers
                }

                set_cached(query, result)
                return jsonify(result)

        except Exception as e:
            # on continue proprement vers le fallback réel
            pass

    # 2. fallback réel propre
    offers = enrich_offers_with_review_score(build_real_fallback_offers(query))
    best_offer = choose_best_offer(offers, mode)

    result = {
        "ok": True,
        "query": query,
        "mode": mode,
        "source": "fallback_real_links",
        "used_fallback": True,
        "best_offer": best_offer,
        "lowest_offer": None,
        "cheaper_comparator_offer": None,
        "has_cheaper_comparator": False,
        "offers": offers
    }

    set_cached(query, result)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
