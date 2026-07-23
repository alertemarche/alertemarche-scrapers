"""Robot de collecte — Togo 🇹🇬 · Port Autonome de Lomé (marchés PUBLICS).

Source : Port Autonome de Lomé (Togo Port) — page « Marchés Publics »
https://www.togo-port.net/les-informations-du-port/marches-publics-togo-port/

Structure HTML : le contenu des avis peut être présenté sous forme de tableau,
d'articles ou de liens vers des documents (PDF). Le robot tente plusieurs
sélecteurs et reste robuste : s'il ne trouve rien, il retourne une liste vide.

Seules des métadonnées et les liens officiels sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.togo.port")

from common.html_base import HtmlScraper  # noqa: E402


class TogoPortScraper(HtmlScraper):
    country = "TG"
    source_name = "Port Autonome de Lomé (Togo Port)"
    tender_type = "public"

    BASE = "https://www.togo-port.net"
    LISTING_URLS = [
        "https://www.togo-port.net/les-informations-du-port/marches-publics-togo-port/",
        "https://www.togo-port.net/marches-publics/marches-publics-togo-port/",
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
            logger.warning("[TG] Togo Port injoignable — 0 item")
            return items

        content = soup.select_one("div.entry-content, article, main, #content") or soup
        # Liens vers des avis / documents (PDF ou pages dédiées).
        for link in content.find_all("a", href=True):
            href = link["href"]
            text = self.clean(link.get_text())
            if not text or len(text) < 12:
                continue
            if not re.search(r"appel|offre|avis|marché|marche|consultation|manifestation|\.pdf",
                             (href + " " + text), re.IGNORECASE):
                continue
            # Exclusion de la navigation générique.
            if re.search(r"marches-publics-togo-port/?$", href):
                continue
            source_url = urljoin(self.BASE, href)
            parent = link.find_parent(["td", "tr", "li", "article", "div"]) or link
            pub = self.parse_fr_date(parent.get_text(" ", strip=True))

            external_id = None
            slug = re.search(r"/([a-z0-9\-]+?)(?:\.pdf)?/?$", href, re.IGNORECASE)
            if slug:
                external_id = f"togoport-{slug.group(1)[:60]}"
            if external_id and external_id in seen:
                continue
            if external_id:
                seen.add(external_id)

            dao_url = source_url if href.lower().endswith(".pdf") else None
            items.append(self.make_item(
                title=text,
                institution=self.source_name,
                publication_date=pub,
                source_url=source_url,
                dao_url=dao_url,
                external_id=external_id,
            ))
        if not items:
            logger.info("[TG] Togo Port — aucun avis détecté (contenu dynamique ?)")
        return items


def build() -> TogoPortScraper:
    return TogoPortScraper()
