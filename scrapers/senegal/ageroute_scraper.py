"""Robot de collecte — Sénégal 🇸🇳 · AGEROUTE (marchés PUBLICS · routes).

Source : Agence de Gestion des Routes du Sénégal — https://ageroute.sn/
Section « Appels d'offres », déclinée en plusieurs rubriques (travaux,
fournitures, services, manifestations d'intérêt, avis généraux de passation).

Le site (Elementor / WordPress) présente chaque avis avec un titre (`h3`) et
un lien de téléchargement du dossier (`/download/{id}/{categorie}/…`). On ne
retient que les liens dont la catégorie correspond à un avis de marché
(travaux, fournitures, services, manifestation d'intérêt, passation) — les
formulaires, procédures et publications diverses sont écartés.

Seules des métadonnées et le lien vers le dossier officiel sont collectés.
Principe de robustesse : en cas d'indisponibilité, on journalise un
avertissement et on retourne une liste vide — jamais de crash.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.senegal.ageroute")

from common.html_base import HtmlScraper  # noqa: E402


class AgerouteSnScraper(HtmlScraper):
    country = "SN"
    source_name = "AGEROUTE Sénégal — Agence de Gestion des Routes"
    tender_type = "public"

    BASE = "https://ageroute.sn"
    LISTING_URLS = [
        "https://ageroute.sn/avis-dappel-doffres-de-travaux/",
        "https://ageroute.sn/avis-dappel-doffres-de-fournitures/",
        "https://ageroute.sn/avis-dappel-doffres-de-services/",
        "https://ageroute.sn/avis-de-manifestation-dinteret/",
        "https://ageroute.sn/avis-general-de-passations-de-marche/",
    ]

    # Catégories (3e segment du lien /download/{id}/{categorie}/…) correspondant
    # à de véritables avis de marché.
    TENDER_CAT_RE = re.compile(
        r"(appel|appels-doffres|manifestation|passation|"
        r"avis-appels-offres|avis-dappel|avis-de-manifestation)",
        re.IGNORECASE,
    )
    DOWNLOAD_RE = re.compile(r"/download/\d+/([^/]+)/", re.IGNORECASE)

    # Le site liste les avis du plus récent au plus ancien : on plafonne par
    # rubrique pour ne pas réinjecter des années d'archives à chaque passe.
    MAX_PER_CATEGORY = 20

    def __init__(self):
        super().__init__()
        # Le certificat TLS d'ageroute.sn n'est pas toujours vérifiable.
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def fetch_html(self, url: str, params: dict | None = None) -> str | None:
        """GET HTML sans vérification TLS stricte (chaîne parfois incomplète)."""
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
                logger.warning("[SN] AGEROUTE GET %s échec %s/%s : %s",
                               url, attempt, config.MAX_RETRIES, exc)
                time.sleep(1.2 * attempt)
        return None

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        pages_ok = 0

        for listing in self.LISTING_URLS:
            soup = self.soup(listing)
            if not soup:
                continue
            pages_ok += 1
            kept_here = 0

            for link in soup.find_all("a", href=True):
                if kept_here >= self.MAX_PER_CATEGORY:
                    break
                href = link.get("href", "")
                m = self.DOWNLOAD_RE.search(href)
                if not m:
                    continue
                category = m.group(1)
                if not self.TENDER_CAT_RE.search(category):
                    continue

                dao_url = urljoin(self.BASE, href)

                # Titre : h3/h2 précédent, sinon texte du lien, sinon slug.
                heading = link.find_previous(["h3", "h2"])
                title = self.clean(heading.get_text(" ", strip=True)) if heading else ""
                if not title or len(title) < 12:
                    title = self.clean(link.get_text(" ", strip=True))
                if not title or len(title) < 12:
                    slug = href.rstrip("/").split("/")[-1]
                    title = self.clean(slug.replace("-", " ")).title()
                if not title or len(title) < 6:
                    continue

                slug = href.rstrip("/").split("/")[-1]
                ext = "ageroute-sn-" + re.sub(r"[^a-zA-Z0-9]", "", slug)[:50]
                if ext in seen:
                    continue
                seen.add(ext)
                kept_here += 1

                # Référence : motif normalisé contenant au moins un chiffre
                # (ex « AOI N°03/2026 »), sinon aucune (on évite « Travaux »).
                reference = None
                mref = re.search(
                    r"\b(?:AO[IO]?|AAO[IN]?|AMI|DRP\w*)\s*N?[°ºo]?\s*[\w./\-]*\d[\w./\-]*",
                    title, re.IGNORECASE)
                if mref:
                    reference = self.clean(mref.group(0))[:120]

                items.append(self.make_item(
                    title=title[:255],
                    institution=self.source_name,
                    reference=reference,
                    source_url=dao_url,
                    dao_url=dao_url,
                    market_type=category.replace("-", " "),
                    external_id=ext,
                ))

        if pages_ok == 0:
            logger.warning("[SN] AGEROUTE injoignable — 0 item")
        else:
            logger.info("[SN] AGEROUTE : %d avis collectés (%d/%d rubriques)",
                        len(items), pages_ok, len(self.LISTING_URLS))
        return items


def build() -> AgerouteSnScraper:
    return AgerouteSnScraper()
