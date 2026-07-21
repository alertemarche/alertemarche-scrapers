"""Classification des types de procédure de passation des marchés publics.

Objectif : rattacher chaque opportunité à l'une des sous-catégories affichées
sous « Appels d'offres publics » sur AlerteMarché :

    - cotation : Demande de cotation (DC)
    - drp      : Demande de renseignement et de prix (DRP)
    - aaon     : Avis d'appel d'offres national (AOO, AOR…)
    - aaoi     : Avis d'appel d'offres international (AOI, AOOIP, AOIR…)
    - ami      : Avis à manifestation d'intérêt (AMI, AMII)
    - autre    : autres modes (entente directe/gré à gré, consultation…)

Deux points d'entrée :
    - ``from_code(code)``  : à partir du code « mode de passation » du portail
      SIGMAP (champ ``modepassation_ID.code`` des plans de passation).
    - ``from_text(text)``  : à partir d'un libellé/intitulé libre (avis formels
      dont l'API n'expose pas le mode de passation).
"""
from __future__ import annotations

# Sous-catégories canoniques exposées côté frontend.
COTATION = "cotation"
DRP = "drp"
AAON = "aaon"
AAOI = "aaoi"
AMI = "ami"
AUTRE = "autre"

# --- Mapping direct depuis les codes SIGMAP -----------------------------
# Codes réellement observés sur les plans de passation 2026 (portail DNCMP).
_CODE_MAP = {
    "DC": COTATION,      # Demande de Cotation
    "DRP": DRP,          # Demande de Renseignement et de Prix
    "AOO": AAON,         # Appel d'Offres (National) Ouvert
    "AOR": AAON,         # Appel d'Offres (National) Restreint
    "AOON": AAON,        # variante libellée « national »
    "AOI": AAOI,         # Appel d'Offres International Ouvert
    "AOOI": AAOI,        # Appel d'Offres Ouvert International
    "AOIR": AAOI,        # Appel d'Offres International Restreint
    "AOOIP": AAOI,       # AO International Ouvert avec Pré-qualification
    "AMI": AMI,          # Avis (National) à Manifestation d'Intérêt
    "AMII": AMI,         # Avis International à Manifestation d'Intérêt
    "MED": AUTRE,        # Marché par Entente Directe (gré à gré)
    "ED": AUTRE,         # Entente Directe
    "CR": AUTRE,         # Consultation Restreinte
    "GAG": AUTRE,        # Gré à Gré
}


def from_code(code: str | None) -> str | None:
    """Retourne la sous-catégorie canonique pour un code mode de passation."""
    if not code:
        return None
    key = str(code).strip().upper()
    if key in _CODE_MAP:
        return _CODE_MAP[key]
    # Repli : on tente une reconnaissance partielle sur des préfixes connus.
    if key.startswith("DRP"):
        return DRP
    if key.startswith("DC"):
        return COTATION
    if key.startswith("AMI"):
        return AMI
    if key.startswith("AOI") or key.startswith("AOOI"):
        return AAOI
    if key.startswith("AO"):
        return AAON
    return AUTRE


def from_text(text: str | None) -> str | None:
    """Devine la sous-catégorie à partir d'un intitulé/objet libre.

    Utilisé pour les avis formels (API DNCMP « appelsoffres ») qui n'exposent
    pas le mode de passation : on s'appuie sur les tournures normalisées des
    intitulés officiels béninois.
    """
    if not text:
        return None
    t = " " + str(text).lower() + " "

    def has(*needles: str) -> bool:
        return any(n in t for n in needles)

    # International prioritaire sur national (souvent « … international » suffixé).
    international = has("international", "internationale")

    if has("manifestation d'int", "manifestation d’int", "manifestation d intérêt",
           "manifestation d'intérêt", " ami ", "à manifestation"):
        return AMI
    if has("demande de renseignement", "renseignement et de prix", " drp ",
           "renseignements et de prix"):
        return DRP
    if has("demande de cotation", "cotation", " dc "):
        return COTATION
    if has("entente directe", "gré à gré", "gre a gre", "de gré", "marché négocié"):
        return AUTRE
    if has("appel d'offres", "appel d’offres", "appel d offres", "appel à concurrence",
           " aoo", " aoi", " aao"):
        return AAOI if international else AAON
    return None


# Libellés lisibles (pour d'éventuels usages/documentation).
LABELS = {
    COTATION: "Demande de cotation",
    DRP: "Demande de renseignement et de prix (DRP)",
    AAON: "Avis d'appel d'offres national (AAON)",
    AAOI: "Avis d'appel d'offres international (AAOI)",
    AMI: "Avis à manifestation d'intérêt (AMI)",
    AUTRE: "Autre procédure",
}
