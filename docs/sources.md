# Sources de collecte par pays

Les scrapers collectent les **appels d'offres publics et privés** depuis les sources officielles de chaque pays couvert. Seuls les métadonnées et le lien vers la source sont conservés — les documents officiels (DAO) ne sont jamais stockés.

## 🇧🇯 Bénin

| Source | Type | URL |
|--------|------|-----|
| ARMP Bénin — Autorité de Régulation des Marchés Publics | Appels d'offres publics | https://armp.bj |
| Portail national des marchés publics (SIGMAP/DNCMP) | Appels d'offres publics | à confirmer |
| Presse & plateformes privées | Appels d'offres privés | divers |

## 🇹🇬 Togo

| Source | Type | URL |
|--------|------|-----|
| ARMP Togo — Autorité de Régulation des Marchés Publics | Appels d'offres publics | https://armp.tg |
| Direction Nationale du Contrôle des Marchés Publics (DNCMP) | Appels d'offres publics | à confirmer |
| Presse & plateformes privées | Appels d'offres privés | divers |

## 🇨🇮 Côte d'Ivoire

| Source | Type | URL |
|--------|------|-----|
| ANRMP — Autorité Nationale de Régulation des Marchés Publics | Appels d'offres publics | https://www.anrmp.ci |
| Portail des marchés publics (DGMP / marchespublics.ci) | Appels d'offres publics | à confirmer |
| Presse & plateformes privées | Appels d'offres privés | divers |

## 🇧🇫 Burkina Faso

| Source | Type | URL |
|--------|------|-----|
| DGCMEF — Quotidien des Marchés Publics (PDF officiel quotidien) | Appels d'offres publics | https://www.dgcmef.gov.bf/fr/appels-d-offre |
| DGCMEF — Plans de Passation des Marchés (PPM) | Avis généraux / planification | https://www.dgcmef.gov.bf/fr/plan-de-passation-des-march-s-publics |
| UNGM — Nations Unies & organismes internationaux | Appels d'offres privés | https://www.ungm.org |
| Banque Mondiale (World Bank) | Appels d'offres privés | https://search.worldbank.org |
| AFD (Agence Française de Développement) | Appels d'offres privés | https://afd.dgmarket.com |
| PNUD Burkina Faso | Appels d'offres privés | https://procurement-notices.undp.org |
| BAD (Banque Africaine de Développement) | Appels d'offres privés | https://www.afdb.org |
| BOAD (Banque Ouest-Africaine de Développement) | Appels d'offres privés | https://www.boad.org |
| Délégation de l'Union Européenne | Appels d'offres privés | https://www.eeas.europa.eu |

## Notes d'implémentation

- Chaque source dispose de son module dédié dans `scrapers/<pays>/`.
- Fréquence de collecte configurable via `SCRAPE_INTERVAL_MINUTES` (voir `.env.example`).
- Respect des règles d'usage (robots.txt) et d'un `User-Agent` identifiable.
- Les opportunités collectées sont envoyées à l'API interne du backend pour analyse IA et matching.
