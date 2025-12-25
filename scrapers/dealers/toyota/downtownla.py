import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

from scrapers.base.toyota_base import ToyotaBaseScraper


class DowntownLaToyotaScraper(ToyotaBaseScraper):
    dealer_name = "Toyota of Downtown LA"
    specials_url = "https://www.toyotaofdowntownla.com/specials/vehiclespecials"

    def fetch_df(self) -> pd.DataFrame:
        resp = requests.get(
            self.specials_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # this site uses a different layout than NorthHollywood;
        # try a couple of common card containers
        cards = soup.select(
            "div.specials-card, div.vehicle-special, div.offer-item, div.special-offers.offer-box"
        )

        rows = []

        for card in cards:
            # ---------- MODEL ----------
            model = None
            for sel in ["h3.make", "h2", "h3", ".srp-title", "a[aria-label]"]:
                el = card.select_one(sel)
                txt = el.get_text(" ", strip=True) if el else None
                if txt and ("Toyota" in txt or txt.lower().startswith("new ")):
                    model = txt
                    break

            # ---------- MONTHLY ----------
            monthly = None
            monthly_el = card.select_one("h3.offer-price, .payment, .lease-price, .price")
            if monthly_el:
                monthly = self._money_to_number(monthly_el.get_text(" ", strip=True))

            # ---------- TERM ----------
            term = None
            term_el = card.select_one(".offerbox-details-text2, .term, .months")
            if term_el:
                term = self._first_int(term_el.get_text(" ", strip=True))

            # ---------- DUE AT SIGNING ----------
            due = None
            due_el = card.select_one(".offerbox-details-text3, .due, .due-at-signing")
            if due_el:
                due = self._money_to_number(due_el.get_text(" ", strip=True))

            # ---------- MSRP / TSRP ----------
            msrp = None

            # if it’s explicitly labeled TSRP on the card
            tsrp_label = None
            for d in card.find_all(["div", "span", "p"]):
                if d.get_text(strip=True).upper() == "TSRP":
                    tsrp_label = d
                    break

            if tsrp_label and tsrp_label.parent:
                sibs = tsrp_label.parent.find_all(["div", "span", "p"], recursive=False)
                if len(sibs) >= 2:
                    msrp = self._money_to_number(sibs[1].get_text(" ", strip=True))

            # fallback: sometimes shown as "TSRP $xx,xxx"
            if msrp is None:
                msrp = self._money_to_number(card.get_text(" ", strip=True), require_dollar=False)

            # ---------- EXPIRES ----------
            expires = None
            for el in card.select(".offerbox-details .small-font.font-weight-bold"):
                txt = el.get_text(strip=True)
                if txt.lower().startswith("expires"):
                    expires = txt.split(":")[-1].strip()
                    break

            # skip empty junk cards
            if not any([model, monthly, term, due, msrp, expires]):
                continue

            rows.append({
                "Model": model,
                "Monthly ($)": monthly,
                "Term (months)": term,
                "Due at Signing ($)": due,
                "MSRP ($)": msrp,
                "Expires": expires,
                "Dealer Specials Link": self.specials_url,
            })

        return pd.DataFrame(rows)

    @staticmethod
    def _money_to_number(text: str | None, require_dollar: bool = True):
        """
        Extract the first money-like number.
        - If require_dollar=True: prefers $12,345.67
        - Else: accepts 12345.67 too
        Returns float or None.
        """
        if not text:
            return None

        if require_dollar:
            m = re.search(r"\$\s*([\d,]+(?:\.\d{1,2})?)", text)
        else:
            m = re.search(r"([\d,]+(?:\.\d{1,2})?)", text)

        if not m:
            return None

        return float(m.group(1).replace(",", ""))

    @staticmethod
    def _first_int(text: str | None):
        if not text:
            return None
        m = re.search(r"(\d+)", text)
        return int(m.group(1)) if m else None
