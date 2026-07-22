"""Robot de collecte — Bénin 🇧🇯 · AFD (Agence Française de Développement).

Source : portail dgMarket de l'AFD (https://afd.dgmarket.com), où les maîtres
d'ouvrage publient les avis des marchés financés par l'AFD. La liste est
filtrable par pays via le paramètre `locationISO` (bj = Bénin) :

    https://afd.dgmarket.com/tenders/brandedNoticeList.do?locationISO=bj

Chaque avis pointe vers une fiche `/tender/{id}`. Ces marchés (bailleur
international) relèvent des appels d'offres « privés » au sens de la plateforme.
Seules des métadonnées et le lien vers la fiche officielle sont collectés.
"""
import logging
import re
from datetime import date, datetime
from urllib.parse import urljoin

from common.html_base import HtmlScraper

logger = logging.getLogger("scrapers.benin.afd")

BASE = "https://afd.dgmarket.com"
LISTING = "https://afd.dgmarket.com/tenders/brandedNoticeList.do"
MAX_PAGES = 10

# Abréviations de mois dgMarket (mélange FR/EN) -> numéro.
_MONTHS = {
    "jan": 1, "fev": 2, "feb": 2, "fév": 2, "mar": 3, "avr": 4, "apr": 4,
    "mai": 5, "may": 5, "jun": 6, "juin": 6, "jul": 7, "juil": 7,
    "aou": 8, "aug": 8, "aoû": 8, "sep": 9, "sept": 9, "oct": 10,
    "nov": 11, "dec": 12, "déc": 12,
}


class AfdScraper(HtmlScraper):
    country = "BJ"
    source_name = "AFD (Agence Française de Développement)"
    tender_type = "prive"
    method = "html"

    @staticmethod
    def _parse_date(raw: str | None) -> str | None:
        """« Jul 13, 2026 » / « Sept 10, 2026 » / « Aou 17, 2026 » -> ISO."""
        if not raw:
            return None
        m = re.search(r"([A-Za-zéûôà]{3,4})\.?\s+(\d{1,2}),?\s+(20\d{2})", raw.strip())
        if not m:
            return None
        mo = _MONTHS.get(m.group(1).lower().rstrip("."))
        if not mo:
            return None
        try:
            return date(int(m.group(3)), mo, int(m.group(2))).strftime("%Y-%m-%d")
        except ValueError:
            return None

    def _map_row(self, link) -> dict | None:
        href = link.get("href", "")
        m = re.search(r"/tender/(\d+)", href)
        if not m:
            return None
        tender_id = m.group(1)

        title = self.clean(link.get_text(" ", strip=True))
        if not title or len(title) < 6:
            return None

        # La ligne <tr> porte : Pays | Titre(lien) | Publié | Date limite.
        row = link.find_parent("tr")
        published = deadline = None
        if row:
            cells = [self.clean(c.get_text(" ", strip=True)) for c in row.find_all("td")]
            dates = [d for d in (self._parse_date(c) for c in cells) if d]
            if len(dates) >= 2:
                published, deadline = dates[0], dates[1]
            elif len(dates) == 1:
                # Une seule date : c'est la publication (avis sans date limite).
                published = dates[0]

        source_url = urljoin(BASE, href)
        return self.make_item(
            title=title[:255],
            institution=self.source_name,
            deadline=deadline,
            publication_date=published,
            source_url=source_url,
            dao_url=source_url,
            external_id=f"afd-{tender_id}",
            tender_type="prive",
        )

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        for page in range(1, MAX_PAGES + 1):
            params = {"locationISO": "bj"}
            if page > 1:
                params["pageNo"] = page
            soup = self.soup(LISTING, params=params)
            if not soup:
                break
            links = soup.select('a[href*="/tender/"]')
            new_on_page = 0
            for link in links:
                m = re.search(r"/tender/(\d+)", link.get("href", ""))
                if not m:
                    continue
                tid = m.group(1)
                if tid in seen:
                    continue
                seen.add(tid)
                mapped = self._map_row(link)
                if mapped:
                    items.append(mapped)
                    new_on_page += 1
            if new_on_page == 0:
                break
        return items


def build() -> AfdScraper:
    return AfdScraper()
