"""Robot de collecte — Côte d'Ivoire 🇨🇮 · Marchés Publics (PUBLICS).

Source : portail des marchés publics de Côte d'Ivoire —
https://www.marchespublics.ci/appel_offre

Structure HTML : un unique tableau listant l'ensemble des appels d'offres.
Colonnes : Numéro AO · Type de marché · Objet · Autorité Contractante ·
Date de publication · Date limite.

Seules des métadonnées sont collectées (le tableau ne propose pas de lien par
ligne ; l'URL de la source est la page de listing officielle).
"""
import logging

logger = logging.getLogger("scrapers.cote_ivoire.marchespublics")

from common.html_base import HtmlScraper  # noqa: E402


class MarchesPublicsCiScraper(HtmlScraper):
    country = "CI"
    source_name = "Marchés Publics Côte d'Ivoire — Portail national"
    tender_type = "public"

    LISTING_URLS = [
        "https://www.marchespublics.ci/appel_offre",
        "https://marchespublics.ci/appel_offre",
    ]

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
            logger.warning("[CI] Marchés Publics CI injoignable — 0 item")
            return items

        table = soup.find("table")
        if not table:
            logger.warning("[CI] Marchés Publics CI — tableau introuvable")
            return items

        rows = table.find_all("tr")
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) < 6:
                continue
            reference = self.clean(cells[0].get_text(" ", strip=True)) or None
            market_type = self.clean(cells[1].get_text(" ", strip=True)) or None
            title = self.clean(cells[2].get_text(" ", strip=True))
            institution = self.clean(cells[3].get_text(" ", strip=True)) or self.source_name
            pub = self.parse_fr_date(cells[4].get_text(" ", strip=True))
            deadline = self.parse_fr_date(cells[5].get_text(" ", strip=True))
            if not title or len(title) < 6:
                continue
            # Montant estimatif si présent dans la ligne (colonne facultative
            # selon les mises à jour du portail).
            amount = self.amount_from_text(row.get_text(" ", strip=True))

            external_id = f"mpci-{reference}" if reference else None
            key = external_id or (title[:60] + "|" + (deadline or ""))
            if key in seen:
                continue
            seen.add(key)

            items.append(self.make_item(
                title=title,
                institution=institution,
                reference=reference,
                market_type=market_type,
                publication_date=pub,
                deadline=deadline,
                estimated_amount=amount,
                source_url=base,
                external_id=external_id,
            ))
        return items


def build() -> MarchesPublicsCiScraper:
    return MarchesPublicsCiScraper()
