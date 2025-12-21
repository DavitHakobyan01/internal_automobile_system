import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from scrapers.base.toyota_base import ToyotaBaseScraper


class NorthridgeToyotaScraper(ToyotaBaseScraper):
    dealer_name = "Northridge Toyota"
    brand = "Toyota"
    specials_url = "https://www.northridgetoyota.com/new-car-specials/"

    COLS = [
        "Model",
        "Monthly ($)",
        "Term (months)",
        "Due at Signing ($)",
        "MSRP ($)",
        "APR (%)",
        "Expires",
        "Dealer Specials Link",
    ]

    def fetch_df(self) -> pd.DataFrame:
        html = self._get_html()
        soup = BeautifulSoup(html, "html.parser")

        rows = []
        imgs = soup.find_all("img", alt=True)

        for img in imgs:
            alt = img.get("alt", "") or ""
            if "Lease for $" not in alt:
                continue

            # climb up to the offer block that contains DISCLAIMER + full disclaimer text
            card = img.parent
            for _ in range(12):
                if not card:
                    break
                txt = card.get_text(" ", strip=True)
                if "DISCLAIMER" in txt and "Lease a new" in txt:
                    break
                card = card.parent
            if not card:
                continue

            blob = " ".join(card.stripped_strings)

            monthly = self._parse_monthly(blob)
            term = self._parse_term_months(blob)
            due = self._parse_due_at_signing(blob)
            msrp = self._parse_tsrp_or_msrp(blob)
            expires = self._parse_expires(blob)

            rows.append({
                "Model": self._parse_model(blob),
                "Monthly ($)": monthly,
                "Term (months)": term,
                "Due at Signing ($)": due,
                "MSRP ($)": msrp,
                "APR (%)": None,
                "Expires": expires,
                "Dealer Specials Link": self.specials_url,
            })

        df = pd.DataFrame(rows)
        for c in self.COLS:
            if c not in df.columns:
                df[c] = pd.NA
        return df[self.COLS]

    def _get_html(self) -> str:
        ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
        )
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=ua)
            page.goto(self.specials_url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(1500)
            html = page.content()
            browser.close()
            return html

    # ---------------- FIXED PARSERS ----------------

    def _parse_monthly(self, text: str) -> int | None:
        # "Lease for $87 per month"
        val = self.extract(r"Lease\s*for\s*\$([0-9,]+)", text)
        return self.money_to_int(val)

    def _parse_term_months(self, text: str) -> int | None:
        # "Per month for 36 months" OR "for 36 months"
        val = self.extract(r"\bfor\s+(\d{2})\s+months\b", text)
        return self.first_int(val)

    def _parse_due_at_signing(self, text: str) -> int | None:
        # IMPORTANT: capture ONLY the number right before "Due At Signing"
        # Example: "with $5,999 Due At Signing"
        val = self.extract(r"\bwith\s*\$([0-9,]+)\s*Due\s*At\s*Signing\b", text)
        if not val:
            val = self.extract(r"\$([0-9,]+)\s*Due\s*At\s*Signing\b", text)
        return self.money_to_int(val)

    def _parse_tsrp_or_msrp(self, text: str) -> int | None:
        # Example: "TSRP: $34,658."
        val = self.extract(r"\b(?:TSRP|MSRP)\s*:\s*\$([0-9,]+)\b", text)
        return self.money_to_int(val)

    def _parse_expires(self, text: str) -> str | None:
        # Example: "Expires 1/05/26."
        return self.extract(r"\bExpires\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})\b", text)

    def _parse_model(self, text: str) -> str | None:
        # From page content: "New 2025 Toyota Tacoma" then "SR5 RWD" etc.
        name = self.extract(r"\bNew\s+20\d{2}\s+Toyota\s+([A-Za-z0-9\- ]+?)\b", text)
        trim = self.extract(r"\b(LE|SE|XLE|XSE|SR5|TRD\s+PRO|LIMITED|PLATINUM)\b", text)
        if name and trim:
            return f"{name.strip()} {trim.strip()}"
        return name.strip() if name else None


if __name__ == "__main__":
    df = NorthridgeToyotaScraper().fetch_df()
    print(df)
    print("Total specials:", len(df))
