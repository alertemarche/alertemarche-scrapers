"""Robot de collecte — Bénin 🇧🇯.

Sources : ARMP Bénin (Autorité de Régulation des Marchés Publics) et
portail national des marchés publics (DNCMP/SIGMAP). Collecte des métadonnées
d'appels d'offres publics ; les documents (DAO) ne sont jamais stockés.
"""
from urllib.parse import urljoin

from common.base import BaseScraper


class BeninScraper(BaseScraper):
    country = "BJ"
    source_name = "ARMP Bénin"
    tender_type = "public"

    def start_urls(self) -> list[str]:
        base = self.base_url or "https://armp.bj"
        # Pages de listing probables ; l'heuristique s'adapte si la structure change.
        candidates = [
            base,
            urljoin(base + "/", "avis-dappel-doffres"),
            urljoin(base + "/", "appels-doffres"),
            urljoin(base + "/", "actualites"),
        ]
        # Déduplication de la liste d'URLs.
        seen, urls = set(), []
        for u in candidates:
            if u not in seen:
                seen.add(u)
                urls.append(u)
        return urls


def build() -> BeninScraper:
    return BeninScraper()
