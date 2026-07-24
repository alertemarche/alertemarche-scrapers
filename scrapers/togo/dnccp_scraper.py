"""Robot de collecte — Togo 🇹🇬 · DNCCP (marchés PUBLICS).

Source : Direction Nationale de Contrôle de la Commande Publique du Togo —
https://dnccp.gouv.tg/ (catégorie « Avis d'appel d'offres »).

C'est le portail OFFICIEL qui centralise les avis d'appel d'offres publics du
Togo (AAOO, AAOI, AMI, demandes de renseignement et de prix…). Le site est un
WordPress paginé : chaque avis est un `article` avec un titre `h2 a` pointant
vers la fiche détaillée (qui porte le PDF du dossier — DAO).

C'est de loin la source PUBLIQUE la plus riche pour le Togo (une centaine
d'avis courants répartis sur ~10 pages). On collecte l'ensemble des pages afin
de capturer 100 % des avis en cours.

Seules des métadonnées et le lien vers la fiche officielle sont collectés —
jamais le document lui-même.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.togo.dnccp")

from common.html_base import HtmlScraper  # noqa: E402


class DnccpTgScraper(HtmlScraper):
    country = "TG"
    source_name = "DNCCP Togo — Direction Nationale de Contrôle de la Commande Publique"
    tender_type = "public"

    # Catégorie « Avis d'appel d'offres » du portail DNCCP.
    BASE = "https://dnccp.gouv.tg/dnccp/category/avis-d-appel-d-offres/"
    MAX_PAGES = 20  # garde-fou (le site tourne autour de 10 pages)

    # Référence d'avis fréquente : « AAOI 001-2026 », « n°02/2026/ICAT/PRMP »,
    # « DAOO N°01/06/2026/… », « AMI N° 001/2026/OTR/… ».
    REF_RE = re.compile(
        r"((?:AAOO|AAOI|AAO|AMI|DAOO|DAO|DRP|AOO|AOI|N[°o])\s*[°o]?\s*[0-9][0-9A-Z/\-\.]{2,})",
        re.IGNORECASE,
    )

    def _page_url(self, page: int) -> str:
        if page <= 1:
            return self.BASE
        return f"{self.BASE}page/{page}/"

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()

        for page in range(1, self.MAX_PAGES + 1):
            soup = self.soup(self._page_url(page))
            if not soup:
                # Page injoignable : on arrête (fin de pagination probable).
                if page == 1:
                    logger.warning("[TG] DNCCP injoignable — 0 item")
                break

            articles = soup.select("article")
            if not articles:
                break

            new_on_page = 0
            for art in articles:
                title_el = (art.select_one("h2.entry-title a")
                            or art.select_one("h2 a")
                            or art.select_one("h3.entry-title a")
                            or art.select_one("h3 a")
                            or art.select_one(".entry-title a"))
                if not title_el:
                    continue

                title = self.clean(title_el.get_text())
                # Certains titres sont préfixés par la catégorie « F/T/SC » —
                # on nettoie ce préfixe parasite s'il est présent.
                title = re.sub(r"^(?:F/T/SC|F/T|T/SC)\s+", "", title).strip()
                if not title or len(title) < 8:
                    continue

                href = title_el.get("href")
                source_url = urljoin(self.BASE, href) if href else self.BASE

                # external_id : slug de la fiche (stable).
                mid = re.search(r"/([a-z0-9\-]+)/?$", source_url)
                external_id = f"dnccp-tg-{mid.group(1)[:70]}" if mid else None
                key = external_id or title[:70]
                if key in seen:
                    continue
                seen.add(key)

                # Référence extraite du titre lorsqu'elle y figure.
                mref = self.REF_RE.search(title)
                reference = self.clean(mref.group(1)) if mref else None

                # Date de publication : le slug/URL WordPress porte souvent
                # l'année ; sinon on laisse l'API dater à la collecte.
                pub = None
                mdate = re.search(r"/(20\d{2})/(\d{2})/", source_url)
                if mdate:
                    pub = f"{mdate.group(1)}-{mdate.group(2)}-01"

                items.append(self.make_item(
                    title=title,
                    institution=self.source_name,
                    reference=reference,
                    location="Togo",
                    publication_date=pub,
                    source_url=source_url,
                    external_id=external_id,
                ))
                new_on_page += 1

            # Plus aucun nouvel avis sur la page : fin de pagination.
            if new_on_page == 0:
                break

        return items


def build() -> DnccpTgScraper:
    return DnccpTgScraper()
