import re
from scrapers.base.base_scraper import BaseScraper


class ToyotaBaseScraper(BaseScraper):
    """
    ABSTRACT Toyota base.
    NO network calls.
    NO dealer-specific logic.
    """

    @staticmethod
    def extract(pattern: str, text: str | None):
        if not text:
            return None
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1) if m else None

    @staticmethod
    def money_to_int(text: str | None):
        if not text:
            return None
        digits = re.sub(r"[^\d]", "", text)
        return int(digits) if digits else None

    @staticmethod
    def first_int(text: str | None):
        if not text:
            return None
        m = re.search(r"(\d+)", text)
        return int(m.group(1)) if m else None

