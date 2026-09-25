"""
Scraper pour le portail national des marchés publics du Sénégal
https://www.marchespublics.sn/

⚠️ IMPORTANT : Ce portail est géo-bloqué (accessible uniquement depuis le Sénégal).
Le scraper DOIT utiliser un proxy sénégalais (Webshare SN) pour fonctionner.
Configuration : voir variables SENEGAL_PROXY_* dans .env
"""
import logging
import os
import re
from urllib.parse import urljoin
from common import config
from common.html_base import HtmlScraper


class MarchesPublicsSnScraper(HtmlScraper):
    """Scraper pour marchespublics.sn - Portail national Sénégal
    
    Utilise obligatoirement un proxy IP sénégalais pour contourner le géo-blocage.
    """
    
    BASE_URL = "https://www.marchespublics.sn"
    
    def __init__(self):
        super().__init__()
        self.country = "SN"
        self.source_name = "Marchés Publics Sénégal (Portail National)"
        self.tender_type = "public"
        
        # Proxy sénégalais dédié (via Webshare avec géo-ciblage SN)
        sn_user = os.getenv("SENEGAL_PROXY_USER") or os.getenv("WEBSHARE_PROXY_USER", "")
        sn_pass = os.getenv("SENEGAL_PROXY_PASS") or os.getenv("WEBSHARE_PROXY_PASS", "")
        sn_host = os.getenv("SENEGAL_PROXY_HOST", "p.webshare.io")
        sn_port = os.getenv("SENEGAL_PROXY_PORT", "80")
        
        if sn_user and sn_pass:
            proxy_url = f"http://{sn_user}:{sn_pass}@{sn_host}:{sn_port}"
            self.session.proxies.update({"http": proxy_url, "https": proxy_url})
            logging.info(f"[{self.source_name}] Proxy sénégalais activé : {sn_host}:{sn_port}")
        else:
            logging.warning(f"[{self.source_name}] AUCUN proxy sénégalais configuré — "
                            "le portail sera probablement injoignable (géo-bloqué).")

        # Le portail marchespublics.sn présente un certificat SSL invalide/incomplet.
        # On désactive la vérification TLS UNIQUEMENT pour cette source (session dédiée).
        self.session.verify = False
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass

    def fetch_html(self, url: str, params: dict | None = None):
        """Override : force verify=False (cert SSL invalide du portail SN)."""
        import time
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=params,
                                        timeout=config.REQUEST_TIMEOUT, verify=False)
                resp.raise_for_status()
                if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
                    resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            except Exception as exc:  # noqa: BLE001
                logging.warning("[%s] GET %s échec %s/%s : %s",
                                self.source_name, url, attempt, config.MAX_RETRIES, exc)
                time.sleep(1.2 * attempt)
        return None
    
    # Composant Joomla du portail : com_loffres (liste des offres).
    # La page liste par catégorie renvoie un tableau `cooltable` :
    #   Référence | Objet | Autorité contractante | Publié le | Date limite | Détail
    # URL type : index.php?option=com_loffres&task=view&idcat=NNN&Itemid=104&gestion=AAAA&statut=1
    LOFFRES_ITEMID = "104"
    # Catégories connues (fallback si l'extraction dynamique échoue).
    FALLBACK_CATEGORIES = [
        "001", "002", "003", "004", "006", "007",
        "090", "091", "093", "096", "097", "098",
    ]

    def _list_url(self, idcat: str | None, year: int, statut: int = 1) -> str:
        base = (f"{self.BASE_URL}/index.php?option=com_loffres"
                f"&Itemid={self.LOFFRES_ITEMID}")
        if idcat:
            base += f"&task=view&idcat={idcat}"
        return base + f"&gestion={year}&statut={statut}"

    def _discover_categories(self, year: int) -> list[str]:
        """Extrait dynamiquement les idcat disponibles depuis la page liste."""
        cats: list[str] = []
        soup = self.soup(self._list_url(None, year))
        if soup:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "com_loffres" in href and "task=view" in href:
                    m = re.search(r"idcat=(\d+)", href)
                    if m and m.group(1) not in cats:
                        cats.append(m.group(1))
        if not cats:
            cats = list(self.FALLBACK_CATEGORIES)
            logging.info("[%s] Catégories non détectées, fallback (%d)",
                         self.source_name, len(cats))
        return cats

    def collect(self):
        """Collecte les avis ouverts du portail national via le composant com_loffres.

        NB : pas de test host_reachable() ici — il ouvre un socket TCP DIRECT
        (sans proxy) qui échoue depuis l'IP française du VPS (géo-blocage).
        L'accès réel passe par le proxy sénégalais configuré dans __init__.
        """
        from datetime import date as _date
        year = _date.today().year
        items: list[dict] = []
        seen: set[str] = set()

        categories = self._discover_categories(year)
        logging.info("[%s] %d catégorie(s) à parcourir (année %d)",
                     self.source_name, len(categories), year)

        for cat in categories:
            url = self._list_url(cat, year)
            soup = self.soup(url)
            if not soup:
                logging.warning("[%s] Catégorie %s injoignable", self.source_name, cat)
                continue

            # Le vrai tableau des avis a une ligne d'en-tête `cooltablehdr`.
            # Les lignes de données sont ses lignes sœurs directes. On évite
            # ainsi les tables de mise en page imbriquées (menu, filtres).
            header_rows = soup.find_all("tr", class_=re.compile(r"cooltablehdr", re.I))
            for hdr in header_rows:
                for row in hdr.find_next_siblings("tr"):
                    row_classes = row.get("class") or []
                    if any("cooltablehdr" in c for c in row_classes):
                        continue
                    # td directs uniquement (pas les cellules de tables imbriquées)
                    cells = row.find_all("td", recursive=False)
                    if len(cells) < 6:
                        continue
                    try:
                        item = self._parse_cooltable_row(cells)
                        if not item:
                            continue
                        ext = item.get("external_id")
                        if ext in seen:
                            continue
                        seen.add(ext)
                        if self.is_active(item.get("deadline")):
                            items.append(item)
                    except Exception as e:  # noqa: BLE001
                        logging.warning("[%s] Erreur parsing ligne : %s",
                                        self.source_name, e)
                        continue

        logging.info("[%s] %d avis actifs collectés", self.source_name, len(items))
        return items

    def _parse_cooltable_row(self, cells):
        """Parse une ligne du tableau cooltable (6 colonnes)."""
        reference = self.clean(cells[0].get_text()) or None
        title = self.clean(cells[1].get_text())
        institution = self.clean(cells[2].get_text())
        publication_date = self._extract_date(self.clean(cells[3].get_text()))
        deadline = self._extract_date(self.clean(cells[4].get_text()))

        if not title:
            return None

        source_url = self._list_url(None, __import__("datetime").date.today().year)
        dao_url = None
        key = None
        for a in cells[5].find_all("a", href=True):
            href = a["href"].replace("&amp;", "&")
            if "task=txt" in href:
                source_url = urljoin(self.BASE_URL + "/", href)
                m = re.search(r"key=(\d+)", href)
                if m:
                    key = m.group(1)
            elif "task=moffres" in href:
                dao_url = urljoin(self.BASE_URL + "/", href)

        external_id = f"mpsn-{key or reference or self.clean(title)[:40]}"

        return self.make_item(
            title=title,
            institution=institution,
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
    return MarchesPublicsSnScraper()
