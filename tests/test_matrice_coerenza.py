"""Coerenza tra matrice di copertura e codice: ogni quadro esportabile o supportato e' nella matrice; i quadri non
supportati non risultano «controllo locale»."""
import re
from pathlib import Path

from successioni.quadri import QUADRI
from successioni.telematico.esporta import QUADRI_ESPORTABILI

MATRICE = (Path(__file__).resolve().parents[1] / "docs" / "MATRICE_COPERTURA.md").read_text(encoding="utf-8")
SINTESI = MATRICE.split("## Dettaglio campo")[0]


def _righe_sintesi():
    return [r for r in SINTESI.splitlines() if r.startswith("| ") and not r.startswith("| Quadro") and not r.startswith("|---")]


def _riga_del_quadro(sigla):
    for r in _righe_sintesi():
        prima = r.split("|")[1]
        if re.search(rf"\b{sigla}\b", prima):
            return r
    return None


def test_ogni_quadro_esportabile_e_nella_matrice():
    mancanti = [q for q in QUADRI_ESPORTABILI if _riga_del_quadro(q) is None]
    assert mancanti == [], f"quadri esportabili assenti dalla tabella di sintesi della matrice: {mancanti}"


def test_ogni_quadro_supportato_e_nella_matrice():
    mancanti = [q["id"] for q in QUADRI if q["id"].startswith("E") and q.get("supportato") and _riga_del_quadro(q["id"]) is None]
    assert mancanti == [], f"quadri supportati assenti dalla matrice: {mancanti}"


def test_quadri_non_supportati_non_sono_controllo_locale():
    # i quadri generati dal programma (EE, EF, EH) non si compilano: il registro li segna non selezionabili ma sono esportati
    for q in QUADRI:
        if q["id"].startswith("E") and q.get("supportato") is False and "generato automaticamente" not in q.get("motivo", ""):
            riga = _riga_del_quadro(q["id"])
            if riga is None:
                riga = _riga_del_quadro("EI_new") if q["id"] == "EI" else None
            assert riga is not None, f"quadro non supportato {q['id']} assente dalla matrice"
            stato = riga.split("|")[2]
            assert "controllo locale" not in stato, f"{q['id']} e' non supportato ma la matrice dice: {stato.strip()}"


def test_i_quadri_esportabili_sono_tutti_supportati_nel_registro():
    supportati = {q["id"] for q in QUADRI if q.get("supportato")}
    non_registrati = [q for q in QUADRI_ESPORTABILI if q not in supportati and q not in ("EE", "EF", "EG", "EH")]
    assert non_registrati == [], f"esportabili ma non supportati nel registro dei quadri: {non_registrati}"
