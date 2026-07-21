"""Robot de collecte — Bénin 🇧🇯 · MCA Bénin II (marchés PRIVÉS / programme).

Source : Millennium Challenge Account Bénin II —
https://www.mcabenin2.bj/statut/show/marche/ouvert (marchés ouverts).

La structure exacte du portail peut évoluer et le domaine est parfois
indisponible depuis certains réseaux. Le robot essaie plusieurs URLs
candidates puis applique un parseur tolérant : il repère les lignes de tableau
ou les liens dont le libellé évoque un marché, en récupérant une éventuelle
date proche. En cas d'indisponibilité, il journalise un avertissement et
retourne une liste vide (jamais de crash).

Seules des métadonnées et le lien vers la fiche officielle sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.benin.mca")

from common.html_base import HtmlScraper  # noqa: E402

_KEYWORDS = re.compile(
    r"(appel d|avis|manifestation|consultation|march[ée]|recrutement|"
    r"sélection|selection|fourniture|travaux|acquisition|demande de|sollicitation)",
    re.IGNORECASE,
)


class McaScraper(HtmlScraper):
    country = "BJ"
    source_name = "MCA Bénin II — Millennium Challenge Account"
    tender_type = "prive"

    CANDIDATE_URLS = [
        "https://www.mcabenin2.bj/statut/show/marche/ouvert",
        "https://mcabenin2.bj/statut/show/marche/ouvert",
        "https://www.mcabenin2.bj/marche/",
        "https://mcabenin2.bj/typemarche/show/avis-specifiques",
    ]

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        soup = None
        base_url = self.CANDIDATE_URLS[0]
        for url in self.CANDIDATE_URLS:
            soup = self.soup(url)
            if soup:
                base_url = url
                break
        if not soup:
            logger.warning("[BJ] MCA Bénin II injoignable (DNS/site) — 0 item")
            return items

        # 1) Lignes de tableau structurées.
        for tr in soup.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            row_text = self.clean(tr.get_text(" ", strip=True))
            if not _KEYWORDS.search(row_text):
                continue
            link = tr.find("a", href=True)
            # Titre = cellule la plus longue / texte du lien.
            title = self.clean(link.get_text()) if link and len(self.clean(link.get_text())) > 8 else None
            if not title:
                title = max((self.clean(c.get_text()) for c in cells), key=len, default="")
            if not title or len(title) < 8 or title.lower().startswith(("objet", "titre", "intitulé")):
                continue
            deadline = self.parse_fr_date(row_text)
            source_url = urljoin(base_url, link["href"]) if link and link.get("href") else base_url
            self._add(items, seen, title, deadline, source_url)

        # 2) Repli : liens évocateurs si aucun tableau exploitable.
        if not items:
            for a in soup.find_all("a", href=True):
                title = self.clean(a.get_text())
                if len(title) < 12 or not _KEYWORDS.search(title):
                    continue
                parent = a.find_parent(["tr", "li", "div", "article", "p"])
                deadline = self.parse_fr_date(parent.get_text(" ", strip=True)) if parent else None
                source_url = urljoin(base_url, a["href"])
                self._add(items, seen, title, deadline, source_url)
        return items

    def _add(self, items, seen, title, deadline, source_url):
        external_id = "mca-" + re.sub(r"[^a-zA-Z0-9]", "", (source_url.rsplit("/", 1)[-1] or title))[:40]
        if external_id in seen:
            return
        seen.add(external_id)
        items.append(self.make_item(
            title=title[:255],
            institution=self.source_name,
            deadline=deadline,
            source_url=source_url,
            external_id=external_id,
        ))


def build() -> McaScraper:
    return McaScraper()
