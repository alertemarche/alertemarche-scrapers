"""Robot de collecte — Bénin 🇧🇯 · Appels d'offres PRIVÉS (organismes internationaux).

Source : UNGM (United Nations Global Marketplace), portail officiel des marchés
du système des Nations Unies. On y trouve les avis d'appel d'offres des agences
et organismes internationaux opérant au Bénin (PNUD, UNICEF, UNFPA, PAM, OMS,
FAO…) — c.-à-d. des marchés « privés » au sens de la plateforme (acheteurs non
étatiques).

Seules des métadonnées et le lien vers la fiche officielle sont collectés.
"""
import logging

from common.ungm_base import UNGM_COUNTRY_IDS, UngmScraper

logger = logging.getLogger("scrapers.benin.private")


class BeninPrivateScraper(UngmScraper):
    country = "BJ"
    source_name = "UNGM — Nations Unies & organismes internationaux (Bénin)"
    tender_type = "prive"
    ungm_country_id = UNGM_COUNTRY_IDS["BJ"]


def build() -> BeninPrivateScraper:
    return BeninPrivateScraper()
