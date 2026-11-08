"""Tabelle usate dai calcoli, con la fonte (versione 0.4). Sola lettura.

Nessun valore e' scritto qui: ogni riga viene letta dalle costanti e dalle funzioni dei moduli di calcolo (``telematico.calcolo``,
``telematico.quadri_efgh``, ``telematico.usufrutto``, ``valore_catastale``), cosi' la tabella mostrata e' per costruzione quella
applicata. Se un modulo cambia, cambia anche questa pagina; ``tests/test_tabelle.py`` lo verifica.
"""
from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

from . import valore_catastale as VC
from .telematico import calcolo as C
from .telematico import quadri_efgh as EF
from .telematico import usufrutto as U


def _pct(x) -> str:
    v = Decimal(x.numerator) / Decimal(x.denominator) * 100 if isinstance(x, Fraction) else Decimal(x) * 100
    return f"{v.normalize():f}".replace(".", ",") + "%"


def _euro(n) -> str:
    return f"{int(n):,}".replace(",", ".") + " €"


def _gradi(g) -> str:
    return ", ".join(sorted(g))


NOTA = ("Valori letti dai moduli di calcolo del programma: sono quelli effettivamente applicati. Per ogni tabella la fonte e "
        "le successioni a cui si applica; la verifica sulla norma resta del professionista.")


