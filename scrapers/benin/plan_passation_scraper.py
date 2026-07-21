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
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from urllib.parse import quote

from common.api_base import ApiScraper
from common import procedures

logger = logging.getLogger("scrapers.benin.plan_passation")

API_AUTORITES = "https://api.marches-publics.bj/v2/api/portail/plandepassations/autorites"
API_PLAN = "https://api.marches-publics.bj/v2/api/portail/plandepassations/{slug}"
PORTAIL_PLAN = "https://www.marches-publics.bj/plan-de-passation/{slug}"
PAGE_SIZE = 50
# Nombre maximum d'autorités traitées. 0 (ou variable d'env <=0) = toutes les
# autorités du plan de passation de l'année en cours (~279 en 2026). On couvre
# ainsi l'intégralité des marchés planifiés/actifs, comme le fait la concurrence.
MAX_AUTORITES = int(os.getenv("PPM_MAX_AUTORITES", "0"))
# Nombre de requêtes autorités traitées en parallèle (I/O réseau).
MAX_WORKERS = int(os.getenv("PPM_MAX_WORKERS", "8"))
MAX_PAGES = 40       # garde-fou pagination (autorités et réalisations)


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
            if MAX_AUTORITES > 0 and len(autorites) >= MAX_AUTORITES:
                break
        return autorites[:MAX_AUTORITES] if MAX_AUTORITES > 0 else autorites

    # ---- Étape 2 : réalisations d'une autorité ------------------------
    def _fetch_realisations(self, slug: str, annee: int) -> list[dict]:
        realisations: list[dict] = []
        # Certains sigles d'autorités contiennent un « / » (ex. « PRODIJ/Aviculture »)
        # qui casserait le chemin de l'URL : on encode le slug.
        slug_enc = quote(slug, safe="-")
        for page in range(0, MAX_PAGES):
            data = self.fetch_json(API_PLAN.format(slug=slug_enc), params={
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

        # Type de procédure de passation : on lit le code officiel du mode de
        # passation (DC, DRP, AOO, AOI, AMI…) et on le rattache à l'une des
        # sous-catégories « Appels d'offres publics ». Repli sur le libellé si
        # le code est absent.
        mode_code = self._get(row, "modepassation_ID", "code")
        procedure_type = procedures.from_code(mode_code)
        if procedure_type is None:
            mode_libelle = self._get(row, "modepassation_ID", "libelle")
            procedure_type = procedures.from_text(mode_libelle) or procedures.from_text(libelle)

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
            procedure_type=procedure_type,
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
        logger.info("[BJ] Plans de passation — %s autorités à traiter (workers=%s)",
                    len(autorites), MAX_WORKERS)

        # Slugs valides.
        slugs = [
            f"{aut['sigle']}-{aut['id']}"
            for aut in autorites
            if aut.get("sigle") and aut.get("id") is not None
        ]

        def _process(slug: str) -> list[dict]:
            out: list[dict] = []
            try:
                for row in self._fetch_realisations(slug, annee):
                    mapped = self._map(row, slug, today)
                    if mapped:
                        out.append(mapped)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[BJ] Plan de passation %s : %s", slug, exc)
            return out

        # Collecte parallèle (I/O réseau) sur l'ensemble des autorités.
        with ThreadPoolExecutor(max_workers=max(1, MAX_WORKERS)) as pool:
            futures = {pool.submit(_process, slug): slug for slug in slugs}
            for fut in as_completed(futures):
                items.extend(fut.result())

        logger.info("[BJ] Plans de passation — %s opportunités actives/planifiées", len(items))
        return items


def build() -> PlanPassationScraper:
    return PlanPassationScraper()
