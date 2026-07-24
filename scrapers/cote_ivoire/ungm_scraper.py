"""Robot de collecte — Côte d'Ivoire 🇨🇮 · Appels d'offres PRIVÉS (Nations Unies).

Source : UNGM (United Nations Global Marketplace), portail officiel des marchés
du système des Nations Unies. On y trouve les avis d'appel d'offres des agences
et organismes internationaux opérant en Côte d'Ivoire (PNUD, UNICEF, UNFPA,
PAM, OMS, FAO, HCR…) — c.-à-d. des marchés « privés » au sens de la plateforme.

Seules des métadonnées et le lien vers la fiche officielle sont collectés.
"""
import logging

from common.ungm_base import UNGM_COUNTRY_IDS, UngmScraper

logger = logging.getLogger("scrapers.cote_ivoire.ungm")


class CiPrivateScraper(UngmScraper):
    country = "CI"
    source_name = "UNGM — Nations Unies & organismes internationaux (Côte d'Ivoire)"
    tender_type = "prive"
    ungm_country_id = UNGM_COUNTRY_IDS["CI"]


def build() -> CiPrivateScraper:
    return CiPrivateScraper()
