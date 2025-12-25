# scrapers/dealers/toyota/norwalk.py

import re
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from scrapers.base.base_scraper import BaseScraper
from scrapers.base.toyota_base import ToyotaBaseScraper


class NorwalkToyotaScraper(ToyotaBaseScraper):
    dealer_name = "Norwalk Toyota"
    brand = "Toyota"
    specials_url = "https://www.norwalktoyota.com/specials/"

    # ---------------- EXISTING REGEX (UNCHANGED) ----------------
    RE_MONTHLY = re.compile(r"\$\s*\d{2,4}\s*(?:/|\s*)?(?:mo|month)", re.I)
    RE_TERM = re.compile(r"\b(\d{2,3})\s*(?:month|months|monthly payments?)\b", re.I)

    # ---------------- PARSING REGEX (UNCHANGED) ----------------
    RE_MONTHLY_VAL = re.compile(r"payment of\s*\$(\d{2,4})", re.I)
    RE_TERM_VAL = re.compile(r"(\d{2,3})\s*monthly payments", re.I)
    RE_DUE_VAL = re.compile(r"\$(\d{1,2},\d{3})\s*Due At Signing", re.I)
    RE_MSRP_VAL = re.compile(r"Total SRP of\s*\$(\d{1,3}(?:,\d{3})*)", re.I)
    RE_MODEL_VAL = re.compile(r"Lease example based on\s*(.*?)\s*Model", re.I)
    RE_EXPIRES_VAL = re.compile(r"Expires?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",re.I)


    # ---------------- NETWORK (UNCHANGED LOGIC) ----------------
    def _fetch_rendered_html(self) -> str:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                )
            )
            page.goto(self.specials_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("button:has-text('Disclaimer')", timeout=60000)
            page.wait_for_timeout(1000)
            html = page.content()
            browser.close()
            return html

    # ---------------- LEASE FILTER (UNCHANGED) ----------------
    def _is_lease_offer(self, href: str | None, disclaimer: str | None) -> bool:
        if not disclaimer:
            return False

        d = disclaimer.strip()
        dl = d.lower()
        hl = (href or "").lower()

        if dl.startswith("apr:") or dl.startswith("apr available"):
            return False
        if "schedule-service" in hl:
            return False
        if hl.rstrip("/") == self.specials_url.rstrip("/").lower():
            return False
        if not dl.startswith("lease:"):
            return False

        has_term = bool(self.RE_TERM.search(d)) or ("monthly payments" in dl)
        if not has_term:
            return False

        if href and "/inventory/" not in hl:
            return False

        return True

    # ---------------- CORE SCRAPE (UNCHANGED) ----------------
    def _scrape_lease_cards(self) -> list[dict]:
        html = self._fetch_rendered_html()
        soup = BeautifulSoup(html, "html.parser")

        disclaimer_divs = soup.select("div.FJVwI")

        raw_cards = []
        for div in disclaimer_divs:
            disclaimer = " ".join(div.get_text(" ", strip=True).split())
            a = div.find_previous("a", href=True)
            href = urljoin(self.specials_url, a["href"]) if a else None
            raw_cards.append({"href": href, "disclaimer": disclaimer})

        lease_cards = [
            c for c in raw_cards
            if self._is_lease_offer(c["href"], c["disclaimer"])
        ]

        seen = set()
        out = []
        for c in lease_cards:
            key = ((c["href"] or "").rstrip("/"), c["disclaimer"][:120])
            if key in seen:
                continue
            seen.add(key)
            out.append(c)

        return out

    # ---------------- REQUIRED BASE METHOD ----------------
    def fetch_df(self) -> pd.DataFrame:
        offers = self._scrape_lease_cards()
        rows = []

        for o in offers:
            d = o["disclaimer"]

            def grab(rx):
                m = rx.search(d)
                return m.group(1) if m else None

            rows.append({
                "APR (%)": None,
                "Dealer Specials Link": self.specials_url,
                "Due at Signing ($)": self.money_to_int(grab(self.RE_DUE_VAL)),
                "Expires": grab(self.RE_EXPIRES_VAL),
                "MSRP ($)": self.money_to_int(grab(self.RE_MSRP_VAL)),
                "Model": grab(self.RE_MODEL_VAL),
                "Monthly ($)": self.first_int(grab(self.RE_MONTHLY_VAL)),
                "Term (months)": self.first_int(grab(self.RE_TERM_VAL)),
            })

        return pd.DataFrame(rows)
