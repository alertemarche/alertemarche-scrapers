"""Robot de collecte — Togo 🇹🇬 · CNCT (marchés PUBLICS / privés).

Source : Conseil National des Chargeurs du Togo — page « Marchés Publics »
https://cnct-togo.com/marches-publics/

Structure HTML : chaque avis est présenté par un titre `h3` cliquable pointant
vers la fiche de l'avis (« /marches-publics/... ») avec une date au format
« 15/06/2026 ».

Seules des métadonnées et le lien officiel sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.togo.cnct")

from common.html_base import HtmlScraper  # noqa: E402


class CnctScraper(HtmlScraper):
    country = "TG"
    source_name = "CNCT — Conseil National des Chargeurs du Togo"
    tender_type = "public"

    BASE = "https://cnct-togo.com"
    LISTING_URLS = [
        "https://cnct-togo.com/marches-publics/",
    ]

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        soup = None
        for url in self.LISTING_URLS:
            soup = self.soup(url)
            if soup:
                break
        if not soup:
            logger.warning("[TG] CNCT injoignable — 0 item")
            return items

        # Titres cliquables pointant vers une fiche d'avis.
        for link in soup.select("h3 a[href], article a[href], h2 a[href]"):
            href = link.get("href", "")
            if "/marches-publics/" not in href:
                continue
            # On exclut le lien vers la page de listing elle-même.
            if href.rstrip("/").endswith("/marches-publics"):
                continue
            title = self.clean(link.get_text())
            if not title or len(title) < 8:
                continue
            source_url = urljoin(self.BASE, href)

            # Date à proximité du titre (dans le conteneur parent).
            container = link.find_parent(["article", "div", "li"]) or link
            ctext = container.get_text(" ", strip=True)
            pub = self.parse_fr_date(ctext)
            reference = None
            m = re.search(r"(?:AOI|AAOI|AON|AOO|AMI|N°)\s*[\w/\-.]+", ctext, re.IGNORECASE)
            if m:
                reference = self.clean(m.group(0))[:120]

            external_id = None
            slug = re.search(r"/marches-publics/([a-z0-9\-]+)", href)
            if slug:
                external_id = f"cnct-{slug.group(1)[:60]}"
            if external_id and external_id in seen:
                continue
            if external_id:
                seen.add(external_id)

            items.append(self.make_item(
                title=title,
                institution=self.source_name,
                reference=reference,
                publication_date=pub,
                source_url=source_url,
                external_id=external_id,
            ))
        return items


def build() -> CnctScraper:
    return CnctScraper()
