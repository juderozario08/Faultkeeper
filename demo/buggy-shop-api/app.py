"""Buggy Shop API: a tiny Flask backend with deliberate bugs, monitored by Faultkeeper.

It uses the *official* `sentry-sdk`, pointed at Faultkeeper through a DSN.
"""

import os
import random

import sentry_sdk
from flask import Flask, jsonify, request
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn=os.environ.get(
        "FAULTKEEPER_DSN", "http://67043222324838d283f263d0f092cc06@localhost:8000/2"
    ),
    release=os.environ.get("RELEASE", "buggy-shop-api@1.0.0"),
    environment=os.environ.get("ENVIRONMENT", "demo"),
    integrations=[FlaskIntegration()],
    send_default_pii=False,
)

app = Flask(__name__)

PRODUCTS = {
    "keyboard": {"name": "Mechanical Keyboard", "price": 129.0, "stock": 12},
    "mouse": {"name": "Wireless Mouse", "price": 49.0, "stock": 0},
    "monitor": {"name": "27\" Monitor", "price": 329.0, "stock": 4},
}

REVIEWS = {
    "keyboard": [{"rating": 5, "text": "Clacky and great."}],
    "monitor": [{"rating": 4, "text": "Sharp picture."}],
}


@app.after_request
def cors(response):  # the storefront runs on another port
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, sentry-trace, baggage"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/products")
def products():
    return jsonify([{"id": pid, **p} for pid, p in PRODUCTS.items()])


def average_rating(reviews):
    # BUG: no reviews -> ZeroDivisionError
    return sum(r["rating"] for r in reviews) / len(reviews)


@app.get("/products/<product_id>/reviews")
def reviews(product_id):
    product_reviews = REVIEWS.get(product_id, [])
    return {"average": average_rating(product_reviews), "reviews": product_reviews}


def apply_discount(subtotal, coupon):
    percentages = {"SAVE10": 10, "HALF": 50}
    # BUG: unknown coupon -> KeyError
    return subtotal * (1 - percentages[coupon] / 100)


def reserve_stock(cart):
    for item in cart:
        product = PRODUCTS[item["id"]]
        if product["stock"] < item["qty"]:
            # BUG: raising a generic exception instead of returning a 409
            raise RuntimeError(f"Insufficient stock for {item['id']}: wanted {item['qty']}, have {product['stock']}")


@app.route("/checkout", methods=["POST", "OPTIONS"])
def checkout():
    if request.method == "OPTIONS":
        return "", 204
    body = request.get_json(silent=True) or {}
    cart = body.get("cart", [])
    reserve_stock(cart)
    subtotal = sum(PRODUCTS[i["id"]]["price"] * i["qty"] for i in cart)
    total = apply_discount(subtotal, body["coupon"]) if body.get("coupon") else subtotal
    return {"order_id": random.randint(1000, 9999), "total": round(total, 2)}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5175)))
