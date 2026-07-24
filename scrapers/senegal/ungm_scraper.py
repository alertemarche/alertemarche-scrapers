"""Robot de collecte — Sénégal 🇸🇳 · Appels d'offres PRIVÉS (Nations Unies).

Source : UNGM (United Nations Global Marketplace), portail officiel des marchés
du système des Nations Unies. On y trouve les avis d'appel d'offres des agences
et organismes internationaux opérant au Sénégal (PNUD, UNICEF, UNFPA, PAM, OMS,
FAO, HCR…) — c.-à-d. des marchés « privés » au sens de la plateforme.

Seules des métadonnées et le lien vers la fiche officielle sont collectés.
"""
import logging

from common.ungm_base import UNGM_COUNTRY_IDS, UngmScraper

logger = logging.getLogger("scrapers.senegal.ungm")


class SnPrivateScraper(UngmScraper):
    country = "SN"
    source_name = "UNGM — Nations Unies & organismes internationaux (Sénégal)"
    tender_type = "prive"
    ungm_country_id = UNGM_COUNTRY_IDS["SN"]


def build() -> SnPrivateScraper:
    return SnPrivateScraper()
