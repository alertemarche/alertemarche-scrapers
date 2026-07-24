"""
Scraper pour le portail des services publics du Togo
https://service-public.gouv.tg/category/marches-publics/
"""
import logging
import re
from urllib.parse import urljoin
from common.html_base import HtmlScraper


class ServicePublicTgScraper(HtmlScraper):
    """Scraper pour service-public.gouv.tg - Portail services publics Togo"""
    
    BASE_URL = "https://service-public.gouv.tg"
    LISTING_URL = "https://service-public.gouv.tg/category/marches-publics/"
    
    def __init__(self):
        super().__init__()
        self.country = "TG"
        self.source_name = "Portail Services Publics Togo"
        self.tender_type = "public"
    
    def collect(self):
        """Collect tenders from the public services portal"""
        logging.info(f"[{self.source_name}] Fetching {self.LISTING_URL}")
        soup = self.soup(self.LISTING_URL)
        if not soup:
            logging.warning(f"[{self.source_name}] No HTML content")
            return []
        
        items = []
        
        # Find article/card elements
        articles = soup.find_all(["article", "div"], class_=re.compile(r"(post|card|item|marche)", re.I))
        
        if not articles:
            # Fallback: find links
            articles = soup.find_all("a", href=re.compile(r"(marche|appel|offre)", re.I))
        
        logging.info(f"[{self.source_name}] Found {len(articles)} items")
        
        for article in articles:
            try:
                item = self._parse_article(article)
                if item and self.is_active(item):
                    items.append(item)
            except Exception as e:
                logging.warning(f"[{self.source_name}] Error parsing article: {e}")
                continue
        
        logging.info(f"[{self.source_name}] Collected {len(items)} active tenders")
        return items
    
    def _parse_article(self, article):
        """Parse an article element"""
        # Find title
        title_elem = article.find(["h1", "h2", "h3", "h4"])
        if not title_elem:
            title_elem = article.find("a")
        
        if not title_elem:
            return None
        
        title = self.clean(title_elem.get_text())
        if len(title) < 10:
            return None
        
        # Find source URL
        link = article.find("a")
        source_url = urljoin(self.BASE_URL, link.get("href", "")) if link else self.LISTING_URL
        
        # Extract info from article text
        article_text = article.get_text()
        
        # Extract deadline
        deadline = None
        deadline_match = re.search(r"(date.*limite|cl[ôo]ture|deadline|expire)\s*:?\s*([^\n<>]{0,50})", article_text, re.I)
        if deadline_match:
            deadline = self._extract_date(deadline_match.group(2))
        else:
            deadline = self._extract_date(article_text)
        
        # Extract publication date
        publication_date = None
        pub_elem = article.find(class_=re.compile(r"(date|time|post)", re.I))
        if pub_elem:
            publication_date = self._extract_date(pub_elem.get_text())
        
        # Extract reference
        reference = None
        ref_match = re.search(r'(N[°o]?\s*[\d\-/A-Z]{3,}|R[éÉ]f[\.\s]*:?\s*[\d\-/A-Z]{3,})', article_text)
        if ref_match:
            reference = ref_match.group(1)
        
        # Extract DAO URL
        dao_url = None
        pdf_link = article.find("a", href=re.compile(r'\.pdf$', re.I))
        if pdf_link:
            dao_url = urljoin(self.BASE_URL, pdf_link.get("href", ""))
        
        external_id = f"sptg-{reference}" if reference else f"sptg-{source_url.split('/')[-2]}"
        
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
    return ServicePublicTgScraper()
