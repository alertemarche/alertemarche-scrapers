"""Chargement de la configuration des robots de collecte AlerteMarché."""
import os

from dotenv import load_dotenv

load_dotenv()


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


# URL de base de l'API backend (ex. http://app:8080/api).
API_BASE = os.getenv("BACKEND_API_URL", "http://app:8080/api").rstrip("/")
INGEST_TENDERS_URL = f"{API_BASE}/ingest/tenders"
INGEST_LOG_URL = f"{API_BASE}/ingest/log"

# Jeton partagé (doit correspondre à SCRAPERS_API_TOKEN du backend).
API_TOKEN = os.getenv("SCRAPERS_API_TOKEN") or os.getenv("BACKEND_API_TOKEN", "")

# Sources par pays.
SOURCES = {
    "BJ": os.getenv("BENIN_SOURCE_URL", "https://armp.bj"),
    "TG": os.getenv("TOGO_SOURCE_URL", "https://armp.tg"),
    "CI": os.getenv("CI_SOURCE_URL", "https://www.anrmp.ci"),
}

# Paramètres HTTP.
USER_AGENT = os.getenv("USER_AGENT", "AlerteMarcheBot/1.0 (+https://alertemarche.com)")
REQUEST_TIMEOUT = _int("REQUEST_TIMEOUT", 30)
MAX_RETRIES = _int("MAX_RETRIES", 3)

# --- Proxy Webshare -------------------------------------------------
# Les requêtes SORTANTES des robots (vers les portails externes) sont routées
# via le proxy rotatif Webshare afin d'éviter les blocages géographiques et les
# 401/403 des sources. L'ingestion vers le backend interne (http://app:8080/api)
# n'utilise PAS de session partagée (voir common/sender.py) et n'est donc jamais
# proxifiée ; l'hôte interne est en plus listé dans NO_PROXY par sécurité.
PROXY_USER = os.getenv("WEBSHARE_PROXY_USER", "")
PROXY_PASS = os.getenv("WEBSHARE_PROXY_PASS", "")
PROXY_HOST = os.getenv("WEBSHARE_PROXY_HOST", "p.webshare.io")
PROXY_PORT = os.getenv("WEBSHARE_PROXY_PORT", "80")

PROXIES: dict | None = None
if PROXY_USER and PROXY_PASS:
    _proxy_url = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"
    PROXIES = {"http": _proxy_url, "https": _proxy_url}


def get_proxies() -> dict | None:
    """Retourne le mapping de proxies requests, ou None si non configuré."""
    return PROXIES

# Fréquence de collecte (minutes). Le cahier des charges prévoit ~2h.
SCRAPE_INTERVAL_MINUTES = _int("SCRAPE_INTERVAL_MINUTES", 120)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
