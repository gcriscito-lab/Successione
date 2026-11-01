import json
import pytest
from successioni.archivio import Archivio
from successioni.servizio import (Servizio, ConflittoRevisione, DatiNonValidi, ChiaveRiutilizzata,
                                  impronta_dichiarativa)


@pytest.fixture
def sv(tmp_path):
    return Servizio(Archivio(tmp_path / "dati"))


def pers(**k):
    return {"op": "upsert", "coll": "persone", "campi": k}


def test_a04_doppia_richiesta_non_duplica(sv):
    p = sv.crea_pratica("Rossi", chiave="k1")
    p2 = sv.crea_pratica("Rossi", chiave="k1")
    assert p2["ripetuta"] and p2["pratica_id"] == p["pratica_id"]
    assert len(sv.elenca()) == 1
    op = [pers(cognome="Rossi", nome="Mario", ruolo="defunto")]
    r1 = sv.aggiorna(p["pratica_id"], 1, op, chiave="u1", canale="mcp")
    # stessa richiesta ripetuta con revisione ormai obsoleta: nessun conflitto, nessun doppione
    r2 = sv.aggiorna(p["pratica_id"], 1, op, chiave="u1", canale="mcp")
    assert r2["ripetuta"] and r2["revisione"] == r1["revisione"]
    assert len(sv.leggi(p["pratica_id"])["dati"]["persone"]) == 1


def test_chiave_riutilizzata_con_contenuto_diverso(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [pers(cognome="A")], chiave="k")
    with pytest.raises(ChiaveRiutilizzata):
        sv.aggiorna(pid, 1, [pers(cognome="B")], chiave="k")


def test_a04_conflitto_leggibile_e_non_sovrascrive(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [pers(id="p_aaaa1111", cognome="Manuale")], canale="gui")  # rev 2 (utente)
    with pytest.raises(ConflittoRevisione) as e:
        sv.aggiorna(pid, 1, [pers(id="p_aaaa1111", cognome="Claude")], canale="mcp")
    d = e.value.asdict()
    assert d["revisione_corrente"] == 2 and d["modifiche_successive"][0]["canale"] == "gui"
    assert sv.leggi(pid)["dati"]["persone"][0]["cognome"] == "Manuale"


def test_atomicita_nessuna_modifica_se_una_operazione_e_invalida(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    with pytest.raises(DatiNonValidi) as e:
        sv.aggiorna(pid, 1, [pers(cognome="Ok"), pers(codice_fiscale="corto")])
    assert e.value.dettagli["errori"][0]["percorso"].endswith(".codice_fiscale")
    assert sv.leggi(pid)["revisione"] == 1 and sv.leggi(pid)["dati"]["persone"] == []


def test_importi_e_quote_esatti(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    with pytest.raises(DatiNonValidi):
        sv.aggiorna(pid, 1, [{"op": "upsert", "coll": "beni", "campi": {"tipo": "terreno", "valore": "1.234,50"}}])
    with pytest.raises(DatiNonValidi):
        sv.aggiorna(pid, 1, [{"op": "upsert", "coll": "beni", "campi": {"quota_defunto": {"num": 3, "den": 2}}}])
    sv.aggiorna(pid, 1, [{"op": "upsert", "coll": "beni", "campi": {
        "tipo": "terreno", "valore": "1234.50", "quota_defunto": {"num": 1, "den": 3}, "rendita": {"stato": "da_confermare"}}}])


def test_riferimento_pendente_impedisce_rimozione(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [pers(id="p_aaaa1111", cognome="A"),
                         {"op": "upsert", "coll": "beni", "id": "b_bbbb2222", "campi": {"tipo": "terreno"}},
                         {"op": "upsert", "coll": "devoluzioni", "campi": {
                             "bene_id": "b_bbbb2222", "persona_id": "p_aaaa1111", "quota": "1/1"}}])
    with pytest.raises(DatiNonValidi):
        sv.aggiorna(pid, 2, [{"op": "remove", "coll": "persone", "id": "p_aaaa1111"}])


def test_a16_invalidazione_selettiva(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [pers(id="p_aaaa1111", cognome="A", ruolo="defunto")])
    base = sv.leggi(pid)["impronta_dichiarativa"]
    sv.aggiorna(pid, 2, [{"op": "set", "sezione": "note", "campi": {"promemoria": "telefonare"}}])
    assert sv.leggi(pid)["impronta_dichiarativa"] == base            # nota interna: nessuna invalidazione
    sv.aggiorna(pid, 3, [pers(id="p_aaaa1111", cognome="B")])
    assert sv.leggi(pid)["impronta_dichiarativa"] != base            # dato dichiarativo: invalida


def test_impronta_ignora_ordine_e_origine():
    a = {"persone": [{"id": "p_1", "x": 1, "_origine": {"x": "inserito"}}, {"id": "p_2"}]}
    b = {"persone": [{"id": "p_2"}, {"id": "p_1", "x": 1, "_origine": {"x": "confermato"}}]}
    assert impronta_dichiarativa(a) == impronta_dichiarativa(b)


def test_revisioni_diff_e_ripristino_non_distruttivo(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [pers(id="p_aaaa1111", cognome="A")])
    sv.aggiorna(pid, 2, [pers(id="p_aaaa1111", cognome="B")])
    assert any("cognome" in r for r in sv.differenze(pid, 2, 3))
    sv.ripristina_revisione(pid, 3, 2)
    assert sv.leggi(pid)["dati"]["persone"][0]["cognome"] == "A"
    assert len(sv.revisioni(pid)) == 4                                  # storia intatta


def test_a02_backup_ripristino_identico(sv, tmp_path):
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [pers(cognome="A")])
    atteso = sv.leggi(pid)
    dest = sv.arch.backup(tmp_path / "bk")
    sv2 = Servizio(Archivio(dest))
    assert sv2.leggi(pid) == atteso
    assert sv2.revisioni(pid) == sv.revisioni(pid)


def test_verifica_interna_segnala_quote_incomplete(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [pers(id="p_aaaa1111", cognome="D", ruolo="defunto", codice_fiscale="RSSMRA50A01H501X"),
                         {"op": "upsert", "coll": "beni", "id": "b_bbbb2222", "campi": {"tipo": "terreno", "foglio": "1", "particella": "2"}},
                         {"op": "upsert", "coll": "devoluzioni", "campi": {"bene_id": "b_bbbb2222", "persona_id": "p_aaaa1111", "quota": "1/3", "diritto": "proprieta"}}])
    cod = [r["codice"] for r in sv.verifica(pid)["rilievi"]]
    assert cod == ["DEVOLUZIONI_INCOMPLETE"]
