"""Valore catastale degli immobili (fabbricati EC e terreni EB): il valore minimo che non e' soggetto a rettifica.

Il programma lo PROPONE e lo confronta con il valore dichiarato; non lo scrive mai da solo. Il valore dichiarato resta quello
inserito dal professionista (il valore venale puo' essere piu' alto).

Fonti (testi letti il 2026-11-07, scheda in ``docs/regole/valore_catastale.md``):
- rivalutazione: L. 23 dicembre 1996 n. 662, art. 3, c. 48 (rendite catastali urbane +5%) e c. 51 (redditi dominicali +25%),
  applicabili alle successioni aperte dal 1° gennaio 1997 (c. 52, lett. b). Normattiva, testo vigente al 07/11/2026.
- moltiplicatori: D.Lgs. 5 agosto 2026 n. 141, testo unico adempimenti e accertamento, art. 309 c. 6-8 (GU n. 181 del
  6-8-2026, S.O. n. 28, p. 267), applicabile dal 1° gennaio 2027 (art. 368). L'articolo riunisce senza cambiarli i
  moltiplicatori gia' vigenti indicati nella sua sotto-rubrica: art. 34 D.Lgs. 346/1990, art. 52 c. 4 DPR 131/1986,
  art. 2 c. 63 L. 350/2003 (+10% prima casa), art. 1-bis c. 7 D.L. 168/2004 (+20% gli altri), art. 2 c. 45 D.L. 262/2006
  (+40% gruppo B). Per questo valgono anche per le successioni aperte prima del 2027, a partire dal 2007 (prima del D.L.
  262/2006 il gruppo B aveva un altro moltiplicatore: quelle date non sono calcolate).
- prima casa: «L'agevolazione 'prima casa' si estende agli altri eventuali soggetti beneficiari» (Fascicolo I p. PDF 26):
  basta un codice P o Z su una riga di devoluzione del bene. Lo stesso vale per la casella «Diritto di abitazione» del
  fabbricato con i codici 1, 2, 5, 6 (Fascicolo I pp. PDF 31-32, N.B.: «L'agevolazione, qualora richiesta, si estende anche
  alle quote dell'immobile spettanti agli altri beneficiari»).
- esclusi (c. 8): terreni con destinazione edificatoria. Esclusi qui anche i diritti diversi dalla piena proprieta' (c. 7
  rinvia all'art. 99 del testo unico registro per nuda proprieta' e diritti reali: non ancora implementato).
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_CEILING, Decimal

from . import valori as V
from .telematico import formati as F
from .telematico import supplemento as SUP

FONTE_RIVALUTAZIONE = "L. 662/1996 art. 3 c. 48 (rendite +5%) e c. 51 (redditi dominicali +25%)"
FONTE_MOLTIPLICATORI = ("art. 34 c. 5 D.Lgs. 346/1990 e art. 52 c. 4 DPR 131/1986, con le rivalutazioni di art. 2 c. 63 "
                        "L. 350/2003, art. 1-bis c. 7 D.L. 168/2004 e art. 2 c. 45 D.L. 262/2006; riuniti senza modifiche "
                        "nel D.Lgs. 141/2026 art. 309 c. 6 (GU 6-8-2026 S.O. 28 p. 267), applicabile dal 1/1/2027")
FONTE_PRIMA_CASA = "Succ_FASCICOLO_I_Nov_23.pdf p. PDF 26 (la prima casa si estende agli altri beneficiari)"
DECORRENZA = date(2007, 1, 1)
RIV_RENDITA = Decimal("1.05")
RIV_DOMINICALE = Decimal("1.25")
#: art. 309 c. 6: lettera -> (moltiplicatore, descrizione)
MOLT_TERRENI = Decimal("90")
MOLT_B = Decimal("168")
MOLT_C1_E = Decimal("40.80")
MOLT_A10_D = Decimal("60")
MOLT_PRIMA_CASA = Decimal("110")
MOLT_ALTRI = Decimal("120")
CODICI_PRIMA_CASA = ("P", "Z")
#: categorie per cui l'agevolazione prima casa non si applica (A/1, A/8, A/9 come telematico/prima_casa.CAT_ESCLUSE; A/10 e
#: A/11 non sono case di abitazione ai fini della lettera e): moltiplicatore ordinario
CATEGORIE_SENZA_PRIMA_CASA = ("A1", "A8", "A9", "A11")
#: casella «Diritto di abitazione» del fabbricato: codici con prima casa sull'immobile principale o contiguo (1, 2; 5, 6 per il
#: coniuge rinunciatario che mantiene il legato ex lege); 3 e 7 riguardano la pertinenza (cod. X), 4 e 8 sono senza prima casa
CODICI_DA_PRIMA_CASA = ("1", "2", "5", "6")
FONTE_PRIMA_CASA_DA = ("Succ_FASCICOLO_I_Nov_23.pdf pp. PDF 31-32, «Diritto di abitazione», codici 1, 2, 5, 6 e N.B.: "
                       "l'agevolazione si estende alle quote degli altri beneficiari della sezione devoluzione")


def _num(v):
    if v in (None, "") or V.e_stato(v):
        return None
    try:
        return V.parse_importo(v)
    except V.ValoreNonValido:
        return None


def _quota(v):
    try:
        return V.parse_quota(v) if v not in (None, "") and not V.e_stato(v) else None
    except V.ValoreNonValido:
        return None



def _codice_diritto(v) -> str:
    """Codice del diritto, accettando anche la descrizione ammessa dall'esportazione («proprieta» -> «1»)."""
    s = str(v or "").strip()
    if not s or s.upper() in ("1", "1S", "1T", "2", "2S", "2T", "4", "5", "6", "10"):
        return s.upper()
    try:
        from .codici import alias
        from .telematico.esporta import _norm
        return alias().get("beni.diritto@immobile", {}).get(_norm(s), s)
    except Exception:
        return s


