"""Robot de collecte — Côte d'Ivoire 🇨🇮 · AGEROUTE (marchés PUBLICS).

Source : Agence de Gestion des Routes de Côte d'Ivoire — https://ageroute.ci/
Section « Appels d'offres », déclinée en plusieurs rubriques :
  - avis d'appel d'offres de travaux (AAO national / international) ;
  - appel d'offres de fournitures ;
  - avis de manifestation d'intérêt (AMI) ;
  - avis de passation de marchés ;
  - avis du réseau AFRICATIP.

Toutes ces catégories sont collectées afin de couvrir l'ensemble des types
d'avis (AAON, AAOI, AMI, avis de passation, etc.). Chaque avis est présenté
dans un `article.uk-article` avec un titre-lien (`h2.uk-article-title a`) et
une date de publication (« 13 Aoû 2025 »).

Seules des métadonnées et le lien vers la fiche officielle sont collectés.
Principe de robustesse : en cas d'indisponibilité, on journalise un
avertissement et on retourne une liste vide — jamais de crash.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.cote_ivoire.ageroute")

from common.html_base import HtmlScraper  # noqa: E402


class AgerouteScraper(HtmlScraper):
    country = "CI"
    source_name = "AGEROUTE Côte d'Ivoire — Agence de Gestion des Routes"
    tender_type = "public"

    BASE = "https://ageroute.ci"
    LISTING_URLS = [
        "https://ageroute.ci/appels-d-offres/avis-d-appel-d-offres-de-travaux",
        "https://ageroute.ci/appels-d-offres/appel-offre-de-fournitures",
        "https://ageroute.ci/appels-d-offres/avis-de-manifestation-d-interet",
        "https://ageroute.ci/appels-d-offres/avis-de-passation-de-marches",
        "https://ageroute.ci/appels-d-offres/avis-du-reseau-africatip",
    ]

    # Nombre maximal de fiches de détail visitées par passe.
    MAX_DETAILS = 40

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        pages_ok = 0
        details_fetched = 0

        for listing in self.LISTING_URLS:
            soup = self.soup(listing)
            if not soup:
                continue
            pages_ok += 1
            for art in soup.select("article.uk-article"):
                link = art.select_one("h2.uk-article-title a[href], a.uk-article-title[href]")
                if not link:
                    link = art.find("a", href=re.compile(r"/appels-d-offres/.+/\d+-"))
                if not link:
                    continue
                href = link.get("href", "")
                # On ne garde que les fiches d'avis (URL numérotée), pas les
                # liens de rubrique.
                if not re.search(r"/\d+-", href):
                    continue
                full_url = urljoin(self.BASE, href)
                if full_url in seen:
                    continue
                seen.add(full_url)

                title = self.clean(link.get_text(" ", strip=True))
                if not title or len(title) < 6:
                    continue

                content_txt = art.get_text(" ", strip=True)
                pub = self.parse_fr_date(content_txt)

                reference = None
                m = re.search(r"\b(?:AO[IO]?|AMI|T|F|P|S)\s*N?[°ºo]?\s*[\w./\-]+/\d{4}",
                              title, re.IGNORECASE)
                if m:
                    reference = self.clean(m.group(0))[:120]

                # --- Enrichissement depuis la fiche de détail ---------
                # L'échéance (« … au plus tard le … ») et parfois le montant
                # estimatif en FCFA figurent dans le corps de l'avis.
                deadline = None
                amount = None
                if details_fetched < self.MAX_DETAILS:
                    detail = self.detail_text(full_url)
                    details_fetched += 1
                    if detail:
                        deadline = self.deadline_from_text(detail)
                        amount = self.amount_from_text(detail)

                items.append(self.make_item(
                    title=title[:255],
                    institution=self.source_name,
                    reference=reference,
                    publication_date=pub,
                    deadline=deadline,
                    estimated_amount=amount,
                    source_url=full_url,
                    dao_url=full_url,
                    external_id=f"ageroute-{abs(hash(full_url)) % (10 ** 10)}",
                ))

        if pages_ok == 0:
            logger.warning("[CI] AGEROUTE injoignable — 0 item")
        else:
            logger.info("[CI] AGEROUTE : %d avis collectés (%d/%d rubriques)",
                        len(items), pages_ok, len(self.LISTING_URLS))
        return items


def build() -> AgerouteScraper:
    return AgerouteScraper()
