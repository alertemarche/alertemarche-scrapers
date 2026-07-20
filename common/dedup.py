"""Déduplication des opportunités collectées.

Le hash reproduit exactement la logique du backend (IngestController) :
sha256( titre_minuscule | institution_minuscule | date_limite ).
Un cache local évite de renvoyer plusieurs fois la même opportunité au sein
d'une même exécution ; le backend reste la source de vérité (firstOrCreate).
"""
import hashlib


def compute_hash(title: str, institution: str, deadline: str | None) -> str:
    title = (title or "").strip().lower()
    institution = (institution or "").strip().lower()
    deadline = (deadline or "").strip()
    raw = f"{title}|{institution}|{deadline}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def deduplicate(items: list[dict]) -> list[dict]:
    """Supprime les doublons d'une liste d'opportunités (par hash)."""
    seen: set[str] = set()
    unique: list[dict] = []
    for item in items:
        h = compute_hash(
            item.get("title", ""),
            item.get("institution", ""),
            item.get("deadline"),
        )
        if h in seen:
            continue
        seen.add(h)
        unique.append(item)
    return unique
