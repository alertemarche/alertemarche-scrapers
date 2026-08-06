"""Robot de collecte — Burkina Faso 🇧🇫 (Plans de Passation des Marchés).

Source : Direction Générale du Contrôle des Marchés et des Engagements Financiers
(https://www.dgcmef.gov.bf/fr/plan-de-passation-des-march-s-publics), qui publie
les plans de passation des marchés publics (PPM) par entité publique.

Stratégie : Le robot récupère la page HTML listant les PPM, extrait les entités
et leurs avis généraux de passation. Contrairement aux quotidiens, les PPM sont
des documents de planification annuelle plutôt que des avis urgents, donc ce
scraper peut tourner moins fréquemment.
"""
import logging
import re
from datetime import date

from bs4 import BeautifulSoup

from common.html_base import HtmlScraper
from common import procedures

logger = logging.getLogger("scrapers.burkina_faso.ppm")

PAGE_URL = "https://www.dgcmef.gov.bf/fr/plan-de-passation-des-march-s-publics"
BASE_URL = "https://www.dgcmef.gov.bf"


class PlanPassationScraper(HtmlScraper):
    country = "BF"
    source_name = "DGCMEF - Plans de Passation des Marchés (Burkina Faso)"
    tender_type = "public"
    method = "html"

    def _extract_entities(self, html: str) -> list[tuple[str, str, str | None]]:
        """Extrait les entités et leurs documents PPM depuis la page HTML.
        
        Returns:
            Liste de tuples (entité, url_pdf_ppm, url_pdf_avis)
        """
        soup = BeautifulSoup(html, "lxml")
        entities = []
        
        # Recherche des lignes du tableau PPM
        # Format : Entité | Fichiers (PPM + Avis Général)
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                entity_cell = cells[0]
                files_cell = cells[1]
                
                entity_name = entity_cell.get_text(strip=True)
                if not entity_name or len(entity_name) < 3:
                    continue
                
                # Extraire les liens vers les fichiers
                links = files_cell.find_all("a", href=True)
                ppm_url = None
                avis_url = None
                
                for link in links:
                    href = link["href"]
                    link_text = link.get_text(strip=True).upper()
                    
                    if not href.startswith("http"):
                        href = BASE_URL + href
                    
                    # Distinguer PPM et Avis Général
                    if "AVIS" in link_text and "GENERAL" in link_text:
                        avis_url = href
                    elif "PLAN" in link_text or "PPM" in link_text or not avis_url:
                        ppm_url = href
                
                if ppm_url or avis_url:
                    entities.append((entity_name, ppm_url or avis_url, avis_url))
        
        return entities

    def _create_ppm_item(self, entity: str, ppm_url: str | None, avis_url: str | None) -> dict | None:
        """Crée un item structuré pour un Plan de Passation.
        
        Les PPM sont des documents de planification annuelle, pas des AO individuels.
        On crée donc un "tender" agrégé représentant les projets planifiés de l'entité.
        
        Args:
            entity: Nom de l'entité publique
            ppm_url: URL du document PPM (si disponible)
            avis_url: URL de l'avis général (préféré si disponible)
            
        Returns:
            Dictionnaire structuré ou None
        """
        if not entity:
            return None
        
        # Titre descriptif
        current_year = date.today().year
        title = f"Plan de Passation des Marchés {current_year} - {entity}"
        
        # L'avis général est prioritaire sur le PPM brut pour l'URL source
        source_url = avis_url or ppm_url or PAGE_URL
        
        # Référence unique
        # On nettoie le nom de l'entité pour créer un slug stable
        entity_slug = re.sub(r'[^\w\s-]', '', entity).strip()
        entity_slug = re.sub(r'[-\s]+', '-', entity_slug)[:50]
        external_id = f"BF-PPM-{current_year}-{entity_slug}"
        
        return self.make_item(
            title=self.fix_encoding(title),
            institution=self.fix_encoding(entity),
            reference=f"PPM-{current_year}",
            publication_date=f"{current_year}-01-01",  # Date fictive (début d'année)
            market_type="Plan de passation",
            procedure_type="Avis général",
            source_url=source_url,
            external_id=external_id,
        )

    def collect(self) -> list[dict]:
        """Point d'entrée principal du scraper PPM."""
        items = []
        
        try:
            # 1. Récupérer la page HTML listant les PPM
            html = self.fetch_html(PAGE_URL)
            if not html:
                logger.warning("Impossible de récupérer la page HTML des PPM")
                return []
            
            # 2. Extraire les entités et leurs documents
            entities = self._extract_entities(html)
            logger.info(f"Trouvé {len(entities)} entités avec PPM")
            
            # 3. Créer un item pour chaque entité
            for entity_name, ppm_url, avis_url in entities:
                item = self._create_ppm_item(entity_name, ppm_url, avis_url)
                if item:
                    items.append(item)
            
            logger.info(f"Total : {len(items)} plans de passation collectés pour le Burkina Faso")
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des PPM Burkina Faso : {e}")
        
        return items


def build() -> PlanPassationScraper:
    return PlanPassationScraper()
