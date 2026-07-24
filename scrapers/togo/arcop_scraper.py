"""Robot de collecte — Togo 🇹🇬 · ARCOP-TG (marchés PUBLICS).

Source : Autorité de Régulation de la Commande Publique du Togo —
https://arcop.tg/ (catégorie « Appels d'offres »).

Structure HTML : site WordPress. Chaque avis est un `article` contenant un
titre `h2.entry-title > a` (lien vers l'avis) et une date de publication au
format « Post published: 6 mai 2025 ».

Seules des métadonnées et le lien officiel sont collectés.
"""
import logging
import re

logger = logging.getLogger("scrapers.togo.arcop")

from common.html_base import HtmlScraper  # noqa: E402


class ArcopTgScraper(HtmlScraper):
    country = "TG"
    source_name = "ARCOP Togo — Autorité de Régulation de la Commande Publique"
    tender_type = "public"

    LISTING_URLS = [
        "https://arcop.tg/category/appels-doffre/",
        "https://arcop.tg/appels-doffres/",
    ]

    # Nombre maximal de pages de détail visitées par passe (maîtrise du temps).
    MAX_DETAILS = 40

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        soup = None
        for url in self.LISTING_URLS:
            soup = self.soup(url)
            if soup:
                break
        if not soup:
            logger.warning("[TG] ARCOP-TG injoignable — 0 item")
            return items

        for art in soup.select("article"):
            title_el = art.select_one("h2.entry-title a, h2.entry-title, h2 a, h3.entry-title a")
            if not title_el:
                continue
            title = self.clean(title_el.get_text())
            if not title or len(title) < 8:
                continue
            href = title_el.get("href") if title_el.name == "a" else None
            if not href:
                a = title_el.find("a", href=True)
                href = a["href"] if a else None
            source_url = href or self.LISTING_URLS[0]

            text = art.get_text(" ", strip=True)
            # « Post published: 6 mai 2025 »
            m = re.search(r"published\s*:?\s*(.+?)(?:Post|Read|Lire|$)", text, re.IGNORECASE)
            pub = self.parse_fr_date(m.group(1)) if m else self.parse_fr_date(text)

            external_id = None
            mid = re.search(r"/([a-z0-9\-]+)/?$", source_url)
            if mid:
                external_id = f"arcop-tg-{mid.group(1)[:60]}"
            if external_id and external_id in seen:
                continue
            if external_id:
                seen.add(external_id)

            # --- Enrichissement depuis la page de détail --------------
            # Le texte de l'avis contient l'échéance (« … au plus tard le … »)
            # et parfois un montant estimatif en FCFA, absents de la liste.
            deadline = None
            amount = None
            if source_url.startswith("http") and len(items) < self.MAX_DETAILS:
                detail = self.detail_text(source_url)
                if detail:
                    deadline = self.deadline_from_text(detail)
                    amount = self.amount_from_text(detail)

            items.append(self.make_item(
                title=title,
                institution=self.source_name,
                publication_date=pub,
                deadline=deadline,
                estimated_amount=amount,
                source_url=source_url,
                external_id=external_id,
            ))
        return items


def build() -> ArcopTgScraper:
    return ArcopTgScraper()
