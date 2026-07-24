"""
Scraper pour le site de l'ARMP Bénin
https://armp.bj/category/actualites/appels-doffres/
"""
import logging
import re
from urllib.parse import urljoin
from common.html_base import HtmlScraper


class ArmpBjScraper(HtmlScraper):
    """Scraper pour armp.bj - ARMP Bénin"""
    
    BASE_URL = "https://armp.bj"
    LISTING_URL = "https://armp.bj/category/actualites/appels-doffres/"
    
    def __init__(self):
        super().__init__()
        self.country = "BJ"
        self.source_name = "ARMP Bénin (Autorité de Régulation)"
        self.tender_type = "public"
    
    def collect(self):
        """Collect tenders from ARMP website"""
        logging.info(f"[{self.source_name}] Fetching {self.LISTING_URL}")
        soup = self.soup(self.LISTING_URL)
        if not soup:
            logging.warning(f"[{self.source_name}] No HTML content")
            return []
        
        items = []
        
        # Find article/post elements
        posts = soup.find_all(["article", "div"], class_=re.compile(r"(post|article|entry|item)", re.I))
        
        if not posts:
            # Fallback: find any links to tender pages
            posts = soup.find_all("a", href=re.compile(r"(appel|offre)", re.I))
        
        logging.info(f"[{self.source_name}] Found {len(posts)} potential items")
        
        for post in posts:
            try:
                item = self._parse_post(post)
                if item and self.is_active(item):
                    items.append(item)
            except Exception as e:
                logging.warning(f"[{self.source_name}] Error parsing post: {e}")
                continue
        
        logging.info(f"[{self.source_name}] Collected {len(items)} active tenders")
        return items
    
    def _parse_post(self, post):
        """Parse a post/article element"""
        # Find title
        title_elem = post.find(["h1", "h2", "h3", "h4", "a"], class_=re.compile(r"title|heading", re.I))
        if not title_elem:
            title_elem = post.find("a")
        
        if not title_elem:
            return None
        
        title = self.clean(title_elem.get_text())
        if len(title) < 10:
            return None
        
        # Find source URL
        link = title_elem if title_elem.name == "a" else title_elem.find("a")
        if not link:
            link = post.find("a")
        
        source_url = urljoin(self.BASE_URL, link.get("href", "")) if link else self.LISTING_URL
        
        # Extract date info from post
        post_text = post.get_text()
        
        # Extract deadline
        deadline = None
        deadline_match = re.search(r"(date.*limite|cl[ôo]ture|deadline)\s*:?\s*([^\n<>]{0,50})", post_text, re.I)
        if deadline_match:
            deadline = self._extract_date(deadline_match.group(2))
        else:
            deadline = self._extract_date(post_text)
        
        # Extract publication date
        publication_date = None
        pub_elem = post.find(class_=re.compile(r"(date|time|publish)", re.I))
        if pub_elem:
            publication_date = self._extract_date(pub_elem.get_text())
        
        # Extract reference
        reference = None
        ref_match = re.search(r'(N[°o]?\s*[\d\-/A-Z]{3,}|R[éÉ]f[\.\s]*:?\s*[\d\-/A-Z]{3,})', post_text)
        if ref_match:
            reference = ref_match.group(1)
        
        # Extract DAO URL
        dao_url = None
        pdf_link = post.find("a", href=re.compile(r'\.pdf$', re.I))
        if pdf_link:
            dao_url = urljoin(self.BASE_URL, pdf_link.get("href", ""))
        
        external_id = f"armpbj-{reference}" if reference else f"armpbj-{source_url.split('/')[-2]}"
        
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
    return ArmpBjScraper()
