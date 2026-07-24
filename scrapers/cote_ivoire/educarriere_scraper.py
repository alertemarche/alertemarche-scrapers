"""Robot de collecte — Côte d'Ivoire 🇨🇮 · Educarrière (appels d'offres PRIVÉS).

Source : https://appelsdoffres.educarriere.ci/ — la plus grosse plateforme
privée d'appels d'offres de Côte d'Ivoire (ONG, entreprises, cabinets,
projets financés par des bailleurs). Elle agrège des opportunités qui ne
figurent PAS sur les portails publics officiels (SIGOMAP / marchés publics).

Structure HTML : une grille de cartes `div.ao-card`, chacune contenant :
  • le lien vers la fiche détaillée (`ao-<id>-<slug>.html`) ;
  • l'organisme (`div.ao-card-org[title]`) ;
  • le titre de l'appel d'offres ;
  • le secteur d'activité ;
  • la date limite (`… Date limite …<span class="dt">JJ/MM/AAAA</span>`).

Seules des métadonnées et le lien vers la fiche officielle sont collectés —
jamais le document lui-même.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.cote_ivoire.educarriere")

from common.html_base import HtmlScraper  # noqa: E402


class EducarriereCiScraper(HtmlScraper):
    country = "CI"
    source_name = "Educarrière — Appels d'offres (Côte d'Ivoire)"
    tender_type = "prive"

    BASE = "https://appelsdoffres.educarriere.ci"
    LISTING_URLS = [
        "https://appelsdoffres.educarriere.ci/",
        "https://educarriere.ci/appelsdoffres/page/all",
    ]

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()

        soup = None
        for url in self.LISTING_URLS:
            soup = self.soup(url)
            if soup and soup.select("div.ao-card"):
                break
        if not soup:
            logger.warning("[CI] Educarrière injoignable — 0 item")
            return items

        cards = soup.select("div.ao-card")
        logger.info("[CI] Educarrière : %s cartes détectées", len(cards))

        for card in cards:
            link = card.find("a", href=re.compile(r"/ao-\d+"))
            if not link:
                continue
            href = link.get("href", "")
            source_url = urljoin(self.BASE + "/", href)

            m = re.search(r"/ao-(\d+)", source_url)
            ext_id = "ec-" + m.group(1) if m else None
            if ext_id and ext_id in seen:
                continue
            if ext_id:
                seen.add(ext_id)

            # Organisme (attribut title de .ao-card-org)
            org_el = card.select_one(".ao-card-org")
            institution = None
            if org_el:
                institution = self.clean(org_el.get("title") or org_el.get_text(" "))

            # Titre : lien .ao-card-title si présent, sinon slug de l'URL
            title = None
            title_el = card.select_one(".ao-card-title, h3, h2")
            if title_el:
                title = self.clean(title_el.get_text(" "))
            if not title:
                # reconstruit depuis le slug de l'URL
                slug = re.sub(r"^ao-\d+-", "", href.rsplit("/", 1)[-1])
                slug = re.sub(r"\.html?$", "", slug)
                title = self.clean(slug.replace("-", " ")).upper()
            if not title or len(title) < 6:
                continue

            # Secteur (badge après « Marchés en cours »)
            sector = None
            sec_el = card.select_one(".ao-card-cat, .ao-card-sector, .ao-badge")
            if sec_el:
                sector = self.clean(sec_el.get_text(" ")) or None

            # Date limite : <span class="dt">JJ/MM/AAAA</span>
            deadline = None
            card_txt = card.get_text(" ", strip=True)
            m = re.search(r"Date\s+limite\s*([0-9]{1,2}/[0-9]{1,2}/20\d{2})", card_txt)
            if m:
                deadline = self.parse_fr_date(m.group(1))
            if not deadline:
                dt_el = card.select_one("span.dt")
                if dt_el:
                    deadline = self.parse_fr_date(dt_el.get_text(" "))

            # On ne garde que les avis actifs (deadline future ou absente)
            if not self.is_active(deadline):
                continue

            items.append(self.make_item(
                title=title,
                institution=institution or self.source_name,
                source_url=source_url,
                location=sector,  # le secteur sert d'indication (pas de localisation fournie)
                deadline=deadline,
                external_id=ext_id,
            ))

        logger.info("[CI] Educarrière : %s appels d'offres actifs collectés", len(items))
        return items


def build() -> EducarriereCiScraper:
    return EducarriereCiScraper()
