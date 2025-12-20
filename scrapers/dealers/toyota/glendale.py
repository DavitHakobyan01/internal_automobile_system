import re
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from scrapers.base.toyota_base import ToyotaBaseScraper


class ToyotaGlendaleScraper(ToyotaBaseScraper):
    dealer_name = "Toyota of Glendale"
    brand = "Toyota"
    specials_url = "https://www.toyotaofglendale.com/new-monthly-specials/"

    def fetch_df(self) -> pd.DataFrame:
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "darwin", "mobile": False}
        )
        resp = scraper.get(self.specials_url, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        rows: list[dict] = []

        imgs = soup.find_all(
            "img",
            alt=re.compile(r"^(New\s+\d{4}\s+Toyota|Toyota Certified)", re.I),
        )

        for img in imgs:
            model_text = (img.get("alt") or "").strip()

            # exclude non-model offer
            if model_text.lower().startswith("toyota certified"):
                continue

            # walk up to get text block containing disclaimer
            container = img
            block_text = ""
            for _ in range(8):
                container = container.parent
                if not container:
                    break
                txt = " ".join(container.stripped_strings)
                if "View Disclaimer" in txt and "Expires" in txt:
                    block_text = txt
                    break

            disclaimer = self.extract(
                r"(\*.*?Expires\s+\d{1,2}/\d{1,2}/\d{2,4}\.?)",
                block_text,
            )
            if not disclaimer:
                continue

            # keep ONLY lease specials (filters out the Tacoma APR financing card)
            is_lease = (
                re.search(r"due at signing", disclaimer, re.I) is not None
                and re.search(r"1st month[’']?s payment", disclaimer, re.I) is not None
            )
            if not is_lease:
                continue

            monthly = self.money_to_int(
                self.extract(r"1st month[’']?s payment of\s*\$([\d,]+)", disclaimer)
            )
            due = self.money_to_int(
                self.extract(r"\$([\d,]+)\s+due at signing", disclaimer)
            )
            expires = self.extract(r"Expires\s+(\d{1,2}/\d{1,2}/\d{2,4})", disclaimer)

            rows.append(
                {
                    "Model": model_text or None,
                    "Monthly ($)": monthly,
                    "Term (months)": None,      # lease term is image-only
                    "Due at Signing ($)": due,
                    "MSRP ($)": None,
                    "APR (%)": None,
                    "Expires": expires or None,
                    "Dealer Specials Link": self.specials_url,  # <-- ALWAYS this page
                }
            )

        df = pd.DataFrame(
            rows,
            columns=[
                "Model",
                "Monthly ($)",
                "Term (months)",
                "Due at Signing ($)",
                "MSRP ($)",
                "APR (%)",
                "Expires",
                "Dealer Specials Link",
            ],
        )

        # keep real Python None instead of NaN in output objects
        df = df.astype("object").where(pd.notna(df), None)
        return df
