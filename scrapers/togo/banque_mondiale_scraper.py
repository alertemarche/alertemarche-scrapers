"""Robot de collecte — Togo 🇹🇬 · Banque Mondiale (World Bank).

Décline le robot Banque Mondiale (API officielle « procnotices ») pour les
projets financés au Togo. Ces marchés (passés par des maîtres d'ouvrage/agences
pour le compte de bailleurs) relèvent des appels d'offres « privés » au sens de
la plateforme.
"""
import logging

from scrapers.benin.banque_mondiale_scraper import BanqueMondialeScraper

logger = logging.getLogger("scrapers.togo.banque_mondiale")


class BanqueMondialeTgScraper(BanqueMondialeScraper):
    country = "TG"
    source_name = "Banque Mondiale (Togo)"
    tender_type = "prive"
    wb_country_name = "Togo"


def build() -> BanqueMondialeTgScraper:
    return BanqueMondialeTgScraper()
