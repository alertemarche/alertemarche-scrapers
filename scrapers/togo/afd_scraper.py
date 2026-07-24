"""Robot de collecte — Togo 🇹🇬 · AFD (Agence Française de Développement).

Décline le robot AFD (portail des appels d'offres, filtrable par `locationISO`)
pour le Togo. Marchés « privés » (bailleur international).
"""
import logging

from scrapers.benin.afd_scraper import AfdScraper

logger = logging.getLogger("scrapers.togo.afd")


class AfdTgScraper(AfdScraper):
    country = "TG"
    source_name = "AFD (Agence Française de Développement) — Togo"
    tender_type = "prive"
    afd_iso = "tg"


def build() -> AfdTgScraper:
    return AfdTgScraper()
