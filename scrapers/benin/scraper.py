"""Robot de collecte — Bénin 🇧🇯 (source officielle : Portail des Marchés Publics).

Source : Portail des Marchés Publics du Bénin (https://www.marches-publics.bj),
géré par la DNCMP via SIGMAP. Le portail expose une API JSON officielle qui
renvoie les avis d'appel à concurrence de façon propre et structurée :

    https://api.marches-publics.bj/v2/api/portail/appelsoffres?page=..&size=..&status=1

status=1 = avis « en cours » (délai de dépôt non expiré). C'est la source
autoritative : elle remplace l'ancienne heuristique HTML qui remontait des
liens de navigation. Seules des MÉTADONNÉES sont collectées ; le lien vers le
DAO (dao_url) est conservé, jamais le fichier.
"""
import logging

from common.api_base import ApiScraper
from common import procedures

logger = logging.getLogger("scrapers.benin")

API_ROOT = "https://api.marches-publics.bj/v2/api/portail/appelsoffres"
PORTAIL_LISTING = "https://www.marches-publics.bj/appels-doffres"
# Page officielle « fiche » d'un avis : le portail (Angular) expose la route
# /appels-doffres/{dosID} qui ouvre la fiche de l'avis avec le bouton
# « TÉLÉCHARGER » du DAO. On y renvoie l'utilisateur pour qu'il télécharge
# lui-même le dossier depuis la source officielle (jamais le PDF en direct).
PORTAIL_DETAIL = "https://www.marches-publics.bj/appels-doffres/{dos_id}"
PAGE_SIZE = 50
MAX_PAGES = 20  # garde-fou (1000 avis max par passe)


class BeninScraper(ApiScraper):
    country = "BJ"
    source_name = "Portail des Marchés Publics du Bénin (DNCMP)"
    tender_type = "public"
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

    def _map(self, row: dict) -> dict | None:
        ao = row.get("appelsoffres") or {}
        title = self.fix_encoding(ao.get("apoObjet"))
        if not title or len(title) < 8:
            return None  # avis sans objet exploitable : ignoré

        institution = self.fix_encoding(self._get(row, "autoriteContractante", "denomination")) \
            or self.source_name
        reference = row.get("dosReference") or ao.get("apoReference")
        market_type = self.fix_encoding(self._get(ao, "typemarche", "libelle"))

        # Type de procédure : l'API « appelsoffres » n'expose pas le mode de
        # passation de façon structurée. On tente d'abord un éventuel code de
        # procédure présent dans l'avis, puis on reconnaît la procédure à partir
        # de l'objet/type d'avis (intitulés normalisés béninois).
        proc_code = self._get(ao, "typeprocedure", "code") or self._get(ao, "modepassation", "code")
        type_avis = self.fix_encoding(self._get(ao, "typeavis", "libelle"))
        procedure_type = (
            procedures.from_code(proc_code)
            or procedures.from_text(type_avis)
            or procedures.from_text(title)
        )

        location = self.fix_encoding(row.get("doslieuacquisitiondao") or row.get("dosLieuDepotDossier"))
        deadline = row.get("dosDateLimiteDepot")          # YYYY-MM-DD
        publication = row.get("dosDatePublication")       # YYYY-MM-DD
        nb_lots = row.get("dosNombreLots")
        dao_url = row.get("dosFichier")                   # lien PDF officiel
        dos_id = row.get("dosID")
        external_id = str(dos_id or ao.get("apoID") or "") or None

        try:
            nb_lots = int(nb_lots) if nb_lots not in (None, "") else None
        except (TypeError, ValueError):
            nb_lots = None

        # Lien officiel : on renvoie vers la FICHE de l'avis sur le portail
        # (page officielle), et non vers le fichier PDF en direct. L'utilisateur
        # télécharge ainsi le DAO lui-même depuis la source officielle.
        if dos_id is not None:
            source_url = PORTAIL_DETAIL.format(dos_id=dos_id)
        else:
            source_url = PORTAIL_LISTING

        return self.make_item(
            title=title,
            institution=institution,
            reference=reference,
            location=location,
            deadline=deadline,
            publication_date=publication,
            nb_lots=nb_lots,
            market_type=market_type,
            procedure_type=procedure_type,
            dao_url=dao_url,
            source_url=source_url,
            external_id=external_id,
        )

    def collect(self) -> list[dict]:
        items: list[dict] = []
        for page in range(0, MAX_PAGES):
            data = self.fetch_json(API_ROOT, params={
                "page": page, "size": PAGE_SIZE, "search": "", "status": 1,
            })
            if not data:
                break
            content = data.get("content") if isinstance(data, dict) else None
            if not content:
                break
            for row in content:
                mapped = self._map(row)
                if mapped:
                    items.append(mapped)
            # Dernière page ?
            if data.get("last") is True or len(content) < PAGE_SIZE:
                break
        return items


def build() -> BeninScraper:
    return BeninScraper()
