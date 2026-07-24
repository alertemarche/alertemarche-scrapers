"""Robot de collecte — Sénégal 🇸🇳 · Port Autonome de Dakar (PAD).

Source : Port Autonome de Dakar — https://www.portdakar.sn/
Section « Opportunité d'affaire / Appels d'offres ».

La page de listing présente les avis sous forme de liens vers des fiches de
détail (`/fr/opportunite-daffaire/appels-d-offres/{slug}`). On visite chaque
fiche pour tenter d'extraire la date limite (« au plus tard le … », « date
limite … »).

Seules des métadonnées et le lien vers la fiche officielle sont collectés.
Principe de robustesse : en cas d'indisponibilité, on journalise un
avertissement et on retourne une liste vide — jamais de crash.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.senegal.pad")

from common.html_base import HtmlScraper  # noqa: E402


class PadScraper(HtmlScraper):
    country = "SN"
    source_name = "Port Autonome de Dakar (PAD)"
    tender_type = "public"

    BASE = "https://www.portdakar.sn"
    LISTING_URL = "https://www.portdakar.sn/fr/opportunite-daffaire/appels-d-offres"

    # Garde-fou : nombre maximal de fiches de détail visitées par passe.
    MAX_DETAILS = 30

    # Lien de fiche d'avis : /fr/opportunite-daffaire/appels-d-offres/{slug}
    OFFER_RE = re.compile(r"/opportunite-daffaire/appels-d-offres/[^/#?]+$", re.I)

    def __init__(self):
        super().__init__()
        # Le certificat TLS du PAD n'est pas vérifiable (chaîne incomplète).
        # On désactive donc la vérification pour ce site précis.
        self._verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def fetch_html(self, url: str, params: dict | None = None) -> str | None:
        """GET HTML sans vérification TLS (certificat PAD non vérifiable)."""
        import time
        from common import config
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=params,
                                        timeout=config.REQUEST_TIMEOUT, verify=False)
                resp.raise_for_status()
                if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
                    resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            except Exception as exc:  # noqa: BLE001
                logger.warning("[SN] PAD GET %s échec %s/%s : %s",
                               url, attempt, config.MAX_RETRIES, exc)
                time.sleep(1.2 * attempt)
        return None

    def soup(self, url: str, params: dict | None = None):
        """Le HTML du PAD n'est pas parsé correctement par lxml → html.parser."""
        from bs4 import BeautifulSoup
        html = self.fetch_html(url, params=params)
        if not html:
            return None
        return BeautifulSoup(html, "html.parser")

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        details = 0

        soup = self.soup(self.LISTING_URL)
        if not soup:
            logger.warning("[SN] PAD injoignable — 0 item")
            return items

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if not self.OFFER_RE.search(href):
                continue

            title = self.clean(link.get_text(" ", strip=True))
            if not title or len(title) < 6:
                continue

            full_url = urljoin(self.BASE, href)
            slug = href.rstrip("/").split("/")[-1]
            ext = "pad-" + re.sub(r"[^a-zA-Z0-9]", "", slug)[:50]
            if ext in seen:
                continue
            seen.add(ext)

            # Enrichissement : échéance depuis la fiche de détail.
            deadline = None
            if details < self.MAX_DETAILS:
                detail = self.detail_text(full_url)
                details += 1
                if detail:
                    deadline = self.deadline_from_text(detail)

            items.append(self.make_item(
                title=title[:255],
                institution=self.source_name,
                deadline=deadline,
                source_url=full_url,
                dao_url=full_url,
                external_id=ext,
            ))

        logger.info("[SN] PAD : %d avis collectés", len(items))
        return items


def build() -> PadScraper:
    return PadScraper()
