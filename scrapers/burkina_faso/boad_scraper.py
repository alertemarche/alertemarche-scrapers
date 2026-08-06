"""Robot de collecte — Burkina Faso 🇧🇫 · BOAD (Banque Ouest-Africaine de Développement).

Source : portail des appels d'offres de la BOAD (www.boad.org), institution
financière de l'UEMOA qui finance des projets dans les 8 pays membres dont le
Burkina Faso. Les avis sont collectés puis filtrés pour ne garder que ceux
concernant le Burkina Faso.

Ces marchés (financés par la BOAD mais passés par des maîtres d'ouvrage) relèvent
des appels d'offres « privés » au sens de la plateforme (bailleur international).
Seuls les avis ACTIFS (échéance future ou absente) sont conservés.
"""
import logging
import re
from urllib.parse import urljoin

from common.html_base import HtmlScraper

logger = logging.getLogger("scrapers.burkina_faso.boad")

BASE = "https://www.boad.org"
LISTING_URL = "https://www.boad.org/appels-doffres/"
BF_TOKENS = ("burkina", "burkinabe", "burkinabè", "burkinabé", "ouagadougou")


class BoadBfScraper(HtmlScraper):
    country = "BF"
    source_name = "BOAD (Banque Ouest-Africaine de Développement)"
    tender_type = "prive"
    method = "html"

    def _is_bf(self, text: str) -> bool:
        low = text.lower()
        return any(tok in low for tok in BF_TOKENS)

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        soup = self.soup(LISTING_URL)
        if not soup:
            logger.warning("[BF] BOAD injoignable — 0 item")
            return items

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        for item in soup.select("article, div.item, div.post, div.entry, tr"):
            text = self.clean(item.get_text(" ", strip=True))
            if len(text) < 20 or not self._is_bf(text):
                continue

            link = item.find("a", href=True)
            if not link:
                continue

            href = urljoin(BASE, link["href"])
            if href in seen or href == LISTING_URL:
                continue
            seen.add(href)

            title = self.clean(link.get_text(" ", strip=True))
            if not title or len(title) < 10:
                heading = item.find(["h1", "h2", "h3", "h4", "h5"])
                if heading:
                    title = self.clean(heading.get_text(" ", strip=True))
            if not title or len(title) < 10:
                title = text[:255]

            reference = None
            ref_match = re.search(r"([A-Z]{2,}\s*[N°n]\s*[\d/-]+)", text)
            if ref_match:
                reference = self.clean(ref_match.group(1))

            deadline = self.parse_fr_date(text)

            # On ne garde que les avis actifs (échéance future ou absente).
            if not self.is_active(deadline):
                continue

            pub_date = None
            pub_match = re.search(r"(?:publié|posted|date)\s*:?\s*(\d{1,2}\s+\w+\s+\d{4})", text, re.I)
            if pub_match:
                pub_date = self.parse_fr_date(pub_match.group(1))

            items.append(self.make_item(
                title=title[:255],
                institution=self.source_name,
                reference=reference,
                deadline=deadline,
                publication_date=pub_date,
                source_url=href,
                dao_url=href,
                external_id=f"boad-bf-{abs(hash(href)) % (10**10)}",
                tender_type="prive",
            ))

        logger.info("[BF] BOAD : %d avis collectés", len(items))
        return items


def build() -> BoadBfScraper:
    return BoadBfScraper()