def _categoria(b: dict) -> str:
    return str(b.get("categoria") or "").strip().upper().replace(" ", "")


def moltiplicatore_fabbricato(categoria: str, prima_casa: bool) -> tuple[Decimal | None, str]:
    """Moltiplicatore della rendita rivalutata per categoria (art. 309 c. 6, lettere b-f)."""
    c = categoria.replace("/", "")
    if not c or c.startswith("F"):
        return None, "categoria fittizia (gruppo F) o mancante: nessuna rendita"
    if c.startswith("B"):
        return MOLT_B, "gruppo B (lettera b)"
    if c == "C1" or c.startswith("E"):
        return MOLT_C1_E, "categoria C/1 o gruppo E (lettera c)"
    if c == "A10" or c.startswith("D"):
        return MOLT_A10_D, "categoria A/10 o gruppo D (lettera d)"
    if c.startswith("A") and prima_casa and c not in CATEGORIE_SENZA_PRIMA_CASA:
        return MOLT_PRIMA_CASA, "casa di abitazione con agevolazione prima casa (lettera e)"
    return MOLT_ALTRI, "altre case di abitazione e altre categorie (lettera f)"


def calcola(dati: dict, b: dict) -> dict:
    """Valore catastale della quota del defunto per un fabbricato o un terreno.

    Restituisce ``{"bene_id", "calcolabile", "valore", "formula", "fonti", "motivo", "dichiarato", "inferiore"}``.
    ``valore`` e' arrotondato all'euro per eccesso, perche' il valore dichiarato deve essere «non inferiore»."""
    out = {"bene_id": b.get("id"), "tipo": b.get("tipo"), "calcolabile": False, "valore": None, "formula": None,
           "fonti": [], "motivo": None, "dichiarato": None, "inferiore": False}
    dich = _num(b.get("valore"))
    out["dichiarato"] = str(dich) if dich is not None else None
    if b.get("tipo") not in ("fabbricato", "terreno"):
        out["motivo"] = "solo fabbricati e terreni hanno un valore catastale"
        return out
    if str(b.get("provincia") or "").strip().upper() == "EE":
        out["motivo"] = "immobile all'estero: nessun valore catastale italiano"
        return out
    dd = F.data_decesso_defunto(dati)
    if dd is None:
        out["motivo"] = "manca la data del decesso"
        return out
    if dd < DECORRENZA:
        out["motivo"] = "successione aperta prima del 2007: moltiplicatori non gestiti da questa versione"
        return out
    diritto = _codice_diritto(b.get("diritto"))
    if diritto != "1":
        out["motivo"] = ("calcolo previsto solo per la piena proprieta' (codice diritto 1): per nuda proprieta' e altri diritti "
                         "il valore catastale segue l'art. 99 del testo unico registro, non ancora gestito")
        return out
    q = _quota(b.get("quota_defunto"))
    if q is None:
        out["motivo"] = "manca la quota posseduta dal defunto"
        return out
    if b["tipo"] == "terreno":
        natura = str(b.get("natura") or "").strip().upper()
        tip = str(b.get("tipologia_terreno") or "").strip()
        if natura not in ("", "T", "R") or tip in ("1", "2"):
            out["motivo"] = "terreno edificabile o non agricolo: il valore catastale non si applica (art. 309 c. 8)"
            return out
        rd = _num(b.get("reddito_dominicale"))
        if rd is None:
            out["motivo"] = "manca il reddito dominicale"
            return out
        base = rd * RIV_DOMINICALE * MOLT_TERRENI
        formula = f"reddito dominicale {rd} × 1,25 × 90 × quota {q.numerator}/{q.denominator}"
        out["fonti"] = [FONTE_RIVALUTAZIONE, FONTE_MOLTIPLICATORI + " (lettera a)"]
        if not tip:
            out["avviso"] = "vale solo se il terreno non e' edificabile: indicare la tipologia del terreno"
    else:
        rendita = _num(b.get("rendita"))
        if rendita is None:
            out["motivo"] = "manca la rendita catastale"
            return out
        da = SUP.attr(dati, "beni", b, "diritto_abitazione")
        prima_da = not isinstance(da, dict) and str(da or "").strip() in CODICI_DA_PRIMA_CASA
        prima = prima_da or any(d.get("bene_id") == b.get("id")
                                and str(SUP.attr(dati, "devoluzioni", d, "agevolazioni") or "").strip().upper() in CODICI_PRIMA_CASA
                                for d in dati.get("devoluzioni", []))
        molt, voce = moltiplicatore_fabbricato(_categoria(b), prima)
        if molt is None:
            out["motivo"] = voce
            return out
        base = rendita * RIV_RENDITA * molt
        formula = f"rendita {rendita} × 1,05 × {str(molt).replace('.', ',')} ({voce}) × quota {q.numerator}/{q.denominator}"
        out["fonti"] = [FONTE_RIVALUTAZIONE, FONTE_MOLTIPLICATORI] + ([FONTE_PRIMA_CASA] if prima else []) + (
            [FONTE_PRIMA_CASA_DA] if prima_da else [])
    valore = (base * Decimal(q.numerator) / Decimal(q.denominator)).quantize(Decimal("1"), rounding=ROUND_CEILING)
    out.update(calcolabile=True, valore=str(valore), formula=formula + f" = {valore} euro (arrotondato per eccesso)",
               inferiore=dich is not None and dich < valore)
    return out


def calcola_pratica(dati: dict) -> list[dict]:
    return [calcola(dati, b) for b in dati.get("beni", []) if b.get("tipo") in ("fabbricato", "terreno")]


def avvisi(dati: dict, attivi: set[str] | None = None) -> list[dict]:
    """Avvisi (non bloccanti) per i beni con valore dichiarato inferiore al valore catastale."""
    from .quadri import quadro_di
    out = []
    for b in dati.get("beni", []):
        if b.get("tipo") not in ("fabbricato", "terreno") or (attivi is not None and quadro_di("beni", b) not in attivi):
            continue
        r = calcola(dati, b)
        if r["inferiore"]:
            out.append({"codice": "VALORE_SOTTO_CATASTALE", "percorso": f"beni[{b['id']}].valore",
                        "messaggio": f"il valore dichiarato ({r['dichiarato']} euro) e' inferiore al valore catastale "
                                     f"({r['valore']} euro): l'ufficio puo' rettificarlo. Calcolo: {r['formula']}",
                        "fonte": "; ".join(r["fonti"])})
    return out
