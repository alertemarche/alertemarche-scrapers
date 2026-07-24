"""Robot de collecte — Côte d'Ivoire 🇨🇮 · Banque Mondiale (World Bank).

Décline le robot Banque Mondiale (API officielle « procnotices ») pour les
projets financés en Côte d'Ivoire. Ces marchés (passés par des maîtres
d'ouvrage/agences pour le compte de bailleurs) relèvent des appels d'offres
« privés » au sens de la plateforme.
"""
import logging

from scrapers.benin.banque_mondiale_scraper import BanqueMondialeScraper

logger = logging.getLogger("scrapers.cote_ivoire.banque_mondiale")


class BanqueMondialeCiScraper(BanqueMondialeScraper):
    country = "CI"
    source_name = "Banque Mondiale (Côte d'Ivoire)"
    tender_type = "prive"
    wb_country_name = "Cote d'Ivoire"


def build() -> BanqueMondialeCiScraper:
    return BanqueMondialeCiScraper()
