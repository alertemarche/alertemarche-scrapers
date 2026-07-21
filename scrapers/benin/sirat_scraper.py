"""Robot de collecte — Bénin 🇧🇯 · SIRAT SA (marchés PUBLICS).

Source : Société Immobilière et de Réaménagement des Terres —
https://www.sirat.bj/avis-dappels-doffres/

Structure HTML : les avis sont présentés dans un carrousel Divi. Chaque item
(`div.dipi_carousel_child`) porte un titre du type « DATE LIMITE : 27 juillet
2026 », un statut (🟢 En cours / 🔴 Expiré) et un bouton « Afficher » pointant
vers le PDF de l'avis. Le libellé métier est dérivé du nom de fichier PDF.

Seules des métadonnées et le lien vers l'avis officiel sont collectés.
"""
import logging
import re
from urllib.parse import unquote, urljoin

logger = logging.getLogger("scrapers.benin.sirat")

from common.html_base import HtmlScraper  # noqa: E402


class SiratScraper(HtmlScraper):
    country = "BJ"
    source_name = "SIRAT — Société Immobilière et de Réaménagement des Terres"
    tender_type = "public"

    LISTING = "https://www.sirat.bj/avis-dappels-doffres/"

    def _title_from_pdf(self, url: str) -> str:
        """Construit un libellé lisible à partir du nom de fichier PDF."""
        name = unquote(url.rsplit("/", 1)[-1])
        name = re.sub(r"\.pdf$", "", name, flags=re.IGNORECASE)
        name = re.sub(r"[_\-]+", " ", name)
        name = re.sub(r"\d{6,}", "", name)  # timbres date/heure
        name = self.clean(name)
        return name

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        soup = self.soup(self.LISTING)
        if not soup:
            logger.warning("[BJ] SIRAT injoignable — 0 item")
            return items

        cards = soup.select("div.dipi_carousel_child")
        for card in cards:
            text = card.get_text(" ", strip=True)
            link = card.find("a", href=re.compile(r"\.pdf", re.IGNORECASE))
            source_url = self.LISTING
            dao_url = None
            if link and link.get("href"):
                dao_url = urljoin(self.LISTING, link["href"])
                source_url = dao_url

            deadline = None
            md = re.search(r"DATE\s+LIMITE\s*:?\s*(.+?)(?:🟢|🔴|En cours|Expiré|Afficher|$)",
                           text, re.IGNORECASE)
            if md:
                deadline = self.parse_fr_date(md.group(1))

            title_el = card.find(["h2", "h3", "h4"])
            base_title = self.clean(title_el.get_text()) if title_el else ""
            derived = self._title_from_pdf(dao_url) if dao_url else ""
            if derived and len(derived) > 6:
                title = f"Avis d'appel d'offres SIRAT — {derived}"
            elif base_title:
                title = f"Avis d'appel d'offres SIRAT ({base_title})"
            else:
                title = "Avis d'appel d'offres — SIRAT SA"
            title = title[:255]

            external_id = None
            if dao_url:
                external_id = "sirat-" + re.sub(r"[^a-zA-Z0-9]", "",
                                                dao_url.rsplit("/", 1)[-1])[:40]
                if external_id in seen:
                    continue
                seen.add(external_id)

            items.append(self.make_item(
                title=title,
                institution=self.source_name,
                deadline=deadline,
                source_url=source_url,
                dao_url=dao_url,
                external_id=external_id,
            ))
        return items


def build() -> SiratScraper:
    return SiratScraper()
