"""
Scraper pour le portail gouvernemental du Bénin
https://www.gouv.bj/articles/appels-doffres/
"""
import logging
import re
from urllib.parse import urljoin
from common.html_base import HtmlScraper


class GouvBjScraper(HtmlScraper):
    """Scraper pour gouv.bj - Portail gouvernemental Bénin"""
    
    BASE_URL = "https://www.gouv.bj"
    LISTING_URL = "https://www.gouv.bj/articles/appels-doffres/"
    
    def __init__(self):
        super().__init__()
        self.country = "BJ"
        self.source_name = "Portail Gouvernemental Bénin (gouv.bj)"
        self.tender_type = "public"
    
    def collect(self):
        """Collect tenders from the government portal"""
        logging.info(f"[{self.source_name}] Fetching {self.LISTING_URL}")
        soup = self.soup(self.LISTING_URL)
        if not soup:
            logging.warning(f"[{self.source_name}] No HTML content")
            return []
        
        items = []
        
        # Strategy 1: Find article cards
        articles = soup.find_all("article")
        if articles:
            logging.info(f"[{self.source_name}] Found {len(articles)} articles")
            for article in articles:
                try:
                    item = self._parse_article(article)
                    if item and self.is_active(item):
                        items.append(item)
                except Exception as e:
                    logging.warning(f"[{self.source_name}] Error parsing article: {e}")
                    continue
        
        # Strategy 2: Find any links to tender pages
        if not items:
            links = soup.find_all("a", href=re.compile(r"(appel|offre|marche|tender)", re.I))
            logging.info(f"[{self.source_name}] Found {len(links)} potential tender links")
            for link in links[:50]:  # Limit to first 50
                try:
                    item = self._parse_link(link)
                    if item and self.is_active(item):
                        items.append(item)
                except Exception as e:
                    logging.warning(f"[{self.source_name}] Error parsing link: {e}")
                    continue
        
        logging.info(f"[{self.source_name}] Collected {len(items)} active tenders")
        return items
    
    def _parse_article(self, article):
        """Parse an article element"""
        # Find title link
        title_elem = article.find(["h1", "h2", "h3", "h4", "a"])
        if not title_elem:
            return None
        
        title = self.clean(title_elem.get_text())
        
        # Find source URL
        link = article.find("a")
        source_url = urljoin(self.BASE_URL, link.get("href", "")) if link else self.LISTING_URL
        
        # Extract deadline
        deadline = None
        article_text = article.get_text()
        deadline = self._extract_date(article_text, keyword="limite|cl[ôo]ture|deadline")
        
        # Extract publication date
        publication_date = self._extract_date(article_text, keyword="publi|post|date")
        
        # Extract reference
        reference = None
        ref_match = re.search(r'(N[°o]?\s*[\d\-/A-Z]{3,})', article_text)
        if ref_match:
            reference = ref_match.group(1)
        
        # Extract DAO URL
        dao_url = None
        pdf_link = article.find("a", href=re.compile(r'\.pdf$', re.I))
        if pdf_link:
            dao_url = urljoin(self.BASE_URL, pdf_link.get("href", ""))
        
        external_id = f"gouvbj-{reference}" if reference else f"gouvbj-{source_url.split('/')[-2]}"
        
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
    
    def _parse_link(self, link):
        """Parse a simple link element"""
        title = self.clean(link.get_text())
        if len(title) < 10:
            return None
        
        source_url = urljoin(self.BASE_URL, link.get("href", ""))
        
        # Try to extract info from parent context
        parent = link.find_parent(["div", "article", "li"])
        context_text = parent.get_text() if parent else link.get_text()
        
        deadline = self._extract_date(context_text, keyword="limite|cl[ôo]ture")
        reference = None
        ref_match = re.search(r'(N[°o]?\s*[\d\-/A-Z]{3,})', context_text)
        if ref_match:
            reference = ref_match.group(1)
        
        external_id = f"gouvbj-{reference}" if reference else f"gouvbj-{source_url.split('/')[-1]}"
        
        return self.make_item(
            title=title,
            institution="",
            deadline=deadline,
            source_url=source_url,
            external_id=external_id,
            reference=reference,
        )
    
    def _extract_date(self, text, keyword=None):
        """Extract date from text with optional keyword filter"""
        if keyword:
            # Find context around keyword
            match = re.search(rf"({keyword})\s*:?\s*([^\n<>]{{0,50}})", text, re.I)
            if match:
                text = match.group(2)
        
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
    return GouvBjScraper()
