"""Robot de collecte — Togo 🇹🇬.

Sources : ARMP Togo (Autorité de Régulation de la Commande Publique) et
DNCMP. Collecte des métadonnées d'appels d'offres publics uniquement.
"""
from urllib.parse import urljoin

from common.base import BaseScraper


class TogoScraper(BaseScraper):
    country = "TG"
    source_name = "ARMP Togo"
    tender_type = "public"

    def start_urls(self) -> list[str]:
        base = self.base_url or "https://armp.tg"
        candidates = [
            base,
            urljoin(base + "/", "appels-doffres"),
            urljoin(base + "/", "avis"),
            urljoin(base + "/", "actualites"),
        ]
        seen, urls = set(), []
        for u in candidates:
            if u not in seen:
                seen.add(u)
                urls.append(u)
        return urls


def build() -> TogoScraper:
    return TogoScraper()
