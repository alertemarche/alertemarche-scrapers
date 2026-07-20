"""Envoi des opportunités collectées vers l'API backend AlerteMarché."""
import logging
import time

import requests

from . import config

logger = logging.getLogger("scrapers.sender")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.API_TOKEN}",
        "X-Scraper-Token": config.API_TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": config.USER_AGENT,
    }


def send_tenders(items: list[dict]) -> dict:
    """POST /ingest/tenders. Retourne {received, new} ou lève une exception."""
    if not items:
        return {"received": 0, "new": 0}

    payload = {"items": items}
    last_error: Exception | None = None

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = requests.post(
                config.INGEST_TENDERS_URL,
                json=payload,
                headers=_headers(),
                timeout=config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("Ingestion OK : %s reçus, %s nouveaux", data.get("received"), data.get("new"))
            return data
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Échec d'envoi (tentative %s/%s) : %s", attempt, config.MAX_RETRIES, exc)
            time.sleep(2 * attempt)

    raise RuntimeError(f"Impossible d'envoyer les opportunités : {last_error}")


def send_log(country: str, source_name: str, status: str,
             items_collected: int = 0, items_new: int = 0, message: str = "") -> None:
    """POST /ingest/log — journalise une exécution de scraper (best effort)."""
    payload = {
        "country": country,
        "source_name": source_name,
        "status": status,
        "items_collected": items_collected,
        "items_new": items_new,
        "message": message[:2000] if message else "",
    }
    try:
        requests.post(
            config.INGEST_LOG_URL,
            json=payload,
            headers=_headers(),
            timeout=config.REQUEST_TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Journalisation impossible (%s) : %s", source_name, exc)
