"""Robot de collecte — Bénin 🇧🇯 · SBEE (marchés PUBLICS).

Source : portail des marchés publics de la Société Béninoise d'Énergie
Électrique — https://marches-publics.sbee.bj/

Structure HTML : chaque avis est une carte `div.blog-item-wrapper` contenant
un titre `h3`, la référence, le type de marché, la date de publication et la
date limite de dépôt, ainsi qu'un lien « Demander le dossier » (identifiant
stable) et « Télécharger l'avis ».

Seules des métadonnées et les liens officiels sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.benin.sbee")

from common.html_base import HtmlScraper  # noqa: E402


class SbeeScraper(HtmlScraper):
    country = "BJ"
    source_name = "SBEE — Société Béninoise d'Énergie Électrique"
    tender_type = "public"

    LISTING_URLS = [
        "https://marches-publics.sbee.bj/appels-doffres",
        "https://marches-publics.sbee.bj/",
    ]

    def _label_value(self, text: str, label: str) -> str | None:
        """Récupère la valeur suivant un libellé dans le texte de la carte."""
        m = re.search(re.escape(label) + r"\s*:?\s*(.+?)(?:Type de marché|"
                      r"Nombre de lots|Date de publication|Date limite|"
                      r"Télécharger|Demander|$)", text, re.IGNORECASE)
        return self.clean(m.group(1)) if m else None

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        soup = None
        for url in self.LISTING_URLS:
            soup = self.soup(url)
            if soup:
                base_url = url
                break
        if not soup:
            logger.warning("[BJ] SBEE injoignable — 0 item")
            return items

        cards = soup.select("div.blog-item-wrapper")
        for card in cards:
            title_el = card.find(["h3", "h2", "h4"])
            title = self.clean(title_el.get_text()) if title_el else None
            if not title or len(title) < 6:
                continue
            text = card.get_text(" ", strip=True)

            deadline = self.parse_fr_date(self._label_value(text, "Date limite de dépôt") or "")
            pub = self.parse_fr_date(self._label_value(text, "Date de publication") or "")
            market_type = self._label_value(text, "Type de marché")

            # Référence : bloc de texte entre le titre et « Type de marché ».
            reference = None
            # On exige une référence structurée : sigle + n° + chemin avec « / ».
            m = re.search(r"(?:DC|DAO|DAOOI|DRP|AAO|AON|AOO|AMI|DP)\s*n?[°ºo]\s*[\w/\-.]*/[\w/\-.]+",
                          text, re.IGNORECASE)
            if m:
                reference = self.clean(m.group(0))[:120]

            # Liens : demande de dossier (id stable) + téléchargement de l'avis.
            source_url = base_url
            external_id = None
            dossier = card.find("a", href=re.compile(r"demande-dossier"))
            if dossier and dossier.get("href"):
                source_url = urljoin(base_url, dossier["href"])
                mid = re.search(r"/(\d+)$", source_url)
                if mid:
                    external_id = f"sbee-{mid.group(1)}"
            dao_url = None
            avis = card.find("a", href=re.compile(r"uploads|\.pdf", re.IGNORECASE))
            if avis and avis.get("href"):
                dao_url = urljoin(base_url, avis["href"])

            if external_id and external_id in seen:
                continue
            if external_id:
                seen.add(external_id)

            items.append(self.make_item(
                title=title,
                institution=self.source_name,
                reference=reference,
                deadline=deadline,
                publication_date=pub,
                market_type=market_type,
                source_url=source_url,
                dao_url=dao_url,
                external_id=external_id,
            ))
        return items


def build() -> SbeeScraper:
    return SbeeScraper()
