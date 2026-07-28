"""Robot de collecte — Sénégal 🇸🇳 · BAD (Banque Africaine de Développement / AfDB).

Source : portail des avis de passation de marchés de la BAD (www.afdb.org).

⚠️ IMPORTANT — le portail afdb.org N'EST PAS filtrable côté serveur.
Le paramètre d'URL `?f[0]=country:Senegal` est ignoré par le rendu HTML : la
page renvoie TOUS les avis, tous pays confondus (Éthiopie, Zimbabwe, Namibie…),
répartis sur des dizaines de pages. L'ancienne version se contentait de chercher
le mot « Sénégal » dans le texte de la page puis prenait le PREMIER lien de la
ligne — un avis d'un pays quelconque. C'est ainsi que des marchés d'autres pays
se retrouvaient dans la section Sénégal d'AlerteMarché.

✅ Correction : chaque avis AfDB encode son pays de façon fiable dans l'URL ET
dans le titre, juste après le préfixe de type :
    « aoi-senegal-... », « ami-senegal-... »   -> Sénégal (conservé)
    « aao-cote-divoire-... », « spn-mali-... »  -> autre pays (rejeté)
On parcourt donc les pages de listing et on ne conserve QUE les avis dont le
pays extrait vaut explicitement « Sénégal ». Tout avis rattaché à un autre pays
(ou dont le pays est indéterminé) est rejeté.

Le portail afdb.org est protégé par un pare-feu applicatif (Cloudflare) ; le
scraper reste DÉFENSIF : en cas de blocage il journalise un avertissement et
retourne une liste vide — jamais de crash.
"""
import logging
import re
from urllib.parse import urljoin

from common.html_base import HtmlScraper

logger = logging.getLogger("scrapers.senegal.bad")

BASE = "https://www.afdb.org"

LISTING_BASE = (
    f"{BASE}/en/documents/project-related-procurement/procurement-notices"
)

LISTING_SEGMENTS = (
    "specific-procurement-notices",
    "request-for-expression-of-interest",
    "invitation-for-bids",
)

MAX_PAGES = 12

# Le pays cible est toujours le token « senegal » juste après le préfixe de type.
_SENEGAL_SLUG_RE = re.compile(r"^[a-z]{2,6}-senegal-", re.IGNORECASE)

_SLUG_COUNTRY_RE = re.compile(r"^[a-z]{2,6}-([a-z]+)-", re.IGNORECASE)

_NOTICE_SLUG_RE = re.compile(r"^[a-z]{2,6}-[a-z]", re.IGNORECASE)

_TITLE_COUNTRY_RE = re.compile(
    r"^\s*[A-Za-zÉ]{2,6}\s*[-–]\s*([A-Za-zÀ-ÿ'’ ]+?)\s*[-–]"
)

SN_TOKENS = ("senegal", "sénégal", "senegalese", "sénégalais", "sénégalaise")


class BadSnScraper(HtmlScraper):
    country = "SN"
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

    # ---- Filtrage pays ------------------------------------------------
    @staticmethod
    def _slug_of(href: str) -> str:
        path = href.split("?", 1)[0].split("#", 1)[0]
        return path.rstrip("/").split("/")[-1].lower()

    def _is_notice_link(self, href: str) -> bool:
        if "/documents/" not in href:
            return False
        return bool(_NOTICE_SLUG_RE.match(self._slug_of(href)))

    def _notice_country_is_target(self, href: str, title: str) -> bool:
        """Ne valide QUE les avis explicitement rattachés au Sénégal."""
        slug = self._slug_of(href)

        if _SENEGAL_SLUG_RE.match(slug):
            return True
        m = _SLUG_COUNTRY_RE.match(slug)
        if m:
            return m.group(1).lower() in ("senegal",)

        mt = _TITLE_COUNTRY_RE.match(title or "")
        if mt:
            country = mt.group(1).strip().lower()
            return any(country.startswith(tok) for tok in SN_TOKENS)

        return False

    # ---- Parsing ------------------------------------------------------
    def _parse_listing(self, soup) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        for a in soup.select("a[href*='/documents/']"):
            href = a.get("href", "")
            if not self._is_notice_link(href):
                continue
            title = self.clean(a.get_text(" ", strip=True))
            if not self._notice_country_is_target(href, title):
                continue
            full = urljoin(BASE, href)
            if full in seen:
                continue
            seen.add(full)
            slug = self._slug_of(href)
            if len(title) < 6:
                title = slug.replace("-", " ").strip().capitalize()
            deadline = None
            parent = a.find_parent(["div", "article", "li", "tr", "td", "p"])
            if parent is not None:
                ptext = self.clean(parent.get_text(" ", strip=True))
                if len(ptext) <= 400:
                    deadline = (self.deadline_from_text(ptext)
                                or self.parse_fr_date(ptext))
            items.append(self.make_item(
                title=title[:255],
                institution=self.source_name,
                location="Sénégal",
                deadline=deadline,
                source_url=full,
                dao_url=full,
                external_id=f"bad-sn-{abs(hash(full)) % (10**10)}",
                tender_type="prive",
            ))
        return items

    @staticmethod
    def _is_blocked(html: str) -> bool:
        low = html.lower()
        return ("attention required" in low
                or "verify you are human" in low
                or "checking your browser" in low)

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen_urls: set[str] = set()
        blocked = 0
        pages_read = 0
        from bs4 import BeautifulSoup
        for seg in LISTING_SEGMENTS:
            for page in range(MAX_PAGES):
                url = (f"{LISTING_BASE}/{seg}"
                       f"?f%5B0%5D=country%3ASenegal&page={page}")
                html = self.fetch_html(url)
                if not html:
                    blocked += 1
                    break
                if self._is_blocked(html):
                    logger.warning("[SN] BAD — page bloquée (Cloudflare) : %s",
                                   url)
                    blocked += 1
                    break
                pages_read += 1
                soup = BeautifulSoup(html, "lxml")
                notice_links = [a for a in soup.select("a[href*='/documents/']")
                                if self._is_notice_link(a.get("href", ""))]
                if not notice_links:
                    break
                for it in self._parse_listing(soup):
                    if it["source_url"] not in seen_urls:
                        seen_urls.add(it["source_url"])
                        items.append(it)

        if not items and blocked:
            logger.warning("[SN] BAD — aucune donnée collectée (%s pages "
                           "inaccessibles). Portail probablement protégé.",
                           blocked)
        else:
            logger.info("[SN] BAD — %s avis Sénégal retenus (%s pages lues, "
                        "%s pages bloquées/injoignables).",
                        len(items), pages_read, blocked)
        return items


def build() -> BadSnScraper:
    return BadSnScraper()
