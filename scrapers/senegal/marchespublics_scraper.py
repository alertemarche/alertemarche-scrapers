"""
Scraper pour le portail national des marchés publics du Sénégal
https://www.marchespublics.sn/
"""
import logging
import re
from urllib.parse import urljoin
from common.html_base import HtmlScraper


class MarchesPublicsSnScraper(HtmlScraper):
    """Scraper pour marchespublics.sn - Portail national Sénégal"""
    
    BASE_URL = "https://www.marchespublics.sn"
    
    def __init__(self):
        super().__init__()
        self.country = "SN"
        self.source_name = "Marchés Publics Sénégal (Portail National)"
        self.tender_type = "public"
    
    def collect(self):
        """Collect tenders from the national portal"""
        items = []
        
        # URLs candidates pour la liste des marchés
        candidate_urls = [
            f"{self.BASE_URL}/appels-doffres",
            f"{self.BASE_URL}/appel-offre",
            f"{self.BASE_URL}/liste-appels-offres",
            f"{self.BASE_URL}/",
        ]
        
        for url in candidate_urls:
            logging.info(f"[{self.source_name}] Trying {url}")
            soup = self.soup(url)
            if not soup:
                continue
            
            # Strategy 1: Find tender cards/items
            cards = soup.find_all(["article", "div"], class_=re.compile(r"(tender|marche|appel|offre|card)", re.I))
            if cards:
                logging.info(f"[{self.source_name}] Found {len(cards)} tender cards")
                for card in cards:
                    try:
                        item = self._parse_card(card)
                        if item and self.is_active(item):
                            items.append(item)
                    except Exception as e:
                        logging.warning(f"[{self.source_name}] Error parsing card: {e}")
                        continue
                
                if items:
                    break
            
            # Strategy 2: Find table rows
            rows = soup.find_all("tr")
            if len(rows) > 5:  # At least some data rows
                logging.info(f"[{self.source_name}] Found {len(rows)} table rows")
                for row in rows[1:]:  # Skip header
                    try:
                        item = self._parse_row(row)
                        if item and self.is_active(item):
                            items.append(item)
                    except Exception as e:
                        logging.warning(f"[{self.source_name}] Error parsing row: {e}")
                        continue
                
                if items:
                    break
        
        logging.info(f"[{self.source_name}] Collected {len(items)} active tenders")
        return items
    
    def _parse_card(self, card):
        """Parse a tender card element"""
        # Find title link
        title_link = card.find("a", href=re.compile(r"(detail|offre|marche|tender)", re.I))
        if not title_link:
            title_link = card.find("a")
        
        if not title_link:
            return None
        
        title = self.clean(title_link.get_text())
        source_url = urljoin(self.BASE_URL, title_link.get("href", ""))
        
        # Extract deadline
        deadline = None
        deadline_elem = card.find(string=re.compile(r"(date.*limite|cl[ôo]ture|deadline)", re.I))
        if deadline_elem:
            deadline_text = deadline_elem.parent.get_text() if hasattr(deadline_elem, 'parent') else str(deadline_elem)
            deadline = self._extract_date(deadline_text)
        
        # Extract publication date
        publication_date = None
        pub_elem = card.find(string=re.compile(r"(publi|post)", re.I))
        if pub_elem:
            pub_text = pub_elem.parent.get_text() if hasattr(pub_elem, 'parent') else str(pub_elem)
            publication_date = self._extract_date(pub_text)
        
        # Extract reference
        reference = None
        ref_match = re.search(r'(N[°o]?\s*[\d\-/A-Z]+)', card.get_text())
        if ref_match:
            reference = ref_match.group(1)
        
        # Extract DAO URL (PDF link)
        dao_url = None
        pdf_link = card.find("a", href=re.compile(r'\.pdf$', re.I))
        if pdf_link:
            dao_url = urljoin(self.BASE_URL, pdf_link.get("href", ""))
        
        # Generate external_id
        external_id = f"mpsn-{reference}" if reference else f"mpsn-{source_url.split('/')[-1]}"
        
        return self.make_item(
            title=title,
            institution="",
            deadline=deadline,
            source_url=source_url,
            external_id=external_id,
            publication_date=publication_date,
            reference=reference,
            dao_url=dao_url,
        )
    
    def _parse_row(self, row):
        """Parse a table row"""
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            return None
        
        # Extract data from cells
        title = None
        deadline = None
        reference = None
        source_url = None
        
        for cell in cells:
            cell_text = self.clean(cell.get_text())
            
            # Look for title (usually the longest text or has a link)
            link = cell.find("a")
            if link and len(cell_text) > 20:
                title = cell_text
                source_url = urljoin(self.BASE_URL, link.get("href", ""))
            
            # Look for reference pattern
            if re.search(r'N[°o]?\s*[\d\-/A-Z]{3,}', cell_text):
                reference = cell_text
            
            # Look for date
            if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', cell_text):
                deadline = self._extract_date(cell_text)
        
        if not title:
            # Use first cell with significant text
            for cell in cells:
                text = self.clean(cell.get_text())
                if len(text) > 10:
                    title = text
                    break
        
        if not title:
            return None
        
        external_id = f"mpsn-{reference}" if reference else f"mpsn-{self.clean(title)[:30]}"
        
        return self.make_item(
            title=title,
            institution="",
            deadline=deadline,
            source_url=source_url or self.BASE_URL,
            external_id=external_id,
            reference=reference,
        )
    
    def _extract_date(self, text):
        """Extract date from text"""
        # Try DD/MM/YYYY or DD-MM-YYYY
        match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', text)
        if match:
            day, month, year = match.groups()
            if len(year) == 2:
                year = f"20{year}"
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Try French date format
        return self.parse_fr_date(text)


def build():
    return MarchesPublicsSnScraper()
