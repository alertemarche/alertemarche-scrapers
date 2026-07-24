"""Robot de collecte — Sénégal 🇸🇳 · Banque Mondiale (World Bank).

Décline le robot Banque Mondiale (API officielle « procnotices ») pour les
projets financés au Sénégal. Ces marchés (passés par des maîtres d'ouvrage/agences
pour le compte de bailleurs) relèvent des appels d'offres « privés » au sens de
la plateforme.
"""
import logging

from scrapers.benin.banque_mondiale_scraper import BanqueMondialeScraper

logger = logging.getLogger("scrapers.senegal.banque_mondiale")


class BanqueMondialeSnScraper(BanqueMondialeScraper):
    country = "SN"
    source_name = "Banque Mondiale (Sénégal)"
    tender_type = "prive"
    wb_country_name = "Senegal"


def build() -> BanqueMondialeSnScraper:
    return BanqueMondialeSnScraper()
