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


# Taille des lots d'ingestion. L'API traite chaque item (déduplication +
# création + dispatch d'un job). Envoyer des milliers d'items en une seule
# requête dépasse le timeout HTTP : on découpe en lots raisonnables.
BATCH_SIZE = 150


def _post_batch(items: list[dict]) -> dict:
    """POST d'un lot unique vers /ingest/tenders, avec retries."""
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
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Échec d'envoi lot (tentative %s/%s) : %s", attempt, config.MAX_RETRIES, exc)
            time.sleep(2 * attempt)

    raise RuntimeError(f"Impossible d'envoyer un lot d'opportunités : {last_error}")


def send_tenders(items: list[dict]) -> dict:
    """POST /ingest/tenders par lots. Retourne {received, new, updated} cumulés."""
    if not items:
        return {"received": 0, "new": 0}

    total = {"received": 0, "new": 0, "updated": 0}
    nb_batches = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]
        data = _post_batch(batch)
        for k in ("received", "new", "updated"):
            if data.get(k) is not None:
                total[k] += int(data[k])
        logger.info("Lot %s/%s ingéré : %s reçus, %s nouveaux",
                    i // BATCH_SIZE + 1, nb_batches, data.get("received"), data.get("new"))

    logger.info("Ingestion OK : %s reçus, %s nouveaux, %s mis à jour",
                total["received"], total["new"], total.get("updated", 0))
    return total


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
