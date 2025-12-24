import json
import os
import threading
import time

import pandas as pd
from flask import Flask, redirect, render_template, request, session, url_for, jsonify

from registry import SCRAPERS

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")
MANUAL_OFFERS_DIR = os.path.join(os.path.dirname(__file__), "manual_offers")


CREDENTIALS = {
    "admin": {"admin": "admin123"},
    "user": {"user": "user123"},
}

# ---------------- GLOBAL SCRAPE STATE ----------------

SCRAPE_STATE = {
    "running": False,
    "progress": 0,
    "total": len(SCRAPERS),
    "rows": [],
}

# ---------------- AUTH ----------------

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

# ---------------- BACKGROUND SCRAPER ----------------

def background_scrape():
    SCRAPE_STATE["running"] = True
    SCRAPE_STATE["progress"] = 0
    SCRAPE_STATE["rows"] = []

    for scraper in SCRAPERS:
        try:
            df = scraper.fetch_df()
            SCRAPE_STATE["rows"].extend(df.to_dict("records"))
        except Exception as e:
            print(f"[ERROR] {scraper.__class__.__name__}: {e}")

        SCRAPE_STATE["progress"] += 1

    SCRAPE_STATE["running"] = False


# ---------------- API ENDPOINTS ----------------

@app.route("/start-scraping")
def start_scraping():
    if not SCRAPE_STATE["running"]:
        t = threading.Thread(target=background_scrape, daemon=True)
        t.start()
        return jsonify({"status": "started"})

    return jsonify({"status": "already_running"})


@app.route("/scrape-status")
def scrape_status():
    return jsonify({
        "running": SCRAPE_STATE["running"],
        "progress": SCRAPE_STATE["progress"],
        "total": SCRAPE_STATE["total"],
    })


@app.route("/scrape-results")
def scrape_results():
    return jsonify(SCRAPE_STATE["rows"])


@app.route("/manual-offers/save", methods=["POST"])
def save_manual_offers():
    payload = request.get_json(silent=True) or {}
    dealership = (payload.get("dealership") or "").strip()
    offers = payload.get("offers") or []

    if not dealership:
        return jsonify({"error": "Dealership name is required."}), 400

    if not isinstance(offers, list) or len(offers) == 0:
        return jsonify({"error": "At least one offer is required."}), 400

    sanitized_dealership = "".join(
        c if c.isalnum() or c in ("-", "_") else "_" for c in dealership
    )
    sanitized_dealership = sanitized_dealership or "manual_offers"

    os.makedirs(MANUAL_OFFERS_DIR, exist_ok=True)
    file_path = os.path.join(MANUAL_OFFERS_DIR, f"{sanitized_dealership}.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(offers, f, indent=2)

    return jsonify(
        {
            "status": "saved",
            "file": file_path,
            "message": f"Saved manual offers to {file_path}.",
        }
    )



# ---------------- PAGES ----------------

@app.route("/specials")
def specials():
    role = session.get("role")
    username = session.get("username")
    if not role or not username:
        return redirect(url_for("login"))

    template = "admin_table.html" if role == "admin" else "login_table.html"

    # Render immediately with NO DATA
    return render_template(
        template,
        tables=[],
        total=0,
        role=role,
        username=username,
    )


@app.route("/manual-offers")
def manual_offers():
    role = session.get("role")
    username = session.get("username")
    if not role or not username:
        return redirect(url_for("login"))

    offer_link = request.args.get("offer_link", "")
    dealership = request.args.get("dealership", "")
    return render_template(
        "manual_offers.html",
        role=role,
        username=username,
        offer_link=offer_link,
        dealership=dealership,
    )


if __name__ == "__main__":
    app.run(debug=True)
