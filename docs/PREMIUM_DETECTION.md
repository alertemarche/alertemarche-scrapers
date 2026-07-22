# Système de Détection des Opportunités Premium

## Vue d'ensemble

Le système de détection premium identifie automatiquement les **appels d'offres à fort potentiel commercial** en analysant plusieurs critères objectifs. Les opportunités qualifiées sont marquées avec un flag `is_premium=True` et un `priority_score`, permettant au backend de :

- Afficher un **badge ⭐ Opportunité Premium** dans l'interface utilisateur
- Envoyer des **alertes email ciblées** aux utilisateurs concernés
- **Prioriser** ces opportunités dans les recommandations IA du système de matching

---

## Critères de Scoring

### 1. Montant Estimé (+3 points)
**Seuil** : ≥ 50 000 000 FCFA (~76 000 EUR)

- Détection automatique depuis le champ `estimated_amount`
- Gère les formats variés : `"125 000 000 FCFA"`, `"125 millions FCFA"`, `"125.000.000 F CFA"`
- Score maximum attribué aux grands marchés (infrastructures, équipements lourds)

### 2. Secteurs Stratégiques (+2 points)
Analyse du titre, type de marché et institution pour détecter les mots-clés :

#### BTP / Travaux / Infrastructure
- `travaux`, `construction`, `réhabilitation`, `aménagement`, `bâtiment`, `génie civil`
- `infrastructure`, `route`, `pont`, `barrage`

#### IT / Informatique / Digital
- `informatique`, `logiciel`, `système d'information`, `digitalisation`, `numérique`
- `serveur`, `réseau`, `cybersecurity`, `cloud`, `data center`

#### Consulting / Études / Audit
- `consulting`, `conseil`, `étude`, `audit`, `expertise`, `assistance technique`
- `maîtrise d'œuvre`, `contrôle`, `suivi-évaluation`

#### Santé / Médical
- `santé`, `médical`, `hôpital`, `clinique`, `laboratoire`, `pharmaceutique`
- `équipement médical`, `vaccin`, `dispositif médical`

#### Énergie / Environnement
- `énergie`, `électrique`, `solaire`, `éolien`, `groupe électrogène`, `transformateur`
- `environnement`, `eau`, `assainissement`, `déchets`

#### Équipements Stratégiques
- `véhicule`, `engin`, `matériel roulant`, `climatisation`, `générateur`

### 3. Institutions Importantes (+1 point)
Vérification dans `institution` ET `source_name` pour identifier :

#### IFI (Institutions Financières Internationales)
- Banque Mondiale, BAD, AFD, BCEAO, FMI

#### ONU & Agences
- PNUD, UNICEF, UNESCO, OMS, FAO, PAM, OIM

#### Union Européenne
- Délégation UE, Commission Européenne

#### Coopération Bilatérale
- USAID, GIZ, DFID, JICA, Ambassades

#### Ministères Régaliens
- Ministères des Finances, Santé, Défense, Intérieur, Économie, Infrastructure, Énergie, Eau

#### Projets d'Envergure
- MCA, Compact, Projets Banque Mondiale, Projets BAD

### 4. Type de Marché Prioritaire (+1 point)
- `Travaux` = priorité haute (construction, infrastructure)

---

## Seuil de Qualification

**Un appel d'offres est qualifié "Premium" si son score ≥ 3**

### Exemples de combinaisons :
- **Score 5** : Montant > 50M + Secteur stratégique + Institution IFI + Travaux
- **Score 4** : Montant > 50M + Secteur stratégique + Travaux
- **Score 3** (minimum) :
  - Montant > 50M seul ✓
  - Secteur stratégique + Institution IFI ✓
  - Secteur stratégique + Travaux + aucun montant mais mots-clés forts ✓

---

## Distribution Observée (Tests Réels)

Sur un échantillon de **136 appels d'offres** collectés (DNCMP, CDC, SBEE) :

| Score | Nombre | Pourcentage |
|-------|--------|-------------|
| **3** (Premium) | 10 | **7.4%** |
| **2** | 46 | 33.8% |
| **0** | 80 | 58.8% |

**Taux de détection Premium : ~7-10% des AO publics**

*Note* : Le taux varie selon les sources. Les IFI et grands projets d'infrastructure ont un taux plus élevé.

---

## Intégration Technique

### Architecture
Le module `common/premium_detector.py` est **automatiquement appelé** par la méthode `make_item()` présente dans :
- `common/api_base.py` (scrapers API)
- `common/base.py` (scrapers HTML legacy)
- `common/html_base.py` (hérite de `api_base.py` via composition)

