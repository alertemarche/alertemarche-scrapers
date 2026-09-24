"""Robot de collecte — Burkina Faso 🇧🇫 · BCEAO (agence d'Ouagadougou).

Source : portail des appels d'offres « Marchés publics / Achats » de la Banque
Centrale des États de l'Afrique de l'Ouest (www.bceao.int). La BCEAO publie ses
marchés pour l'ensemble de ses sites de l'UEMOA. On ne conserve ici que les avis
concernant le Burkina Faso (agence d'Ouagadougou).

Ces marchés (émis par une institution financière régionale) relèvent des appels
d'offres « privés » au sens de la plateforme (bailleur / institution).
"""
import logging
import re

from common.html_base import HtmlScraper

logger = logging.getLogger("scrapers.burkina_faso.bceao")

LISTING_URL = "https://www.bceao.int/fr/appels-offres/appels-offres-marches-publics-achats"
# Un avis concerne le BF s'il vise Ouagadougou ou le Burkina Faso.
BF_TOKENS = ("ouagadougou", "burkina", "burkinabé", "burkinabe", "burkinabè")


class BceaoBfScraper(HtmlScraper):
    country = "BF"
    source_name = "BCEAO — Banque Centrale des États de l'Afrique de l'Ouest (Ouagadougou)"
    tender_type = "prive"
    method = "html"

    def _is_bf(self, text: str) -> bool:
        low = text.lower()
        return any(tok in low for tok in BF_TOKENS)

    def collect(self) -> list[dict]:
        items: list[dict] = []
        soup = self.soup(LISTING_URL)
        if not soup:
            logger.warning("[BF] BCEAO injoignable — 0 item")
            return items

        seen: set[str] = set()
        for row in soup.select("div.views-row"):
            link = row.find("a", href=True)
            if not link:
                continue
            href = link["href"].strip()
            if not href or href in seen:
                continue

            title_el = row.select_one("span.ttr")
            title = self.clean(title_el.get_text(" ", strip=True)) if title_el else ""
            full_text = self.clean(row.get_text(" ", strip=True))
            if not title or len(title) < 8:
                title = full_text[:255]

            # Filtrer : ne garder que les avis liés au Burkina Faso (Ouagadougou).
            if not self._is_bf(title) and not self._is_bf(full_text):
                continue

            seen.add(href)

            # Date de publication : span.infoFile → « Publié le <time> »
            pub_date = None
            info = row.select_one("span.infoFile")
            if info:
                pub_date = self.parse_fr_date(info.get_text(" ", strip=True))

            # Date limite : span.subTtr → « Date limite le <time> »
            deadline = None
            sub = row.select_one("span.subTtr")
            if sub:
                deadline = self.parse_fr_date(sub.get_text(" ", strip=True))

            # Référence éventuelle (ex. AO/Z00/DBA/044/2026)
            reference = None
            ref_match = re.search(r"(AO[A-Z0-9/\-]{4,})", full_text)
            if ref_match:
                reference = self.clean(ref_match.group(1))

            items.append(self.make_item(
                title=title[:255],
                institution=self.source_name,
                reference=reference,
                publication_date=pub_date,
                deadline=deadline,
                source_url=href,
                dao_url=href,
                external_id=f"bceao-bf-{abs(hash(href)) % (10 ** 10)}",
                tender_type="prive",
            ))

        logger.info("[BF] BCEAO (Ouagadougou) : %d avis collectés", len(items))
        return items


def build() -> BceaoBfScraper:
    return BceaoBfScraper()
