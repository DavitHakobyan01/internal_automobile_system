# scrapers/dealers/mercedes/los_angeles.py

import re
from typing import Optional, Dict, Any, List

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from scrapers.base.mercedes_base import MercedesBaseScraper


class LosAngelesMercedesScraper(MercedesBaseScraper):
    dealer_name: str = "Mercedes-Benz of Los Angeles"
    specials_url: str = (
        "https://www.mbzla.com/dtw-new-mercedes-benz-lease-incentives-finance-offers-los-angeles-ca/"
    )

    CARD_SEL = "div.ncs-container"

    _money_re = re.compile(r"\$?\s*([\d,]+(?:\.\d+)?)")
    _expire_re = re.compile(r"Offers expire\s+(\d{1,2}/\d{1,2}/\d{2,4})", re.IGNORECASE)

    def fetch_df(self) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                locale="en-US",
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(self.specials_url, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)

            self._dismiss_overlays(page)

            try:
                page.wait_for_selector(self.CARD_SEL, timeout=30000)
            except PlaywrightTimeoutError:
                browser.close()
                # Return empty normalized DF (will raise if missing cols; so create empty with cols)
                empty = pd.DataFrame(columns=self.TABLE_COLUMNS)
                return self._normalize_df(empty)

            self._scroll_to_load_all_cards(page)

            cards = page.query_selector_all(self.CARD_SEL)
            for card in cards:
                row = self._extract_lease_row(card)
                if row is not None:
                    rows.append(row)

            browser.close()

        df = pd.DataFrame(rows, columns=self.TABLE_COLUMNS)

        # Remove duplicate rows where all values match
        df = df.drop_duplicates().reset_index(drop=True)

        # Enforce Mercedes schema + types/date format via base class
        return self._normalize_df(df)

    # ---------------- Internals (same logic, just moved into methods) ----------------

    def _to_text(self, el) -> str:
        try:
            return el.inner_text().strip()
        except Exception:
            return ""

    def _attr(self, el, name: str) -> str:
        try:
            v = el.get_attribute(name)
            return (v or "").strip()
        except Exception:
            return ""

    def _money_int(self, s: str) -> Optional[int]:
        if not s:
            return None
        s = s.replace("\xa0", " ").strip()
        m = self._money_re.search(s)
        if not m:
            return None
        try:
            return int(float(m.group(1).replace(",", "")))
        except Exception:
            return None

    def _parse_expires_from_disclaimer(self, disclaimer: str) -> Optional[str]:
        if not disclaimer:
            return None
        m = self._expire_re.search(disclaimer)
        if not m:
            return None
        # keep site format; _normalize_df will standardize later
        return m.group(1).strip()

    def _build_model(self, card) -> str:
        year = self._to_text(card.query_selector(".title-year"))
        make = self._to_text(card.query_selector(".title-make"))
        model = self._to_text(card.query_selector(".title-model"))

        trim_el = card.query_selector(".title-trim")
        trim = ""
        if trim_el:
            trim = self._attr(trim_el, "data-trim") or self._to_text(trim_el)

        body = self._to_text(card.query_selector(".title-body-style"))

        parts = [p for p in [year, make, model, trim, body] if p]
        if parts:
            return " ".join(parts).strip()

        h3 = card.query_selector("h3")
        return self._to_text(h3)

    def _extract_lease_row(self, card) -> Optional[Dict[str, Any]]:
        # Monthly
        monthly_el = card.query_selector(".ncs-price-block.lease .ncs-price")
        monthly = self._money_int(self._to_text(monthly_el)) if monthly_el else None

        # Term + due at signing (from lease term text)
        lease_term_el = card.query_selector(".ncs-price-block.lease .ncs-price-term")
        lease_term_text = self._to_text(lease_term_el)

        term_months = None
        due_at_signing = None

        if lease_term_text:
            m_term = re.search(r"\bfor\s+(\d+)\s+mos\b", lease_term_text, re.IGNORECASE)
            if m_term:
                term_months = int(m_term.group(1))

            m_due = re.search(
                r"w/\s*\$?\s*([\d,]+)\s*due at signing",
                lease_term_text,
                re.IGNORECASE,
            )
            if m_due:
                try:
                    due_at_signing = int(m_due.group(1).replace(",", ""))
                except Exception:
                    due_at_signing = None

        # MSRP
        msrp = None
        msrp_num_el = card.query_selector(".ncs-msrp .ncs-price-number")
        if msrp_num_el:
            msrp = self._money_int(self._to_text(msrp_num_el))
        if msrp is None:
            msrp_buy_el = card.query_selector(".ncs-price-block.buy .ncs-price")
            msrp = self._money_int(self._to_text(msrp_buy_el)) if msrp_buy_el else None

        # Expires
        disclaimer_el = card.query_selector(".ncs-disclaimer")
        disclaimer = self._to_text(disclaimer_el)
        expires = self._parse_expires_from_disclaimer(disclaimer)

        # lease-only filter (your rule)
        if monthly is None or term_months is None or due_at_signing is None:
            return None

        return {
            "Due at Signing ($)": due_at_signing,
            "Expires": expires,
            "MSRP ($)": msrp,
            "Model": self._build_model(card),
            "Monthly ($)": monthly,
            "Term (months)": term_months,
        }

    def _dismiss_overlays(self, page) -> None:
        page.evaluate(
            """
            () => {
              const sels = [
                'iframe[title*="chat" i]', 'iframe[src*="chat" i]',
                '.drift-widget', '#drift-widget', '.drift-conductor-item',
                '.lc-chat', '.livechat', '.chat-widget'
              ];
              for (const s of sels) {
                document.querySelectorAll(s).forEach(el => {
                  try { el.style.display = 'none'; el.style.visibility='hidden'; } catch(e) {}
                });
              }
            }
            """
        )

    def _scroll_to_load_all_cards(self, page, stable_rounds: int = 6, max_rounds: int = 250) -> int:
        last = 0
        same = 0
        for _ in range(max_rounds):
            count = page.locator(self.CARD_SEL).count()
            if count == last:
                same += 1
            else:
                same = 0
                last = count

            if same >= stable_rounds:
                break

            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(900)

        return page.locator(self.CARD_SEL).count()


