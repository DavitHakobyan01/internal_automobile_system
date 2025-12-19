from flask import Flask, render_template
from registry import SCRAPERS
import pandas as pd

app = Flask(__name__)


@app.route("/")
def index():
    dfs = [scraper.fetch_df() for scraper in SCRAPERS]
    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    return render_template(
        "table.html",
        tables=[df.to_html(index=False)],
        total=len(df)
    )


if __name__ == "__main__":
    app.run(debug=True)
