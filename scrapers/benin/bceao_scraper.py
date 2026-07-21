"""Robot de collecte — Bénin 🇧🇯 · BCEAO (marchés PRIVÉS / institutionnels).

Source : Banque Centrale des États de l'Afrique de l'Ouest —
https://www.bceao.int/fr/appels-offres/appels-offres-marches-publics-achats

Structure HTML : chaque avis est un `div.itemDoc.views-row` présentant
« Publié le <date> », une référence (ex. AO/Z00/DBA/0114/2026), « Date limite
le <date> » et un titre cliquable vers la fiche de l'avis.

Seules des métadonnées et le lien vers la fiche officielle sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.benin.bceao")

from common.html_base import HtmlScraper  # noqa: E402


class BceaoScraper(HtmlScraper):
    country = "BJ"
    source_name = "BCEAO — Banque Centrale des États de l'Afrique de l'Ouest"
    tender_type = "prive"

    LISTING = "https://www.bceao.int/fr/appels-offres/appels-offres-marches-publics-achats"

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        soup = self.soup(self.LISTING)
        if not soup:
            logger.warning("[BJ] BCEAO injoignable — 0 item")
            return items

        rows = soup.select("div.itemDoc.views-row")
        for row in rows:
            link = row.find("a", href=True)
            if not link:
                continue
            source_url = urljoin(self.LISTING, link["href"])
            text = row.get_text(" ", strip=True)

            pub = None
            mp = re.search(r"Publié le\s*(.+?)(?:[A-Z0-9]{2,}[/]|Date limite|$)", text, re.IGNORECASE)
            if mp:
                pub = self.parse_fr_date(mp.group(1))

            reference = None
            mr = re.search(r"([A-Z]{1,4}[0-9]{0,3}/[A-Z0-9]+/[A-Z0-9][A-Z0-9\-./]{2,})", text)
            if mr:
                reference = self.clean(mr.group(1))[:120]

            # Le libellé du lien contient les métadonnées : le vrai titre suit
            # « Date limite le <date> ». On isole cette portion.
            deadline = None
            title = self.clean(link.get_text())
            md = re.search(r"Date limite le\s+(\d{1,2}\s+[A-Za-zéûôàèùî]+\s+20\d{2})\s*(.*)$",
                           title, re.IGNORECASE)
            if md:
                deadline = self.parse_fr_date(md.group(1))
                if self.clean(md.group(2)):
                    title = self.clean(md.group(2))
            else:
                md2 = re.search(r"Date limite le\s+(\d{1,2}\s+[A-Za-zéûôàèùî]+\s+20\d{2})",
                                text, re.IGNORECASE)
                if md2:
                    deadline = self.parse_fr_date(md2.group(1))
            if not title or len(title) < 6:
                continue

            external_id = None
            if reference:
                external_id = "bceao-" + re.sub(r"[^a-zA-Z0-9]", "", reference)[:40]
            else:
                external_id = "bceao-" + re.sub(r"[^a-zA-Z0-9]", "", source_url.rsplit("/", 1)[-1])[:40]
            if external_id in seen:
                continue
            seen.add(external_id)

            items.append(self.make_item(
                title=title[:255],
                institution=self.source_name,
                reference=reference,
                deadline=deadline,
                publication_date=pub,
                source_url=source_url,
                external_id=external_id,
            ))
        return items


def build() -> BceaoScraper:
    return BceaoScraper()
