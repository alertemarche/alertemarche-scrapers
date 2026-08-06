# AlerteMarché — Scrapers

![AlerteMarché](https://img.shields.io/badge/AlerteMarch%C3%A9-by%20PRO%20BENIN%20SARL-1a7f5a?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)

Robots de collecte de **AlerteMarché**, la plateforme SaaS de veille intelligente pour les appels d'offres au **Bénin**, **Togo**, **Côte d'Ivoire** et **Sénégal**.

## À propos

Ce dépôt contient les robots (scrapers) qui collectent automatiquement les opportunités d'affaires — **appels d'offres publics et privés** — depuis les sources officielles de chaque pays. Les opportunités brutes sont ensuite transmises à l'API [alertemarche-backend](https://github.com/alertemarche/alertemarche-backend) pour analyse IA, matching et notification.

> Les documents officiels (DAO) ne sont **jamais** stockés : seuls les métadonnées et le lien vers la source gouvernementale sont collectés.

## Stack technique

| Composant       | Technologie                       |
|-----------------|-----------------------------------|
| Langage         | Python 3.11+                      |
| Collecte        | requests / httpx, BeautifulSoup, Playwright |
| Planification   | Cron / files d'attente            |
| Sortie          | API interne du backend            |

## Organisation

```
scrapers/
  benin/         # robots pour les sources béninoises
  togo/          # robots pour les sources togolaises
  cote_ivoire/   # robots pour les sources ivoiriennes
docs/
  sources.md     # liste des sources par pays
```

## Démarrage rapide

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # renseigner les URLs sources et la connexion DB
```

## Dépôts du projet

- [alertemarche-backend](https://github.com/alertemarche/alertemarche-backend) — API & cœur métier
- [alertemarche-frontend](https://github.com/alertemarche/alertemarche-frontend) — Interface web
- [alertemarche-scrapers](https://github.com/alertemarche/alertemarche-scrapers) — Robots de collecte (ce dépôt)
- [alertemarche-infra](https://github.com/alertemarche/alertemarche-infra) — Infrastructure & déploiement

## Documentation

- [docs/sources.md](docs/sources.md) — Sources de collecte par pays

---

© PRO BENIN SARL — AlerteMarché
