"""Robot de collecte — Togo 🇹🇬 · DNCCP (marchés PUBLICS).

Source : Direction Nationale de Contrôle de la Commande Publique du Togo —
https://dnccp.gouv.tg/ (portail OFFICIEL des marchés publics togolais).

Le site tourne sous WordPress et expose son API REST (`/wp-json/wp/v2/`). On
interroge directement cette API — bien plus robuste et complète que le scraping
HTML paginé — pour collecter TOUTES les opportunités ouvertes réparties dans
les différentes catégories d'avis :

  • Avis d'appel d'offres (AAO / AAOO / AAOI)
  • Fournitures / Travaux / Services courants (F/T/SC)
  • Prestations intellectuelles (AMI, sélection de consultants)
  • Délégations de service public (DSP)
  • Demandes de cotation / de renseignement et de prix

Les avis d'ATTRIBUTION (résultats, PV, avis d'attribution provisoire/définitive)
ne sont PAS des opportunités : ils sont filtrés. Seules des métadonnées et le
lien vers la fiche officielle sont collectés — jamais le document lui-même.
"""
import logging
import re
from html import unescape

logger = logging.getLogger("scrapers.togo.dnccp")

from common.html_base import HtmlScraper  # noqa: E402


class DnccpTgScraper(HtmlScraper):
    country = "TG"
    source_name = "DNCCP Togo — Direction Nationale de Contrôle de la Commande Publique"
    tender_type = "public"

    API = "https://dnccp.gouv.tg/dnccp/wp-json/wp/v2/posts"

    # Catégories WordPress correspondant à des OPPORTUNITÉS (soumissionnables).
    # (Exclut : attributions, extraits JMP, listes de marchés, textes
    # réglementaires, communiqués, statistiques…)
    OPPORTUNITY_CATEGORIES = [
        45,                     # Avis d'appel d'offres
        108, 113, 184,          # Fournitures / Travaux / Services courants
        110, 112, 182,          # Prestations intellectuelles
        114, 106, 109, 88,      # Délégations de service public (DSP)
        180, 181, 185,          # Travaux / Services courants / Demande de cotation
    ]
    MAX_PAGES = 10  # garde-fou (100 posts/page)

    # Titres à EXCLURE : ce sont des résultats/attributions, pas des appels.
    SKIP_RE = re.compile(
        r"(attribution|r[ée]sultat|proc[èe]s[- ]verbal|\bPV\b|communiqu[ée]|"
        r"avis de report|rectificatif d.attribution)",
        re.IGNORECASE,
    )

    # Référence d'avis dans le titre.
    REF_RE = re.compile(
        r"((?:AAOO|AAOI|AAO|AMI|DAOO|DAO|DRP|DRPR|AOO|AOI|DC)\s*[°oNn]{0,2}\s*[0-9][0-9A-Z/\-\.]{2,})",
        re.IGNORECASE,
    )

    @staticmethod
    def _clean_title(raw: str) -> str:
        txt = unescape(re.sub(r"<[^>]+>", "", raw or "")).strip()
        txt = re.sub(r"\s+", " ", txt)
        # Retire un préfixe de catégorie éventuel (« F/T/SC », « DSP »…).
        txt = re.sub(r"^(?:F/T/SC|F/T|T/SC|DSP|PI)\s+", "", txt).strip()
        return txt

    def _fetch_api(self, page: int) -> list | None:
        params = {
            "categories": ",".join(str(c) for c in self.OPPORTUNITY_CATEGORIES),
            "per_page": 100,
            "page": page,
            "orderby": "date",
            "order": "desc",
        }
        for attempt in range(1, 4):
            try:
                resp = self.session.get(self.API, params=params, timeout=45)
                if resp.status_code == 400:
                    # Au-delà de la dernière page WP renvoie 400 : fin normale.
                    return []
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # noqa: BLE001
                logger.warning("[TG] DNCCP API p.%s échec %s/3 : %s", page, attempt, exc)
        return None

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()

        for page in range(1, self.MAX_PAGES + 1):
            posts = self._fetch_api(page)
            if posts is None:
                # API injoignable : repli sur le scraping HTML historique.
                if page == 1:
                    logger.warning("[TG] DNCCP API injoignable — repli HTML")
                    return self._collect_html()
                break
            if not posts:
                break

            for post in posts:
                title = self._clean_title(post.get("title", {}).get("rendered", ""))
                if not title or len(title) < 8:
                    continue
                if self.SKIP_RE.search(title):
                    continue  # avis d'attribution / résultat : pas une opportunité

                source_url = post.get("link") or self.API
                external_id = f"dnccp-tg-{post.get('id')}" if post.get("id") else None
                key = external_id or title[:70]
                if key in seen:
                    continue
                seen.add(key)

                mref = self.REF_RE.search(title)
                reference = self.clean(mref.group(1)) if mref else None
                pub = (post.get("date") or "")[:10] or None

                items.append(self.make_item(
                    title=title,
                    institution=self.source_name,
                    reference=reference,
                    location="Togo",
                    publication_date=pub,
                    source_url=source_url,
                    external_id=external_id,
                ))

            if len(posts) < 100:
                break

        return items

    # ---- Repli HTML (si l'API REST venait à être désactivée) ----------
    def _collect_html(self) -> list[dict]:
        from urllib.parse import urljoin
        base = "https://dnccp.gouv.tg/dnccp/category/avis-d-appel-d-offres/"
        items: list[dict] = []
        seen: set[str] = set()
        for page in range(1, 12):
            url = base if page == 1 else f"{base}page/{page}/"
            soup = self.soup(url)
            if not soup:
                break
            arts = soup.select("article")
            if not arts:
                break
            new = 0
            for art in arts:
                el = (art.select_one("h2.entry-title a") or art.select_one("h2 a")
                      or art.select_one(".entry-title a"))
                if not el:
                    continue
                title = self._clean_title(el.get_text())
                if not title or len(title) < 8 or self.SKIP_RE.search(title):
                    continue
                href = el.get("href")
                su = urljoin(base, href) if href else base
                mid = re.search(r"/([a-z0-9\-]+)/?$", su)
                eid = f"dnccp-tg-{mid.group(1)[:70]}" if mid else None
                if (eid or title[:70]) in seen:
                    continue
                seen.add(eid or title[:70])
                mref = self.REF_RE.search(title)
                items.append(self.make_item(
                    title=title, institution=self.source_name,
                    reference=self.clean(mref.group(1)) if mref else None,
                    location="Togo", source_url=su, external_id=eid,
                ))
                new += 1
            if new == 0:
                break
        return items


def build() -> DnccpTgScraper:
    return DnccpTgScraper()
