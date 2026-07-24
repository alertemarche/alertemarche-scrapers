"""Robot de collecte — Togo 🇹🇬 · BAD (Banque Africaine de Développement).

Source : portail des avis de passation de marchés de la BAD (www.afdb.org),
filtré sur le Togo. On ne conserve que les avis liés au Togo.

⚠️ Le portail afdb.org est protégé par un pare-feu applicatif (Cloudflare) qui
renvoie fréquemment un code 403 aux robots. Le scraper est donc DÉFENSIF : il
tente plusieurs pages candidates, filtre sur le Togo et — en cas de blocage —
journalise un avertissement et retourne une liste vide (jamais de crash).
"""
import logging
from urllib.parse import urljoin

from common.html_base import HtmlScraper

logger = logging.getLogger("scrapers.togo.bad")

BASE = "https://www.afdb.org"

CANDIDATE_URLS = [
    "https://www.afdb.org/en/documents/project-related-procurement/procurement-notices/specific-procurement-notices?f%5B0%5D=country%3ATogo",
    "https://www.afdb.org/en/documents/project-related-procurement/procurement-notices/request-for-expression-of-interest?f%5B0%5D=country%3ATogo",
    "https://www.afdb.org/en/documents/project-related-procurement/procurement-notices/invitation-for-bids?f%5B0%5D=country%3ATogo",
]

TG_TOKENS = ("togo", "togolaise", "togolais")


class BadTgScraper(HtmlScraper):
    country = "TG"
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

    def _is_tg(self, text: str) -> bool:
        low = text.lower()
        return any(tok in low for tok in TG_TOKENS)

    def _parse_listing(self, soup) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        for row in soup.select("div.views-row, article, tr"):
            text = self.clean(row.get_text(" ", strip=True))
            if len(text) < 12 or not self._is_tg(text):
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
                external_id=f"bad-tg-{abs(hash(href)) % (10**10)}",
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
                logger.warning("[TG] BAD — page bloquée par Cloudflare : %s", url)
                blocked += 1
                continue
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            for it in self._parse_listing(soup):
                if it["source_url"] not in seen_urls:
                    seen_urls.add(it["source_url"])
                    items.append(it)
        if not items and blocked:
            logger.warning("[TG] BAD — aucune donnée (%s/%s pages inaccessibles).",
                           blocked, len(CANDIDATE_URLS))
        return items


def build() -> BadTgScraper:
    return BadTgScraper()
