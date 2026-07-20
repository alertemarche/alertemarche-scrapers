"""Planificateur des robots de collecte AlerteMarché.

Lance une collecte immédiate au démarrage puis à intervalle régulier
(SCRAPE_INTERVAL_MINUTES, ~2h par défaut). Conçu pour tourner en continu
dans le conteneur `scrapers` (voir docker-compose).
"""
import logging
import time

import schedule

from common import config
from run_all import run_all

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scrapers.scheduler")


def job() -> None:
    logger.info("Déclenchement d'une passe de collecte.")
    try:
        run_all()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erreur inattendue durant la collecte : %s", exc)


def main() -> None:
    interval = max(5, config.SCRAPE_INTERVAL_MINUTES)
    logger.info("Planificateur démarré — collecte toutes les %s minutes.", interval)
    job()  # première passe immédiate
    schedule.every(interval).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
