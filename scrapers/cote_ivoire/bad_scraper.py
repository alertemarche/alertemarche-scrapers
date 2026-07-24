"""Robot de collecte — Côte d'Ivoire 🇨🇮 · BAD (Banque Africaine de Développement).

Source : portail des avis de passation de marchés de la BAD (www.afdb.org),
filtré sur la Côte d'Ivoire. On ne conserve que les avis liés à la Côte
d'Ivoire (« Côte d'Ivoire » / « Ivory Coast » dans le titre ou le pays).

⚠️ Le portail afdb.org est protégé par un pare-feu applicatif (Cloudflare) qui
renvoie fréquemment un code 403 aux robots. Le scraper est donc DÉFENSIF : il
tente plusieurs pages candidates avec des en-têtes de navigateur, filtre sur la
Côte d'Ivoire et — en cas de blocage — journalise un avertissement et retourne
une liste vide (jamais de crash).
"""
import logging
from urllib.parse import urljoin

from common.html_base import HtmlScraper

logger = logging.getLogger("scrapers.cote_ivoire.bad")

BASE = "https://www.afdb.org"

CANDIDATE_URLS = [
    "https://www.afdb.org/en/documents/project-related-procurement/procurement-notices/specific-procurement-notices?f%5B0%5D=country%3ACote%20dIvoire",
    "https://www.afdb.org/en/documents/project-related-procurement/procurement-notices/request-for-expression-of-interest?f%5B0%5D=country%3ACote%20dIvoire",
    "https://www.afdb.org/en/documents/project-related-procurement/procurement-notices/invitation-for-bids?f%5B0%5D=country%3ACote%20dIvoire",
]

CI_TOKENS = ("côte d'ivoire", "cote d'ivoire", "cote divoire", "ivory coast", "ivoire")


class BadCiScraper(HtmlScraper):
    country = "CI"
    source_name = "BAD (Banque Africaine de Développement)"
    tender_type = "prive"
    method = "html"

    def __init__(self):
        super().__init__()
        self.session.headers.update({
            "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
                       "image/avif,image/webp,*/*;q=0.8"),
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Upgrade-Insecure-Requests": "1",
        })

    def _is_ci(self, text: str) -> bool:
        low = text.lower()
        return any(tok in low for tok in CI_TOKENS)

    def _parse_listing(self, soup) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        for row in soup.select("div.views-row, article, tr"):
            text = self.clean(row.get_text(" ", strip=True))
            if len(text) < 12 or not self._is_ci(text):
                continue
            link = row.find("a", href=True)
            if not link:
                continue
            href = urljoin(BASE, link["href"])
            if href in seen:
                continue
            seen.add(href)
            title = self.clean(link.get_text(" ", strip=True)) or text[:255]
            if len(title) < 6:
                continue
            items.append(self.make_item(
                title=title[:255],
                institution=self.source_name,
                deadline=self.parse_fr_date(text),
                source_url=href,
                dao_url=href,
                external_id=f"bad-ci-{abs(hash(href)) % (10**10)}",
                tender_type="prive",
            ))
        return items

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen_urls: set[str] = set()
        blocked = 0
        for url in CANDIDATE_URLS:
            html = self.fetch_html(url)
            if not html:
                blocked += 1
                continue
            low = html.lower()
            if "cloudflare" in low and ("attention required" in low or "verify" in low):
                logger.warning("[CI] BAD — page bloquée par Cloudflare : %s", url)
                blocked += 1
                continue
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            for it in self._parse_listing(soup):
                if it["source_url"] not in seen_urls:
                    seen_urls.add(it["source_url"])
                    items.append(it)
        if not items and blocked:
            logger.warning("[CI] BAD — aucune donnée (%s/%s pages inaccessibles).",
                           blocked, len(CANDIDATE_URLS))
        return items


def build() -> BadCiScraper:
    return BadCiScraper()
