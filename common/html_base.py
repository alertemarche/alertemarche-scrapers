"""Base commune aux robots de collecte HTML enrichis.

`HtmlScraper` complète `ApiScraper` (dont il réutilise le riche `make_item`
avec référence, dao_url, external_id…) par une méthode de récupération HTML
robuste (`fetch_html`) et des utilitaires de parsing de dates françaises
(« 13 Août 2026 », « 30 juin 2026 à 10 h », « 22-Jul-26 », « 11-08-2026 »).

Chaque robot HTML hérite de cette classe et implémente `collect()`.
Principe de robustesse : en cas d'indisponibilité de la source, on journalise
un avertissement et on retourne une liste vide — jamais de crash.
"""
import logging
import re
import time
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

from . import config
from .api_base import ApiScraper

logger = logging.getLogger("scrapers.html")

# Mois français -> numéro (avec variantes abrégées).
_FR_MONTHS = {
    "janvier": 1, "janv": 1, "jan": 1,
    "février": 2, "fevrier": 2, "févr": 2, "fevr": 2, "fev": 2, "feb": 2,
    "mars": 3, "mar": 3,
    "avril": 4, "avr": 4, "apr": 4,
    "mai": 5,
    "juin": 6, "jun": 6,
    "juillet": 7, "juil": 7, "jul": 7,
    "août": 8, "aout": 8, "aug": 8, "aoû": 8,
    "septembre": 9, "sept": 9, "sep": 9,
    "octobre": 10, "oct": 10,
    "novembre": 11, "nov": 11,
    "décembre": 12, "decembre": 12, "déc": 12, "dec": 12,
}


class HtmlScraper(ApiScraper):
    method = "html"

    def __init__(self):
        super().__init__()
        # Beaucoup de sites HTML renvoient une erreur si Accept=application/json.
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        })

    # ---- Réseau -------------------------------------------------------
    def fetch_html(self, url: str, params: dict | None = None) -> str | None:
        """GET HTML avec retries. Retourne le texte ou None (jamais d'exception)."""
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=params,
                                        timeout=config.REQUEST_TIMEOUT, verify=True)
                resp.raise_for_status()
                if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
                    resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            except Exception as exc:  # noqa: BLE001
                logger.warning("[%s] GET %s échec %s/%s : %s",
                               self.country, url, attempt, config.MAX_RETRIES, exc)
                time.sleep(1.2 * attempt)
        return None

    def soup(self, url: str, params: dict | None = None) -> BeautifulSoup | None:
        html = self.fetch_html(url, params=params)
        if not html:
            return None
        return BeautifulSoup(html, "lxml")

    # ---- Dates --------------------------------------------------------
    @staticmethod
    def parse_fr_date(text: str) -> str | None:
        """Extrait une date d'un texte FR variés -> 'YYYY-MM-DD' ou None.

        Gère : '13 Août 2026', '30 juin 2026 à 10 h', '31 Juillet 2026 à 16h30',
        '11-08-2026', '2026-08-11', '22-Jul-26'.
        """
        if not text:
            return None
        t = " ".join(str(text).split())

        # ISO : 2026-08-11
        m = re.search(r"(20\d{2})[/-](\d{1,2})[/-](\d{1,2})", t)
        if m:
            y, mo, d = map(int, m.groups())
            return HtmlScraper._safe(y, mo, d)

        # Numérique : 11-08-2026 ou 11/08/2026
        m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](20\d{2})", t)
        if m:
            d, mo, y = map(int, m.groups())
            return HtmlScraper._safe(y, mo, d)

        # 22-Jul-26 / 22-Jul-2026
        m = re.search(r"(\d{1,2})[-\s]([A-Za-zéûôàè]{3,4})[-\s](\d{2,4})", t)
        if m:
            d = int(m.group(1))
            mo = _FR_MONTHS.get(m.group(2).lower().rstrip("."))
            yr = int(m.group(3))
            y = yr + 2000 if yr < 100 else yr
            if mo:
                return HtmlScraper._safe(y, mo, d)

        # Texte FR : 13 Août 2026 / 30 juin 2026
        m = re.search(r"(\d{1,2})\s+([A-Za-zéûôàèùî]+)\.?\s+(20\d{2})", t)
        if m:
            d = int(m.group(1))
            mo = _FR_MONTHS.get(m.group(2).lower())
            y = int(m.group(3))
            if mo:
                return HtmlScraper._safe(y, mo, d)
        return None

    @staticmethod
    def _safe(y: int, mo: int, d: int) -> str | None:
        try:
            return date(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            return None

    @staticmethod
    def is_active(deadline: str | None) -> bool:
        """True si pas de deadline (marché à venir) ou deadline >= aujourd'hui."""
        if not deadline:
            return True
        try:
            return datetime.strptime(deadline, "%Y-%m-%d").date() >= date.today()
        except ValueError:
            return True

    @staticmethod
    def clean(text: str | None) -> str:
        return " ".join((text or "").split())
