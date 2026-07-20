"""Robot de collecte — Bénin 🇧🇯 · Plans de Passation des Marchés (PPM).

Source : Portail des Marchés Publics du Bénin (https://www.marches-publics.bj),
géré par la DNCMP via SIGMAP. Le portail expose les Plans de Passation des
Marchés (PPM) autorité par autorité :

    1) Liste des autorités disposant d'un plan :
       https://api.marches-publics.bj/v2/api/portail/plandepassations/autorites
           ?page=..&size=..&annee=2026

    2) Réalisations (lignes du plan) d'une autorité donnée :
       https://api.marches-publics.bj/v2/api/portail/plandepassations/{sigle}-{id}
           ?page=..&size=..&annee=2026

Chaque « réalisation » est une opération planifiée (fourniture, travaux,
services…) avec un montant estimé et des dates prévisionnelles. On ne conserve
que les opérations dont l'échéance n'est pas encore passée.

Seules des MÉTADONNÉES sont collectées ; aucun fichier n'est stocké.
"""
import logging
from datetime import date

from common.api_base import ApiScraper

logger = logging.getLogger("scrapers.benin.plan_passation")

API_AUTORITES = "https://api.marches-publics.bj/v2/api/portail/plandepassations/autorites"
API_PLAN = "https://api.marches-publics.bj/v2/api/portail/plandepassations/{slug}"
PORTAIL_PLAN = "https://www.marches-publics.bj/plan-de-passation/{slug}"
PAGE_SIZE = 50
MAX_AUTORITES = 20   # première passe : on limite pour éviter les timeouts
MAX_PAGES = 20       # garde-fou pagination (autorités et réalisations)


class PlanPassationScraper(ApiScraper):
    country = "BJ"
    source_name = "Portail des Marchés Publics du Bénin (DNCMP) — Plans de Passation"
    tender_type = "plan_passation"
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

    # ---- Étape 1 : liste des autorités --------------------------------
    def _fetch_autorites(self, annee: int) -> list[dict]:
        autorites: list[dict] = []
        for page in range(0, MAX_PAGES):
            data = self.fetch_json(API_AUTORITES, params={
                "page": page, "size": PAGE_SIZE, "annee": annee,
            })
            if not data:
                break
            content = data.get("content") if isinstance(data, dict) else None
            if not content:
                break
            autorites.extend(content)
            if data.get("last") is True or len(content) < PAGE_SIZE:
                break
            if len(autorites) >= MAX_AUTORITES:
                break
        return autorites[:MAX_AUTORITES]

    # ---- Étape 2 : réalisations d'une autorité ------------------------
    def _fetch_realisations(self, slug: str, annee: int) -> list[dict]:
        realisations: list[dict] = []
        for page in range(0, MAX_PAGES):
            data = self.fetch_json(API_PLAN.format(slug=slug), params={
                "page": page, "size": PAGE_SIZE, "annee": annee,
            })
            if not isinstance(data, dict):
                break
            block = data.get("realisations") or {}
            content = block.get("content") if isinstance(block, dict) else None
            if not content:
                break
            for row in content:
                # On rattache la dénomination de l'autorité si présente.
                row["_autorite"] = data.get("autorite") or {}
                realisations.append(row)
            if block.get("last") is True or len(content) < PAGE_SIZE:
                break
        return realisations

    def _map(self, row: dict, slug: str, today: date) -> dict | None:
        libelle = self.fix_encoding(row.get("libelle"))
        if not libelle or len(libelle) < 4:
            return None

        # Échéance : ouverture des plis > lancement > aucune.
        deadline = row.get("dateouvertureplis") or row.get("datelancement") or None

        # On ignore les opérations dont l'échéance est déjà passée.
        if deadline:
            try:
                if date.fromisoformat(str(deadline)[:10]) < today:
                    return None
            except ValueError:
                pass  # date non parsable : on garde l'opération par prudence

        institution = self.fix_encoding(
            self._get(row, "_autorite", "denomination")
        ) or self.source_name

        reference = row.get("reference") or None

        # Montant estimé (budget prévisionnel officiel du PPM). On renvoie un
        # entier propre en FCFA — surtout PAS "66939091.0" : le point décimal
        # serait supprimé côté frontend et gonflerait le montant d'un facteur 10.
        montant = row.get("montantEstime")
        estimated_amount = None
        if montant not in (None, ""):
            try:
                estimated_amount = str(int(round(float(montant))))
            except (TypeError, ValueError):
                estimated_amount = None

        market_type = self.fix_encoding(self._get(row, "typeMarche", "libelle"))

        publication = row.get("datelancement")  # YYYY-MM-DD

        rid = row.get("idrealisations") or row.get("id_plan")
        external_id = f"pp-{rid}" if rid is not None else None

        source_url = PORTAIL_PLAN.format(slug=slug)

        return self.make_item(
            title=libelle,
            institution=institution,
            reference=reference,
            estimated_amount=estimated_amount,
            market_type=market_type,
            deadline=deadline,
            publication_date=publication,
            source_url=source_url,
            external_id=external_id,
        )

    def collect(self) -> list[dict]:
        annee = date.today().year
        today = date.today()
        items: list[dict] = []

        autorites = self._fetch_autorites(annee)
        logger.info("[BJ] Plans de passation — %s autorités à traiter", len(autorites))

        for aut in autorites:
            sigle = aut.get("sigle")
            aid = aut.get("id")
            if not sigle or aid is None:
                continue
            slug = f"{sigle}-{aid}"
            realisations = self._fetch_realisations(slug, annee)
            for row in realisations:
                mapped = self._map(row, slug, today)
                if mapped:
                    items.append(mapped)
        return items


def build() -> PlanPassationScraper:
    return PlanPassationScraper()