**Aucune modification nécessaire dans les scrapers individuels** — la détection est transparente.

### Champs Ajoutés aux Items
Chaque item collecté contient maintenant :
```python
{
    "title": "Travaux de construction...",
    "institution": "Ministère des Infrastructures",
    "estimated_amount": "150000000",  # ou None
    "market_type": "Travaux",
    # ... autres champs standards ...
    "is_premium": True,        # ← NOUVEAU
    "priority_score": 4,       # ← NOUVEAU
}
```

### Backend / Frontend
Le backend reçoit ces champs via l'API `/tenders` et peut :
1. Filtrer les opportunités premium : `filter(is_premium=True)`
2. Trier par score de priorité : `order_by(-priority_score)`
3. Déclencher des alertes email automatiques pour les utilisateurs ayant des profils matchés
4. Afficher un badge visuel `⭐ Opportunité Premium` dans l'UI

---

## Logs et Debugging

Le module génère des logs `INFO` pour chaque opportunité premium détectée :

```
INFO: [PREMIUM ⭐] Score=4 — Banque Mondiale | Acquisition d'équipements de contrôle technique mobile mixte VL/PL
```

Les logs `DEBUG` détaillent les points attribués :
```
DEBUG: [PREMIUM] +3 montant : 150000000 FCFA — Travaux de construction...
DEBUG: [PREMIUM] +2 secteur stratégique — Travaux de construction bibliothèque...
DEBUG: [PREMIUM] +1 institution importante : Banque Mondiale
DEBUG: [PREMIUM] +1 type marché Travaux
```

---

## Maintenance et Évolution

### Ajuster les Seuils
Modifier dans `common/premium_detector.py` :
- `MONTANT_SEUIL_FCFA` : seuil de montant (actuellement 50M)
- `SCORE_SEUIL_PREMIUM` : score minimum pour qualification (actuellement 3)

### Ajouter des Secteurs
Enrichir la liste `SECTEURS_STRATEGIQUES` avec de nouveaux patterns regex.

### Ajouter des Institutions
Enrichir la liste `INSTITUTIONS_IMPORTANTES` avec de nouveaux patterns.

### Tester les Modifications
```bash
cd /home/ubuntu/github_repos/alertemarche-scrapers
python3 << 'EOF'
from scrapers.benin.scraper import build
s = build()
items = s.run()[:20]
premium = [i for i in items if i.get("is_premium")]
print(f"Premium détectés : {len(premium)} / {len(items)}")
for p in premium:
    print(f"  ⭐ Score {p['priority_score']} - {p['title'][:60]}")
EOF
```

---

## Impact Business

### Pour les Utilisateurs
- **Gain de temps** : focus immédiat sur les opportunités à fort potentiel
- **Meilleure conversion** : ciblage des marchés adaptés à leur capacité
- **Alertes intelligentes** : notification uniquement pour les AO stratégiques

### Pour la Plateforme
- **Différenciation** : valeur ajoutée vs agrégateurs passifs
- **Engagement** : utilisateurs reviennent pour les alertes premium
- **Monétisation** : potentiel d'abonnement premium avec accès prioritaire

---

## Exemple d'Opportunités Premium Détectées

### Score 5 (Maximum)
```
⭐⭐⭐⭐⭐ Travaux de construction du nouveau siège de la BCEAO
Institution : BCEAO (Banque Centrale des États de l'Afrique de l'Ouest)
Montant estimé : 8 500 000 000 FCFA
Type : Travaux de construction
```

### Score 4
```
⭐⭐⭐⭐ Acquisition système informatique de gestion intégrée (ERP)
Institution : Ministère des Finances et de l'Économie
Montant estimé : 250 000 000 FCFA
Type : Fourniture de logiciel
```

### Score 3
```
⭐⭐⭐ Poursuite et achèvement des travaux d'extension de l'Hôtel de Ville
Institution : Commune de Natitingou
Montant estimé : Non spécifié
Type : Travaux
```

---

## Fichiers du Système

| Fichier | Rôle |
|---------|------|
| `common/premium_detector.py` | Module de détection (logique métier) |
| `common/api_base.py` | Intégration dans `make_item()` pour scrapers API |
| `common/base.py` | Intégration dans `make_item()` pour scrapers HTML legacy |
| `docs/PREMIUM_DETECTION.md` | Cette documentation |

---

**Version** : 1.0  
**Date** : Juillet 2026  
**Auteur** : Équipe AlerteMarché
