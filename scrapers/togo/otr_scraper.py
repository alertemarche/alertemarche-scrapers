"""Robot de collecte — Togo 🇹🇬 · OTR (marchés PUBLICS).

Source : Office Togolais des Recettes — blog des appels d'offres
https://www.otr.tg/index.php/fr/blog/appels-d-offres.html

Structure HTML : site Joomla. Chaque avis est un `article` dont le texte
commence par une date française (« 14 juillet 2026 ») suivie du titre, avec
un lien vers la fiche de l'avis (chemin « /blog/appels-d-offres/NNNN-... »).

Seules des métadonnées et le lien officiel sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.togo.otr")

from common.html_base import HtmlScraper  # noqa: E402


class OtrScraper(HtmlScraper):
    country = "TG"
    source_name = "OTR — Office Togolais des Recettes"
    tender_type = "public"

    BASE = "https://www.otr.tg"
    LISTING_URLS = [
        "https://www.otr.tg/index.php/fr/blog/appels-d-offres.html",
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
            logger.warning("[TG] OTR injoignable — 0 item")
            return items

        for art in soup.select("article"):
            link = art.find("a", href=re.compile(r"appels-d-offres/\d+", re.IGNORECASE))
            if not link:
                continue
            href = link.get("href")
            source_url = urljoin(self.BASE, href)
            title = self.clean(link.get_text())
            text = art.get_text(" ", strip=True)
            if not title or len(title) < 8:
                # Titre parfois porté par le texte de l'article (date + titre).
                title = self.clean(re.sub(r"^\d{1,2}\s+\w+\s+20\d{2}", "", text))
            if not title or len(title) < 8:
                continue

            pub = self.parse_fr_date(text)
            # Référence : AMI/AAOO/AAO N° ...
            reference = None
            m = re.search(r"(?:AMI|AAOO|AAO|AON|AOO|DRP|DP)\s*N?[°ºo]\s*[\w/\-.]+",
                          text, re.IGNORECASE)
            if m:
                reference = self.clean(m.group(0))[:120]

            external_id = None
            mid = re.search(r"/(\d+)-", source_url)
            if mid:
                external_id = f"otr-{mid.group(1)}"
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


def build() -> OtrScraper:
    return OtrScraper()
