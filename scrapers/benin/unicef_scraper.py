"""Robot de collecte — Bénin 🇧🇯 · UNICEF Bénin (marchés PRIVÉS / Nations Unies).

Source : page « Travailler à l'UNICEF » du bureau Bénin —
https://www.unicef.org/benin/travailler-à-lunicef

Structure HTML : les avis d'appel d'offres sont présentés dans un tableau dont
les colonnes sont « Appel d'offres | Date de fermeture de l'offre | Dossier
d'appels d'offres | Autres documents ». Le tableau peut être vide selon la
période ; le robot retourne alors 0 item sans erreur.

Seules des métadonnées et les liens officiels sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.benin.unicef")

from common.html_base import HtmlScraper  # noqa: E402


class UnicefScraper(HtmlScraper):
    country = "BJ"
    source_name = "UNICEF Bénin — Fonds des Nations Unies pour l'Enfance"
    tender_type = "prive"

    LISTING = "https://www.unicef.org/benin/travailler-%C3%A0-lunicef"

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        soup = self.soup(self.LISTING)
        if not soup:
            logger.warning("[BJ] UNICEF Bénin injoignable — 0 item")
            return items

        # Repérer le tableau des appels d'offres via son en-tête.
        target = None
        for table in soup.find_all("table"):
            head = table.get_text(" ", strip=True).lower()
            if "appel" in head and ("fermeture" in head or "offre" in head):
                target = table
                break
        if target is None:
            logger.info("[BJ] UNICEF — tableau d'appels d'offres introuvable (0 item)")
            return items

        rows = target.find_all("tr")
        for tr in rows:
            cells = tr.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            title = self.clean(cells[0].get_text())
            # Ignorer la ligne d'en-tête et les lignes vides.
            if not title or len(title) < 6 or title.lower().startswith("appel"):
                continue

            deadline = self.parse_fr_date(cells[1].get_text()) if len(cells) > 1 else None

            dao_url = None
            for c in cells[1:]:
                a = c.find("a", href=True)
                if a:
                    dao_url = urljoin(self.LISTING, a["href"])
                    break
            source_url = dao_url or self.LISTING

            external_id = "unicef-" + re.sub(r"[^a-zA-Z0-9]", "", title)[:40]
            if external_id in seen:
                continue
            seen.add(external_id)

            items.append(self.make_item(
                title=title[:255],
                institution=self.source_name,
                deadline=deadline,
                source_url=source_url,
                dao_url=dao_url,
                external_id=external_id,
            ))
        return items


def build() -> UnicefScraper:
    return UnicefScraper()
