"""Strumenti di studio della versione 0.4: copia anonima, preventivo e parcella, elenco delle pratiche in CSV. Dati SINTETICI."""
import csv
import io
import json
from decimal import Decimal

import pytest
from starlette.testclient import TestClient

import telematico_casi as T
from successioni import anonimizza as AN
from successioni import cruscotto as CR
from successioni import preventivo as PV
from successioni.archivio import Archivio
from successioni.errori import DatiNonValidi
from successioni.servizio import Servizio
from successioni.telematico.identificativi import cf_persona_fisica_valido
from successioni.web import crea_app


def _servizio_con_caso(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    dati = T.caso_completo()
    pid = sv.crea_pratica("Successione ROSSI MARIO", iniziali=AN.operazioni(dati))["pratica_id"]
    return sv, pid, dati


def _client(sv):
    cl = TestClient(crea_app(sv, token="tok123", ammetti_host_di_prova=True), base_url="http://testserver")
    cl.get("/", params={"t": "tok123"})
    return cl


# ------------------------------------------------------------------ copia anonima
def test_anonimizza_dati_nessun_dato_personale_resta(tmp_path):
    dati = T.caso_completo()
    originali = set()
    for p in dati["persone"]:
        originali |= {p.get(k) for k in ("cognome", "nome", "codice_fiscale") if p.get(k)}
    originali |= {T.IBAN_SINTETICO, "0612345678", "Via Esempio 1", "Fatture 1-5/2025", "Contratto mutuo rep. 123"}
    anon, fatto = AN.anonimizza_dati(dati)
    testo = json.dumps(anon, ensure_ascii=False)
    for x in originali:
        assert x not in testo, x
    assert anon["note"] == {} and anon["documenti_ref"] == [] and fatto
    for p in anon["persone"]:
        if p.get("codice_fiscale"):
            assert cf_persona_fisica_valido(p["codice_fiscale"]), p["codice_fiscale"]
    # date, importi e quote restano (servono ai calcoli)
    assert [b.get("valore") for b in anon["beni"]] == [b.get("valore") for b in dati["beni"]]
    assert [d.get("quota") for d in anon["devoluzioni"]] == [d.get("quota") for d in dati["devoluzioni"]]
    assert [p.get("data_nascita") for p in anon["persone"]] == [p.get("data_nascita") for p in dati["persone"]]
    # il presentatore e il titolare del conto puntano ancora alle stesse persone, con il codice nuovo
    dich = anon["opzioni"]["telematico"]["dichiarazione"]
    assert dich["presentatore"]["persona_id"] == "p_anna0001" and dich["presentatore"]["telefono"] == "0600000000"
    anna = next(p for p in anon["persone"] if p["id"] == "p_anna0001")
    assert dich["versamento"]["cf_titolare"] == anna["codice_fiscale"] and "iban" not in dich["versamento"]


def test_copia_anonima_crea_una_pratica_nuova_e_non_tocca_l_originale(tmp_path):
    sv, pid, _ = _servizio_con_caso(tmp_path)
    prima = sv.leggi(pid)
    cl = _client(sv)
    r = cl.post(f"/api/pratiche/{pid}/copia-anonima", json={"chiave": "k1"}).json()
    assert r["pratica_id"] != pid and r["titolo"].startswith("Copia anonima") and r["modifiche"]
    dopo = sv.leggi(pid)
    assert dopo["revisione"] == prima["revisione"] and dopo["dati"] == prima["dati"]
    nuova = sv.leggi(r["pratica_id"])
    assert all(p["cognome"] == "PERSONA" for p in nuova["dati"]["persone"])
    assert "ROSSI" not in nuova["titolo"]
    # stessa chiave: nessun doppione
    r2 = cl.post(f"/api/pratiche/{pid}/copia-anonima", json={"chiave": "k1"}).json()
    assert r2["pratica_id"] == r["pratica_id"]


def test_copia_anonima_esportabile_come_l_originale(tmp_path):
    from successioni.telematico.esporta import esporta_xml
    dati = T.caso_a10()
    anon, _ = AN.anonimizza_dati(dati)
    # tolti dalla copia: IBAN e documenti EG (gli allegati non si copiano); il test li rimette per provare il resto
    anon["opzioni"]["telematico"]["dichiarazione"]["versamento"]["iban"] = T.IBAN_SINTETICO
    anon["documenti_ref"] = dati["documenti_ref"]
    anna = next(p for p in anon["persone"] if p["id"] == "p_anna0001")
    r1 = esporta_xml(dati, T.contesto_caso_a10())
    r2 = esporta_xml(anon, T.contesto_caso_a10(cf_fornitore=anna["codice_fiscale"]))
    assert r1.xml is not None
    assert r2.xml is not None, [(e.codice, e.messaggio) for e in r2.errori]


# ------------------------------------------------------------------ preventivo e parcella
def test_calcola_solo_somme_con_percentuali_del_professionista():
    c = PV.calcola({"voci": [{"descrizione": "Dichiarazione", "importo": "1000"}, {"descrizione": "Volture", "importo": "250.50"}],
                    "cassa_pct": "4", "iva_pct": "22", "ritenuta_pct": "20"})
    assert c["compensi"] == Decimal("1250.50")
    assert c["cassa"] == Decimal("50.02") and c["iva"] == Decimal("286.11") and c["ritenuta"] == Decimal("250.10")
    assert c["totale"] == Decimal("1250.50") + Decimal("50.02") + Decimal("286.11") - Decimal("250.10")
    vuoto = PV.calcola({"voci": [{"descrizione": "A", "importo": "100"}]})
    assert vuoto["totale"] == Decimal("100") and vuoto["iva"] == 0
    with pytest.raises(DatiNonValidi):
        PV.calcola({"voci": [{"descrizione": "A", "importo": "-1"}]})
    with pytest.raises(DatiNonValidi):
        PV.calcola({"iva_pct": "150"})


def test_preventivo_e_parcella_html(tmp_path):
    sv, pid, _ = _servizio_con_caso(tmp_path)
    rev = sv.leggi(pid)["revisione"]
    sv.aggiorna(pid, rev, [{"op": "set", "sezione": "note", "campi": {"preventivo": {
        "voci": [{"descrizione": "Predisposizione <b>dichiarazione</b>", "importo": "800"}], "iva_pct": "22", "numero": "7/2026",
        "data": "2026-11-08", "intestatario": "Anna Rossi", "includi_imposte": True}}}])
    cl = _client(sv)
    h = cl.get(f"/api/pratiche/{pid}/preventivo", params={"tipo": "preventivo"}).text
    assert "Preventivo n. 7/2026" in h and "08/11/2026" in h and "976,00 €" in h and "IVA 22%" in h
    assert "&lt;b&gt;dichiarazione" in h            # testo dell'utente sempre escapato
    assert "genera prima il file" in h               # imposte richieste ma file non ancora generato
    p = cl.get(f"/api/pratiche/{pid}/preventivo", params={"tipo": "parcella"}).text
    assert "Parcella n. 7/2026" in p and "non una fattura" in p
    assert cl.get(f"/api/pratiche/{pid}/preventivo", params={"tipo": "fattura"}).status_code == 422
    # il preventivo sta nelle note interne: il dichiarato non cambia
    from successioni.servizio import impronta_dichiarativa
    d = sv.leggi(pid)["dati"]
    assert impronta_dichiarativa(d) == impronta_dichiarativa({**d, "note": {}})


# ------------------------------------------------------------------ elenco in CSV
def test_elenco_csv(tmp_path):
    sv, pid, _ = _servizio_con_caso(tmp_path)
    sv.crea_pratica("=HYPERLINK(\"x\")")
    cl = _client(sv)
    r = cl.get("/api/pratiche.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert r.headers["content-disposition"].startswith("attachment")
    testo = r.content.decode("utf-8")
    assert testo.startswith("﻿")
    righe = list(csv.reader(io.StringIO(testo[1:]), delimiter=";"))
    assert righe[0][:3] == ["Pratica", "Data di riferimento del termine", "Termine di presentazione"]
    assert len(righe) == 1 + 2
    titoli = {x[0] for x in righe[1:]}
    assert "Successione ROSSI MARIO" in titoli and "'=HYPERLINK(\"x\")" in titoli   # niente formule in Excel
    assert len(CR.csv_elenco(sv).splitlines()) == 3
