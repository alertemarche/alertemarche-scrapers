"""Robot de collecte — Bénin 🇧🇯 · Ambassade de France au Bénin.

Source : Site officiel de l'Ambassade de France au Bénin, qui publie
occasionnellement des appels d'offres et avis de concurrence pour ses
opérations locales (travaux, fournitures, services) :

    https://bj.diplomatie.gouv.fr/

Ces marchés (émis par une représentation diplomatique) relèvent des appels
d'offres « privés » au sens de la plateforme (acheteur non étatique, budget
hors finances publiques béninoises). La publication est irrégulière et sans
page « appels d'offres » dédiée — les avis apparaissent en lien direct depuis
la page d'accueil ou la section services. Seules des métadonnées et le lien
vers l'avis officiel sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

from common.html_base import HtmlScraper

logger = logging.getLogger("scrapers.benin.ambassade_france")

HOME_URL = "https://bj.diplomatie.gouv.fr/"


class AmbassadeFranceScraper(HtmlScraper):
    country = "BJ"
    source_name = "Ambassade de France Bénin"
    tender_type = "prive"
    method = "html"

    def collect(self) -> list[dict]:
        items: list[dict] = []
        soup = self.soup(HOME_URL)
        if not soup:
            return items

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # Stratégie : parcourir tous les liens de la page d'accueil et identifier
        # ceux qui mentionnent « appel », « concurrence », « marché », « offre »
        # dans leur texte ou leur URL. On exclut les liens de navigation générale
        # (« voir toutes les démarches », etc.).
        KEYWORDS = re.compile(
            r"(appel.*offre|appel.*concurrence|appel.*march[ée]|avis.*concurrence|avis.*march[ée])",
            re.IGNORECASE,
        )
        EXCLUDE = re.compile(r"^(voir toutes?|tout|service|d[ée]marches?)$", re.IGNORECASE)

        seen: set[str] = set()
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if not href or href.startswith("#"):
                continue
            full_url = urljoin(HOME_URL, href)
            if full_url in seen:
                continue

            text = " ".join(link.get_text(" ", strip=True).split())
            # Chercher les mots-clés dans le texte OU l'URL
            if not KEYWORDS.search(text + " " + href):
                continue
            # Exclure les liens de navigation générique
            if EXCLUDE.match(text):
                continue

            seen.add(full_url)

            # Utiliser le texte du lien comme titre
            title = text if text and len(text) >= 10 else "Avis Ambassade de France Bénin"

            items.append(self.make_item(
                title=title[:255],
                institution=self.source_name,
                source_url=full_url,
                dao_url=full_url,
                external_id=f"ambafr-{abs(hash(full_url)) % (10 ** 10)}",
                tender_type="prive",
            ))

        logger.info("[BJ] Ambassade France : %d avis collectés", len(items))
        return items


def build() -> AmbassadeFranceScraper:
    return AmbassadeFranceScraper()
