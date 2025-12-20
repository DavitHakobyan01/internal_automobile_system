import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

from scrapers.base.toyota_base import ToyotaBaseScraper


class NorthHollywoodToyotaScraper(ToyotaBaseScraper):
    dealer_name = "Toyota of North Hollywood"
    specials_url = "https://www.northhollywoodtoyota.com/specials/vehicle-specials"

    def fetch_df(self) -> pd.DataFrame:
        resp = requests.get(
            self.specials_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.special-offers.offer-box")

        rows = []

        for card in cards:

            # ---------- MODEL ----------
            model_el = card.select_one("h3.make")
            model = model_el.get_text(strip=True) if model_el else None

            # ---------- MONTHLY ----------
            monthly_el = card.select_one("h3.offer-price")
            monthly = self._money_to_int(monthly_el.get_text()) if monthly_el else None

            # ---------- TERM ----------
            term_el = card.select_one(".offerbox-details-text2")
            term = self._first_int(term_el.get_text()) if term_el else None

            # ---------- DUE AT SIGNING ----------
            due_el = card.select_one(".offerbox-details-text3")
            due = self._money_to_int(due_el.get_text()) if due_el else None

            # ---------- MSRP (STRICT TSRP ONLY) ----------
            msrp = None
            tsrp_div = None

            for d in card.find_all("div"):
                if d.get_text(strip=True).upper() == "TSRP":
                    tsrp_div = d
                    break

            if tsrp_div:
                parent = tsrp_div.parent
                if parent:
                    children = parent.find_all("div", recursive=False)
                    if len(children) >= 2:
                        msrp = self._money_to_int(children[1].get_text(strip=True))

            # ---------- EXPIRES (VISIBLE DATE ONLY) ----------
            expires = None
            for el in card.select(".offerbox-details .small-font.font-weight-bold"):
                txt = el.get_text(strip=True)
                if txt.lower().startswith("expires"):
                    expires = txt.split(":")[-1].strip()
                    break

            rows.append({
                "Model": model,
                "Monthly ($)": monthly,
                "Term (months)": term,
                "Due at Signing ($)": due,
                "MSRP ($)": msrp,
                "APR (%)": None,
                "Expires": expires,
                "Dealer Specials Link": self.specials_url,
            })

        return pd.DataFrame(rows)

    # ---------------- HELPERS ---------------- #

    @staticmethod
    def _money_to_int(text: str | None):
        if not text:
            return None
        digits = re.sub(r"[^\d]", "", text)
        return int(digits) if digits else None

    @staticmethod
    def _first_int(text: str | None):
        if not text:
            return None
        m = re.search(r"(\d+)", text)
        return int(m.group(1)) if m else None
