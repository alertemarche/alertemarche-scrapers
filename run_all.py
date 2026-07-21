"""Orchestrateur de collecte AlerteMarché.

Exécute successivement les robots des trois pays, déduplique localement, puis
envoie les opportunités à l'API backend et journalise chaque exécution.

Usage :
    python run_all.py            # une passe de collecte
    python run_all.py --country BJ   # un seul pays
"""
import argparse
import logging
import sys

from common import config
from common.dedup import deduplicate
from common.sender import send_log, send_tenders
from scrapers.benin.avis_generaux_scraper import build as build_avis_generaux
from scrapers.benin.bceao_scraper import build as build_bceao
from scrapers.benin.cdc_scraper import build as build_cdc
from scrapers.benin.mca_scraper import build as build_mca
from scrapers.benin.plan_passation_scraper import build as build_plan_passation
from scrapers.benin.pnud_scraper import build as build_pnud
from scrapers.benin.private_scraper import build as build_benin_private
from scrapers.benin.sbee_scraper import build as build_sbee
from scrapers.benin.scraper import build as build_benin
from scrapers.benin.simau_scraper import build as build_simau
from scrapers.benin.sirat_scraper import build as build_sirat
from scrapers.benin.unicef_scraper import build as build_unicef
from scrapers.cote_ivoire.scraper import build as build_ci
from scrapers.togo.scraper import build as build_togo

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scrapers.run")

# Chaque pays possède une liste de ROBOTS INDÉPENDANTS (un par source).
# Bénin : marchés publics (portail DNCMP) + marchés privés (UNGM/Nations Unies).
BUILDERS = {
    "BJ": [
        build_benin, build_benin_private, build_avis_generaux, build_plan_passation,
        # Sources publiques additionnelles (institutions d'État béninoises).
        build_sbee, build_sirat, build_simau,
        # Sources privées / institutionnelles.
        build_cdc, build_bceao, build_mca, build_pnud, build_unicef,
    ],
    "TG": [build_togo],
    "CI": [build_ci],
}


def run_robot(code: str, builder) -> dict:
    """Exécute un robot (une source) et journalise son exécution séparément."""
    scraper = builder()
    result = {"country": code, "source": scraper.source_name,
              "collected": 0, "new": 0, "status": "success"}
    try:
        raw = scraper.run()
        items = deduplicate(raw)
        result["collected"] = len(items)
        resp = send_tenders(items) if items else {"received": 0, "new": 0}
        result["new"] = resp.get("new", 0)
        send_log(code, scraper.source_name, "success",
                 items_collected=len(items), items_new=result["new"],
                 message=f"{len(items)} opportunités uniques collectées.")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Échec de collecte pour %s / %s : %s", code, scraper.source_name, exc)
        result["status"] = "failure"
        send_log(code, scraper.source_name, "failure", message=str(exc))
    return result


def run_country(code: str) -> list[dict]:
    """Exécute tous les robots (sources) d'un pays."""
    results = []
    for builder in BUILDERS[code]:
        results.append(run_robot(code, builder))
    return results


def run_all(country: str | None = None) -> list[dict]:
    codes = [country] if country else list(BUILDERS.keys())
    results = []
    for code in codes:
        if code not in BUILDERS:
            logger.error("Pays inconnu : %s", code)
            continue
        logger.info("=== Collecte %s ===", code)
        results.extend(run_country(code))
    logger.info("Résumé : %s", results)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Collecte des appels d'offres AlerteMarché")
    parser.add_argument("--country", choices=list(BUILDERS.keys()), help="Limiter à un pays")
    args = parser.parse_args()

    if not config.API_TOKEN:
        logger.warning("SCRAPERS_API_TOKEN absent : les envois seront refusés par le backend.")

    results = run_all(args.country)
    failed = [r for r in results if r["status"] == "failure"]
    return 1 if failed and len(failed) == len(results) else 0


if __name__ == "__main__":
    sys.exit(main())
