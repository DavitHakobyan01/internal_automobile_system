# scrapers/dealers/toyota/manhattan_beach.py

import re
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from scrapers.base.toyota_base import ToyotaBaseScraper


class ManhattanBeachToyotaScraper(ToyotaBaseScraper):
    dealer_name = "Manhattan Beach Toyota"
    brand = "Toyota"
    specials_url = "https://www.manhattanbeachtoyota.com/specials/"

    # -------- parsing regex (dealer-specific) --------
    RE_MONTHLY_VAL = re.compile(r"first month's payment of\s*\$(\d{2,4})", re.I)
    RE_TERM_VAL = re.compile(r"\b(\d{2,3})\s*month\s*lease\s*offer\b", re.I)
    RE_DUE_VAL = re.compile(r"\$(\d{1,2},\d{3})\s*Due At Signing", re.I)

    # IMPORTANT: Total SRP is what this site provides (not MSRP)
    RE_TOTAL_SRP_VAL = re.compile(r"Total SRP of\s*\$([\d,]+)", re.I)

    RE_MODEL_VAL = re.compile(r"Lease example based on\s*(.*?)\s*Model", re.I)
    RE_EXPIRES_VAL = re.compile(r"Expires?\s*(\d{2}[-/]\d{2}[-/]\d{4})", re.I)
    RE_COUNT_VAL = re.compile(r"\b(\d+)\s*at this deal\b", re.I)

    # -------- network --------
    def _fetch_rendered_html(self) -> str:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_navigation_timeout(60000)
            page.set_default_timeout(60000)

            print(f"[GOTO] {self.specials_url}")
            try:
                page.goto(self.specials_url, wait_until="domcontentloaded", timeout=60000)
            except PWTimeout:
                print("[WARN] goto timeout — continuing")

            # disclaimers exist but are collapsed; wait for DOM attachment, not visibility
            page.wait_for_selector("div.FJVwI", state="attached", timeout=60000)
            page.wait_for_timeout(300)

            html = page.content()
            browser.close()
            return html

    # -------- lease filter --------
    def _is_lease_offer(self, href: str | None, disclaimer: str | None) -> bool:
        if not disclaimer:
            return False
        d = disclaimer.strip()
        dl = d.lower()
        hl = (href or "").lower()

        if not dl.startswith("lease:"):
            return False
        if dl.startswith("apr:") or dl.startswith("apr available"):
            return False
        if not self.RE_TERM_VAL.search(d):
            return False
        if href and "/inventory/" not in hl:
            return False
        return True

    # -------- core scrape --------
    def _scrape_lease_cards(self) -> list[dict]:
        html = self._fetch_rendered_html()
        soup = BeautifulSoup(html, "html.parser")

        disclaimer_divs = soup.select("div.FJVwI")
        print(f"[FOUND] disclaimers: {len(disclaimer_divs)}")

        raw = []
        for div in disclaimer_divs:
            disclaimer = " ".join(div.get_text(" ", strip=True).split())
            a = div.find_previous("a", href=True)
            href = urljoin(self.specials_url, a["href"]) if a else None
            raw.append({"href": href, "disclaimer": disclaimer})

        lease_cards = [c for c in raw if self._is_lease_offer(c["href"], c["disclaimer"])]
        print(f"[KEEP] lease offers: {len(lease_cards)}")

        # de-dupe
        seen, out = set(), []
        for c in lease_cards:
            key = ((c["href"] or "").rstrip("/"), c["disclaimer"][:120])
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
        return out

    # -------- required abstract method --------
    def fetch_df(self) -> pd.DataFrame:
        offers = self._scrape_lease_cards()

        cols = [
            "Dealer Specials Link",
            "Due at Signing ($)",
            "Expires",
            "MSRP ($)",          # your table expects this column name
            "Model",
            "Monthly ($)",
            "Term (months)",
        ]

        if not offers:
            return pd.DataFrame(columns=cols)

        rows = []
        for o in offers:
            d = o["disclaimer"]

            def grab(rx):
                m = rx.search(d)
                return m.group(1) if m else None

            total_srp = self.money_to_int(grab(self.RE_TOTAL_SRP_VAL))

            rows.append({
                "Dealer Specials Link": self.specials_url,
                "Due at Signing ($)": self.money_to_int(grab(self.RE_DUE_VAL)),
                "Expires": grab(self.RE_EXPIRES_VAL),
                "MSRP ($)": total_srp,  # store Total SRP into MSRP column for UI consistency
                "Model": grab(self.RE_MODEL_VAL),
                "Monthly ($)": self.first_int(grab(self.RE_MONTHLY_VAL)),
                "Term (months)": self.first_int(grab(self.RE_TERM_VAL)),
            })

        return pd.DataFrame(rows, columns=cols)
