import json
import os
import threading
import math
import numpy as np
import pandas as pd

from flask import Flask, redirect, render_template, request, session, url_for, jsonify
from registry import SCRAPERS

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

# 🔴 CRITICAL: forbid NaN in JSON output
app.config["JSONIFY_ALLOW_NAN"] = False

MANUAL_OFFERS_DIR = os.path.join(os.path.dirname(__file__), "manual_offers")

# ---------------- AUTH ----------------

CREDENTIALS = {
    "admin": {"admin": "admin123"},
    "user": {"user": "user123"},
}

# ---------------- GLOBAL SCRAPE STATE ----------------

SCRAPE_LOCK = threading.Lock()

SCRAPE_STATE = {
    "running": False,
    "progress": 0,
    "total": len(SCRAPERS),
    "rows": [],
}

# ---------------- SANITIZER ----------------

def sanitize(obj):
    """Recursively replace NaN / inf with None (valid JSON)."""
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if obj is np.nan:
        return None
    return obj

# ---------------- MANUAL OFFERS ----------------

def load_manual_offers():
    rows = []

    if not os.path.isdir(MANUAL_OFFERS_DIR):
        return rows

    for filename in os.listdir(MANUAL_OFFERS_DIR):
        if not filename.lower().endswith(".json"):
            continue

        path = os.path.join(MANUAL_OFFERS_DIR, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                offers = json.load(f)
        except Exception as e:
            print(f"[ERROR] Manual offers load failed: {filename}: {e}")
            continue

        if not isinstance(offers, list):
            continue

        for offer in offers:
            if not isinstance(offer, dict):
                continue

            row = dict(offer)
            row.setdefault("Dealership", os.path.splitext(filename)[0])
            rows.append(row)

    return rows

# ---------------- BACKGROUND SCRAPER ----------------

def background_scrape():
    with SCRAPE_LOCK:
        SCRAPE_STATE["running"] = True
        SCRAPE_STATE["progress"] = 0
        SCRAPE_STATE["rows"].clear()
        SCRAPE_STATE["rows"].extend(load_manual_offers())

    for scraper in SCRAPERS:
        try:
            df = scraper.fetch_df()

            dealer = getattr(scraper, "dealer_name", None)
            if not dealer:
                dealer = scraper.__class__.__name__

            df.insert(0, "Dealership", dealer)

            # 🔴 HARD NaN KILL (Pandas + NumPy)
            records = (
                df.where(pd.notnull(df), None)
                .replace({np.nan: None})
                .to_dict("records")
            )

            with SCRAPE_LOCK:
                SCRAPE_STATE["rows"].extend(records)

            print(f"[OK] {dealer}: {len(records)} rows")

        except Exception as e:
            print(f"[ERROR] {scraper.__class__.__name__}: {e}")

        with SCRAPE_LOCK:
            SCRAPE_STATE["progress"] += 1

    with SCRAPE_LOCK:
        SCRAPE_STATE["running"] = False

# ---------------- API ----------------

@app.route("/start-scraping")
def start_scraping():
    with SCRAPE_LOCK:
        if SCRAPE_STATE["running"]:
            return jsonify({"status": "already_running"})

        threading.Thread(target=background_scrape, daemon=True).start()
        return jsonify({"status": "started"})

@app.route("/scrape-status")
def scrape_status():
    with SCRAPE_LOCK:
        return jsonify({
            "running": SCRAPE_STATE["running"],
            "progress": SCRAPE_STATE["progress"],
            "total": SCRAPE_STATE["total"],
        })

@app.route("/scrape-results")
def scrape_results():
    with SCRAPE_LOCK:
        clean = sanitize(SCRAPE_STATE["rows"])
        return jsonify(clean)

# ---------------- AUTH ROUTES ----------------

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        role = request.form.get("role")
        username = request.form.get("username")
        password = request.form.get("password")

        role_creds = CREDENTIALS.get(role, {})
        if username in role_creds and password == role_creds[username]:
            session["role"] = role
            session["username"] = username
            return redirect(url_for("specials"))

        error = "Invalid credentials"

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- PAGES ----------------

@app.route("/specials")
def specials():
    if not session.get("role"):
        return redirect(url_for("login"))

    template = "admin_table.html" if session["role"] == "admin" else "login_table.html"

    return render_template(
        template,
        role=session["role"],
        username=session["username"],
    )

@app.route("/manual-offers")
def manual_offers():
    if not session.get("role"):
        return redirect(url_for("login"))

    return render_template(
        "manual_offers.html",
        role=session["role"],
        username=session["username"],
        offer_link=request.args.get("offer_link", ""),
        dealership=request.args.get("dealership", ""),
    )

@app.route("/scrape-monitor")
def scrape_monitor():
    if not session.get("role"):
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("specials"))

    return render_template(
        "scrape_monitor.html",
        role=session["role"],
        username=session["username"],
    )

@app.route("/manual-offers/save", methods=["POST"])
def save_manual_offers():
    payload = request.get_json(silent=True) or {}
    dealership = (payload.get("dealership") or "").strip()
    offers = payload.get("offers") or []

    if not dealership or not isinstance(offers, list) or not offers:
        return jsonify({"error": "Invalid payload"}), 400

    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in dealership)
    os.makedirs(MANUAL_OFFERS_DIR, exist_ok=True)

    path = os.path.join(MANUAL_OFFERS_DIR, f"{safe_name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(offers, f, indent=2)

    return jsonify({"status": "saved"})

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=False, port=8001)
