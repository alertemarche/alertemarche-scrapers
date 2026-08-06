"""Robot de collecte — Burkina Faso 🇧🇫 · PNUD (marchés PRIVÉS / Nations Unies).

Source : portail mondial des avis de marchés du PNUD —
https://procurement-notices.undp.org/  (filtré sur le bureau Burkina Faso,
UNDP-BFA). Chaque avis est un `a.vacanciesTable__row` présentant « Title »,
« Ref No », « UNDP Office/Country », « Process », « Deadline » et « Posted ».

Seuls les avis ACTIFS (échéance future ou absente) et des MÉTADONNÉES + le lien
vers la fiche officielle sont collectés.
"""
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.burkina_faso.pnud")

from common.html_base import HtmlScraper  # noqa: E402


class PnudBfScraper(HtmlScraper):
    country = "BF"
    source_name = "PNUD Burkina Faso — Programme des Nations Unies pour le Développement"
    tender_type = "prive"

    PORTAL = "https://procurement-notices.undp.org/"

    def _field(self, text: str, label: str, stops: str) -> str | None:
        m = re.search(re.escape(label) + r"\s*(.+?)(?:" + stops + r"|$)", text, re.IGNORECASE)
        return self.clean(m.group(1)) if m else None

    def collect(self) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        soup = self.soup(self.PORTAL)
        if not soup:
            logger.warning("[BF] PNUD injoignable — 0 item")
            return items

        rows = soup.select("a.vacanciesTable__row")
        stops = "Title|Ref No|UNDP Office|Country|Process|Deadline|Posted|Documents"
        for row in rows:
            text = row.get_text(" ", strip=True)
            up = text.upper()
            # Filtre Burkina Faso : bureau UNDP-BFA ou pays /BURKINA.
            if "UNDP-BFA" not in up and "/BURKINA" not in up and "BURKINA" not in up:
                continue

            title = self._field(text, "Title", stops)
            if not title or len(title) < 6:
                continue
            reference = self._field(text, "Ref No", stops)
            process = self._field(text, "Process", stops)
            deadline = self.parse_fr_date(self._field(text, "Deadline", stops) or "")
            pub = self.parse_fr_date(self._field(text, "Posted", stops) or "")

            # On ne garde que les avis actifs (échéance future ou absente).
            if not self.is_active(deadline):
                continue

            href = row.get("href", "")
            source_url = urljoin(self.PORTAL, href) if href else self.PORTAL

            external_id = None
            if reference:
                external_id = "pnud-bf-" + re.sub(r"[^a-zA-Z0-9]", "", reference)[:40]
            else:
                mid = re.search(r"(?:nego_id|notice_id)=(\d+)", source_url)
                if mid:
                    external_id = f"pnud-bf-{mid.group(1)}"
            if external_id and external_id in seen:
                continue
            if external_id:
                seen.add(external_id)

            items.append(self.make_item(
                title=title[:255],
                institution=self.source_name,
                reference=reference,
                deadline=deadline,
                publication_date=pub,
                market_type=process,
                source_url=source_url,
                external_id=external_id,
                tender_type="prive",
            ))
        logger.info("[BF] PNUD : %d avis collectés", len(items))
        return items


def build() -> PnudBfScraper:
    return PnudBfScraper()
