"""Robot de collecte — Côte d'Ivoire 🇨🇮 · FER (marchés PUBLICS).

Source : Fonds d'Entretien Routier de Côte d'Ivoire — https://fer.ci/
Page de listing : https://fer.ci/appels_offre/liste_appels_offre

Structure HTML : chaque avis est associé à un fichier PDF hébergé sous
`/uploads/appels_offre/`. Le conteneur parent porte l'objet du marché, le type
de procédure (« Appel d'Offre Ouvert (AOO) », « Demande de Cotation », etc.),
la référence et éventuellement une date (attribution / publication).

Seules des métadonnées et le lien PDF officiel (`dao_url`) sont collectés.
Principe de robustesse : indisponibilité → avertissement + liste vide.
"""
import logging
import re
from urllib.parse import unquote, urljoin

logger = logging.getLogger("scrapers.cote_ivoire.fer")

from common.html_base import HtmlScraper  # noqa: E402


class FerScraper(HtmlScraper):
    country = "CI"
    source_name = "FER Côte d'Ivoire — Fonds d'Entretien Routier"
    tender_type = "public"

    BASE = "https://fer.ci"
    LISTING_URLS = [
        "https://fer.ci/appels_offre/liste_appels_offre",
        "https://fer.ci/appels_offre/procedures",
    ]

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        pages_ok = 0

        for listing in self.LISTING_URLS:
            soup = self.soup(listing)
            if not soup:
                continue
            pages_ok += 1
            for link in soup.select("a[href*='/uploads/appels_offre/']"):
                href = link.get("href", "")
                if not href.lower().endswith(".pdf"):
                    continue
                dao_url = urljoin(self.BASE, href)
                if dao_url in seen:
                    continue
                seen.add(dao_url)

                # Contexte : la ligne/carte parente contient l'objet du marché.
                parent = link.find_parent(["tr", "div", "li", "article", "td"])
                ctx = self.clean(parent.get_text(" ", strip=True)) if parent else ""

                # Titre : texte du lien, sinon objet extrait du contexte, sinon
                # nom de fichier nettoyé.
                title = self.clean(link.get_text(" ", strip=True))
                if not title or len(title) < 10 or title.lower() in ("télécharger", "voir", "pdf"):
                    title = self.clean(ctx)
                # L'objet précède souvent « Date d'attribution » / « Appel d'Offre ».
                # On coupe systématiquement ces mentions parasites en fin de titre.
                title = self.clean(re.split(
                    r"\s+Date\s+d|\s+Appel\s+d.?Offre|\s+Demande\s+de\s|\s+N[°ºo]\s",
                    title, maxsplit=1, flags=re.IGNORECASE)[0])
                if not title or len(title) < 10:
                    fname = unquote(href.split("/")[-1]).rsplit(".", 1)[0]
                    title = self.clean(fname.replace("_", " ").replace("-", " "))
                if not title or len(title) < 6:
                    continue

                # Type de procédure / référence dans le contexte.
                market_type = None
                mt = re.search(r"(Appel d.?Offre[^/|]*|Demande de Cotation|"
                               r"Demande de Renseignement[^/|]*|Manifestation d.?Int[ée]r[êe]t)",
                               ctx, re.IGNORECASE)
                if mt:
                    market_type = self.clean(mt.group(1))[:80]
                reference = None
                rm = re.search(r"\b[A-Z]{1,3}\s?\d{1,3}/\d{4}\b", ctx)
                if rm:
                    reference = self.clean(rm.group(0))[:80]

                pub = self.parse_fr_date(ctx)

                items.append(self.make_item(
                    title=title[:255],
                    institution=self.source_name,
                    reference=reference,
                    market_type=market_type,
                    publication_date=pub,
                    source_url=listing,
                    dao_url=dao_url,
                    external_id=f"fer-{abs(hash(dao_url)) % (10 ** 10)}",
                ))

        if pages_ok == 0:
            logger.warning("[CI] FER injoignable — 0 item")
        else:
            logger.info("[CI] FER : %d avis collectés", len(items))
        return items


def build() -> FerScraper:
    return FerScraper()
