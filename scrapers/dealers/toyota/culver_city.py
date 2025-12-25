import re
import requests
import pandas as pd

from scrapers.base.toyota_base import ToyotaBaseScraper


class CulverCityToyotaScraper(ToyotaBaseScraper):
    dealer_name = "Culver City Toyota"
    brand = "Toyota"
    specials_url = "https://www.culvercitytoyota.com/offers-incentives/"

    API_URL = "https://www.buyatoyota.com/api/layout?limit=all&url=%2Fsocal%2Flanding%2Fdealer_offers_frame%2F"

    def fetch_df(self) -> pd.DataFrame:
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "referer": "https://www.buyatoyota.com/socal/landing/dealer_offers_frame/?limit=all",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "x-api-key": "JK97CcjSOjlPusmD5RLO",
        }

        cookies = {
            "uuid": "53593329-65b2-4a77-a028-e25cb83116c4",
            "ens_syncData": "%7B%22psync_uuid%22%3A%22d7874738-39aa-4774-b960-8109ed757302%22%7D",
            "tmsvisitor": "fff71fc59fe206bf%5Ecd30c0f25fd6aa70",
            "tms_vi": "fff71fc59fe206bf%5Ecd30c0f25fd6aa70",
            "s_vi": "fff71fc59fe206bf%5Ecd30c0f25fd6aa70",
        }

        r = requests.get(self.API_URL, headers=headers, cookies=cookies, timeout=30)
        r.raise_for_status()

        ct = (r.headers.get("content-type") or "").lower()
        if "application/json" not in ct and not r.text.lstrip().startswith(("{", "[")):
            raise RuntimeError(
                f"Not JSON. content-type={ct}\nFirst 200 chars:\n{r.text[:200]}"
            )

        data = r.json()
        cards = self._walk_cards(data)
        df = self._extract_leases_df(cards)

        return df

    # ----------------------------
    # Internal helpers (same logic)
    # ----------------------------

    def _walk_cards(self, obj) -> list[dict]:
        found = []

        def walk(x):
            if isinstance(x, dict):
                keys = set(x.keys())
                score = sum(k in keys for k in ("typeText", "heading", "details", "endDate", "offerId"))
                if score >= 3:
                    found.append(x)
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)

        walk(obj)

        # dedupe by offerId/id
        seen = set()
        out = []
        for c in found:
            oid = c.get("offerId") or c.get("id")
            if oid and oid in seen:
                continue
            if oid:
                seen.add(oid)
            out.append(c)
        return out

    def _pick_model_text(self, card: dict) -> str | None:
        heading = card.get("heading")
        desc = card.get("description")
        sub = card.get("subHeading")

        for t in (heading, desc, sub):
            if isinstance(t, str) and t.strip():
                return t.strip()

        yr = card.get("year")
        series = card.get("seriesName")
        if yr and series:
            return f"{yr} {series}"
        return None
    
    def _extract_trim(self, card: dict) -> str | None:
        """
        Extract human trim name like:
        LE, SE, XLE, XSE, LE Hybrid, XSE Hybrid, etc.
        """
        disclaimers = card.get("disclaimers") or []
        if not disclaimers:
            return None

        text = " ".join(disclaimers)

        # Common Toyota trims (expandable)
        trim_pattern = (
            r"\b("
            r"LE|SE|XLE|XSE|SR|SR5|TRD Pro|Limited|Platinum"
            r")(?:\s+(Hybrid|AWD|FWD))?\b"
        )

        m = re.search(trim_pattern, text, re.IGNORECASE)
        if not m:
            return None

        base = m.group(1).upper()
        suffix = m.group(2)

        if suffix:
            return f"{base} {suffix.capitalize()}"

        return base

    
    def _extract_msrp_from_disclaimer(self, card: dict) -> float | None:
        disclaimers = card.get("disclaimers") or []
        if not disclaimers:
            return None

        text = " ".join(disclaimers)
        m = re.search(r"Total SRP of \$([\d,]+)", text)
        if not m:
            return None

        return float(m.group(1).replace(",", ""))



    def _money(self, x):
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x)
        m = re.search(r"(\d[\d,]*)(\.\d+)?", s)
        if not m:
            return None
        return float((m.group(1) + (m.group(2) or "")).replace(",", ""))

    def _intnum(self, x):
        v = self._money(x)
        return int(v) if v is not None else None

    def _floatnum(self, x):
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        m = re.search(r"\d+(\.\d+)?", str(x))
        return float(m.group(0)) if m else None

    def _extract_leases_df(self, cards: list[dict]) -> pd.DataFrame:
        rows = []

        for c in cards:
            # STRICT lease filter
            if (c.get("typeText") or "").lower() != "lease" and (c.get("type") or "").lower() != "lease":
                continue

            details = c.get("details") if isinstance(c.get("details"), dict) else {}

            base_model = self._pick_model_text(c)
            trim = self._extract_trim(c)

            model_text = base_model
            if trim:
                model_text = f"{base_model} {trim}"

            monthly = self._money(details.get("rate"))
            term = self._intnum(details.get("duration"))
            due = self._money(details.get("due"))

            msrp = self._extract_msrp_from_disclaimer(c)

            rows.append(
                {
                    "Model": model_text,
                    "Monthly ($)": monthly,
                    "Term (months)": term,
                    "Due at Signing ($)": due,
                    "MSRP ($)": msrp,
                    "Expires": c.get("endDate"),
                    "Dealer Specials Link": self.specials_url,
                    "offer_id": c.get("offerId") or c.get("id"),
                }
            )

        df = pd.DataFrame(rows)

        if not df.empty:
            df = (
                df.drop_duplicates(subset=["offer_id"])
                .drop(columns=["offer_id"])
                .sort_values(["Model", "Monthly ($)"], na_position="last")
                .reset_index(drop=True)
            )

        return df




