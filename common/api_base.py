"""Classe de base pour les robots de collecte via API JSON officielle.

Architecture modulaire : chaque source dispose d'un robot indépendant qui
déclare sa *méthode* de collecte. `ApiScraper` implémente la méthode « api »
(consommation d'une API JSON structurée), complémentaire de `BaseScraper`
(méthode « html/heuristique »).

Une API officielle est la source la plus fiable : données propres, paginées,
sans bruit de navigation. Seules des MÉTADONNÉES sont collectées ; le lien vers
le DAO (`dao_url`) est conservé, jamais le fichier lui-même.
"""
import logging
import time

import requests

from . import config

logger = logging.getLogger("scrapers.api")


class ApiScraper:
    country: str = ""            # BJ | TG | CI
    source_name: str = ""        # Nom lisible de la source
    tender_type: str = "public"  # public | prive
    method: str = "api"          # méthode de collecte déclarée (monitoring)

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json",
        })

    # ---- Réseau -------------------------------------------------------
    def fetch_json(self, url: str, params: dict | None = None):
        """GET JSON avec retries. Retourne l'objet décodé ou None."""
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # noqa: BLE001
                logger.warning("[%s] GET %s échec %s/%s : %s",
                               self.country, url, attempt, config.MAX_RETRIES, exc)
                time.sleep(1.5 * attempt)
        return None

    # ---- Utilitaires --------------------------------------------------
    @staticmethod
    def _score(s: str) -> int:
        """Score de « francité » : + pour accents FR valides, - pour caractères parasites."""
        good = "éèàçùâêîôûëïüœæ"
        # Caractères de contrôle (U+0080–U+009F) + majuscules accentuées isolées
        # typiques du mojibake CP850 (Ú, ┌, ┐, ▓…).
        bad_chars = "\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f" \
                    "\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f" \
                    "Ú┌┐└┘├┤┬┴┼─│▓▒░╚╔╗╝"
        score = 0
        for ch in s:
            if ch in good:
                score += 2
            elif ch in bad_chars:
                score -= 3
            elif ch == "\ufffd":
                score -= 3
        return score

    @classmethod
    def fix_encoding(cls, text) -> str | None:
        """Répare le mojibake des sources (octets latin-1/cp1252 décodés en CP850).

        Ex. « UniversitÚ » -> « Université ». On génère des variantes candidates
        par round-trip d'encodage, puis on conserve celle qui maximise le nombre
        d'accents français valides tout en minimisant les caractères parasites.
        Les chaînes déjà correctes ne sont jamais dégradées.
        """
        if not text:
            return None
        s = str(text)
        candidates = [s]
        for enc_from, enc_to in (("cp850", "latin-1"), ("latin-1", "utf-8"), ("cp1252", "utf-8")):
            try:
                candidates.append(s.encode(enc_from).decode(enc_to))
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
        best = max(candidates, key=cls._score)
        return " ".join(best.split())

    def make_item(self, title: str, institution: str, source_url: str,
                  reference: str | None = None, location: str | None = None,
                  estimated_amount: str | None = None, deadline: str | None = None,
                  publication_date: str | None = None, nb_lots: int | None = None,
                  market_type: str | None = None, dao_url: str | None = None,
                  external_id: str | None = None, tender_type: str | None = None,
                  procedure_type: str | None = None) -> dict:
        return {
            "title": (title or "")[:255],
            "institution": (institution or self.source_name)[:255],
            "reference": (reference or None),
            "location": (location[:255] if location else None),
            "estimated_amount": estimated_amount,
            "deadline": deadline,
            "publication_date": publication_date,
            "nb_lots": nb_lots,
            "country": self.country,
            "type": tender_type or self.tender_type,
            "market_type": market_type,
            "procedure_type": procedure_type,
            "source_name": self.source_name,
            "source_url": source_url,
            "dao_url": dao_url,
            "external_id": external_id,
        }

    # ---- À surcharger -------------------------------------------------
    def collect(self) -> list[dict]:
        """Collecte propre à la source. À implémenter par chaque robot API."""
        raise NotImplementedError

    # ---- Exécution ----------------------------------------------------
    def run(self) -> list[dict]:
        try:
            items = self.collect()
        except Exception as exc:  # noqa: BLE001
            logger.exception("[%s] %s — erreur de collecte : %s",
                             self.country, self.source_name, exc)
            items = []
        logger.info("[%s] %s (%s) — %s opportunités collectées",
                    self.country, self.source_name, self.method, len(items))
        return items
