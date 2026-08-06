"""Classe de base commune aux robots de collecte.

Chaque scraper pays hérite de BaseScraper et implémente `parse(html, base_url)`
pour extraire les opportunités depuis la ou les page(s) de listing.

Un extracteur heuristique générique (`heuristic_extract`) est fourni : il repère
les liens dont le libellé évoque un appel d'offres (mots-clés) lorsque la
structure exacte de la source n'est pas connue. Seules des **métadonnées** et le
lien vers la source sont collectés — jamais les documents (DAO).
"""
import logging
import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from . import config

logger = logging.getLogger("scrapers.base")

# Mots-clés (déjà normalisés : sans apostrophe, minuscules) indiquant une
# opportunité de marché. Le texte des liens est normalisé de la même façon.
KEYWORDS = [
    "appel d offres", "appel doffres", "appel a candidature",
    "avis de", "avis d appel", "avis dappel", "avis de recrutement",
    "consultation", "manifestation d interet", "manifestation dinteret",
    "demande de proposition", "demande de prix", "appel a manifestation",
    "sollicitation", "marche public", "marches publics", "recrutement",
    " dao ", "aoo", "aon", "avis general",
]


def _normalize(text: str) -> str:
    """Minuscule, sans apostrophes/accents, espaces simples — pour le matching."""
    text = (text or "").lower()
    for ch in ("'", "’", "`", "´"):
        text = text.replace(ch, " ")
    accents = str.maketrans("àâäéèêëïîôöùûüç", "aaaeeeeiioouuuc")
    text = text.translate(accents)
    return " ".join(text.split())

DATE_PATTERNS = [
    (re.compile(r"(\d{2})[/-](\d{2})[/-](\d{4})"), "%d/%m/%Y"),
    (re.compile(r"(\d{4})[/-](\d{2})[/-](\d{2})"), "%Y/%m/%d"),
]


class BaseScraper:
    country: str = ""            # BJ | TG | CI
    source_name: str = ""        # Nom lisible de la source
    tender_type: str = "public"  # public | prive

    def __init__(self):
        self.base_url = config.SOURCES.get(self.country, "")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})
        # Routage via le proxy rotatif Webshare (requêtes vers portails externes).
        if config.PROXIES:
            self.session.proxies.update(config.PROXIES)

    # ---- Réseau -------------------------------------------------------
    def fetch(self, url: str) -> str | None:
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp.text
            except Exception as exc:  # noqa: BLE001
                logger.warning("[%s] GET %s échec %s/%s : %s",
                               self.country, url, attempt, config.MAX_RETRIES, exc)
        return None

    # ---- À surcharger -------------------------------------------------
    def start_urls(self) -> list[str]:
        """URLs de listing à visiter. Par défaut : la page d'accueil de la source."""
        return [self.base_url] if self.base_url else []

    def parse(self, html: str, page_url: str) -> list[dict]:
        """Extraction spécifique à la source. Par défaut : heuristique générique."""
        return self.heuristic_extract(html, page_url)

    # ---- Heuristique générique ---------------------------------------
    def heuristic_extract(self, html: str, page_url: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        items: list[dict] = []
        for a in soup.find_all("a", href=True):
            text = " ".join(a.get_text(" ", strip=True).split())
            if len(text) < 12:
                continue
            norm = _normalize(text)
            if not any(kw.strip() in norm for kw in KEYWORDS):
                continue
            href = urljoin(page_url, a["href"])
            deadline = self._nearby_date(a)
            items.append(self.make_item(
                title=text[:255],
                institution=self.source_name,
                source_url=href,
                deadline=deadline,
            ))
        return items

    def _nearby_date(self, node) -> str | None:
        """Cherche une date proche du lien (ligne / parent)."""
        context = ""
        parent = node.find_parent(["tr", "li", "div", "article", "p"])
        if parent:
            context = parent.get_text(" ", strip=True)
        return self.extract_date(context)

    # ---- Utilitaires --------------------------------------------------
    @staticmethod
    def extract_date(text: str) -> str | None:
        if not text:
            return None
        for pattern, fmt in DATE_PATTERNS:
            m = pattern.search(text)
            if m:
                try:
                    return datetime.strptime(m.group(0), fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
        return None

    def make_item(self, title: str, institution: str, source_url: str,
                  deadline: str | None = None, estimated_amount: str | None = None,
                  tender_type: str | None = None, procedure_type: str | None = None) -> dict:
        from .premium_detector import detect_premium
        item = {
            "title": title,
            "institution": institution or self.source_name,
            "estimated_amount": estimated_amount,
            "deadline": deadline,
            "country": self.country,
            "type": tender_type or self.tender_type,
            "procedure_type": procedure_type,
            "source_name": self.source_name,
            "source_url": source_url,
        }
        # Détection des opportunités « premium » (fort potentiel)
        return detect_premium(item)

    # ---- Exécution ----------------------------------------------------
    def run(self) -> list[dict]:
        collected: list[dict] = []
        for url in self.start_urls():
            html = self.fetch(url)
            if not html:
                continue
            try:
                collected.extend(self.parse(html, url))
            except Exception as exc:  # noqa: BLE001
                logger.exception("[%s] Erreur de parsing sur %s : %s", self.country, url, exc)
        logger.info("[%s] %s — %s opportunités brutes collectées",
                    self.country, self.source_name, len(collected))
        return collected
