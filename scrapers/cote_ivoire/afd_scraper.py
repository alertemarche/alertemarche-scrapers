"""Robot de collecte — Côte d'Ivoire 🇨🇮 · AFD (Agence Française de Développement).

Décline le robot AFD (portail des appels d'offres, filtrable par `locationISO`)
pour la Côte d'Ivoire. Marchés « privés » (bailleur international).
"""
import logging

from scrapers.benin.afd_scraper import AfdScraper

logger = logging.getLogger("scrapers.cote_ivoire.afd")


class AfdCiScraper(AfdScraper):
    country = "CI"
    source_name = "AFD (Agence Française de Développement) — Côte d'Ivoire"
    tender_type = "prive"
    afd_iso = "ci"


def build() -> AfdCiScraper:
    return AfdCiScraper()
