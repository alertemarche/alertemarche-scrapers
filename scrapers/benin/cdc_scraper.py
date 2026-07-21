"""Robot de collecte — Bénin 🇧🇯 · CDC Bénin (marchés PRIVÉS).

Source : Caisse des Dépôts et Consignations du Bénin —
https://www.cdcb.bj/Appels-d-offre

Structure HTML : chaque avis est un bloc `div.client-information` présentant
« Publié le », « Objet », « Référence », « Date de clôture » et un lien
« En savoir plus » pointant vers le PDF de l'avis.

Seules des métadonnées et le lien vers l'avis officiel sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.benin.cdc")

from common.html_base import HtmlScraper  # noqa: E402


class CdcScraper(HtmlScraper):
    country = "BJ"
    source_name = "CDC Bénin — Caisse des Dépôts et Consignations"
    tender_type = "prive"

    LISTING = "https://www.cdcb.bj/Appels-d-offre"

    def _field(self, text: str, label: str, stops: str) -> str | None:
        m = re.search(re.escape(label) + r"\s*:?\s*(.+?)(?:" + stops + r"|$)",
                      text, re.IGNORECASE)
        return self.clean(m.group(1)) if m else None

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        soup = self.soup(self.LISTING)
        if not soup:
            logger.warning("[BJ] CDC Bénin injoignable — 0 item")
            return items

        cards = soup.select("div.client-information")
        stops = "Publié le|Objet|Référence|Reference|Date de clôture|En savoir plus"
        for card in cards:
            text = card.get_text(" ", strip=True)
            title = self._field(text, "Objet", stops)
            if not title or len(title) < 6:
                # Repli : premier lien titré.
                a = card.find("a")
                title = self.clean(a.get_text()) if a else None
            if not title or len(title) < 6:
                continue

            reference = self._field(text, "Référence", stops) or self._field(text, "Reference", stops)
            pub = self.parse_fr_date(self._field(text, "Publié le", stops) or "")
            deadline = self.parse_fr_date(self._field(text, "Date de clôture", stops) or "")

            link = card.find("a", href=re.compile(r"\.pdf", re.IGNORECASE)) or card.find("a", href=True)
            dao_url = urljoin(self.LISTING, link["href"]) if link and link.get("href") else None
            source_url = dao_url or self.LISTING

            external_id = None
            if reference:
                external_id = "cdc-" + re.sub(r"[^a-zA-Z0-9]", "", reference)[:40]
            elif dao_url:
                external_id = "cdc-" + re.sub(r"[^a-zA-Z0-9]", "", dao_url.rsplit("/", 1)[-1])[:40]
            if external_id and external_id in seen:
                continue
            if external_id:
                seen.add(external_id)

            items.append(self.make_item(
                title=title[:255],
                institution=self.source_name,
                reference=reference,
                deadline=deadline,
                publication_date=pub,
                source_url=source_url,
                dao_url=dao_url,
                external_id=external_id,
            ))
        return items


def build() -> CdcScraper:
    return CdcScraper()
