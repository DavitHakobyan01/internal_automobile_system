import os

import pandas as pd
from flask import Flask, redirect, render_template, request, session, url_for

from registry import SCRAPERS

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

CREDENTIALS = {
    "admin": {
        "admin": "admin123",
    },
    "user": {
        "user": "user123",
    },
}


@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        role = request.form.get("role")
        username = request.form.get("username")
        password = request.form.get("password")
        role_credentials = CREDENTIALS.get(role, {})
        if username in role_credentials and password == role_credentials[username]:
            session["role"] = role
            session["username"] = username
            return redirect(url_for("specials"))
        error = "Invalid credentials. Please try again."
    return render_template("login.html", error=error)


@app.route("/specials")
def specials():
    role = session.get("role")
    username = session.get("username")
    if not role or not username:
        return redirect(url_for("login"))
    dfs = [scraper.fetch_df() for scraper in SCRAPERS]
    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    template_name = "admin_table.html" if role == "admin" else "login_table.html"
    return render_template(
        template_name,
        tables=[df.to_html(index=False)],
        total=len(df),
        role=role,
        username=username,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/manual-offers")
def manual_offers():
    role = session.get("role")
    username = session.get("username")
    if not role or not username:
        return redirect(url_for("login"))

    offer_link = request.args.get("offer_link", "")
    return render_template("manual_offers.html", role=role, username=username, offer_link=offer_link)


if __name__ == "__main__":
    app.run(debug=True)