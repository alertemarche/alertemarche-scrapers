"""Robot de collecte — Sénégal 🇸🇳 · SENELEC (marchés PUBLICS · électricité).

Source : Société Nationale d'Électricité du Sénégal — https://www.senelec.sn/
Section « Marchés / Passation » (onglet « Appels d'offres »).

La page expose UNE table HTML propre : chaque ligne (`<tr>`) présente
la référence, l'objet, le type d'avis, la date limite (JJ/MM/AAAA) et un lien
vers l'avis officiel (PDF « Voir avis »).

Seules des métadonnées et le lien vers l'avis officiel sont collectés.
Principe de robustesse : en cas d'indisponibilité, on journalise un
avertissement et on retourne une liste vide — jamais de crash.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.senegal.senelec")

from common.html_base import HtmlScraper  # noqa: E402


class SenelecScraper(HtmlScraper):
    country = "SN"
    source_name = "SENELEC — Société Nationale d'Électricité du Sénégal"
    tender_type = "public"

    BASE = "https://www.senelec.sn"
    LISTING_URL = "https://www.senelec.sn/marches/passation/?tab=appels"

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()

        soup = self.soup(self.LISTING_URL)
        if not soup:
            logger.warning("[SN] SENELEC injoignable — 0 item")
            return items

        rows = soup.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 4:
                continue

            reference = self.clean(cells[0].get_text(" ", strip=True))
            title = self.clean(cells[1].get_text(" ", strip=True))
            market_type = self.clean(cells[2].get_text(" ", strip=True))
            deadline_raw = self.clean(cells[3].get_text(" ", strip=True))

            # Ligne d'en-tête : « Référence Objet Type Date limite ».
            if not title or "objet" in title.lower() or "référence" in reference.lower():
                continue
            if len(title) < 6:
                continue

            deadline = self.parse_fr_date(deadline_raw)

            # Lien PDF « Voir avis » (dernière cellule le cas échéant).
            dao_url = None
            link = row.find("a", href=True)
            if link:
                dao_url = urljoin(self.BASE, link.get("href", ""))

            # Identifiant stable basé sur la référence (ou le titre à défaut).
            key = reference or title[:40]
            ext = "senelec-" + re.sub(r"[^a-zA-Z0-9]", "", key)[:50]
            if ext in seen:
                continue
            seen.add(ext)

            items.append(self.make_item(
                title=title[:255],
                institution=self.source_name,
                reference=reference or None,
                deadline=deadline,
                market_type=market_type or None,
                source_url=dao_url or self.LISTING_URL,
                dao_url=dao_url,
                external_id=ext,
            ))

        logger.info("[SN] SENELEC : %d avis collectés", len(items))
        return items


def build() -> SenelecScraper:
    return SenelecScraper()
