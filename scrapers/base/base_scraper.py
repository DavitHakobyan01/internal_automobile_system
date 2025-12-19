from abc import ABC, abstractmethod
import pandas as pd


class BaseScraper(ABC):
    dealer_name: str
    brand: str
    specials_url: str

    @abstractmethod
    def fetch_df(self) -> pd.DataFrame:
        pass
