"""Robot de collecte — Bénin 🇧🇯 · Banques & Assurances.

Agrège les avis d'appels d'offres publiés par les banques et compagnies
d'assurance présentes au Bénin. Ces marchés (achats, prestations, agréments
fournisseurs) relèvent des appels d'offres « privés » au sens de la plateforme
(acheteur non étatique).

Réalité du terrain (juillet 2026) : la plupart des banques/assureurs béninois
ne publient PAS leurs appels d'offres sur une page web structurée et accessible
aux robots :
    - Orabank, NSIA Banque .......... 403 (pare-feu / anti-robot)
    - NSIA Assurances, Africaine .... hôte injoignable
    - BOA Bénin, Ecobank, SUNU ...... pas de rubrique « appels d'offres »

La SEULE source actuellement exploitable est **Banque Atlantique** (groupe
ABI — Atlantic Business International), qui maintient une page dédiée listant
ses avis groupe, applicables à ses filiales dont la Banque Atlantique Bénin :

    https://www.banqueatlantique.net/appels-doffres/

Ce robot est conçu pour être EXTENSIBLE : chaque source est un parseur isolé,
tolérant aux pannes (retourne une liste vide en cas de blocage ou d'absence de
contenu), afin qu'une source indisponible n'empêche jamais la collecte des
autres. Seules des métadonnées et le lien vers la page officielle sont
collectés — jamais le document lui-même.
"""
import logging
import re

from common.html_base import HtmlScraper

logger = logging.getLogger("scrapers.benin.banques_assurances")

# --- Sources -----------------------------------------------------------------
BANQUE_ATLANTIQUE_URL = "https://www.banqueatlantique.net/appels-doffres/"

# Repère une référence d'appel d'offres (« AO 014-2026-ABI-CI… », « AO/O3/2O26… »,
# « AVIS D'APPEL D'OFFRES OUVERT … »). Le « O » (lettre) est toléré car certains
# intitulés utilisent la lettre O à la place du chiffre 0.
AO_PATTERN = re.compile(
    r"(A\s?O\s*[\dO]{2,}\s*[-/][\w/\-]+|AVIS\s+D['’]APPEL\s+D['’]OFFRES?[^\n]{0,120})",
    re.IGNORECASE,
)


class BanquesAssurancesScraper(HtmlScraper):
    country = "BJ"
    source_name = "Banques & Assurances"
    tender_type = "prive"
    method = "html"

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _norm_ref(text: str) -> str:
        """Normalise une référence pour la déduplication (majuscules, sans espaces)."""
        return re.sub(r"\s+", "", text.upper()).replace("O", "0")

    # -------------------------------------------------- source : Banque Atlantique
    def _collect_banque_atlantique(self) -> list[dict]:
        items: list[dict] = []
        try:
            soup = self.soup(BANQUE_ATLANTIQUE_URL)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[BJ] Banque Atlantique injoignable : %s", exc)
            return items
        if not soup:
            return items

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        seen: set[str] = set()
        for el in soup.find_all(["li", "p", "h2", "h3", "h4", "h5", "strong", "div"]):
            txt = " ".join(el.get_text(" ", strip=True).split())
            if not (15 < len(txt) < 400):
                continue
            m = AO_PATTERN.search(txt)
            if not m:
                continue
            ref = m.group(0).strip(" .:-")
            key = self._norm_ref(txt[:60])
            if key in seen:
                continue
            seen.add(key)

            items.append(self.make_item(
                title=txt[:255],
                institution="Banque Atlantique (Groupe ABI)",
                reference=ref[:120] or None,
                source_url=BANQUE_ATLANTIQUE_URL,
                dao_url=BANQUE_ATLANTIQUE_URL,
                external_id=f"ba-{abs(hash(key)) % (10 ** 10)}",
                tender_type="prive",
            ))

        logger.info("[BJ] Banque Atlantique : %d avis", len(items))
        return items

    # --------------------------------------------------------------- collecte
    def collect(self) -> list[dict]:
        items: list[dict] = []
        # Chaque source est isolée : une panne n'interrompt pas les autres.
        for collector in (self._collect_banque_atlantique,):
            try:
                items.extend(collector())
            except Exception as exc:  # noqa: BLE001
                logger.warning("[BJ] source banque/assurance en échec : %s", exc)
        return items


def build() -> BanquesAssurancesScraper:
    return BanquesAssurancesScraper()
