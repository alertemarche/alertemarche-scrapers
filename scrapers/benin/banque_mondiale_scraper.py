"""Robot de collecte — Bénin 🇧🇯 · Banque Mondiale (World Bank).

Source : API officielle de recherche des avis de passation de marchés de la
Banque Mondiale (« Procurement Notices »). Elle expose un endpoint JSON propre,
filtrable par pays du projet (`project_ctry_name`) :

    https://search.worldbank.org/api/v2/procnotices?format=json&project_ctry_name=Benin

Ces marchés (financés par la Banque Mondiale mais passés par des maîtres
d'ouvrage/agences) relèvent des appels d'offres « privés » au sens de la
plateforme (acheteur non étatique / bailleur international).

On exclut les avis d'attribution (« Contract Award ») pour ne conserver que
les OPPORTUNITÉS ouvertes (manifestations d'intérêt, appels d'offres, avis
généraux). Seules des métadonnées et le lien vers la fiche officielle sont
collectés — jamais le document.
"""
import logging
from datetime import datetime

from common.api_base import ApiScraper

logger = logging.getLogger("scrapers.benin.banque_mondiale")

API_ROOT = "https://search.worldbank.org/api/v2/procnotices"
DETAIL_URL = "https://projects.worldbank.org/fr/projects-operations/procurement-detail/{id}"
PAGE_SIZE = 100
MAX_PAGES = 30  # garde-fou (3000 avis max)

# Types d'avis à IGNORER : ce sont des résultats, pas des opportunités.
SKIP_TYPES = {"contract award"}


class BanqueMondialeScraper(ApiScraper):
    country = "BJ"
    source_name = "Banque Mondiale"
    tender_type = "prive"
    method = "api"

    # Nom du pays tel qu'attendu par l'API World Bank (`project_ctry_name`).
    # Surchargé par les déclinaisons Côte d'Ivoire / Togo.
    wb_country_name = "Benin"

    def __init__(self):
        super().__init__()
        self.session.headers.update({
            "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
            "Accept": "application/json",
        })

    @staticmethod
    def _iso(raw: str | None) -> str | None:
        """« 2026-07-24T00:00:00Z » ou « 17-Jul-2026 » -> « 2026-07-24 »."""
        if not raw:
            return None
        raw = str(raw).strip()
        # Format ISO renvoyé par l'API
        if "T" in raw or (len(raw) >= 10 and raw[4] == "-"):
            return raw[:10]
        # Format « 17-Jul-2026 »
        try:
            return datetime.strptime(raw[:11], "%d-%b-%Y").strftime("%Y-%m-%d")
        except ValueError:
            return None

    def _map(self, row: dict) -> dict | None:
        notice_type = (row.get("notice_type") or "").strip()
        if notice_type.lower() in SKIP_TYPES:
            return None

        title = self.clean_txt(row.get("bid_description") or row.get("project_name"))
        if not title or len(title) < 6:
            return None

        notice_id = row.get("id")
        reference = row.get("bid_reference_no") or row.get("project_id")
        project = self.clean_txt(row.get("project_name"))
        deadline = self._iso(row.get("submission_deadline_date") or row.get("submission_date"))
        publication = self._iso(row.get("noticedate"))

        # On ne conserve que les OPPORTUNITÉS encore pertinentes :
        #   - échéance de dépôt future (avis ouvert), OU
        #   - pas d'échéance mais publication de moins de 120 jours.
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if deadline:
            if deadline < today:
                return None
        elif publication:
            try:
                age = (datetime.utcnow() - datetime.strptime(publication, "%Y-%m-%d")).days
                if age > 120:
                    return None
            except ValueError:
                pass

        # Institution : agence contractante si dispo, sinon le projet, sinon la source.
        institution = (self.clean_txt(row.get("contact_organization"))
                       or project or self.source_name)

        source_url = DETAIL_URL.format(id=notice_id) if notice_id else API_ROOT

        return self.make_item(
            title=title,
            institution=institution[:255],
            reference=reference or None,
            deadline=deadline,
            publication_date=publication,
            market_type=notice_type or None,
            source_url=source_url,
            dao_url=source_url,
            external_id=f"wb-{notice_id}" if notice_id else None,
            tender_type="prive",
        )

    @staticmethod
    def clean_txt(text) -> str:
        return " ".join(str(text or "").split())

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        for page in range(0, MAX_PAGES):
            data = self.fetch_json(API_ROOT, params={
                "format": "json",
                "rows": PAGE_SIZE,
                "os": page * PAGE_SIZE,
                "project_ctry_name": self.wb_country_name,
            })
            if not data:
                break
            notices = data.get("procnotices") if isinstance(data, dict) else None
            if not notices:
                break
            new_on_page = 0
            for row in notices:
                nid = str(row.get("id") or "")
                if nid and nid in seen:
                    continue
                if nid:
                    seen.add(nid)
                mapped = self._map(row)
                if mapped:
                    items.append(mapped)
                    new_on_page += 1
            if len(notices) < PAGE_SIZE:
                break
        return items


def build() -> BanqueMondialeScraper:
    return BanqueMondialeScraper()
