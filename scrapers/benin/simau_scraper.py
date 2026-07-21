"""Robot de collecte — Bénin 🇧🇯 · SImAU (marchés PUBLICS).

Source : Société Immobilière et d'Aménagement Urbain —
https://simaubenin.com/annonce_appel_offre

Structure HTML : chaque annonce est un `article.n-container` contenant la date
de dépôt (« Date de dépôt : 30 juin 2026 à 10 h »), un statut (En cours /
Clôturé) et un titre cliquable pointant vers /detail_offre/{id}. La liste est
paginée via `?page=N`.

Seules des métadonnées et le lien vers la fiche officielle sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.benin.simau")

from common.html_base import HtmlScraper  # noqa: E402


class SimauScraper(HtmlScraper):
    country = "BJ"
    source_name = "SImAU — Société Immobilière et d'Aménagement Urbain"
    tender_type = "public"

    BASE = "https://simaubenin.com/annonce_appel_offre"
    MAX_PAGES = 10

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()

        for page in range(1, self.MAX_PAGES + 1):
            params = {"page": page} if page > 1 else None
            soup = self.soup(self.BASE, params=params)
            if not soup:
                break
            articles = soup.select("article.n-container")
            if not articles:
                break

            new_on_page = 0
            for art in articles:
                link = art.find("a", href=re.compile(r"detail_offre/\d+"))
                if not link:
                    continue
                source_url = urljoin(self.BASE, link["href"])
                mid = re.search(r"detail_offre/(\d+)", source_url)
                external_id = f"simau-{mid.group(1)}" if mid else None
                if external_id and external_id in seen:
                    continue
                if external_id:
                    seen.add(external_id)
                new_on_page += 1

                title = self.clean(link.get_text())
                if not title or len(title) < 6:
                    continue

                text = art.get_text(" ", strip=True)
                deadline = None
                md = re.search(r"Date de dépôt\s*:?\s*(.+?)(?:Clôturé|En cours|Historiques|$)",
                               text, re.IGNORECASE)
                if md:
                    deadline = self.parse_fr_date(md.group(1))

                items.append(self.make_item(
                    title=title,
                    institution=self.source_name,
                    deadline=deadline,
                    source_url=source_url,
                    external_id=external_id,
                ))

            if new_on_page == 0:
                break
        return items


def build() -> SimauScraper:
    return SimauScraper()
