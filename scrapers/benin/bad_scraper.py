"""Robot de collecte — Bénin 🇧🇯 · BAD (Banque Africaine de Développement / AfDB).

Source : portail des avis de passation de marchés de la BAD (www.afdb.org).

⚠️ IMPORTANT — le portail afdb.org N'EST PAS filtrable côté serveur.
Le paramètre d'URL `?f[0]=country:Benin` est ignoré par le rendu HTML : la page
renvoie TOUS les avis, tous pays confondus (Mali, Éthiopie, Soudan, Djibouti…),
répartis sur des dizaines de pages. L'ancienne version se contentait de chercher
le mot « Benin » dans le texte de la page (présent dans le fil d'ariane / le
titre du filtre) puis prenait le PREMIER lien de la page — un avis « à la une »
d'un pays quelconque. C'est ainsi que des marchés du Mali se retrouvaient dans
la section Bénin d'AlerteMarché.

✅ Correction : chaque avis AfDB encode son pays de façon fiable dans l'URL ET
dans le titre, juste après le préfixe de type :
    « aoi-benin-... », « ami-benin-... »   -> Bénin (conservé)
    « aao-mali-... », « spn-ethiopia-... » -> autre pays (rejeté)
On parcourt donc les pages de listing et on ne conserve QUE les avis dont le
pays extrait vaut explicitement « Bénin ». Tout avis rattaché à un autre pays
(ou dont le pays est indéterminé) est rejeté.

Le portail afdb.org est protégé par un pare-feu applicatif (Cloudflare) ; le
scraper reste DÉFENSIF : en cas de blocage il journalise un avertissement et
retourne une liste vide — jamais de crash.
"""
import logging
import re
from urllib.parse import urljoin

from common.html_base import HtmlScraper

logger = logging.getLogger("scrapers.benin.bad")

BASE = "https://www.afdb.org"

# Base des listings d'avis de passation de marchés (portail Drupal AfDB).
LISTING_BASE = (
    f"{BASE}/en/documents/project-related-procurement/procurement-notices"
)

# Segments de listing parcourus (avis spécifiques, manifestations d'intérêt,
# appels d'offres). On conserve le paramètre `country:Benin` par convention même
# s'il est ignoré côté serveur (voir docstring).
LISTING_SEGMENTS = (
    "specific-procurement-notices",
    "request-for-expression-of-interest",
    "invitation-for-bids",
)

# La liste AfDB n'étant pas filtrable côté serveur, on parcourt les premières
# pages de chaque type et on filtre nous-mêmes sur le Bénin. Borne haute pour
# éviter de parcourir les ~86 pages (tous pays) du portail.
MAX_PAGES = 12

# Un avis AfDB a un slug de la forme « <type>-<pays>-<description> » :
#   aoi-benin-acquisition-…, ami-benin-recrutement-…, aao-mali-…, spn-ethiopia-…
# Le pays du Bénin est toujours le mot « benin » juste après le préfixe de type.
_BENIN_SLUG_RE = re.compile(r"^[a-z]{2,6}-benin-", re.IGNORECASE)

# Extrait le pays encodé dans le slug (2e segment) : « aao-mali-… » -> « mali ».
_SLUG_COUNTRY_RE = re.compile(r"^[a-z]{2,6}-([a-z]+)-", re.IGNORECASE)

# Un lien d'avis (à distinguer des liens de pagination / navigation) : slug de
# type « xxx-yyy… » (préfixe court suivi d'un tiret puis de lettres), sans query.
_NOTICE_SLUG_RE = re.compile(r"^[a-z]{2,6}-[a-z]", re.IGNORECASE)

# Pays extrait d'un titre « AOI - Benin - … » / « AAO - Mali - … ».
_TITLE_COUNTRY_RE = re.compile(
    r"^\s*[A-Za-zÉ]{2,6}\s*[-–]\s*([A-Za-zÀ-ÿ'’ ]+?)\s*[-–]"
)

BENIN_TOKENS = ("benin", "bénin")


