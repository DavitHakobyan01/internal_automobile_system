import pandas as pd
from scrapers.base.mercedes_base import MercedesBaseScraper


class BeverlyHillsMercedesScraper(MercedesBaseScraper):
    dealer_name: str = "Mercedes-Benz of Beverly Hills"
    specials_url: str = "https://www.bhbenz.com/new-vehicles/new-vehicle-specials/"

    def fetch_df(self) -> pd.DataFrame:
        """
        Return an empty DataFrame with the canonical Mercedes lease schema.
        """
        return pd.DataFrame(columns=self.TABLE_COLUMNS)
