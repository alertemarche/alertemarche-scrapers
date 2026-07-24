"""Robot de collecte — Sénégal 🇸🇳 · SenOffre (portail national d'appels d'offres).

Contexte : le portail public officiel (marchespublics.sn) est fréquemment
injoignable hors du Sénégal (timeout TCP). SenOffre (https://senoffre.com) est
une plateforme sénégalaise qui agrège et republie les avis d'appel d'offres
PUBLICS et privés du pays (marchés de l'État, agences, ministères…), avec une
fiche par avis exposant l'objet, l'autorité contractante, la référence, la date
de publication et la date limite.

Méthode : la page « latest-jobs » (et la page d'accueil) listent les avis
récents sous forme de liens `/{slug}-{id}`. On visite chaque fiche pour en
extraire des MÉTADONNÉES propres (jamais le document lui-même) et on conserve le
lien vers la fiche officielle (source_url).
"""
import logging
import re
from urllib.parse import urljoin

from common.html_base import HtmlScraper

logger = logging.getLogger("scrapers.senegal.senoffre")

BASE = "https://senoffre.com"
LISTING_URLS = [
    "https://senoffre.com/latest-jobs",
    "https://senoffre.com/",
]
MAX_LISTING_PAGES = 5   # garde-fou pagination
MAX_DETAILS = 80        # garde-fou nombre de fiches visitées

# Lien de fiche d'avis : slug se terminant par un identifiant numérique.
OFFER_RE = re.compile(r"^https://senoffre\.com/([a-z0-9][a-z0-9\-]*-(\d+))/?$", re.I)

# Chrome requis (certaines réponses filtrent les user-agents non navigateurs).
CHROME_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Mots-clés indiquant un marché PUBLIC (par défaut on considère « public »).
_PRIVATE_CUES = re.compile(r"\b(soci[ée]t[ée] priv|entreprise priv|groupe priv)\b", re.I)


class SenOffreScraper(HtmlScraper):
    country = "SN"
    source_name = "SenOffre — Appels d'offres publics du Sénégal"
    tender_type = "public"
    method = "html"

    def __init__(self):
        super().__init__()
        self.session.headers.update({"User-Agent": CHROME_UA})

    # ---- Réseau rapide (fiches) ---------------------------------------
    def _soup_fast(self, url: str):
        """GET unique avec timeout court (les fiches SenOffre répondent vite)."""
        from bs4 import BeautifulSoup
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = resp.apparent_encoding or "utf-8"
            return BeautifulSoup(resp.text, "lxml")
        except Exception as exc:  # noqa: BLE001
            logger.warning("[SN] SenOffre fiche injoignable %s : %s", url, exc)
            return None

    # ---- Découverte des liens de fiches -------------------------------
    def _discover(self) -> list[tuple[str, str]]:
        """Retourne une liste (url_fiche, id) unique, dans l'ordre de découverte."""
        found: dict[str, str] = {}
        for listing in LISTING_URLS:
            for page in range(1, MAX_LISTING_PAGES + 1):
                url = listing if page == 1 else f"{listing}?page={page}"
                html = self.fetch_html(url)
                if not html:
                    break
                before = len(found)
                for m in re.finditer(r'href="(https://senoffre\.com/[^"]+)"', html):
                    om = OFFER_RE.match(m.group(1).rstrip("/") + "/")
                    if not om:
                        continue
                    offer_url, oid = f"{BASE}/{om.group(1)}", om.group(2)
                    found.setdefault(oid, offer_url)
                # Aucun NOUVEL avis sur cette page : pagination épuisée/statique.
                if len(found) == before:
                    break
        # Ordonne par identifiant décroissant (avis les plus récents d'abord).
        ordered = sorted(found.items(), key=lambda kv: int(kv[0]), reverse=True)
        return [(url, oid) for oid, url in ordered][:MAX_DETAILS]

    # ---- Extraction d'une fiche ---------------------------------------
    def _parse_detail(self, url: str, oid: str) -> dict | None:
        soup = self._soup_fast(url)
        if not soup:
            return None

        # Titre : balise og:title / <title> « OBJET, Localité ».
        raw_title = ""
        og = soup.find("meta", attrs={"property": "og:title"})
        if og and og.get("content"):
            raw_title = og["content"]
        elif soup.title:
            raw_title = soup.title.get_text(" ", strip=True)
        raw_title = self.clean(raw_title)

        location = None
        title = raw_title
        if "," in raw_title:
            # « OBJET, Dakar » -> objet + localité.
            head, _, tail = raw_title.rpartition(",")
            if head and len(tail.strip()) <= 40:
                title, location = self.clean(head), self.clean(tail)
        if not title or len(title) < 6:
            return None

        # Texte complet (meta description + corps) pour dates / institution.
        desc = ""
        md = soup.find("meta", attrs={"name": "description"})
        if md and md.get("content"):
            desc = md["content"]
        body = self.clean(soup.get_text(" ", strip=True))
        blob = f"{desc} {body}"

        # Institution / autorité contractante (best-effort).
        institution = None
        mi = re.search(r"(Minist[èe]re[^.,;]{3,80}|Direction\s+[^.,;]{3,80}|"
                       r"Agence\s+[^.,;]{3,80}|Soci[ée]t[ée]\s+[^.,;]{3,80})",
                       desc or body, re.I)
        if mi:
            institution = self.clean(mi.group(1))

        # Dates : la fiche affiche une date de publication ISO (AAAA-MM-JJ).
        publication_date = None
        mp = re.search(r"(20\d{2}-\d{2}-\d{2})", body)
        if mp:
            publication_date = mp.group(1)
        # Date limite : recherche contextuelle (« date limite de dépôt … »).
        deadline = self.deadline_from_text(blob)

        # Type d'offre (« Appel d'offre », « Manifestation d'intérêt »…).
        market_type = None
        mt = re.search(r"Type d'offre\s*:?\s*([A-Za-zÀ-ÿ'’ \-]{4,40})", body)
        if mt:
            market_type = self.clean(mt.group(1))

        tender_type = "prive" if _PRIVATE_CUES.search(blob) else "public"
        amount = self.amount_from_text(blob)

        return self.make_item(
            title=title[:255],
            institution=(institution or self.source_name)[:255],
            reference=oid,
            location=location,
            estimated_amount=amount,
            deadline=deadline,
            publication_date=publication_date,
            market_type=market_type,
            source_url=url,
            dao_url=url,
            external_id=f"senoffre-{oid}",
            tender_type=tender_type,
        )

    def collect(self) -> list[dict]:
        if not self.host_reachable(BASE):
            logger.warning("[SN] SenOffre injoignable — 0 item")
            return []
        offers = self._discover()
        if not offers:
            logger.warning("[SN] SenOffre — aucun avis découvert")
            return []
        items: list[dict] = []
        for url, oid in offers:
            mapped = self._parse_detail(url, oid)
            if mapped:
                items.append(mapped)
        logger.info("[SN] SenOffre : %d avis collectés", len(items))
        return items


def build() -> SenOffreScraper:
    return SenOffreScraper()
