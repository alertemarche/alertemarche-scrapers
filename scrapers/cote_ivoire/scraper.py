"""Robot de collecte — Côte d'Ivoire 🇨🇮.

Sources : ANRMP (Autorité Nationale de Régulation des Marchés Publics) et
portail des marchés publics (DGMP / marchespublics.ci). Collecte des
métadonnées d'appels d'offres publics uniquement.
"""
from urllib.parse import urljoin

from common.base import BaseScraper


class CoteIvoireScraper(BaseScraper):
    country = "CI"
    source_name = "ANRMP Côte d'Ivoire"
    tender_type = "public"

    def start_urls(self) -> list[str]:
        base = self.base_url or "https://www.anrmp.ci"
        candidates = [
            base,
            urljoin(base + "/", "avis-dappel-doffres"),
            urljoin(base + "/", "appels-offres"),
            urljoin(base + "/", "actualites"),
        ]
        seen, urls = set(), []
        for u in candidates:
            if u not in seen:
                seen.add(u)
                urls.append(u)
        return urls


def build() -> CoteIvoireScraper:
    return CoteIvoireScraper()
