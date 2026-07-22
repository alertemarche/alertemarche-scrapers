"""Détection des opportunités « premium » (fort potentiel commercial).

Ce module analyse les appels d'offres collectés et attribue un score de priorité
basé sur plusieurs critères objectifs :
    - Montant estimé élevé (seuil : 50M FCFA)
    - Secteurs stratégiques (BTP, IT, Infrastructure, Consulting, Santé, Énergie)
    - Institutions émettrices importantes (IFI, ministères régaliens)
    - Type de marché (Travaux = priorité haute)

Les opportunités avec un score ≥ seuil sont marquées `is_premium=True`, ce qui
permet au backend de :
    - Afficher un badge « ⭐ Opportunité Premium » dans l'UI
    - Envoyer des alertes email ciblées aux utilisateurs concernés
    - Prioriser dans les recommandations IA
"""
import logging
import re

logger = logging.getLogger("common.premium_detector")

# ============================================================================
# CRITÈRES ET SEUILS
# ============================================================================

# Montant estimé minimum pour le critère « gros marché » (en FCFA)
MONTANT_SEUIL_FCFA = 50_000_000  # 50 millions FCFA (~76K EUR)

# Mots-clés définissant les secteurs stratégiques à fort potentiel
SECTEURS_STRATEGIQUES = [
    # BTP / Travaux / Infrastructure
    r"\b(travaux|construction|r[ée]habilitation|am[ée]nagement|b[âa]timent|g[ée]nie.?civil|infrastructure|route|pont|barrage)\b",
    # IT / Informatique / Digital
    r"\b(informatique|logiciel|syst[èe]me.?information|digitalisation|num[ée]rique|serveur|r[ée]seau|cybersecurity|cloud|data.?center)\b",
    # Consulting / Études / Audit
    r"\b(consulting|conseil|[ée]tude|audit|expertise|assistance.?technique|ma[îi]trise.?d.?œuvre|contr[ôo]le|suivi.[ée]valuation)\b",
    # Santé / Médical
    r"\b(sant[ée]|m[ée]dical|h[ôo]pital|clinique|laboratoire|pharmaceutique|[ée]quipement.?m[ée]dical|vaccin|dispositif.?m[ée]dical)\b",
    # Énergie / Environnement
    r"\b([ée]nergie|[ée]lectrique|solaire|[ée]olien|groupe.?[ée]lectrog[èe]ne|transformateur|environnement|eau|assainissement|d[ée]chets)\b",
    # Équipements / Fournitures stratégiques
    r"\b(v[ée]hicule|engin|mat[ée]riel.?roulant|climatisation|g[ée]n[ée]rateur|mobilier.?technique)\b",
]
SECTEURS_PATTERN = re.compile("|".join(SECTEURS_STRATEGIQUES), re.IGNORECASE)

# Institutions émettrices considérées comme « importantes » (bailleurs, ministères clés)
INSTITUTIONS_IMPORTANTES = [
    # IFI (Institutions Financières Internationales)
    r"\b(banque.?mondiale|world.?bank|bad|afdb|afd|bceao|fmi|imf)\b",
    # ONU & agences
    r"\b(onu|nations.?unies|pnud|undp|unicef|unesco|oms|who|fao|pam|oim)\b",
    # Union Européenne
    r"\b(union.?europ[ée]enne|d[ée]l[ée]gation.?ue|eeas|commission.?europ[ée]enne)\b",
    # Coopération bilatérale
    r"\b(usaid|giz|dfid|jica|ambassade)\b",
    # Ministères régaliens / stratégiques
    r"\b(minist[èe]re.?(finance|sant[ée]|d[ée]fense|int[ée]rieur|[ée]conomie|infrastructure|[ée]nergie|eau))\b",
    # Projets et programmes d'envergure
    r"\b(mca|compact|projet.?banque.?mondiale|projet.?bad)\b",
]
INSTITUTIONS_PATTERN = re.compile("|".join(INSTITUTIONS_IMPORTANTES), re.IGNORECASE)

# Types de marchés prioritaires
TYPES_PRIORITAIRES = re.compile(r"\b(travaux|fourniture|prestation)\b", re.IGNORECASE)

