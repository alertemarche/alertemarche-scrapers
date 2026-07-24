"""Robot de collecte — Togo 🇹🇬 · Portail des Marchés Publics (PUBLICS).

Source : portail national des marchés publics du Togo —
https://marchespublics.tg/ (et variantes de domaine).

Remarque : ce domaine peut ne pas être résolvable depuis certains réseaux ;
le robot tente plusieurs URL candidates et reste robuste — s'il ne trouve rien
(site injoignable ou structure inconnue), il retourne une liste vide sans
jamais lever d'exception.

Le robot tente d'abord un tableau d'avis, puis des cartes/articles.
Seules des métadonnées et les liens officiels sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.togo.marchespublics")

from common.html_base import HtmlScraper  # noqa: E402


class MarchesPublicsTgScraper(HtmlScraper):
    country = "TG"
    source_name = "Marchés Publics Togo — Portail national"
    tender_type = "public"

    LISTING_URLS = [
        "https://marchespublics.tg/appels-offres",
        "https://marchespublics.tg/appels-doffres",
        "https://www.marchespublics.tg/appels-offres",
        "https://marchespublics.tg/",
        "https://www.marchespublics.tg/",
    ]

    def _base_of(self, url: str) -> str:
        m = re.match(r"(https?://[^/]+)", url)
        return m.group(1) if m else url

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
            logger.warning("[TG] Marchés Publics TG injoignable — 0 item")
            return items

        base_url = self._base_of(base)

        # --- 1) Tableau d'avis --------------------------------------------
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                texts = [self.clean(c.get_text(" ", strip=True)) for c in cells]
                title = max(texts, key=len)
                if not title or len(title) < 10:
                    continue
                joined = " ".join(texts)
                # Priorité à l'échéance explicite (« au plus tard le … ») ;
                # sinon, dernière date rencontrée dans la ligne.
                deadline = self.deadline_from_text(joined) or self.parse_fr_date(joined)
                amount = self.amount_from_text(joined)
                link = row.find("a", href=True)
                source_url = urljoin(base_url, link["href"]) if link else base
                reference = None
                m = re.search(r"(?:AOO|AON|AAO|AMI|DRP|DP|N°)\s*[\w/\-.]+", joined, re.IGNORECASE)
                if m:
                    reference = self.clean(m.group(0))[:120]
                key = source_url + "|" + title[:40]
                if key in seen:
                    continue
                seen.add(key)
                items.append(self.make_item(
                    title=title, institution=self.source_name,
                    reference=reference, deadline=deadline,
                    estimated_amount=amount,
                    source_url=source_url,
                ))
        if items:
            return items

        # --- 2) Cartes / articles -----------------------------------------
        for card in soup.select("article, div.card, div.avis, li.avis, div.post"):
            title_el = card.find(["h1", "h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = self.clean(title_el.get_text())
            if not title or len(title) < 10:
                continue
            text = card.get_text(" ", strip=True)
            deadline = self.deadline_from_text(text) or self.parse_fr_date(text)
            amount = self.amount_from_text(text)
            link = card.find("a", href=True)
            source_url = urljoin(base_url, link["href"]) if link else base
            key = source_url + "|" + title[:40]
            if key in seen:
                continue
            seen.add(key)
            items.append(self.make_item(
                title=title, institution=self.source_name,
                deadline=deadline, estimated_amount=amount,
                source_url=source_url,
            ))
        return items


def build() -> MarchesPublicsTgScraper:
    return MarchesPublicsTgScraper()
