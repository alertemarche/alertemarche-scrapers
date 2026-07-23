"""Robot de collecte — Côte d'Ivoire 🇨🇮 · ARCOP-CI (marchés PUBLICS).

Source : Autorité de Régulation de la Commande Publique de Côte d'Ivoire —
https://arcop.ci/documentation/avis/avis-dappel-doffres/

Structure HTML : la « Docuthèque » présente les avis d'appel d'offres dans un
tableau. Chaque ligne comporte le titre de l'avis (lien de téléchargement),
le nombre de vues et la date de publication.

Seules des métadonnées et le lien de téléchargement officiel (`dao_url`) sont
collectés.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.cote_ivoire.arcop")

from common.html_base import HtmlScraper  # noqa: E402


class ArcopCiScraper(HtmlScraper):
    country = "CI"
    source_name = "ARCOP Côte d'Ivoire — Autorité de Régulation de la Commande Publique"
    tender_type = "public"

    BASE = "https://arcop.ci"
    LISTING_URLS = [
        "https://arcop.ci/documentation/avis/avis-dappel-doffres/",
        "https://www.arcop.ci/documentation/avis/avis-dappel-doffres/",
    ]

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        soup = None
        base = self.LISTING_URLS[0]
        for url in self.LISTING_URLS:
            soup = self.soup(url)
            if soup:
                base = url
                break
        if not soup:
            logger.warning("[CI] ARCOP-CI injoignable — 0 item")
            return items

        # Liens de téléchargement des avis d'appel d'offres.
        links = soup.select("a[href*='/download/']")
        for link in links:
            href = link.get("href", "")
            if "avis-dappel-doffres" not in href:
                continue
            title = self.clean(link.get_text())
            if not title or len(title) < 10 or title.lower() == "télécharger":
                # Le libellé peut être « Télécharger » : on récupère le titre
                # depuis la ligne du tableau.
                row = link.find_parent("tr")
                if row:
                    cand = self.clean(row.find(["td", "th"]).get_text(" ", strip=True))
                    if cand and len(cand) >= 10:
                        title = cand
            if not title or len(title) < 10 or title.lower() == "télécharger":
                continue

            dao_url = urljoin(self.BASE, href)
            row = link.find_parent("tr")
            pub = self.parse_fr_date(row.get_text(" ", strip=True)) if row else None

            reference = None
            m = re.search(r"N[°ºo]\s*[\w/\-.]+", title)
            if m:
                reference = self.clean(m.group(0))[:120]

            external_id = None
            mid = re.search(r"/download/\d+/[^/]+/(\d+)/", href)
            if mid:
                external_id = f"arcop-ci-{mid.group(1)}"
            if external_id and external_id in seen:
                continue
            if external_id:
                seen.add(external_id)

            items.append(self.make_item(
                title=title,
                institution=self.source_name,
                reference=reference,
                publication_date=pub,
                source_url=base,
                dao_url=dao_url,
                external_id=external_id,
            ))
        return items


def build() -> ArcopCiScraper:
    return ArcopCiScraper()
