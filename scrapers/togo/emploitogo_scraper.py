"""Robot de collecte — Togo 🇹🇬 · EmploiTogo.info (appels d'offres PRIVÉS/ONG).

Source : https://www.emploitogo.info/appeloffres/ — plateforme togolaise qui
agrège les appels d'offres et avis d'ONG, d'agences de développement, de
projets et d'institutions (OTR, SOS Villages d'Enfants, VSF-Suisse,
INADES-Formation, LuxDev, PNUD…). Beaucoup de ces opportunités ne figurent
PAS sur les portails publics officiels (DNCCP / ARMP).

Le site tourne sous WordPress : on interroge directement son API REST
(`/wp-json/wp/v2/posts`), catégorie « Appel d'offres & Communiqués »
(id 14421). La date limite est extraite du contenu de l'article ; à défaut,
l'avis reste considéré comme actif s'il a été publié récemment (le backend
applique une fenêtre de 90 jours).

Seules des métadonnées et le lien vers la fiche officielle sont collectés.
"""
import logging
import re
from html import unescape

logger = logging.getLogger("scrapers.togo.emploitogo")

from common.html_base import HtmlScraper  # noqa: E402


class EmploiTogoScraper(HtmlScraper):
    country = "TG"
    source_name = "EmploiTogo.info — Appels d'offres (Togo)"
    tender_type = "prive"

    API = "https://www.emploitogo.info/wp-json/wp/v2/posts"
    CATEGORY = 14421          # « Appel d'offres & Communiqués »
    MAX_PAGES = 5             # garde-fou (100 posts/page)

    # Titres à EXCLURE : résultats/attributions/communiqués (pas des opportunités).
    SKIP_RE = re.compile(
        r"(attribution|r[ée]sultat|proc[èe]s[- ]verbal|\bPV\b|"
        r"avis de report|rectificatif d.attribution|communiqu[ée] de presse|"
        r"concours|[ée]preuves? [ée]crites|report du d[ée]roulement)",
        re.IGNORECASE,
    )

    # Date limite dans le corps de l'annonce.
    DEADLINE_RE = re.compile(
        r"(?:date limite|d[ée]p[ôo]t des offres|cl[ôo]ture|au plus tard le|"
        r"remise des offres|date de cl[ôo]ture)[^0-9]{0,40}"
        r"([0-9]{1,2}[ /\-][0-9A-Za-zûéôàèùî]{2,9}[ /\-][0-9]{4})",
        re.IGNORECASE,
    )
    REF_RE = re.compile(
        r"((?:AAOO|AAOI|AAO|AMI|DAOO|DAO|DRP|AOO|AOI|DC)\s*[°oNn]{0,2}\s*[0-9][0-9A-Z/\-\.]{2,})",
        re.IGNORECASE,
    )

    @staticmethod
    def _clean(raw: str) -> str:
        txt = unescape(re.sub(r"<[^>]+>", " ", raw or ""))
        return re.sub(r"\s+", " ", txt).strip()

    def _fetch_api(self, page: int) -> list | None:
        params = {
            "categories": self.CATEGORY,
            "per_page": 100,
            "page": page,
            "orderby": "date",
            "order": "desc",
            "_fields": "id,date,link,title,content,excerpt",
        }
        for attempt in range(1, 4):
            try:
                resp = self.session.get(self.API, params=params, timeout=45)
                if resp.status_code == 400:
                    return []  # au-delà de la dernière page
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # noqa: BLE001
                logger.warning("[TG] EmploiTogo API p.%s échec %s/3 : %s", page, attempt, exc)
        return None

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()

        for page in range(1, self.MAX_PAGES + 1):
            posts = self._fetch_api(page)
            if posts is None:
                logger.warning("[TG] EmploiTogo injoignable — 0 item")
                break
            if not posts:
                break

            for post in posts:
                title = self._clean(post.get("title", {}).get("rendered", ""))
                if not title or len(title) < 8:
                    continue
                if self.SKIP_RE.search(title):
                    continue

                pid = post.get("id")
                external_id = f"emploitogo-{pid}" if pid else None
                key = external_id or title[:70]
                if key in seen:
                    continue
                seen.add(key)

                content = self._clean(post.get("content", {}).get("rendered", ""))
                deadline = None
                mdl = self.DEADLINE_RE.search(content)
                if mdl:
                    deadline = self.parse_fr_date(mdl.group(1))

                # Actif : deadline future/absente. Les avis sans deadline sont
                # gardés (le backend borne à 90 j via la date de publication).
                if not self.is_active(deadline):
                    continue

                mref = self.REF_RE.search(title) or self.REF_RE.search(content[:400])
                reference = self.clean(mref.group(1)) if mref else None
                pub = (post.get("date") or "")[:10] or None

                items.append(self.make_item(
                    title=title,
                    institution=self.source_name,
                    reference=reference,
                    location="Togo",
                    deadline=deadline,
                    publication_date=pub,
                    source_url=post.get("link") or self.API,
                    external_id=external_id,
                ))

            if len(posts) < 100:
                break

        logger.info("[TG] EmploiTogo : %s appels d'offres actifs collectés", len(items))
        return items


def build() -> EmploiTogoScraper:
    return EmploiTogoScraper()
