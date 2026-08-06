"""Robot de collecte — Burkina Faso 🇧🇫 · Banque Mondiale (World Bank).

Décline le robot Banque Mondiale (API officielle « procnotices ») pour les
projets financés au Burkina Faso. Ces marchés (passés par des maîtres d'ouvrage/
agences pour le compte du bailleur) relèvent des appels d'offres « privés » au
sens de la plateforme.

La base filtre déjà les avis expirés (échéance passée) et les avis d'attribution :
seules les OPPORTUNITÉS actives sont conservées.
"""
import logging

from scrapers.benin.banque_mondiale_scraper import BanqueMondialeScraper

logger = logging.getLogger("scrapers.burkina_faso.banque_mondiale")


class BanqueMondialeBfScraper(BanqueMondialeScraper):
    country = "BF"
    source_name = "Banque Mondiale (Burkina Faso)"
    tender_type = "prive"
    wb_country_name = "Burkina Faso"


def build() -> BanqueMondialeBfScraper:
    return BanqueMondialeBfScraper()
