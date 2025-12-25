import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

from scrapers.base.toyota_base import ToyotaBaseScraper


class KeyesToyotaScraper(ToyotaBaseScraper):
    dealer_name = "Keyes Toyota"
    brand = "Toyota"
    specials_url = "https://www.keyestoyota.com/newspecials.html"

    def fetch_df(self) -> pd.DataFrame:
        resp = requests.get(
            self.specials_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.card__coupon")

        rows = []

        for card in cards:
            model_el = card.select_one("h2.card__title--main")
            model = model_el.get_text(strip=True) if model_el else None
            if model and "certified used" in model.lower():
                continue

            disclaimer_el = card.select_one(".card__disclaimer p")
            disclaimer = disclaimer_el.get_text(" ", strip=True) if disclaimer_el else ""

            expires_el = card.select_one(".card__expiration p")
            expires = None
            if expires_el:
                expires = re.sub(
                    r"^Offer\s+Expires\s+",
                    "",
                    expires_el.get_text(strip=True),
                    flags=re.IGNORECASE,
                ).strip()

            monthly_text = self.extract(r"\$([\d,]+)\s*per\s*month", disclaimer)
            if not monthly_text:
                continue

            rows.append({
                "Model": model,
                "Monthly ($)": self.money_to_int(monthly_text),
                "Term (months)": self.first_int(
                    self.extract(r"for\s*(\d+)\s*months", disclaimer)
                ),
                "Due at Signing ($)": self.money_to_int(
                    self.extract(r"\$([\d,]+)\s*Due\s*At\s*Signing", disclaimer)
                ),
                "MSRP ($)": self.money_to_int(
                    self.extract(r"(?:TSRP|MSRP)\s*\$([\d,]+)", disclaimer)
                ),
                "Expires": expires,
                "Dealer Specials Link": self.specials_url,
            })

        return pd.DataFrame(rows)