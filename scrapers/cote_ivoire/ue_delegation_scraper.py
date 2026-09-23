"""Robot de collecte — Côte d'Ivoire 🇨🇮 · Délégation de l'Union Européenne.

Source : Portail officiel du Service européen pour l'action extérieure (EEAS),
section « Appels d'offres » filtrée pour la Côte d'Ivoire :

    https://www.eeas.europa.eu/eeas/appel-d'offres_fr?f[0]=tender_site:Côte d'Ivoire

La Délégation de l'UE en Côte d'Ivoire publie des appels d'offres et des appels
à manifestation d'intérêt (AMI) pour ses opérations locales. Ces marchés (émis
par une institution internationale) relèvent des appels d'offres « privés » au
sens de la plateforme. Seules des métadonnées et le lien officiel sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

from common.html_base import HtmlScraper

logger = logging.getLogger("scrapers.cote_ivoire.ue_delegation")

# tender_site = "Côte d'Ivoire" (encodé : C%C3%B4te%20d%27Ivoire)
LISTING_URL = (
    "https://www.eeas.europa.eu/eeas/appel-d%E2%80%99offres_fr"
    "?f%5B0%5D=tender_site%3AC%C3%B4te%20d%27Ivoire"
)
BASE_URL = "https://www.eeas.europa.eu"
# Les fiches de la délégation CI vivent sous /delegations/côte-divoire/
# (encodé : c%C3%B4te-divoire), parfois en forme décodée selon le parseur.
DELEG_HREF_RE = re.compile(r"/delegations/c(?:%C3%B4|ô)te-divoire/", re.I)
MAX_ITEMS = 20


class UeDelegationCiScraper(HtmlScraper):
    country = "CI"
    source_name = "Délégation UE Côte d'Ivoire"
    tender_type = "prive"
    method = "html"

    def collect(self) -> list[dict]:
        items: list[dict] = []
        soup = self.soup(LISTING_URL)
        if not soup:
            logger.warning("[CI] Délégation UE injoignable — 0 item")
            return items

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        seen: set[str] = set()
        for link in soup.find_all("a", href=DELEG_HREF_RE):
            if len(items) >= MAX_ITEMS:
                break
            href = link.get("href", "")
            if not href:
                continue
            full_url = urljoin(BASE_URL, href)
            if full_url in seen:
                continue
            seen.add(full_url)

            title = " ".join(link.get_text(" ", strip=True).split())
            if not title or len(title) < 15 or re.search(
                r"^(en savoir plus|lire|read more)$", title, re.I
            ):
                parent = link.find_parent(["article", "div", "section"])
                if parent:
                    heading = parent.find(["h1", "h2", "h3", "h4"])
                    if heading:
                        title = " ".join(heading.get_text(" ", strip=True).split())
            if not title or len(title) < 10:
                title = "Appel d'offres Délégation UE Côte d'Ivoire"

            # Tentative d'extraction d'une date limite depuis le contexte proche.
            deadline = None
            parent = link.find_parent(["article", "div", "section"])
            if parent:
                deadline = self.deadline_from_text(parent.get_text(" ", strip=True))

            items.append(self.make_item(
                title=title[:255],
                institution=self.source_name,
                deadline=deadline,
                source_url=full_url,
                dao_url=full_url,
                external_id=f"ue-ci-{abs(hash(full_url)) % (10 ** 10)}",
                tender_type="prive",
            ))

        logger.info("[CI] Délégation UE : %d avis collectés", len(items))
        return items


def build() -> UeDelegationCiScraper:
    return UeDelegationCiScraper()
