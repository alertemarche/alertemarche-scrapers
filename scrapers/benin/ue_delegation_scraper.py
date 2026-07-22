"""Robot de collecte — Bénin 🇧🇯 · Délégation de l'Union Européenne au Bénin.

Source : Portail officiel du Service européen pour l'action extérieure (EEAS),
section « Appels d'offres » filtrée pour le Bénin :

    https://www.eeas.europa.eu/eeas/appel-d%E2%80%99offres_fr?f[0]=tender_site:Benin

La Délégation de l'UE au Bénin publie occasionnellement des appels d'offres
(services, travaux, fournitures) et des appels à manifestation d'intérêt pour
ses opérations locales. Ces marchés (émis par une institution internationale)
relèvent des appels d'offres « privés » au sens de la plateforme (acheteur non
étatique). Seules des métadonnées et le lien vers l'avis officiel sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

from common.html_base import HtmlScraper

logger = logging.getLogger("scrapers.benin.ue_delegation")

LISTING_URL = "https://www.eeas.europa.eu/eeas/appel-d%E2%80%99offres_fr?f[0]=tender_site:Benin"
BASE_URL = "https://www.eeas.europa.eu"


class UeDelegationScraper(HtmlScraper):
    country = "BJ"
    source_name = "Délégation UE Bénin"
    tender_type = "prive"
    method = "html"

    def collect(self) -> list[dict]:
        items: list[dict] = []
        soup = self.soup(LISTING_URL)
        if not soup:
            return items

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # La page EEAS liste les appels d'offres sous forme de liens vers des
        # pages de détail. On identifie les liens spécifiques au Bénin via le
        # pattern d'URL `/delegations/benin/...`.
        seen: set[str] = set()
        for link in soup.find_all("a", href=re.compile(r"/delegations/benin/")):
            href = link.get("href", "")
            if not href:
                continue
            full_url = urljoin(BASE_URL, href)
            if full_url in seen:
                continue
            seen.add(full_url)

            # Le titre est généralement le texte du lien ou d'un parent proche
            title = " ".join(link.get_text(" ", strip=True).split())
            # Si le lien ne contient que "En savoir plus" ou équivalent, chercher
            # dans le parent (article/div) un titre plus descriptif
            if not title or len(title) < 15 or re.search(r"^(en savoir plus|lire|read more)$", title, re.I):
                parent = link.find_parent(["article", "div", "section"])
                if parent:
                    heading = parent.find(["h1", "h2", "h3", "h4"])
                    if heading:
                        title = " ".join(heading.get_text(" ", strip=True).split())

            if not title or len(title) < 10:
                title = "Appel d'offres Délégation UE Bénin"

            items.append(self.make_item(
                title=title[:255],
                institution=self.source_name,
                source_url=full_url,
                dao_url=full_url,
                external_id=f"ue-{abs(hash(full_url)) % (10 ** 10)}",
                tender_type="prive",
            ))

        logger.info("[BJ] Délégation UE : %d avis collectés", len(items))
        return items


def build() -> UeDelegationScraper:
    return UeDelegationScraper()
