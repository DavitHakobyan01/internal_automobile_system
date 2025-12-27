# scrapers/dealers/toyota/south_bay.py

import pandas as pd

from scrapers.base.toyota_base import ToyotaBaseScraper


class SouthBayToyotaScraper(ToyotaBaseScraper):
    dealer_name = "South Bay Toyota"
    brand = "Toyota"
    specials_url = "https://www.southbaytoyota.com/specials/"

    def fetch_df(self) -> pd.DataFrame:
        """
        South Bay Toyota does NOT publish lease specials on their website.
        This scraper intentionally returns an empty DataFrame
        with the standard lease schema so the pipeline stays consistent.
        """

        columns = [
            "Dealer Specials Link",
            "Due at Signing ($)",
            "Expires",
            "MSRP ($)",
            "Model",
            "Monthly ($)",
            "Term (months)",
        ]

        df = pd.DataFrame(columns=columns)

        return df
