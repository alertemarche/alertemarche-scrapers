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

    def parse(self, html: str, page_url: str) -> list[dict]:
        """Filtre les faux-actifs de l'accueil ANRMP.

        La page d'accueil de l'ANRMP mélange actualités, archives et liens de
        navigation captés par l'heuristique générique — presque toujours sans
        échéance. Ces avis non datés étaient affichés comme « actifs » pendant
        90 jours (faux-actifs). On ne conserve donc que les avis réellement
        datés (échéance détectée), qui sont les seuls fiables pour cette source.
        """
        items = super().parse(html, page_url)
        return [it for it in items if it.get("deadline")]


def build() -> CoteIvoireScraper:
    return CoteIvoireScraper()
