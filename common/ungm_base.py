"""Robot de collecte — UNGM (United Nations Global Marketplace).

UNGM (https://www.ungm.org) est le portail officiel unique des marchés du
système des Nations Unies : il agrège les avis de 40+ agences (PNUD, UNICEF,
UNFPA, PAM, OMS, FAO…) ainsi que d'organismes internationaux. Ces acheteurs
ne sont pas des administrations nationales : leurs marchés relèvent donc des
appels d'offres « privés » (organismes internationaux, ONG, coopération).

Méthode de collecte : le portail expose un endpoint de recherche
(`POST /Public/Notice/Search`) qui renvoie un fragment HTML de résultats,
filtrable par pays bénéficiaire. On extrait uniquement des MÉTADONNÉES et le
lien vers la fiche officielle (source_url) ; jamais le document lui-même.

Cette base est paramétrable par pays : il suffit de fournir l'identifiant UNGM
du pays bénéficiaire (`ungm_country_id`) pour l'instancier pour le Bénin, le
Togo ou la Côte d'Ivoire.
"""
import logging
from datetime import datetime

from bs4 import BeautifulSoup

from .api_base import ApiScraper

logger = logging.getLogger("scrapers.ungm")

SEARCH_URL = "https://www.ungm.org/Public/Notice/Search"
NOTICE_URL = "https://www.ungm.org/Public/Notice/{id}"
PAGE_SIZE = 50
MAX_PAGES = 10  # garde-fou

# Identifiants UNGM des pays bénéficiaires (capturés depuis le portail).
# BJ confirmé ; TG/CI à confirmer avant activation (extension future).
UNGM_COUNTRY_IDS = {
    "BJ": "2314",  # Bénin — confirmé
}


class UngmScraper(ApiScraper):
    """Base commune pour la collecte des avis UNGM d'un pays donné."""

    source_name = "UNGM — Nations Unies (organismes internationaux)"
    tender_type = "prive"
    method = "api"  # endpoint de recherche structuré

    ungm_country_id: str = ""

    def __init__(self):
        super().__init__()
        # UNGM exige un User-Agent réaliste + un Referer ; sinon la recherche
        # renvoie une page d'erreur.
        self.session.headers.update({
            "Accept": "text/html, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/json",
            "Referer": "https://www.ungm.org/Public/Notice",
            "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
        })

    # ---- Réseau -------------------------------------------------------
    def _search_page(self, page: int) -> str | None:
        """POST de recherche pour une page. Retourne le fragment HTML ou None."""
        payload = {
            "PageIndex": page,
            "PageSize": PAGE_SIZE,
            "Title": "", "Description": "", "Reference": "",
            "PublishedFrom": "", "PublishedTo": "",
            "DeadlineFrom": "", "DeadlineTo": "",
            "Countries": [self.ungm_country_id],
            "Agencies": [], "UNSPSCs": [], "NoticeTypes": [],
            "SortField": "Deadline", "SortAscending": True,
            "IsActive": True, "TypeOfCompetitions": [],
        }
        for attempt in range(1, 4):
            try:
                resp = self.session.post(SEARCH_URL, json=payload, timeout=45)
                resp.raise_for_status()
                return resp.text
            except Exception as exc:  # noqa: BLE001
                logger.warning("[%s] UNGM recherche p.%s échec %s/3 : %s",
                               self.country, page, attempt, exc)
        return None

    # ---- Parsing ------------------------------------------------------
    @staticmethod
    def _txt(node) -> str:
        return " ".join(node.get_text(" ", strip=True).split()) if node else ""

    @staticmethod
    def _parse_deadline(raw: str) -> str | None:
        """« 21-Jul-2026 15:00 (GMT 1.00) » -> « 2026-07-21 »."""
        if not raw:
            return None
        token = raw.strip().split()[0]  # 21-Jul-2026
        try:
            return datetime.strptime(token, "%d-%b-%Y").strftime("%Y-%m-%d")
        except ValueError:
            return None

    def _map_row(self, row) -> dict | None:
        notice_id = row.get("data-noticeid")
        if not notice_id:
            return None

        title = self._txt(row.select_one(".resultTitle .ungm-title") or
                          row.select_one(".resultTitle"))
        # Retire le libellé parasite « Open in a new window ».
        title = title.replace("Open in a new window", "").strip()
        if not title or len(title) < 6:
            return None

        deadline_raw = self._txt(row.select_one(".resultInfo1.deadline"))
        agency = self._txt(row.select_one(".resultAgency"))
        # Cellules restantes : [published, type, reference, country].
        cells = row.select(".tableCell")
        published = self._txt(cells[3]) if len(cells) > 3 else ""
        market_type = self._txt(cells[5]) if len(cells) > 5 else ""
        reference = self._txt(cells[6]) if len(cells) > 6 else ""

        institution = agency or "Organisme international (Nations Unies)"
        source_url = NOTICE_URL.format(id=notice_id)

        return self.make_item(
            title=title,
            institution=institution,
            reference=reference or None,
            deadline=self._parse_deadline(deadline_raw),
            publication_date=self._parse_deadline(published),
            market_type=market_type or None,
            source_url=source_url,
            dao_url=source_url,  # la fiche officielle porte les documents
            external_id=f"ungm-{notice_id}",
            tender_type="prive",
        )

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        for page in range(0, MAX_PAGES):
            html = self._search_page(page)
            if not html:
                break
            soup = BeautifulSoup(html, "lxml")
            rows = soup.select("[data-noticeid]")
            new_on_page = 0
            for row in rows:
                nid = row.get("data-noticeid")
                if not nid or nid in seen:
                    continue
                seen.add(nid)
                mapped = self._map_row(row)
                if mapped:
                    items.append(mapped)
                    new_on_page += 1
            # Plus aucune nouvelle notice : fin de pagination.
            if new_on_page == 0:
                break
        return items
