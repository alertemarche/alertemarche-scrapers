"""Robot de collecte — Burkina Faso 🇧🇫 · AFD (Agence Française de Développement).

Décline le robot AFD (portail dgMarket, filtrable par `locationISO`) pour le
Burkina Faso (`bf`). Marchés « privés » (bailleur international).
"""
import logging

from scrapers.benin.afd_scraper import AfdScraper

logger = logging.getLogger("scrapers.burkina_faso.afd")


class AfdBfScraper(AfdScraper):
    country = "BF"
    source_name = "AFD (Agence Française de Développement) — Burkina Faso"
    tender_type = "prive"
    afd_iso = "bf"


def build() -> AfdBfScraper:
    return AfdBfScraper()
