import re
from datetime import date
from typing import Optional, Dict, Any, List

import pandas as pd
from bs4 import BeautifulSoup
import requests

from scrapers.base.toyota_base import ToyotaBaseScraper


class PasadenaToyotaScraper(ToyotaBaseScraper):
    dealer_name = "Toyota Pasadena"
    specials_url = "https://www.toyotapasadena.com/new-vehicles/new-vehicle-specials/"

    # -------------------------- helpers --------------------------

    @staticmethod
    def _clean(s: Optional[str]) -> Optional[str]:
        if not s:
            return None
        s = re.sub(r"\s+", " ", s).strip()
        return s or None

    @staticmethod
    def _money_to_float(s: Optional[str]) -> Optional[float]:
        if not s:
            return None
        m = re.search(r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", s)
        if not m:
            return None
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None

    @staticmethod
    def _money_to_int(s: Optional[str]) -> Optional[int]:
        # FIX: reference this class, not ToyotaPasadenaSpecialsScraper
        v = PasadenaScraper._money_to_float(s)
        if v is None:
            return None
        return int(round(v))

    @staticmethod
    def _extract_term_months(s: str) -> Optional[int]:
        m = re.search(r"\bfor\s+(\d{1,3})\s+months?\b", s, re.IGNORECASE)
        return int(m.group(1)) if m else None

    @staticmethod
    def _extract_due_at_signing(s: Optional[str]) -> Optional[int]:
        if not s:
            return None
        m = re.search(r"([\d,]+)\s+due\s+at\s+signing", s, re.IGNORECASE)
        return int(m.group(1).replace(",", "")) if m else None

    @staticmethod
    def _extract_miles_per_year(s: Optional[str]) -> Optional[int]:
        if not s:
            return None
        m = re.search(r"based\s+on\s+([\d,]+)\s*miles\s*/\s*year", s, re.IGNORECASE)
        if m:
            return int(m.group(1).replace(",", ""))
        m = re.search(r"\b([\d,]+)\s*miles\b", s, re.IGNORECASE)
        return int(m.group(1).replace(",", "")) if m else None

    @staticmethod
    def _extract_applies_to_trim(s: Optional[str]) -> Optional[str]:
        if not s:
            return None
        m = re.search(r"\bapplies\s+to\s+([A-Z0-9][A-Z0-9 \-\+]+)\b", s)
        if not m:
            return None
        val = m.group(1).strip()
        if re.search(r"\btrims?\b", val, re.IGNORECASE):
            return None
        return val

    @staticmethod
    def _extract_msrp(text: Optional[str]) -> Optional[int]:
        """
        MSRP is usually not in the lease block; it's often in finance text:
          - "Starting MSRP $31,590"
          - "MSRP: ... $40,090"
        """
        if not text:
            return None

        m = re.search(r"starting\s+msrp\s*\$?\s*([\d,]+)", text, re.IGNORECASE)
        if m:
            return int(m.group(1).replace(",", ""))

        m = re.search(r"\bmsrp\b.*?\$?\s*([\d,]+)", text, re.IGNORECASE)
        if m:
            return int(m.group(1).replace(",", ""))

        return None

    # -------------------------- fetching HTML --------------------------

    def _fetch_html_requests(self) -> Optional[str]:
        sess = requests.Session()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.toyotapasadena.com/",
        }

        r1 = sess.get("https://www.toyotapasadena.com/", headers=headers, timeout=30)
        if r1.status_code >= 400:
            return None

        r2 = sess.get(self.specials_url, headers=headers, timeout=30)
        if r2.status_code >= 400:
            return None

        return r2.text

    def _fetch_html_playwright(self) -> str:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
            page = context.new_page()
            page.goto(self.specials_url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_selector("div.cc-main-container", timeout=60_000)
            html = page.content()
            context.close()
            browser.close()
            return html

    def _get_soup(self) -> BeautifulSoup:
        html = self._fetch_html_requests()
        if html:
            soup = BeautifulSoup(html, "html.parser")
            if soup.select_one("div.cc-main-container"):
                return soup

        html = self._fetch_html_playwright()
        return BeautifulSoup(html, "html.parser")

    # -------------------------- parsing ONLY LEASE --------------------------

    def _parse_card_lease(self, card: BeautifulSoup) -> Optional[Dict[str, Any]]:
        year = self._clean(card.select_one(".vehicle-year").get_text(strip=True)) if card.select_one(".vehicle-year") else None
        make = self._clean(card.select_one(".vehicle-make").get_text(strip=True)) if card.select_one(".vehicle-make") else None
        model = self._clean(card.select_one(".vehicle-model").get_text(strip=True)) if card.select_one(".vehicle-model") else None
        trim = self._clean(card.select_one(".vehicle-trim").get_text(" ", strip=True)) if card.select_one(".vehicle-trim") else None

        title_parts = [p for p in [("New " + year) if year else None, make, model, trim] if p]
        title = self._clean(" ".join(title_parts)) if title_parts else None

        offer_blocks = card.select("div.cc-offer")
        lease_block = None
        for b in offer_blocks:
            t = self._clean(b.get_text(" ", strip=True)) or ""
            if re.search(r"\blease\s+for\s+only\b", t, re.IGNORECASE):
                lease_block = b
                break

        tcard = self._clean(card.get_text(" ", strip=True)) or ""
        msrp = self._extract_msrp(tcard)

        if lease_block is None:
            if not re.search(r"\blease\s+for\s+only\b", tcard, re.IGNORECASE):
                return None
            return self._parse_lease_from_text(title, tcard, msrp)

        t = self._clean(lease_block.get_text(" ", strip=True)) or ""
        return self._parse_lease_from_text(title, t, msrp)

    def _parse_lease_from_text(self, title: Optional[str], text: str, msrp: Optional[int]) -> Optional[Dict[str, Any]]:
        monthly = None
        m = re.search(r"\$?\s*([\d,]+(?:\.\d+)?)\s*/\s*mo\b", text, re.IGNORECASE)
        if m:
            monthly = float(m.group(1).replace(",", ""))

        term = self._extract_term_months(text)
        due = self._extract_due_at_signing(text)
        miles = self._extract_miles_per_year(text)
        applies_trim = self._extract_applies_to_trim(text)

        if monthly is None and term is None:
            return None

        return {
            "title": title,
            "monthly": monthly,
            "term": term,
            "due_at_signing": due,
            "msrp": msrp,
            "miles_per_year": miles,
            "applies_to_trim": applies_trim,
            "scrape_date": date.today().strftime("%m/%d/%Y"),
            "source_url": self.specials_url,
        }

    def fetch_df(self) -> pd.DataFrame:
        soup = self._get_soup()
        cards = soup.select("div.cc-main-container")

        rows: List[Dict[str, Any]] = []
        for c in cards:
            row = self._parse_card_lease(c)
            if row:
                rows.append(row)

        df = pd.DataFrame(rows)

        # Return schema-consistent empty df
        if df.empty:
            return pd.DataFrame(
                columns=[
                    "Model",
                    "Monthly ($)",
                    "Term (months)",
                    "Due at Signing ($)",
                    "MSRP ($)",
                    "APR (%)",
                    "Expires",
                    "Dealer Specials Link",
                ]
            )

        # ONLY change column names / final schema (parser unchanged)
        df = df.rename(
            columns={
                "title": "Model",
                "monthly": "Monthly ($)",
                "term": "Term (months)",
                "due_at_signing": "Due at Signing ($)",
                "msrp": "MSRP ($)",
                "source_url": "Dealer Specials Link",
            }
        )

        # Pasadena lease rows don't have APR
        df["APR (%)"] = None

        # Use your system-wide expiry value (matches your table)
        df["Expires"] = "01/05/2026"

        df = df[
            [
                "Model",
                "Monthly ($)",
                "Term (months)",
                "Due at Signing ($)",
                "MSRP ($)",
                "APR (%)",
                "Expires",
                "Dealer Specials Link",
            ]
        ].drop_duplicates(
            subset=["Model", "Monthly ($)", "Term (months)"],
            keep="first"
        ).reset_index(drop=True)

        return df