def tabelle() -> list[dict]:
    """Elenco di tabelle {id, titolo, decorrenza, colonne, righe, fonte, nota}."""
    al4, f4 = C.aliquota(sorted(C.GRADI_4)[0])
    al6, f6 = C.aliquota(sorted(C.GRADI_6)[0])
    al8, f8 = C.aliquota(sorted(C.GRADI_8)[0])
    al0, f0 = C.aliquota(sorted(C.GRADI_ESENTI)[0])
    _, fonte_fr = C.franchigia("01", False)
    m_terr = VC.MOLT_TERRENI
    fab = [("Gruppo B", "B1", False), ("Categoria C/1 e gruppo E", "C1", False), ("Categoria A/10 e gruppo D", "A10", False),
           ("Abitazioni (gruppo A) con prima casa", "A2", True), ("Altre abitazioni e altre categorie", "A2", False)]
    return [
        {"id": "aliquote", "titolo": "Imposta di successione: aliquote per grado di parentela",
         "decorrenza": "successioni aperte dal " + C.DECORRENZA.strftime("%d/%m/%Y"),
         "colonne": ["Gradi (codici del quadro EA)", "Aliquota", "Fonte"],
         "righe": [[_gradi(C.GRADI_4), _pct(al4), f4], [_gradi(C.GRADI_6), _pct(al6), f6],
                   [_gradi(C.GRADI_8), _pct(al8), f8], [_gradi(C.GRADI_ESENTI), _pct(al0), f0]],
         "fonte": C.VERSIONE_REGOLE, "nota": "Gradi non elencati: calcolo non supportato (lo dice il programma)."},
        {"id": "franchigie", "titolo": "Imposta di successione: franchigie per beneficiario",
         "decorrenza": "successioni aperte dal " + C.DECORRENZA.strftime("%d/%m/%Y"),
         "colonne": ["Beneficiario", "Franchigia"],
         "righe": [["Gradi " + _gradi(C.GRADI_4), _euro(C.FR_LINEA_RETTA)],
                   ["Gradi " + _gradi(C.GRADI_FR_FRATELLI), _euro(C.FR_FRATELLI)],
                   ["Persona con handicap grave, qualunque grado", _euro(C.FR_HANDICAP)]],
         "fonte": fonte_fr, "nota": "Le franchigie non si sommano: si applica la piu' alta."},
        {"id": "ipocatastali", "titolo": "Imposte ipotecaria e catastale, tassa e bollo (quadro EF)",
         "decorrenza": "successioni aperte dal " + EF.DEC_2006.strftime("%d/%m/%Y"),
         "colonne": ["Voce", "Misura", "Fonte"],
         "righe": [["Imposta ipotecaria proporzionale (EF1)", _pct(EF.ALIQUOTA_IPOTECARIA), "Succ_FASCICOLO_I_Nov_23.pdf p. 40, rigo EF1 col. 2"],
                   ["Imposta catastale proporzionale (EF9)", _pct(EF.ALIQUOTA_CATASTALE), "Succ_FASCICOLO_I_Nov_23.pdf p. 43, rigo EF9 col. 2"],
                   ["Misura fissa, decessi dal " + EF.DEC_2014.strftime("%d/%m/%Y"), _euro(EF.imposta_fissa(EF.DEC_2014)), "Fascicolo I p. 39; annotazioni XSD del quadro EF"],
                   ["Misura fissa, decessi dal " + EF.DEC_2006.strftime("%d/%m/%Y") + " al 31/12/2013", _euro(EF.imposta_fissa(EF.DEC_2006)), "Fascicolo I p. 39; annotazioni XSD del quadro EF"],
                   ["Tassa ipotecaria per circoscrizione (EF15)", _euro(EF.TASSA_CIRCOSCRIZIONE), "Fascicolo I p. 44, rigo EF15 col. 2"],
                   ["Tassa per circoscrizione senza volture (cariche 5, 6, 9)", _euro(EF.TASSA_CIRCOSCRIZIONE_SENZA_VOLTURE), "Fascicolo I p. PDF 45, rigo EF15 col. 2"],
                   ["Bollo per circoscrizione (EF16)", _euro(EF.BOLLO_CIRCOSCRIZIONE), "Fascicolo I pp. 45-46, rigo EF16"],
                   ["Bollo per l'attestazione chiesta in dichiarazione (EF16 col. 1)", _euro(EF.BOLLO_ATTESTAZIONE), "Fascicolo I pp. PDF 45-46"],
                   ["Tributi speciali per l'attestazione (EF18)", _euro(EF.TRIBUTI_SPECIALI_ATTESTAZIONE), "Fascicolo I p. PDF 46"]],
         "fonte": "Succ_FASCICOLO_I_Nov_23.pdf e fornituraSUC13_v1.xsd", "nota": ""},
        {"id": "catastale", "titolo": "Valore catastale proposto: rivalutazioni e moltiplicatori",
         "decorrenza": "dal " + VC.DECORRENZA.strftime("%d/%m/%Y"),
         "colonne": ["Immobile", "Rivalutazione", "Moltiplicatore", "Lettera"],
         "righe": [["Terreni (reddito dominicale)", "+" + _pct(VC.RIV_DOMINICALE - 1), f"{m_terr:f}".replace(".", ","), "lettera a"]] + [
             [etichetta, "+" + _pct(VC.RIV_RENDITA - 1), f"{m:f}".replace(".", ","), d]
             for etichetta, cat, pc in fab for m, d in [VC.moltiplicatore_fabbricato(cat, pc)]],
         "fonte": VC.FONTE_MOLTIPLICATORI + "; " + VC.FONTE_RIVALUTAZIONE, "nota": "Il valore e' una proposta: decide il professionista."},
        {"id": "usufrutto", "titolo": "Usufrutto vitalizio: coefficienti per eta' dell'usufruttuario",
         "decorrenza": "successioni aperte dal " + U.DECORRENZA.strftime("%d/%m/%Y"),
         "colonne": ["Eta'", "Coefficiente", "Valore dell'usufrutto sulla piena proprieta'"],
         "righe": [[f"{a}–{b} anni", str(k), _pct(Fraction(k) * U.SAGGIO)] for a, b, k in U.PROSPETTO],
         "fonte": U.FONTE, "nota": f"Saggio legale {_pct(U.SAGGIO)}, verificato fino al {U.VERIFICATO_FINO.strftime('%d/%m/%Y')}."},
    ]