class BadScraper(HtmlScraper):
    country = "BJ"
    source_name = "BAD (Banque Africaine de Développement)"
    tender_type = "prive"
    method = "html"

    def __init__(self):
        super().__init__()
        # En-têtes de navigateur complets pour limiter les blocages Cloudflare.
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
        """Dernier segment d'URL, sans query ni slash final (le « slug »)."""
        path = href.split("?", 1)[0].split("#", 1)[0]
        return path.rstrip("/").split("/")[-1].lower()

    def _is_notice_link(self, href: str) -> bool:
        """Vrai si le lien pointe vers un avis (et non pagination / menu)."""
        if "/documents/" not in href:
            return False
        return bool(_NOTICE_SLUG_RE.match(self._slug_of(href)))

    def _notice_country_is_benin(self, href: str, title: str) -> bool:
        """Ne valide QUE les avis explicitement rattachés au Bénin.

        Le pays est déterminé, par ordre de fiabilité :
          1. depuis le slug de l'URL (« aoi-benin-… ») — signal le plus sûr ;
          2. à défaut, depuis le titre (« AOI - Benin - … »).
        Tout avis dont le pays est un AUTRE pays, ou reste indéterminé, est
        rejeté (politique stricte : en cas de doute, on n'ingère pas).
        """
        slug = self._slug_of(href)

        # 1) Slug : le signal le plus fiable.
        if _BENIN_SLUG_RE.match(slug):
            return True
        m = _SLUG_COUNTRY_RE.match(slug)
        if m:
            # Le slug encode un pays explicite : ce n'est le Bénin que si le mot
            # est « benin ». Sinon (mali, ethiopia, sudan, djibouti…) -> rejet.
            return m.group(1) in BENIN_TOKENS

        # 2) Repli sur le titre « TYPE - Pays - … ».
        mt = _TITLE_COUNTRY_RE.match(title or "")
        if mt:
            country = mt.group(1).strip().lower()
            return any(country.startswith(tok) for tok in BENIN_TOKENS)

        # Pays indéterminé -> rejet (jamais d'ingestion « au doute »).
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
            if not self._notice_country_is_benin(href, title):
                continue
            full = urljoin(BASE, href)
            if full in seen:
                continue
            seen.add(full)
            slug = self._slug_of(href)
            if len(title) < 6:
                # Titre reconstitué depuis le slug si le lien est peu parlant.
                title = slug.replace("-", " ").strip().capitalize()
            # Date limite : au mieux depuis le texte de la ligne parente (petite).
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
                location="Bénin",
                deadline=deadline,
                source_url=full,
                dao_url=full,
                external_id=f"bad-bj-{abs(hash(full)) % (10**10)}",
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
                       f"?f%5B0%5D=country%3ABenin&page={page}")
                html = self.fetch_html(url)
                if not html:
                    blocked += 1
                    break  # source injoignable : on arrête ce type
                if self._is_blocked(html):
                    logger.warning("[BJ] BAD — page bloquée (Cloudflare) : %s",
                                   url)
                    blocked += 1
                    break
                pages_read += 1
                soup = BeautifulSoup(html, "lxml")
                # Fin de liste : plus aucun lien d'avis sur la page.
                notice_links = [a for a in soup.select("a[href*='/documents/']")
                                if self._is_notice_link(a.get("href", ""))]
                if not notice_links:
                    break
                for it in self._parse_listing(soup):
                    if it["source_url"] not in seen_urls:
                        seen_urls.add(it["source_url"])
                        items.append(it)

        if not items and blocked:
            logger.warning("[BJ] BAD — aucune donnée collectée (%s pages "
                           "inaccessibles). Portail probablement protégé.",
                           blocked)
        else:
            logger.info("[BJ] BAD — %s avis Bénin retenus (%s pages lues, "
                        "%s pages bloquées/injoignables).",
                        len(items), pages_read, blocked)
        return items


def build() -> BadScraper:
    return BadScraper()
