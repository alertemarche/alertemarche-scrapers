"""Robot de collecte — Burkina Faso 🇧🇫 (source officielle : DGCMEF Quotidien).

Source : Direction Générale du Contrôle des Marchés et des Engagements Financiers
(https://www.dgcmef.gov.bf/fr/appels-d-offre), qui publie quotidiennement le
"Quotidien des Marchés Publics" en format PDF.

Stratégie : Le robot récupère la page HTML listant les quotidiens, extrait les
liens vers les PDFs des derniers jours (par défaut 3 jours), télécharge et parse
chaque PDF pour extraire les appels d'offres. Seules des MÉTADONNÉES sont
collectées ; les fichiers PDF ne sont jamais stockés.
"""
import io
import logging
import re
from datetime import date, datetime, timedelta

import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup

from common.html_base import HtmlScraper
from common import procedures

logger = logging.getLogger("scrapers.burkina_faso")

PAGE_URL = "https://www.dgcmef.gov.bf/fr/appels-d-offre"
PORTAIL_LISTING = "https://www.dgcmef.gov.bf/fr/appels-d-offre"
MAX_DAYS_BACK = 3  # Nombre de jours à remonter dans l'historique
BASE_URL = "https://www.dgcmef.gov.bf"


class BurkinaFasoScraper(HtmlScraper):
    country = "BF"
    source_name = "DGCMEF - Quotidien des Marchés Publics du Burkina Faso"
    tender_type = "public"
    method = "html+pdf"

    def _extract_pdf_links(self, html: str) -> list[tuple[str, str]]:
        """Extrait les liens vers les PDFs quotidiens et leurs titres.
        
        Returns:
            Liste de tuples (titre, url_pdf)
        """
        soup = BeautifulSoup(html, "lxml")
        pdf_links = []
        
        # Recherche des lignes du tableau contenant les quotidiens
        # Format attendu : "Quotidien n°XXXX – Date"
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                title_cell = cells[0]
                file_cell = cells[1]
                
                title = title_cell.get_text(strip=True)
                link_tag = file_cell.find("a", href=True)
                
                if link_tag and "Quotidien" in title:
                    pdf_url = link_tag["href"]
                    if not pdf_url.startswith("http"):
                        pdf_url = BASE_URL + pdf_url
                    pdf_links.append((title, pdf_url))
        
        # Limiter aux N derniers quotidiens (les plus récents sont en premier)
        return pdf_links[:MAX_DAYS_BACK]

    def _parse_pdf_content(self, pdf_url: str, pdf_title: str) -> list[dict]:
        """Télécharge et parse un PDF quotidien pour extraire les appels d'offres.
        
        Args:
            pdf_url: URL du PDF à télécharger
            pdf_title: Titre du quotidien (pour extraction de date)
            
        Returns:
            Liste des appels d'offres extraits
        """
        items = []
        
        try:
            # Télécharger le PDF
            logger.info(f"Téléchargement du PDF : {pdf_title}")
            resp = self.session.get(pdf_url, timeout=30)
            resp.raise_for_status()
            
            # Parser le PDF
            doc = fitz.open(stream=resp.content, filetype="pdf")
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            doc.close()
            
            # Extraction de la date de publication depuis le titre
            # Format : "Quotidien n°4460 – Jeudi 06 Août 2026"
            publication_date = self._extract_publication_date(pdf_title)
            
            # Parser le contenu pour extraire les appels d'offres
            tenders = self._extract_tenders_from_text(full_text, publication_date, pdf_url)
            items.extend(tenders)
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing du PDF {pdf_title}: {e}")
        
        return items

    def _extract_publication_date(self, title: str) -> str | None:
        """Extrait la date de publication depuis le titre du quotidien.
        
        Args:
            title: Titre du quotidien (ex: "Quotidien n°4460 – Jeudi 06 Août 2026")
            
        Returns:
            Date au format YYYY-MM-DD ou None
        """
        # Pattern : Jour DD Mois YYYY
        match = re.search(r'(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})', title)
        if match:
            day = match.group(1).zfill(2)
            month_name = match.group(2).lower()
            year = match.group(3)
            
            # Conversion du mois français en numéro
            month_map = {
                'janvier': '01', 'février': '02', 'fevrier': '02', 'mars': '03',
                'avril': '04', 'mai': '05', 'juin': '06', 'juillet': '07',
                'août': '08', 'aout': '08', 'septembre': '09', 'octobre': '10',
                'novembre': '11', 'décembre': '12', 'decembre': '12'
            }
            month = month_map.get(month_name, '01')
            
            return f"{year}-{month}-{day}"
        
        return None

    def _extract_tenders_from_text(self, text: str, publication_date: str | None, pdf_url: str) -> list[dict]:
        """Extrait les appels d'offres individuels depuis le texte du PDF.
        
        Args:
            text: Texte complet du PDF
            publication_date: Date de publication du quotidien
            pdf_url: URL du PDF source
            
        Returns:
            Liste des appels d'offres structurés
        """
        items = []
        
        # Pattern pour identifier les appels d'offres
        # Les quotidiens burkinabè suivent généralement un format structuré :
        # - Numéro d'avis
        # - Autorité contractante
        # - Objet
        # - Type de procédure
        # - Date limite de dépôt
        
        # Découpage du texte en sections (chaque AO commence souvent par un numéro)
        # Pattern commun : "AVIS N° XXX" ou "Avis d'Appel d'Offres N° XXX"
        ao_pattern = r'AVIS\s+(?:D[\'\u2019]APPEL\s+D[\'\u2019]OFFRES?\s+)?N[°O]\s*[:\s]*(\S+)'
        sections = re.split(ao_pattern, text, flags=re.IGNORECASE)
        
        # Traiter chaque section (en sautant le préambule)
        for i in range(1, len(sections), 2):
            if i + 1 >= len(sections):
                break
                
            reference = sections[i].strip()
            content = sections[i + 1]
            
            # Extraire les informations de cette section
            tender = self._parse_tender_section(reference, content, publication_date, pdf_url)
            if tender:
                items.append(tender)
        
        # Si aucun AO n'a été trouvé avec le pattern principal, essayer un pattern alternatif
        if not items:
            items = self._fallback_extraction(text, publication_date, pdf_url)
        
        return items

    def _parse_tender_section(self, reference: str, content: str, publication_date: str | None, pdf_url: str) -> dict | None:
        """Parse une section de texte représentant un appel d'offres.
        
        Args:
            reference: Numéro de référence de l'AO
            content: Contenu textuel de la section
            publication_date: Date de publication
            pdf_url: URL source
            
        Returns:
            Dictionnaire structuré de l'AO ou None si parsing échoué
        """
        # Extraction de l'objet (souvent après "Objet :" ou "OBJET :")
        title_match = re.search(r'OBJET\s*[:\-]\s*(.+?)(?:\n|Lot|Mode|Financement|Date)', content, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else None
        
        if not title or len(title) < 10:
            # Tentative alternative : chercher des patterns spécifiques d'objets de marché
            # Patterns positifs : "travaux", "fourniture", "construction", "acquisition", "réhabilitation"
            lines = [l.strip() for l in content.split('\n') if len(l.strip()) > 15]
            
            # Filtrer les lignes qui ressemblent à des vrais objets de marché
            for line in lines:
                line_lower = line.lower()
                # Mots-clés positifs (vrais objets de marché)
                positive_keywords = ['travaux', 'fourniture', 'construction', 'acquisition', 
                                     'réhabilitation', 'réalisation', 'service', 'prestation',
                                     'aménagement', 'installation', 'étude', 'consultant']
                # Patterns à rejeter (messages d'erreur, remarques, références)
                reject_patterns = [
                    r'^non[\s\-]',  # "Non conforme", "Non-respect"
                    r'^n[°o]\s*\d',  # "N°3827", "No 123"
                    r'conforme|conformité',  # Messages de conformité
                    r'^prospectus',  # "prospectus non conforme"
                    r'^offre\s+non',  # "offre non retenue"
                    r'^lettre\s+de',  # "lettre de ..."
                    r'^modèle',  # "modèle de ..."
                ]
                
                # Rejeter si match un pattern négatif
                if any(re.search(pattern, line_lower) for pattern in reject_patterns):
                    continue
                
                # Accepter si contient un mot-clé positif
                if any(kw in line_lower for kw in positive_keywords):
                    title = line
                    break
        
        if not title or len(title) < 10:
            return None
        
        title = self.fix_encoding(title[:500])  # Limiter la longueur
        
        # Extraction de l'autorité contractante
        institution_match = re.search(
            r'(?:Autorit[ée]\s+contractante|Ma[îi]tre\s+d[\'\u2019]ouvrage|MAITRISE\s+D[\'\u2019]OUVRAGE)\s*[:\-]\s*(.+?)(?:\n|OBJET)',
            content,
            re.IGNORECASE | re.DOTALL
        )
        institution = self.fix_encoding(institution_match.group(1).strip()[:300]) if institution_match else self.source_name
        
        # Extraction du type de procédure
        proc_match = re.search(
            r'(?:Mode\s+de\s+passation|Proc[ée]dure|M[ée]thode)\s*[:\-]\s*(.+?)(?:\n|Date|Lieu)',
            content,
            re.IGNORECASE
        )
        procedure_text = proc_match.group(1).strip() if proc_match else ""
        procedure_type = procedures.from_text(procedure_text) or procedures.from_text(title)
        
        # Extraction de la date limite
        deadline_match = re.search(
            r'Date\s+(?:et\s+heure\s+)?limite\s+(?:de\s+)?(?:d[ée]p[ôo]t|remise)\s*[:\-]\s*(.+?)(?:\n|Lieu|$)',
            content,
            re.IGNORECASE
        )
        deadline_str = deadline_match.group(1).strip() if deadline_match else None
        deadline = self._parse_deadline_date(deadline_str) if deadline_str else None
        
        # Extraction du lieu
        location_match = re.search(
            r'Lieu\s+(?:de\s+)?(?:d[ée]p[ôo]t|remise)\s*[:\-]\s*(.+?)(?:\n|Date|$)',
            content,
            re.IGNORECASE
        )
        location = self.fix_encoding(location_match.group(1).strip()[:200]) if location_match else None
        
        # Type de marché
        market_type_match = re.search(
            r'(?:Type\s+de\s+march[ée]|Nature)\s*[:\-]\s*(.+?)(?:\n|Mode)',
            content,
            re.IGNORECASE
        )
        market_type = self.fix_encoding(market_type_match.group(1).strip()[:100]) if market_type_match else None
        
        return self.make_item(
            title=title,
            institution=institution,
            reference=reference,
            location=location,
            deadline=deadline,
            publication_date=publication_date,
            market_type=market_type,
            procedure_type=procedure_type,
            source_url=pdf_url,
            external_id=f"BF-{reference}" if reference else None,
        )

    def _parse_deadline_date(self, deadline_str: str) -> str | None:
        """Parse une date limite depuis le texte (format variable).
        
        Args:
            deadline_str: Chaîne contenant la date (ex: "15 août 2026 à 10h00")
            
        Returns:
            Date au format YYYY-MM-DD ou None
        """
        # Pattern : DD Mois YYYY
        match = re.search(r'(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})', deadline_str)
        if match:
            day = match.group(1).zfill(2)
            month_name = match.group(2).lower()
            year = match.group(3)
            
            month_map = {
                'janvier': '01', 'février': '02', 'fevrier': '02', 'mars': '03',
                'avril': '04', 'mai': '05', 'juin': '06', 'juillet': '07',
                'août': '08', 'aout': '08', 'septembre': '09', 'octobre': '10',
                'novembre': '11', 'décembre': '12', 'decembre': '12'
            }
            month = month_map.get(month_name, '01')
            
            return f"{year}-{month}-{day}"
        
        # Pattern alternatif : DD/MM/YYYY
        match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', deadline_str)
        if match:
            day = match.group(1).zfill(2)
            month = match.group(2).zfill(2)
            year = match.group(3)
            return f"{year}-{month}-{day}"
        
        return None

    def _fallback_extraction(self, text: str, publication_date: str | None, pdf_url: str) -> list[dict]:
        """Extraction de secours si le pattern principal échoue.
        
        Recherche des marqueurs alternatifs communs dans les quotidiens burkinabè.
        """
        items = []
        
        # Pattern alternatif : recherche de sections séparées par plusieurs sauts de ligne
        # ou par des marqueurs comme "***", "---", numéros de page, etc.
        paragraphs = re.split(r'\n{3,}|[\-*]{3,}', text)
        
        for para in paragraphs:
            para = para.strip()
            if len(para) < 100:  # Trop court pour être un AO complet
                continue
            
            # Vérifier si le paragraphe contient des mots-clés d'AO
            keywords = ['appel', 'offre', 'march[ée]', 'soumission', 'consultation']
            if not any(re.search(kw, para, re.IGNORECASE) for kw in keywords):
                continue
            
            # Extraction basique
            lines = [l.strip() for l in para.split('\n') if len(l.strip()) > 10]
            if len(lines) < 2:
                continue
            
            title = self.fix_encoding(lines[0][:500])
            
            item = self.make_item(
                title=title,
                institution=self.source_name,
                publication_date=publication_date,
                source_url=pdf_url,
            )
            items.append(item)
        
        return items[:20]  # Limiter au cas où l'extraction est trop permissive

    def collect(self) -> list[dict]:
        """Point d'entrée principal du scraper."""
        items = []
        
        try:
            # 1. Récupérer la page HTML listant les quotidiens
            html = self.fetch_html(PAGE_URL)
            if not html:
                logger.warning("Impossible de récupérer la page HTML des quotidiens")
                return []
            
            # 2. Extraire les liens vers les PDFs quotidiens
            pdf_links = self._extract_pdf_links(html)
            logger.info(f"Trouvé {len(pdf_links)} quotidiens à parser")
            
            # 3. Parser chaque PDF
            for title, url in pdf_links:
                pdf_items = self._parse_pdf_content(url, title)
                # On ne conserve que les marchés ACTIFS (échéance future ou
                # absente) — cohérent avec le fonctionnement des autres pays.
                active = [it for it in pdf_items if self.is_active(it.get("deadline"))]
                items.extend(active)
                logger.info(
                    f"Extrait {len(active)}/{len(pdf_items)} AO actifs depuis {title}")
            
            logger.info(f"Total : {len(items)} appels d'offres actifs collectés pour le Burkina Faso")
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte Burkina Faso : {e}")
        
        return items


def build() -> BurkinaFasoScraper:
    return BurkinaFasoScraper()
