"""Robot de collecte — Burkina Faso 🇧🇫 · Délégation de l'Union Européenne.

Source : Portail officiel du Service européen pour l'action extérieure (EEAS),
section « Appels d'offres » filtrée pour le Burkina Faso :

    https://www.eeas.europa.eu/eeas/appel-d'offres_fr?f[0]=tender_site:Burkina Faso

La Délégation de l'UE au Burkina Faso publie des appels d'offres et des appels à
manifestation d'intérêt (AMI) pour ses opérations locales. Ces marchés (émis par
une institution internationale) relèvent des appels d'offres « privés » au sens
de la plateforme. Seules des métadonnées et le lien officiel sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

from common.html_base import HtmlScraper

logger = logging.getLogger("scrapers.burkina_faso.ue_delegation")

LISTING_URL = "https://www.eeas.europa.eu/eeas/appel-d%E2%80%99offres_fr?f%5B0%5D=tender_site%3ABurkina%20Faso"
BASE_URL = "https://www.eeas.europa.eu"
MAX_ITEMS = 20


class UeDelegationBfScraper(HtmlScraper):
    country = "BF"
    source_name = "Délégation UE Burkina Faso"
    tender_type = "prive"
    method = "html"

    def collect(self) -> list[dict]:
        items: list[dict] = []
        soup = self.soup(LISTING_URL)
        if not soup:
            logger.warning("[BF] Délégation UE injoignable — 0 item")
            return items

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        seen: set[str] = set()
        for link in soup.find_all("a", href=re.compile(r"/delegations/burkina-faso/")):
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
            if not title or len(title) < 15 or re.search(r"^(en savoir plus|lire|read more)$", title, re.I):
                parent = link.find_parent(["article", "div", "section"])
                if parent:
                    heading = parent.find(["h1", "h2", "h3", "h4"])
                    if heading:
                        title = " ".join(heading.get_text(" ", strip=True).split())
            if not title or len(title) < 10:
                title = "Appel d'offres Délégation UE Burkina Faso"

            # Filtrage des titres non pertinents (plans programmés, prospections, etc.)
            title_lower = title.lower()
            reject_patterns = [
                r'appels?\s+d.offres?\s+programm[ée]s?\s+(en\s+)?\d{4}',  # "Appels d'offres programmés en 2025"
                r'prospection\s+immobili[èe]re',  # "Prospection immobilière"
                r'^plan\s+de\s+passation',  # "Plan de passation"
                r'programme\s+indicatif',  # "Programme indicatif"
            ]
            if any(re.search(pattern, title_lower) for pattern in reject_patterns):
                continue

            items.append(self.make_item(
                title=title[:255],
                institution=self.source_name,
                source_url=full_url,
                dao_url=full_url,
                external_id=f"ue-bf-{abs(hash(full_url)) % (10 ** 10)}",
                tender_type="prive",
            ))

        logger.info("[BF] Délégation UE : %d avis collectés", len(items))
        return items


def build() -> UeDelegationBfScraper:
    return UeDelegationBfScraper()
