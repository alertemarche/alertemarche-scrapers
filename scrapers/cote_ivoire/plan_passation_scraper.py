"""Robot de collecte — Côte d'Ivoire 🇨🇮 · Plans de Passation des Marchés (PPM).

Source : portail de la Direction Générale des Marchés Publics (DGMP) —
https://www.marchespublics.ci/plan_passation

La DGMP publie chaque année la liste des Plans de Passation des Marchés (PPM)
de TOUS les ministères et autorités contractantes sous forme de fichiers PDF
téléchargeables (ex. « LISTE DES PPM PUBLIES DU 01 JANVIER AU 03 JUILLET 2026 »).

Chaque ligne du PDF est une opération planifiée par un ministère :
    N° · MINISTERE · AUTORITE CONTRACTANTE · OBJET DE L'OPERATION · BAILLEUR ·
    LIGNE BUDGETAIRE · TYPE DE MARCHE · MODE DE PASSATION · DATE DE PUBLICATION

Ce robot :
  1) ouvre la page PPM de l'année en cours pour découvrir les PDF publiés,
  2) télécharge chaque PDF et en extrait le tableau (PyMuPDF / fitz),
  3) transforme chaque opération en opportunité de type « plan_passation ».

Les plans de passation n'ont pas de date limite de dépôt (ce sont des
prévisions annuelles) : ils sont conservés durablement (type plan_passation,
jamais purgé par la règle des marchés sans deadline).

Seules des MÉTADONNÉES sont collectées ; aucun fichier n'est stocké.
"""
import io
import logging
import re
from datetime import date

import fitz  # PyMuPDF

from common.html_base import HtmlScraper  # noqa: E402
from common import procedures

logger = logging.getLogger("scrapers.cote_ivoire.plan_passation")


