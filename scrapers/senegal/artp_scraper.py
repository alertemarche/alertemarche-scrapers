"""
Scraper pour l'Autorité de Régulation des Télécommunications et des Postes (ARTP) du Sénégal
Source: https://artp.sn/espace-professionnels/appels-d-offres/
"""

import logging
import re
import time
from urllib.parse import urljoin
from common.html_base import HtmlScraper
from common import config


class ArtpScraper(HtmlScraper):
    country = "SN"
    source_name = "ARTP — Autorité de Régulation des Télécommunications et des Postes"
    tender_type = "public"
    
    BASE_URL = "https://artp.sn/espace-professionnels/appels-d-offres/"
    MAX_ITEMS = 50  # Limite pour éviter les très vieux avis
    
    def fetch_html(self, url: str, params: dict | None = None) -> str | None:
        """Surcharge fetch_html pour désactiver la vérification SSL (certificat ARTP)."""
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=params,
                                        timeout=config.REQUEST_TIMEOUT, verify=False)
                resp.raise_for_status()
                if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
                    resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            except Exception as exc:
                logging.warning("[%s] GET %s échec %s/%s : %s",
                               self.country, url, attempt, config.MAX_RETRIES, exc)
                time.sleep(1.2 * attempt)
        return None
    
    def collect(self) -> list:
        """Collecte les appels d'offres depuis la page ARTP"""
        items = []
        
        try:
            soup = self.soup(self.BASE_URL)
            if not soup:
                logging.warning(f"{self.source_name}: Impossible d'accéder à {self.BASE_URL}")
                return []
            
            # Trouver tous les articles d'appels d'offres
            articles = soup.find_all('article', class_=re.compile(r'node--type-appel-d-offre'))
            
            if not articles:
                logging.warning(f"{self.source_name}: Aucun article trouvé")
                return []
            
            logging.info(f"{self.source_name}: {len(articles)} articles trouvés")
            
            for art in articles[:self.MAX_ITEMS]:
                try:
                    # Titre
                    title_elem = art.find(['h2', 'h3', 'a'])
                    if not title_elem:
                        continue
                    
                    title = self.clean(title_elem.get_text())
                    if not title:
                        continue
                    
                    # Lien source
                    link_elem = art.find('a', href=True)
                    if not link_elem:
                        continue
                    
                    source_url = urljoin(self.BASE_URL, link_elem['href'])
                    
                    # external_id depuis l'URL (dernière partie du slug)
                    external_id = source_url.split('/')[-1] or source_url.split('/')[-2]
                    if not external_id:
                        # Fallback sur le titre nettoyé
                        external_id = re.sub(r'[^a-z0-9]+', '-', title.lower())[:50]
                    
                    external_id = f"artp-{external_id}"
                    
                    # Date de publication
                    date_elem = art.find(class_=re.compile(r'date|time', re.I))
                    publication_date = None
                    
                    if date_elem:
                        date_text = self.clean(date_elem.get_text())
                        publication_date = self.parse_fr_date(date_text)
                    
                    # Chercher une référence dans le titre
                    reference = None
                    ref_match = re.search(
                        r'(N°|n°|REF|Réf)[:\s]*([A-Z0-9/-]+)',
                        title
                    )
                    if ref_match:
                        reference = ref_match.group(2)
                    
                    # Créer l'item (institution="" pour utiliser self.source_name par défaut)
                    item = self.make_item(
                        title=title,
                        institution="",  # Utilisera self.source_name (ARTP)
                        source_url=source_url,
                        external_id=external_id,
                        publication_date=publication_date,
                        reference=reference
                    )
                    
                    # Filtrer les avis expirés (is_active prend deadline, pas l'item entier)
                    if self.is_active(item.get('deadline')):
                        items.append(item)
                
                except Exception as e:
                    logging.warning(f"{self.source_name}: Erreur article: {e}")
                    continue
            
            logging.info(f"{self.source_name}: {len(items)} avis actifs collectés")
            
        except Exception as e:
            logging.error(f"{self.source_name}: Erreur collect: {e}")
            return []
        
        return items


def build():
    """Point d'entrée pour run_all.py"""
    return ArtpScraper()
