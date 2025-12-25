import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from scrapers.base.toyota_base import ToyotaBaseScraper


class MarinaDelReyToyotaScraper(ToyotaBaseScraper):
    dealer_name = "Marina del Rey Toyota"
    brand = "Toyota"
    specials_url = "https://www.marinadelreytoyota.com/specials/new-vehicle/"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120 Safari/537.36"
        )
    }

    def fetch_df(self) -> pd.DataFrame:
        resp = requests.get(self.specials_url, headers=self.HEADERS, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.dv-offers-specials-item")

        rows = []

        for card in cards:
            # ---------- MODEL ----------
            model = card.select_one("h2")
            model = model.get_text(strip=True) if model else None

            # ---------- LINK ----------
            link_el = card.select_one("a.dv-offers-cta-link-plain")
            link = urljoin(self.specials_url, link_el["href"]) if link_el else None

            # ---------- EXPIRES ----------
            expires_el = card.select_one("p.dv-offers-specials-expires span")
            expires = expires_el.get_text(strip=True) if expires_el else None

            # ---------- DISCLAIMER ----------
            disc_el = card.select_one("p.dv-offers-specials-disclaimer-btn[data-disclaimer]")
            disclaimer = disc_el["data-disclaimer"] if disc_el else None

            msrp = monthly = term = due = None

            if disclaimer:
                # MSRP (TSRP from [1])
                msrp_txt = self.extract(r"TSRP\s*\$([\d,]+)", disclaimer)
                msrp = self.money_to_int(msrp_txt)

                # Lease section [2]
                lease_txt = self.extract(r"\[2\](.*)", disclaimer)
                lease_txt = lease_txt or disclaimer

                # Monthly
                monthly_txt = self.extract(r"Lease\s+for\s+\$([\d,]+)", lease_txt)
                monthly = self.money_to_int(monthly_txt)

                # Term
                term = self.first_int(
                    self.extract(r"(\d+)\s+monthly\s+payments", lease_txt)
                )

                # Due at signing
                due_txt = self.extract(
                    r"Amount\s+due\s+at\s+signing\s+\$([\d,]+)", lease_txt
                )
                due = self.money_to_int(due_txt)

            rows.append(
                {
                    "APR (%)": None,
                    "Dealer Specials Link": link,
                    "Due at Signing ($)": due,
                    "Expires": expires,
                    "MSRP ($)": msrp,
                    "Model": model,
                    "Monthly ($)": monthly,
                    "Term (months)": term,
                }
            )

        return pd.DataFrame(rows)