# Score minimum pour qualifier une opportunité de « premium »
SCORE_SEUIL_PREMIUM = 3


# ============================================================================
# FONCTIONS D'ANALYSE
# ============================================================================

def _parse_montant_fcfa(text: str | None) -> float:
    """Extrait un montant en FCFA depuis une chaîne de texte.

    Gère les formats courants : « 125 000 000 FCFA », « 125.000.000 F CFA »,
    « 125 millions FCFA », etc.

    Retourne 0 si aucun montant n'est détecté.
    """
    if not text:
        return 0.0

    text = str(text).replace("\xa0", " ")  # Espace insécable
    text = text.upper()

    # Pattern « X millions » ou « X milliards »
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(MILLION|MILLIARD)", text, re.IGNORECASE)
    if m:
        val = float(m.group(1).replace(",", "."))
        unit = m.group(2).upper()
        if "MILLIARD" in unit:
            return val * 1_000_000_000
        return val * 1_000_000

    # Pattern numérique brut (avec espaces, points ou virgules comme séparateurs)
    # Ex: « 125 000 000 », « 125.000.000 », « 125,000,000 »
    m = re.search(r"(\d[\d\s.,]{5,})\s*F?CFA", text)
    if m:
        raw = m.group(1).replace(" ", "").replace(".", "").replace(",", "")
        try:
            return float(raw)
        except ValueError:
            pass

    return 0.0


def detect_premium(item: dict) -> dict:
    """Analyse un item et lui attribue un score de priorité + flag `is_premium`.

    Args:
        item: Dictionnaire représentant un appel d'offres (titre, institution,
              estimated_amount, market_type, etc.)

    Returns:
        Le même dictionnaire enrichi avec :
            - `is_premium` (bool) : True si score ≥ SCORE_SEUIL_PREMIUM
            - `priority_score` (int) : score de priorité (pour debug/tri)

    Critères de scoring :
        +3 : Montant estimé ≥ 50M FCFA
        +2 : Secteur stratégique détecté (BTP, IT, Santé, Énergie, Consulting)
        +1 : Institution importante (IFI, ONU, UE, ministères clés)
        +1 : Type de marché prioritaire (Travaux)
    """
    score = 0

    # 1. Montant estimé
    montant = item.get("estimated_amount")
    if montant:
        # Si c'est déjà un nombre, l'utiliser directement
        if isinstance(montant, (int, float)):
            val = float(montant)
        else:
            # Sinon, parser la chaîne
            val = _parse_montant_fcfa(str(montant))

        if val >= MONTANT_SEUIL_FCFA:
            score += 3
            logger.debug("[PREMIUM] +3 montant : %.0f FCFA — %s", val, item.get("title", "")[:60])

    # 2. Secteur stratégique (analyse du titre + éventuellement description si disponible)
    text_corpus = " ".join(filter(None, [
        item.get("title", ""),
        item.get("market_type", ""),
        item.get("institution", ""),
    ]))
    if SECTEURS_PATTERN.search(text_corpus):
        score += 2
        logger.debug("[PREMIUM] +2 secteur stratégique — %s", item.get("title", "")[:60])

    # 3. Institution importante (vérifier institution ET source_name)
    # Pour les IFI, le source_name est souvent plus significatif que l'institution
    # bénéficiaire (ex. Banque Mondiale → institution = agence locale)
    institution_text = " ".join(filter(None, [
        item.get("institution", ""),
        item.get("source_name", ""),
    ]))
    if INSTITUTIONS_PATTERN.search(institution_text):
        score += 1
        logger.debug("[PREMIUM] +1 institution importante : %s", item.get("source_name", ""))

    # 4. Type de marché prioritaire
    market_type = item.get("market_type", "")
    if market_type and "travaux" in market_type.lower():
        score += 1
        logger.debug("[PREMIUM] +1 type marché Travaux")

    # Décision
    is_premium = score >= SCORE_SEUIL_PREMIUM

    item["priority_score"] = score
    item["is_premium"] = is_premium

    if is_premium:
        logger.info(
            "[PREMIUM ⭐] Score=%d — %s | %s",
            score,
            item.get("institution", "")[:30],
            item.get("title", "")[:80],
        )

    return item
