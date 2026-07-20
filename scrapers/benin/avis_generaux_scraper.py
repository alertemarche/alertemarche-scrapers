"""Robot de collecte — Bénin 🇧🇯 · Avis Généraux (plans annuels d'achat / AGPM).

Source : Portail des Marchés Publics du Bénin (https://www.marches-publics.bj),
géré par la DNCMP via SIGMAP. L'endpoint « avisgeneraux » expose les Avis
Généraux de Passation des Marchés (AGPM) : ce sont les plans annuels d'achat
publiés par chaque autorité contractante en début d'exercice.

    https://api.marches-publics.bj/v2/api/portail/avisgeneraux?page=..&size=..&annee=2026

Contrairement aux appels d'offres, un avis général n'a pas de délai de dépôt
propre : il couvre l'exercice complet. On fixe donc la deadline au 31 décembre
de l'année concernée pour matérialiser sa fin de validité.

Seules des MÉTADONNÉES sont collectées ; le lien vers le PDF officiel
(dao_url) est conservé, jamais le fichier lui-même.
"""
import logging
from datetime import date

from common.api_base import ApiScraper

logger = logging.getLogger("scrapers.benin.avis_generaux")

API_ROOT = "https://api.marches-publics.bj/v2/api/portail/avisgeneraux"
PORTAIL_LISTING = "https://www.marches-publics.bj/avis-generaux"
PAGE_SIZE = 50
MAX_PAGES = 20  # garde-fou (1000 avis max par passe)


class AvisGenerauxScraper(ApiScraper):
    country = "BJ"
    source_name = "Portail des Marchés Publics du Bénin (DNCMP) — Avis Généraux"
    tender_type = "avis_general"
    method = "api"

    def _get(self, d: dict, *keys, default=None):
        """Accès sûr à des clés potentiellement absentes/nulles."""
        for k in keys:
            if not isinstance(d, dict):
                return default
            d = d.get(k)
            if d is None:
                return default
        return d

    def _map(self, row: dict, annee: int) -> dict | None:
        # On ne retient que les avis actifs (etat == 1).
        etat = row.get("etat")
        if etat not in (1, "1", None):
            return None

        item_annee = row.get("annee") or annee
        try:
            item_annee = int(item_annee)
        except (TypeError, ValueError):
            item_annee = annee

        institution = self.fix_encoding(
            self._get(row, "autoriteContractante", "denomination")
        ) or self.source_name

        numero = row.get("numero")
        reference = str(numero) if numero not in (None, "") else None

        # Un avis général couvre l'exercice : deadline = 31/12 de l'année.
        deadline = f"{item_annee}-12-31"
        publication = row.get("datepublication")  # YYYY-MM-DD

        dao_url = row.get("fichier_Avis") or row.get("fichierAvis")
        source_url = dao_url or PORTAIL_LISTING

        external_id = f"ag-{row.get('id')}" if row.get("id") is not None else None

        if numero:
            title = f"Avis général {item_annee} n°{numero} — {institution}"
        else:
            title = f"Avis général {item_annee} — {institution}"

        return self.make_item(
            title=title,
            institution=institution,
            reference=reference,
            deadline=deadline,
            publication_date=publication,
            dao_url=dao_url,
            source_url=source_url,
            external_id=external_id,
        )

    def collect(self) -> list[dict]:
        annee = date.today().year
        items: list[dict] = []
        for page in range(0, MAX_PAGES):
            data = self.fetch_json(API_ROOT, params={
                "page": page, "size": PAGE_SIZE, "annee": annee,
            })
            if not data:
                break
            content = data.get("content") if isinstance(data, dict) else None
            if not content:
                break
            for row in content:
                mapped = self._map(row, annee)
                if mapped:
                    items.append(mapped)
            if data.get("last") is True or len(content) < PAGE_SIZE:
                break
        return items


def build() -> AvisGenerauxScraper:
    return AvisGenerauxScraper()