class PlanPassationCiScraper(HtmlScraper):
    country = "CI"
    source_name = "Marchés Publics Côte d'Ivoire — Plans de Passation (DGMP)"
    tender_type = "plan_passation"

    # Pages listant les PDF de plans (PPM = Plan de Passation, PSPM = Plan
    # Simplifié). {year} est remplacé par l'année en cours.
    LISTING_TEMPLATES = [
        "https://www.marchespublics.ci/plan_passation/an/PPM/{year}",
        "https://www.marchespublics.ci/plan_passation/an/PSPM/{year}",
    ]

    BASE = "https://www.marchespublics.ci"

    # Entêtes de colonnes attendues dans les PDF (repérage du tableau).
    HEADER_HINTS = ("AUTORITE CONTRACTANTE", "OBJET", "MODE DE PASSATION")

    def _pdf_links(self, year: int) -> list[str]:
        """Découvre les URLs des PDF de plans publiés pour l'année donnée."""
        links: list[str] = []
        seen: set[str] = set()
        for tpl in self.LISTING_TEMPLATES:
            url = tpl.format(year=year)
            soup = self.soup(url)
            if not soup:
                continue
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ".pdf" not in href.lower():
                    continue
                if href.startswith("/"):
                    href = self.BASE + href
                elif not href.startswith("http"):
                    href = f"{self.BASE}/{href}"
                # On ne garde que les PDF de listes de PPM.
                low = href.lower()
                if "ppm" not in low and "plan" not in low:
                    continue
                if href not in seen:
                    seen.add(href)
                    links.append(href)
        return links

    def _download_pdf(self, url: str) -> bytes | None:
        """Télécharge un PDF (via la session, proxy inclus) et renvoie ses octets."""
        for attempt in range(1, 4):
            try:
                resp = self.session.get(url, timeout=90)
                resp.raise_for_status()
                if resp.content[:4] == b"%PDF":
                    return resp.content
                logger.warning("[CI] %s ne renvoie pas un PDF valide", url)
                return None
            except Exception as exc:  # noqa: BLE001
                logger.warning("[CI] Téléchargement PDF %s échec %s/3 : %s", url, attempt, exc)
        return None

    @staticmethod
    def _to_iso(raw: str | None) -> str | None:
        """Convertit '24/04/26' ou '24/04/2026' → '2026-04-24'."""
        if not raw:
            return None
        m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", raw.strip())
        if not m:
            return None
        d, mo, y = m.groups()
        d, mo, y = int(d), int(mo), int(y)
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            return None

    def _parse_pdf(self, pdf_bytes: bytes, source_url: str) -> list[dict]:
        items: list[dict] = []
        try:
            doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
        except Exception as exc:  # noqa: BLE001
            logger.warning("[CI] Ouverture PDF impossible : %s", exc)
            return items

        for page in doc:
            # Lien direct vers la bonne page du PDF (ex: "#page=4").
            # Quand l'utilisateur clique « Voir la source », son lecteur PDF
            # ouvre directement la page exacte — ~21 marchés à parcourir max.
            page_num = page.number + 1          # numérotation humaine (1-based)
            page_url = f"{source_url}#page={page_num}"

            try:
                tabs = page.find_tables()
            except Exception:  # noqa: BLE001
                continue
            for tab in tabs.tables:
                rows = tab.extract()
                if not rows:
                    continue
                # Repérer l'entête pour valider qu'il s'agit du bon tableau.
                header = " ".join(str(c or "") for c in rows[0]).upper()
                if not any(h in header for h in self.HEADER_HINTS):
                    continue
                for row in rows[1:]:
                    item = self._map_row(row, page_url)
                    if item:
                        items.append(item)
        doc.close()
        return items

    def _map_row(self, row: list, source_url: str) -> dict | None:
        # Colonnes attendues :
        # 0:N° 1:MINISTERE 2:AUTORITE 3:OBJET 4:BAILLEUR 5:LIGNE_BUDG
        # 6:TYPE_MARCHE 7:MODE_PASSATION 8:DATE_PUBLICATION
        if len(row) < 9:
            return None

        def cell(i: int) -> str:
            v = row[i]
            return " ".join(str(v).split()) if v else ""

        ministere = cell(1)
        autorite = cell(2)
        objet = cell(3)
        bailleur = cell(4)
        ligne_budg = cell(5)
        type_marche = cell(6)
        mode_passation = cell(7)
        date_pub = cell(8)

        if not objet or len(objet) < 6:
            return None
        # Ignorer les lignes de continuation / entêtes répétées.
        if objet.upper().startswith("OBJET"):
            return None

        # Nettoyer le numéro de ministère en préfixe (ex. « 10 - Ministère... »).
        ministere_clean = re.sub(r"^\d+\s*-\s*", "", ministere).strip()

        # Autorité contractante = acheteur réel ; à défaut, le ministère.
        institution = autorite or ministere_clean or self.source_name

        # Le titre inclut le ministère de tutelle pour le contexte.
        title = objet
        if ministere_clean and ministere_clean.lower() not in objet.lower():
            title = f"{objet} — {ministere_clean}"

        procedure_type = procedures.from_text(mode_passation) or procedures.from_text(type_marche)

        publication_date = self._to_iso(date_pub)

        reference = ligne_budg or None
        external_id = f"ppmci-{re.sub(r'[^A-Za-z0-9]', '', ligne_budg)}" if ligne_budg else None

        return self.make_item(
            title=title,
            institution=institution,
            reference=reference,
            market_type=type_marche or None,
            procedure_type=procedure_type,
            deadline=None,               # les PPM n'ont pas d'échéance de dépôt
            publication_date=publication_date,
            source_url=source_url,
            external_id=external_id,
        )

    def collect(self) -> list[dict]:
        year = date.today().year
        items: list[dict] = []
        seen: set[str] = set()

        # On tente l'année courante puis, si rien, l'année précédente
        # (transition de fin/début d'année où le plan N n'est pas encore publié).
        years_to_try = [year, year - 1]
        pdf_urls: list[str] = []
        for y in years_to_try:
            pdf_urls = self._pdf_links(y)
            if pdf_urls:
                logger.info("[CI] Plans de passation %s : %s PDF trouvés", y, len(pdf_urls))
                break

        if not pdf_urls:
            logger.warning("[CI] Aucun PDF de plan de passation trouvé")
            return items

        for url in pdf_urls:
            pdf_bytes = self._download_pdf(url)
            if not pdf_bytes:
                continue
            for item in self._parse_pdf(pdf_bytes, url):
                # Déduplication locale : objet + acheteur.
                key = (item["title"][:120] + "|" + (item["institution"] or "")[:60]).lower()
                if key in seen:
                    continue
                seen.add(key)
                items.append(item)

        logger.info("[CI] Plans de passation — %s opérations planifiées collectées", len(items))
        return items


def build() -> PlanPassationCiScraper:
    return PlanPassationCiScraper()
