import re
from typing import Optional, List, Dict, Any

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from scrapers.base.toyota_base import ToyotaBaseScraper


class LongoToyotaScraper(ToyotaBaseScraper):
    dealer_name = "Longo Toyota"
    specials_url = "https://www.longotoyota.com/new-toyota-specials-los-angeles.html"

    COLUMNS = [
        "Model",
        "Monthly ($)",
        "Term (months)",
        "Due at Signing ($)",
        "MSRP ($)",
        "Expires",
        "Dealer Specials Link",
    ]

    def __init__(self, debug: bool = False, headless: bool = True, timeout_ms: int = 45000):
        self.debug = debug
        self.headless = headless
        self.timeout_ms = timeout_ms

    def _log(self, msg: str):
        if self.debug:
            print(msg)

    @staticmethod
    def _clean(s: Optional[str]) -> Optional[str]:
        if not s:
            return None
        s = re.sub(r"\s+", " ", s).strip()
        return s or None

    @staticmethod
    def _money_int(s: Optional[str]) -> Optional[int]:
        if not s:
            return None
        m = re.search(r"(\d{1,3}(?:,\d{3})+|\d+)", s)
        return int(m.group(1).replace(",", "")) if m else None

    @staticmethod
    def _money_float(s: Optional[str]) -> Optional[float]:
        if not s:
            return None
        m = re.search(r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", s)
        return float(m.group(1).replace(",", "")) if m else None

    @staticmethod
    def _expires_from_text(text: str) -> Optional[str]:
        m = re.search(r"(?:Offer\s+expires|Expires)\s*(\d{2}/\d{2}/\d{4})", text, re.I)
        return m.group(1) if m else None

    def fetch_df(self) -> pd.DataFrame:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()

            self._log(f"[DEBUG] goto {self.specials_url}")
            page.goto(self.specials_url, wait_until="domcontentloaded", timeout=self.timeout_ms)

            # Wait for Octane specials to be injected
            self._log("[DEBUG] waiting for octane cards...")
            page.wait_for_selector("div.octane-specials-css-special-block", timeout=self.timeout_ms)

            html = page.content()
            browser.close()

        self._log(f"[DEBUG] rendered_html_len={len(html):,}")
        self._log(f"[DEBUG] has octane block? {'octane-specials-css-special-block' in html}")
        self._log(f"[DEBUG] has Total SRP? {'Total SRP' in html}")
        self._log(f"[DEBUG] has Lease tag? {'octane-specials-css-offer-tag' in html}")

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.octane-specials-css-special-block")
        self._log(f"[DEBUG] cards_found={len(cards)}")

        if self.debug and cards:
            # show a small snippet of the first card to confirm we’re parsing right DOM
            first = cards[0]
            self._log("[DEBUG] first_card_title=" + (first.select_one("h2.octane-specials-css-vehicle-title").get_text(" ", strip=True)
                                                     if first.select_one("h2.octane-specials-css-vehicle-title") else "None"))
            self._log("[DEBUG] first_card_text_snippet=" + first.get_text(" ", strip=True)[:250])

        rows: List[Dict[str, Any]] = []

        for i, card in enumerate(cards, start=1):
            title_el = card.select_one("h2.octane-specials-css-vehicle-title")
            model = self._clean(title_el.get_text(" ", strip=True) if title_el else None)

            # Total SRP usually appears in the "vehicle-detail ... last" element
            msrp = None
            msrp_el = card.select_one(".octane-specials-css-vehicle-detail.octane-specials-css-last")
            if msrp_el:
                msrp = self._money_float(msrp_el.get_text(" ", strip=True))
            else:
                # fallback: parse from text
                msrp = self._money_float(card.get_text(" ", strip=True))

            # Expires: in disclaimer text
            disclaimer_text = card.get_text(" ", strip=True)
            expires = self._expires_from_text(disclaimer_text)

            offers = card.select("a.octane-specials-css-special-offer-block")
            if self.debug:
                self._log(f"[DEBUG] card#{i} model={model!r} offers={len(offers)} msrp={msrp} expires={expires}")

            for offer in offers:
                tag_el = offer.select_one(".octane-specials-css-offer-tag")
                tag = self._clean(tag_el.get_text(strip=True) if tag_el else None)

                if (tag or "").lower() != "lease":
                    continue

                monthly_el = offer.select_one(".octane-specials-css-offer-price")
                monthly = self._money_int(monthly_el.get_text(" ", strip=True) if monthly_el else None)

                offer_text = offer.get_text(" ", strip=True)

                term = None
                m = re.search(r"(\d+)\s*-\s*month\s+lease", offer_text, re.I) or re.search(
                    r"(\d+)\s*month\s+lease", offer_text, re.I
                )
                if m:
                    term = int(m.group(1))

                due = None
                m = re.search(r"\$?\s*(\d{1,3}(?:,\d{3})+|\d+)\s+due\s+at\s+signing", offer_text, re.I)
                if m:
                    due = int(m.group(1).replace(",", ""))

                if self.debug:
                    self._log(f"    [DEBUG] LEASE monthly={monthly} term={term} due={due}")

                rows.append(
                    {
                        "Model": model,
                        "Monthly ($)": monthly,
                        "Term (months)": term,
                        "Due at Signing ($)": due,
                        "MSRP ($)": msrp,
                        "Expires": expires,
                        "Dealer Specials Link": self.specials_url,
                    }
                )

        df = pd.DataFrame(rows, columns=self.COLUMNS)
        self._log(f"[DEBUG] lease_rows={len(df)}")
        return df
