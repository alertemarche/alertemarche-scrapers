"""Robot de collecte — Togo 🇹🇬 · Appels d'offres PRIVÉS (Nations Unies).

Source : UNGM (United Nations Global Marketplace), portail officiel des marchés
du système des Nations Unies. On y trouve les avis d'appel d'offres des agences
et organismes internationaux opérant au Togo (PNUD, UNICEF, UNFPA, PAM, OMS,
FAO, HCR…) — c.-à-d. des marchés « privés » au sens de la plateforme.

Seules des métadonnées et le lien vers la fiche officielle sont collectés.
"""
import logging

from common.ungm_base import UNGM_COUNTRY_IDS, UngmScraper

logger = logging.getLogger("scrapers.togo.ungm")


class TgPrivateScraper(UngmScraper):
    country = "TG"
    source_name = "UNGM — Nations Unies & organismes internationaux (Togo)"
    tender_type = "prive"
    ungm_country_id = UNGM_COUNTRY_IDS["TG"]


def build() -> TgPrivateScraper:
    return TgPrivateScraper()
