"""
Scraper pour la DNCCP Togo (Direction Nationale de Contrôle de la Commande Publique)
https://dnccp.gouv.tg/dnccp/liste-des-marches/
"""
import logging
import re
from urllib.parse import urljoin
from common.html_base import HtmlScraper


class DnccpNewScraper(HtmlScraper):
    """Scraper pour dnccp.gouv.tg - DNCCP Togo"""
    
    BASE_URL = "https://dnccp.gouv.tg"
    LISTING_URL = "https://dnccp.gouv.tg/dnccp/liste-des-marches/"
    
    def __init__(self):
        super().__init__()
        self.country = "TG"
        self.source_name = "DNCCP Togo (Direction Nationale de Contrôle)"
        self.tender_type = "public"
    
    def collect(self):
        """Collect tenders from DNCCP portal"""
        logging.info(f"[{self.source_name}] Fetching {self.LISTING_URL}")
        soup = self.soup(self.LISTING_URL)
        if not soup:
            logging.warning(f"[{self.source_name}] No HTML content")
            return []
        
        items = []
        
        # Strategy 1: Find table rows
        tables = soup.find_all("table")
        if tables:
            logging.info(f"[{self.source_name}] Found {len(tables)} tables")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:  # Skip header
                    try:
                        item = self._parse_row(row)
                        if item and self.is_active(item):
                            items.append(item)
                    except Exception as e:
                        logging.warning(f"[{self.source_name}] Error parsing row: {e}")
                        continue
        
        # Strategy 2: Find list items or cards
        if not items:
            cards = soup.find_all(["div", "article", "li"], class_=re.compile(r"(marche|contract|tender|item)", re.I))
            logging.info(f"[{self.source_name}] Found {len(cards)} cards")
            for card in cards:
                try:
                    item = self._parse_card(card)
                    if item and self.is_active(item):
                        items.append(item)
                except Exception as e:
                    logging.warning(f"[{self.source_name}] Error parsing card: {e}")
                    continue
        
        logging.info(f"[{self.source_name}] Collected {len(items)} active tenders")
        return items
    
    def _parse_row(self, row):
        """Parse a table row"""
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            return None
        
        # Extract data
        title = None
        reference = None
        deadline = None
        source_url = None
        institution = None
        
        for cell in cells:
            cell_text = self.clean(cell.get_text())
            
            # Find link (usually the title)
            link = cell.find("a")
            if link and len(cell_text) > 10:
                if not title:
                    title = cell_text
                    source_url = urljoin(self.BASE_URL, link.get("href", ""))
            
            # Reference pattern
            if re.search(r'(N[°o]?\s*[\d\-/A-Z]{3,})', cell_text):
                reference = cell_text
            
            # Date pattern
            if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', cell_text):
                deadline = self._extract_date(cell_text)
            
            # Institution (usually contains "ministère", "direction", etc.)
            if re.search(r'(minist[èe]re|direction|autorit[ée]|agence)', cell_text, re.I):
                institution = cell_text
        
        if not title:
            # Use first cell with text
            for cell in cells:
                text = self.clean(cell.get_text())
                if len(text) > 10:
                    title = text
                    break
        
        if not title:
            return None
        
        external_id = f"dnccp-{reference}" if reference else f"dnccp-{self.clean(title)[:30]}"
        
        return self.make_item(
            title=title,
            institution="",
            deadline=deadline,
            source_url=source_url or self.LISTING_URL,
            external_id=external_id,
            reference=reference,
            institution=institution,
        )
    
    def _parse_card(self, card):
        """Parse a card/item element"""
        # Find title
        title_elem = card.find(["h1", "h2", "h3", "h4", "a"])
        if not title_elem:
            return None
        
        title = self.clean(title_elem.get_text())
        if len(title) < 10:
            return None
        
        # Find link
        link = card.find("a")
        source_url = urljoin(self.BASE_URL, link.get("href", "")) if link else self.LISTING_URL
        
        # Extract from card text
        card_text = card.get_text()
        
        # Reference
        reference = None
        ref_match = re.search(r'(N[°o]?\s*[\d\-/A-Z]{3,})', card_text)
        if ref_match:
            reference = ref_match.group(1)
        
        # Deadline
        deadline = self._extract_date(card_text)
        
        # DAO URL
        dao_url = None
        pdf_link = card.find("a", href=re.compile(r'\.pdf$', re.I))
        if pdf_link:
            dao_url = urljoin(self.BASE_URL, pdf_link.get("href", ""))
        
        external_id = f"dnccp-{reference}" if reference else f"dnccp-{source_url.split('/')[-1]}"
        
        return self.make_item(
            title=title,
            institution="",
            deadline=deadline,
            source_url=source_url,
            external_id=external_id,
            reference=reference,
            dao_url=dao_url,
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
    return DnccpNewScraper()
