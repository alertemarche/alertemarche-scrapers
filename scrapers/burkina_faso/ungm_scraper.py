"""Robot de collecte — Burkina Faso 🇧🇫 · Appels d'offres PRIVÉS (Nations Unies).

Source : UNGM (United Nations Global Marketplace), portail officiel des marchés
du système des Nations Unies. On y trouve les avis d'appel d'offres des agences
et organismes internationaux opérant au Burkina Faso (PNUD, UNICEF, UNFPA, PAM,
OMS, FAO, HCR…) — c.-à-d. des marchés « privés » au sens de la plateforme.

Le portail ne renvoie que les avis ACTIFS (payload `IsActive: True`). Seules des
métadonnées et le lien vers la fiche officielle sont collectés.
"""
import logging

from common.ungm_base import UNGM_COUNTRY_IDS, UngmScraper

logger = logging.getLogger("scrapers.burkina_faso.ungm")


class BfPrivateScraper(UngmScraper):
    country = "BF"
    source_name = "UNGM — Nations Unies & organismes internationaux (Burkina Faso)"
    tender_type = "prive"
    ungm_country_id = UNGM_COUNTRY_IDS["BF"]


def build() -> BfPrivateScraper:
    return BfPrivateScraper()
