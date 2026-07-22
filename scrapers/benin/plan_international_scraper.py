"""Robot de collecte — Bénin 🇧🇯 · Plan International Bénin.

Source : Blog officiel WordPress de Plan International Bénin, qui publie ses
appels d'offres (achats, prestations de services, travaux) ainsi que ses avis
de recrutement dans la catégorie « Appels d'offres » :

    https://planinternationalbenin.wordpress.com/category/appel-doffres/

Ces marchés (émis par une ONG internationale) relèvent des appels d'offres
« privés » au sens de la plateforme (acheteur non étatique). Le blog utilise
une structure WordPress standard avec pagination. Seules des métadonnées et
le lien vers l'article officiel sont collectés — jamais le document lui-même.
"""
import logging
import re

from common.html_base import HtmlScraper

logger = logging.getLogger("scrapers.benin.plan_international")

BASE_URL = "https://planinternationalbenin.wordpress.com/category/appel-doffres/"
MAX_PAGES = 5  # garde-fou : 5 premières pages du blog


class PlanInternationalScraper(HtmlScraper):
    country = "BJ"
    source_name = "Plan International Bénin"
    tender_type = "prive"
    method = "html"

    @staticmethod
    def _extract_date_from_url(url: str) -> str | None:
        """Extrait la date de publication depuis l'URL WordPress (/YYYY/MM/DD/)."""
        m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        return None

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()

        for page_num in range(1, MAX_PAGES + 1):
            if page_num == 1:
                url = BASE_URL
            else:
                url = f"{BASE_URL}page/{page_num}/"

            soup = self.soup(url)
            if not soup:
                break

            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()

            # WordPress structure : articles avec classe "entry-title" ou "post"
            found_on_page = 0
            for entry in soup.find_all(["article", "div"], class_=re.compile(r"post|entry|hentry")):
                # Trouver le lien principal (dans h2.entry-title > a ou similaire)
                link = entry.find("a", href=re.compile(r"/\d{4}/\d{2}/\d{2}/"))
                if not link:
                    continue
                href = link.get("href", "")
                if not href or href in seen:
                    continue
                seen.add(href)

                # Le titre est souvent dans un élément parent .entry-title ou .post-title
                title = None
                title_el = entry.find(class_=re.compile(r"entry-title|post-title"))
                if title_el:
                    title = " ".join(title_el.get_text(" ", strip=True).split())
                if not title or len(title) < 10:
                    # Fallback : texte du lien lui-même
                    title = " ".join(link.get_text(" ", strip=True).split())
                if not title or len(title) < 10:
                    title = "Avis Plan International Bénin"

                # La date est dans l'URL WordPress
                publication = self._extract_date_from_url(href)

                # On ne filtre PAS par date (contrairement aux scrapers avec échéance) :
                # ce blog a un historique utile, et les avis restent pertinents pour
                # référencement fournisseurs. Si besoin de filtrer par âge, on peut
                # ajouter un seuil (ex. < 2 ans) mais le backend déduplique déjà.

                items.append(self.make_item(
                    title=title[:255],
                    institution=self.source_name,
                    publication_date=publication,
                    source_url=href,
                    dao_url=href,
                    external_id=f"plan-{abs(hash(href)) % (10 ** 10)}",
                    tender_type="prive",
                ))
                found_on_page += 1

            if found_on_page == 0:
                # Pas d'items sur cette page → fin de pagination ou page vide
                break

        logger.info("[BJ] Plan International : %d avis collectés", len(items))
        return items


def build() -> PlanInternationalScraper:
    return PlanInternationalScraper()
