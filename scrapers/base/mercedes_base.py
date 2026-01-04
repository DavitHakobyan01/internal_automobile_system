from abc import ABC
from typing import List
import pandas as pd
from scrapers.base.base_scraper import BaseScraper


class MercedesBaseScraper(BaseScraper, ABC):
    brand: str = "Mercedes-Benz"

    # 🔒 Single source of truth for Mercedes lease table
    TABLE_COLUMNS: List[str] = [
        "Due at Signing ($)",
        "Expires",
        "MSRP ($)",
        "Model",
        "Monthly ($)",
        "Term (months)",
    ]

    def _normalize_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enforce Mercedes lease table schema.
        All subclasses MUST pass through this.
        """
        # Ensure all required columns exist
        missing = set(self.TABLE_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(
                f"{self.dealer_name}: missing required columns: {missing}"
            )

        # Exact column order
        df = df[self.TABLE_COLUMNS]

        # Normalize date format
        df["Expires"] = pd.to_datetime(df["Expires"]).dt.strftime("%-m/%-d/%Y")

        # Normalize numeric columns
        for col in [
            "Due at Signing ($)",
            "MSRP ($)",
            "Monthly ($)",
            "Term (months)",
        ]:
            df[col] = pd.to_numeric(df[col], errors="raise").astype(int)

        return df
