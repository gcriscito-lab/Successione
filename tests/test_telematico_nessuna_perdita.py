"""Nessuna perdita silenziosa: togliendo o svuotando un campo alla volta, l'esportazione non deve mai produrre un XML che
ha perso una riga dell'input senza segnalarlo, e senza XML deve sempre esserci almeno un errore, un caso non supportato
o un quadro mancante. Caso: successione testamentaria con legatario e legato (la piu' ricca)."""
import copy
from datetime import date

import pytest

from successioni.telematico.esporta import esporta_xml
from telematico_casi import caso_testamento_legato, contesto_caso_a10

COLLEZIONI = ("persone", "beni", "devoluzioni", "passivita", "documenti_ref")
BASE = caso_testamento_legato()
CTX = contesto_caso_a10(data_riferimento=date(2025, 9, 1))


def _mutazioni():
    for coll in COLLEZIONI:
        for i, e in enumerate(BASE[coll]):
            for campo in (k for k in e if not k.startswith("_") and k != "id"):
                yield ("dato", coll, i, None, campo)
    tel = BASE["opzioni"]["telematico"]
    for coll in ("persone", "beni", "passivita"):
        for id_, dd in tel[coll].items():
            for k in dd:
                yield ("tel", coll, id_, None, k)
    for k in tel["dichiarazione"]:
        yield ("tel", "dichiarazione", None, None, k)
    for sotto in ("testamento", "presentatore"):
        for k in tel["dichiarazione"].get(sotto, {}):
            yield ("tel", "dichiarazione", sotto, None, k)


def _applica(d, m, modo):
    tipo, coll, id_, _, campo = m
    if tipo == "dato":
        tgt = d[coll][id_]
    elif coll == "dichiarazione":
        tgt = d["opzioni"]["telematico"][coll] if id_ is None else d["opzioni"]["telematico"][coll][id_]
    else:
        tgt = d["opzioni"]["telematico"][coll][id_]
    if modo == "del":
        tgt.pop(campo, None)
    else:
        tgt[campo] = ""


@pytest.mark.parametrize("modo", ["del", "vuoto"])
def test_nessuna_perdita_silenziosa(modo):
    anomalie = []
    for m in _mutazioni():
        d = copy.deepcopy(BASE)
        _applica(d, m, modo)
        es = esporta_xml(d, CTX)
        if es.xml is not None:
            persi = [(c, x["id"]) for c in COLLEZIONI for x in d[c] if x["id"] not in es.mappa]
            if persi:
                anomalie.append((m, "XML con righe perse", persi))
        elif not (es.errori or es.non_supportato or es.quadri_mancanti):
            anomalie.append((m, "nessun XML e nessuna segnalazione"))
    assert anomalie == []
