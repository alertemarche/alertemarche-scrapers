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
from scrapers.benin.afd_scraper import build as build_afd
from scrapers.benin.ambassade_france_scraper import build as build_ambassade_france
from scrapers.benin.avis_generaux_scraper import build as build_avis_generaux
from scrapers.benin.bad_scraper import build as build_bad
from scrapers.benin.banque_mondiale_scraper import build as build_banque_mondiale
from scrapers.benin.banques_assurances_scraper import build as build_banques_assurances
from scrapers.benin.bceao_scraper import build as build_bceao
from scrapers.benin.cdc_scraper import build as build_cdc
from scrapers.benin.mca_scraper import build as build_mca
from scrapers.benin.plan_international_scraper import build as build_plan_international
from scrapers.benin.plan_passation_scraper import build as build_plan_passation
from scrapers.benin.pnud_scraper import build as build_pnud
from scrapers.benin.private_scraper import build as build_benin_private
from scrapers.benin.sbee_scraper import build as build_sbee
from scrapers.benin.scraper import build as build_benin
from scrapers.benin.simau_scraper import build as build_simau
from scrapers.benin.sirat_scraper import build as build_sirat
from scrapers.benin.ue_delegation_scraper import build as build_ue_delegation
from scrapers.benin.unicef_scraper import build as build_unicef
from scrapers.benin.gouv_scraper import build as build_gouv_bj
from scrapers.benin.armp_scraper import build as build_armp_bj
from scrapers.cote_ivoire.scraper import build as build_ci
from scrapers.cote_ivoire.arcop_scraper import build as build_ci_arcop
from scrapers.cote_ivoire.marchespublics_scraper import build as build_ci_marchespublics
from scrapers.cote_ivoire.ungm_scraper import build as build_ci_ungm
from scrapers.cote_ivoire.banque_mondiale_scraper import build as build_ci_banque_mondiale
from scrapers.cote_ivoire.afd_scraper import build as build_ci_afd
from scrapers.cote_ivoire.educarriere_scraper import build as build_ci_educarriere
from scrapers.cote_ivoire.ageroute_scraper import build as build_ci_ageroute
from scrapers.cote_ivoire.fer_scraper import build as build_ci_fer
from scrapers.cote_ivoire.pnud_scraper import build as build_ci_pnud
from scrapers.cote_ivoire.bad_scraper import build as build_ci_bad
from scrapers.togo.scraper import build as build_togo
from scrapers.togo.arcop_scraper import build as build_tg_arcop
from scrapers.togo.cnct_scraper import build as build_tg_cnct
from scrapers.togo.marchespublics_scraper import build as build_tg_marchespublics
from scrapers.togo.otr_scraper import build as build_tg_otr
from scrapers.togo.port_scraper import build as build_tg_port
from scrapers.togo.dnccp_scraper import build as build_tg_dnccp
from scrapers.togo.ungm_scraper import build as build_tg_ungm
from scrapers.togo.banque_mondiale_scraper import build as build_tg_banque_mondiale
from scrapers.togo.afd_scraper import build as build_tg_afd
from scrapers.togo.emploitogo_scraper import build as build_tg_emploitogo
from scrapers.togo.pnud_scraper import build as build_tg_pnud
from scrapers.togo.ue_delegation_scraper import build as build_tg_ue_delegation
from scrapers.togo.bad_scraper import build as build_tg_bad
from scrapers.togo.service_public_scraper import build as build_tg_service_public
from scrapers.togo.dnccp_new_scraper import build as build_tg_dnccp_new
from scrapers.senegal.ungm_scraper import build as build_sn_ungm
from scrapers.senegal.marchespublics_scraper import build as build_sn_marchespublics
from scrapers.senegal.senelec_scraper import build as build_sn_senelec
from scrapers.senegal.pad_scraper import build as build_sn_pad
from scrapers.senegal.ageroute_scraper import build as build_sn_ageroute
from scrapers.senegal.artp_scraper import build as build_sn_artp
from scrapers.senegal.banque_mondiale_scraper import build as build_sn_banque_mondiale
from scrapers.senegal.pnud_scraper import build as build_sn_pnud
from scrapers.senegal.bad_scraper import build as build_sn_bad
from scrapers.senegal.ue_delegation_scraper import build as build_sn_ue_delegation
from scrapers.senegal.boad_scraper import build as build_sn_boad
from scrapers.senegal.senoffre_scraper import build as build_sn_senoffre
from scrapers.burkina_faso.scraper import build as build_bf
from scrapers.burkina_faso.plan_passation_scraper import build as build_bf_ppm
from scrapers.burkina_faso.ungm_scraper import build as build_bf_ungm
from scrapers.burkina_faso.banque_mondiale_scraper import build as build_bf_banque_mondiale
from scrapers.burkina_faso.afd_scraper import build as build_bf_afd
from scrapers.burkina_faso.pnud_scraper import build as build_bf_pnud
from scrapers.burkina_faso.bad_scraper import build as build_bf_bad
from scrapers.burkina_faso.boad_scraper import build as build_bf_boad
from scrapers.burkina_faso.ue_delegation_scraper import build as build_bf_ue_delegation

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
        # Sources gouvernementales centralisées (NOUVEAUX - Phase 1).
        build_gouv_bj, build_armp_bj,
        # Sources publiques additionnelles (institutions d'État béninoises).
        build_sbee, build_sirat, build_simau,
        # Sources privées / institutionnelles.
        build_cdc, build_bceao, build_mca, build_pnud, build_unicef,
        # Bailleurs internationaux (IFI) — marchés financés, acheteurs non étatiques.
        build_banque_mondiale, build_afd, build_bad,
        # Banques & compagnies d'assurance présentes au Bénin.
        build_banques_assurances,
        # ONG internationales et représentations diplomatiques.
        build_plan_international, build_ue_delegation, build_ambassade_france,
    ],
    # Togo : DNCCP (portail officiel principal) + ARCOP + OTR + CNCT + Port
    # + bailleurs internationaux (UNGM, Banque Mondiale, AFD).
    "TG": [
        build_togo,
        # Sources publiques nationales.
        build_tg_dnccp,  # portail DNCCP — source publique principale
        # Portails gouvernementaux centralisés (NOUVEAUX - Phase 1).
        build_tg_service_public, build_tg_dnccp_new,
        # NB : build_tg_marchespublics retiré — le domaine marchespublics.tg
        # n'est plus résolvable ; le portail public national est servi par
        # DNCCP (build_tg_dnccp, API REST dnccp.gouv.tg) qui le remplace.
        build_tg_arcop, build_tg_otr,
        build_tg_cnct, build_tg_port,
        # Bailleurs internationaux (marchés privés).
        build_tg_ungm, build_tg_banque_mondiale, build_tg_afd,
        build_tg_pnud, build_tg_bad,
        # ONG internationales et représentations diplomatiques.
        build_tg_ue_delegation,
        # Plateforme privée d'appels d'offres (ONG, projets, institutions).
        build_tg_emploitogo,
    ],
    # Côte d'Ivoire : portail national + ARCOP + bailleurs internationaux
    # (UNGM/Nations Unies, Banque Mondiale, AFD).
    "CI": [
        build_ci,
        # Sources publiques nationales (portail + institutions d'État).
        build_ci_marchespublics, build_ci_arcop,
        build_ci_ageroute, build_ci_fer,
        # Bailleurs internationaux (marchés privés).
        build_ci_ungm, build_ci_banque_mondiale, build_ci_afd,
        build_ci_pnud, build_ci_bad,
        # Plateforme privée d'appels d'offres (ONG, entreprises, cabinets).
        build_ci_educarriere,
    ],
    # Sénégal : portail national + bailleurs internationaux.
    # Volume attendu ~100-300 marchés fiables, similaire à TG/CI.
    "SN": [
        # Portail national centralisé (marchespublics.sn — repli si joignable).
        build_sn_marchespublics,
        # Source nationale d'appels d'offres publics (SenOffre) — remplace de
        # fait le portail officiel souvent injoignable hors Sénégal.
        build_sn_senoffre,
        # Sociétés d'État & agences publiques sénégalaises (Phase 2).
        build_sn_senelec, build_sn_pad, build_sn_ageroute, build_sn_artp,
        # Bailleurs internationaux (marchés privés).
        build_sn_ungm, build_sn_banque_mondiale, build_sn_pnud,
        build_sn_bad, build_sn_boad,
        # ONG internationales et représentations diplomatiques.
        build_sn_ue_delegation,
    ],
    # Burkina Faso : source officielle nationale (DGCMEF — Quotidien des
    # Marchés Publics + Plans de Passation) + bailleurs internationaux (marchés
    # privés). Même architecture que les autres pays ; marchés actifs uniquement.
    "BF": [
        # Sources publiques nationales (DGCMEF).
        build_bf,       # Quotidien des Marchés Publics (PDF officiel)
        build_bf_ppm,   # Plans de Passation des Marchés (PPM)
        # Bailleurs internationaux (marchés privés).
        build_bf_ungm, build_bf_banque_mondiale, build_bf_afd,
        build_bf_pnud, build_bf_bad, build_bf_boad,
        # ONG internationales et représentations diplomatiques.
        build_bf_ue_delegation,
    ],
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
