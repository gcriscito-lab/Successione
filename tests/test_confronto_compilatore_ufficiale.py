"""Confronto con il compilatore ufficiale SuccessioniOnLine 2.3.1 (11/03/2026), dati SINTETICI.

Il 2026-11-06 lo stesso caso inventato e' stato inserito a mano nel compilatore dell'Agenzia
(fonti/Programma e controlli/SUC13 (4).jnlp) e nel nostro programma. Valori letti nel quadro EF del compilatore:
EF1/EF5/EF8 6000, EF9/EF11/EF14 3000, EF15 120, EF18-bis 6600, EF19 9205 (quindi bollo 85).
Dettaglio in docs/CONFRONTO_COMPILATORE_UFFICIALE_20261106.md. Nessun invio, nessun salvataggio nell'archivio del
compilatore.
"""
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import telematico_casi as T  # noqa: E402
from successioni import prospetto_cliente as P  # noqa: E402
from successioni.telematico.calcolo import calcola_da_xml  # noqa: E402
from successioni.telematico.esporta import esporta_xml  # noqa: E402

UFFICIALE = {"Imposta ipotecaria": Decimal(6000), "Imposta catastale": Decimal(3000), "Tassa ipotecaria": Decimal(120),
             "Imposta di bollo": Decimal(85), "Imposta di successione": Decimal(6600)}


def caso_fratelli_300k() -> dict:
    """Defunto celibe, due fratelli germani eredi per legge, un fabbricato A/2 da 300.000 euro, nessuna passivita'."""
    c = T.caso_a10()
    c["beni"] = [b for b in c["beni"] if b["id"] == "b_casa0001"]
    c["beni"][0]["valore"] = "300000"
    c["devoluzioni"] = [d for d in c["devoluzioni"] if d["bene_id"] == "b_casa0001"]
    c["passivita"] = []
    c["documenti_ref"] = [d for d in c["documenti_ref"] if d.get("tipo_eg") == "AlberoGenealogico"]
    tel = c["opzioni"]["telematico"]
    tel.pop("passivita", None)
    tel["beni"] = {k: v for k, v in tel.get("beni", {}).items() if k == "b_casa0001"}
    tel["dichiarazione"].update({"stato_civile": "1", "tempistica_pagamento": "1"})
    for pid in ("p_anna0001", "p_luca0001"):
        tel["persone"][pid]["grado_parentela"] = "10"
    for p in c["persone"]:
        if p["ruolo"] == "erede":
            p["relazione_con_defunto"] = "10"
    return c


def test_imposte_uguali_al_compilatore_ufficiale():
    es = esporta_xml(caso_fratelli_300k(), T.contesto_caso_a10(scopo="bozza_tecnica", data_riferimento=date(2026, 1, 15)))
    assert es.xml is not None, [e.messaggio for e in es.errori + es.quadri_mancanti]
    d = P.leggi(es.xml)
    imposte = {k: v for k, v in d["imposte"] if isinstance(v, Decimal) and not k.startswith("di cui")}
    assert imposte == UFFICIALE
    assert d["totale_ef"] == Decimal("9205.00") and d["importo_da_versare"] == Decimal("9205.00")
    r = calcola_da_xml(es.xml)
    assert r.stato == "completato" and r.imposta_ef18bis == 6600
    assert sorted(str(b.isn_esatta) for b in r.beneficiari) == ["3300", "3300"]


def test_dichiarazione_tardiva_non_genera_ef_senza_sanzioni():
    # stesso caso alla data del confronto (decesso 10/03/2025, oltre dodici mesi): il nostro programma blocca il
    # quadro EF finche' non si indicano le sanzioni; il compilatore ufficiale calcola comunque le imposte.
    es = esporta_xml(caso_fratelli_300k(), T.contesto_caso_a10(scopo="bozza_tecnica", data_riferimento=date(2026, 11, 6)))
    assert any("tardiva" in m.messaggio for m in es.quadri_mancanti + es.errori)
