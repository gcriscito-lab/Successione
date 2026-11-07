"""Terza revisione del 07/11/2026 (sera): concorrenza e validazione degli allegati. Dati SINTETICI, archivi temporanei.

1. Eliminazione/riordino/sostituzione dell'originale: controllo dei righi EG e cancellazione nella stessa transazione
   (riprodotto con due thread: un aggiornamento concorrente non puo' lasciare un rigo EG collegato a un allegato cancellato).
2. ``documenti_ref.allegato_id``: allegato esistente e della stessa pratica (aggiorna rifiuta, verifica segnala).
3. ``prepara_pdfa`` concorrente: un solo derivato, la seconda chiamata restituisce ``gia_convertito``.
4. Albero genealogico: revisione riletta al collegamento, pulizia limitata, rappresentazione circolare, ramo del rappresentato.
5. Esportazioni contemporanee: file temporanei con nome univoco.
"""
import json
import shutil
import threading
import time

import pytest

from successioni import albero_genealogico as AG
from successioni import pdfa
from successioni.archivio import Archivio
from successioni.errori import DatiNonValidi
from successioni.servizio import Servizio
from test_pdfa import crea_pdf


def _sv(tmp_path):
    return Servizio(Archivio(tmp_path / "d"))


def _allegato(sv, pid, nome="doc.pdf", pagine=1):
    crea_pdf(sv.cartella_ingresso / nome, pagine)
    return sv.acquisisci_da_ingresso(pid, nome, tipo_eg="Altro")["allegato_id"]


def _collega(sv, pid, aid, rid="dr_rigo0001", canale="gui"):
    return sv.aggiorna(pid, sv.leggi(pid)["revisione"],
                       [{"op": "upsert", "coll": "documenti_ref", "id": rid, "campi": {"allegato_id": aid, "tipo_eg": "Altro"}}],
                       canale=canale)


def _riferimenti_pendenti(sv, pid):
    ids = {a["id"] for a in sv.elenca_allegati(pid)}
    return [r for r in sv.leggi(pid)["dati"].get("documenti_ref", []) if r.get("allegato_id") not in ids]


# ------------------------------------------------------------------------------------------------------------ punto 1
def test_elimina_e_collegamento_concorrenti_due_thread(tmp_path):
    """Thread A elimina; mentre A ha appena controllato i righi EG, thread B (altra istanza, come MCP) collega l'allegato.
    Prima della correzione B riusciva e il rigo puntava a un allegato cancellato."""
    sv = _sv(tmp_path)
    sv_mcp = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("concorrenza")["pratica_id"]
    aid = _allegato(sv, pid)
    esiti = {}

    def collega():
        try:
            esiti["b"] = _collega(sv_mcp, pid, aid, canale="mcp")
        except DatiNonValidi as e:
            esiti["b"] = e

    originale = sv._usi_in
    th = threading.Thread(target=collega)

    def usi_poi_concorrente(c, a, p):
        r = originale(c, a, p)
        th.start()                 # B parte dopo il controllo di A e prima della sua cancellazione
        time.sleep(0.6)            # B resta in attesa del lock di scrittura di A
        return r

    sv._usi_in = usi_poi_concorrente
    assert sv.elimina_allegato(aid)["eliminato"] is True
    th.join(20)
    assert isinstance(esiti["b"], DatiNonValidi)
    assert esiti["b"].dettagli["errori"][0]["codice"] == "ALLEGATO_INESISTENTE"
    assert _riferimenti_pendenti(sv, pid) == []


def test_elimina_rifiutata_se_collegato_prima(tmp_path):
    sv = _sv(tmp_path)
    pid = sv.crea_pratica("x")["pratica_id"]
    aid = _allegato(sv, pid)
    _collega(sv, pid, aid)
    with pytest.raises(DatiNonValidi) as e:
        sv.elimina_allegato(aid)
    assert "usato nel quadro EG" in e.value.messaggio and e.value.dettagli["righi"] == ["dr_rigo0001"]
    assert aid in {a["id"] for a in sv.elenca_allegati(pid)}


def test_sostituzione_originale_non_cancella_se_ricollegato(tmp_path):
    """_dopo_conversione: se fra lo spostamento dei righi e la cancellazione l'originale viene ricollegato, resta."""
    sv = _sv(tmp_path)
    pid = sv.crea_pratica("x")["pratica_id"]
    aid = _allegato(sv, pid)
    p = tmp_path / "der.pdf"
    crea_pdf(p, 1)
    rap = {"conversione": {"comando_ok": True}, "validazione": {"esito": "non_verificato"}, "avvisi": [], "livello": "1b"}
    with sv.arch.transazione() as c:
        did = sv._registra(c, pid, "doc_pdfa.pdf", p, "derivato", aid, "Altro", None, None, {}, rap)["allegato_id"]
    _collega(sv, pid, aid)
    originale = sv._sposta_riferimenti

    def sposta_poi_ricollega(*a, **k):
        n = originale(*a, **k)
        _collega(sv, pid, aid, rid="dr_rigo0002")        # modifica concorrente dopo lo spostamento
        return n

    sv._sposta_riferimenti = sposta_poi_ricollega
    r = sv._dopo_conversione(sv._riga_allegato(aid), did, rap, "gui")
    assert r["originale_rimosso"] is False and "dr_rigo0002" in r["motivo_originale_conservato"]
    assert _riferimenti_pendenti(sv, pid) == []


def test_riordina_non_cancella_originale_ricollegato(tmp_path):
    sv = _sv(tmp_path)
    pid = sv.crea_pratica("x")["pratica_id"]
    aid = _allegato(sv, pid)
    p = tmp_path / "der.pdf"
    crea_pdf(p, 1)
    rap = {"conversione": {"comando_ok": True}, "validazione": {"esito": "non_verificato"}, "avvisi": [], "livello": "1b"}
    with sv.arch.transazione() as c:
        sv._registra(c, pid, "doc_pdfa.pdf", p, "derivato", aid, "Altro", None, None, {}, rap)
    _collega(sv, pid, aid)
    originale = sv._sposta_riferimenti

    def sposta_poi_ricollega(*a, **k):
        n = originale(*a, **k)
        _collega(sv, pid, aid, rid="dr_rigo0002")
        return n

    sv._sposta_riferimenti = sposta_poi_ricollega
    r = sv.riordina_allegati(pid)
    assert aid not in r["rimossi"] and aid in {a["id"] for a in sv.elenca_allegati(pid)}
    assert _riferimenti_pendenti(sv, pid) == []


# ------------------------------------------------------------------------------------------------------------ punto 2
def test_aggiorna_rifiuta_allegato_inesistente_o_di_altra_pratica(tmp_path):
    sv = _sv(tmp_path)
    p1 = sv.crea_pratica("uno")["pratica_id"]
    p2 = sv.crea_pratica("due")["pratica_id"]
    a2 = _allegato(sv, p2)
    rev = sv.leggi(p1)["revisione"]
    with pytest.raises(DatiNonValidi) as e:
        _collega(sv, p1, "al_inesistente1", canale="mcp")
    assert e.value.dettagli["errori"][0]["codice"] == "ALLEGATO_INESISTENTE"
    with pytest.raises(DatiNonValidi) as e:
        _collega(sv, p1, a2, canale="mcp")
    err = e.value.dettagli["errori"][0]
    assert err["codice"] == "ALLEGATO_DI_ALTRA_PRATICA" and p2 in err["messaggio"]
    assert sv.leggi(p1)["revisione"] == rev                       # nessuna modifica applicata
    # l'allegato della propria pratica va bene; una modifica successiva di altro tipo non ricontrolla il rigo invariato
    a1 = _allegato(sv, p1, "uno.pdf")
    _collega(sv, p1, a1)


def test_verifica_segnala_e_elimina_protegge_riferimenti_preesistenti(tmp_path):
    """Dati scritti prima della validazione (o da un ripristino): verifica_pratica li segnala e l'allegato dell'altra
    pratica, se usato, non si puo' cancellare."""
    sv = _sv(tmp_path)
    p1 = sv.crea_pratica("uno")["pratica_id"]
    p2 = sv.crea_pratica("due")["pratica_id"]
    a2 = _allegato(sv, p2)
    dati = sv.leggi(p1)["dati"]
    dati["documenti_ref"] = [{"id": "dr_altra0001", "allegato_id": a2, "tipo_eg": "Altro", "_origine": {}},
                             {"id": "dr_manca0001", "allegato_id": "al_sparito0001", "tipo_eg": "Altro", "_origine": {}}]
    with sv.arch.transazione() as c:
        c.execute("UPDATE pratiche SET dati=? WHERE id=?", (json.dumps(dati), p1))
    codici = {(x["codice"], x["percorso"]) for x in sv.verifica(p1)["rilievi"]}
    assert ("ALLEGATO_DI_ALTRA_PRATICA", "documenti_ref[dr_altra0001].allegato_id") in codici
    assert ("ALLEGATO_INESISTENTE", "documenti_ref[dr_manca0001].allegato_id") in codici
    with pytest.raises(DatiNonValidi) as e:
        sv.elimina_allegato(a2)
    assert e.value.dettagli["pratiche"] == [p1]


# ------------------------------------------------------------------------------------------------------------ punto 3
def test_prepara_pdfa_concorrente_un_solo_derivato(tmp_path, monkeypatch):
    sv = _sv(tmp_path)
    sv2 = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("x")["pratica_id"]
    aid = _allegato(sv, pid)
    barriera = threading.Barrier(2, timeout=20)

    def converti(src, out, livello):        # finta conversione: entrambe le chiamate superano il primo controllo
        barriera.wait()
        shutil.copyfile(src, out)
        with open(out, "ab") as f:
            f.write(b"\n%" + threading.current_thread().name.encode() + b"\n")
        return {"comando_ok": True, "stderr": ""}

    monkeypatch.setattr(pdfa, "converti_in_pdfa", converti)
    monkeypatch.setattr(pdfa, "valida_pdfa", lambda p, livello: {"esito": "non_verificato"})
    esiti = {}

    def chiama(nome, s, canale):
        esiti[nome] = s.prepara_pdfa(aid, canale=canale)

    ts = [threading.Thread(target=chiama, args=("gui", sv, "gui"), name="gui"),
          threading.Thread(target=chiama, args=("mcp", sv2, "mcp"), name="mcp")]
    for t in ts:
        t.start()
    for t in ts:
        t.join(60)
    derivati = [a for a in sv.elenca_allegati(pid) if a["ruolo"] == "derivato"]
    assert len(derivati) == 1
    assert sorted(bool(e.get("gia_convertito")) for e in esiti.values()) == [False, True]
    assert {e["derivato"]["allegato_id"] for e in esiti.values()} == {derivati[0]["id"]}


# ------------------------------------------------------------------------------------------------------------ punto 4
def P(i, **c):
    return {"op": "upsert", "coll": "persone", "id": i, "campi": c}


DEFUNTO = P("p_def0001", ruolo="defunto", cognome="Sintetico", nome="Mario", luogo_nascita="Roma", data_nascita="1940-01-01",
            data_decesso="2025-03-10", codice_fiscale="SNTMRA40A01H501X")


def _modello(*persone):
    return AG.costruisci({"persone": [dict(op["campi"], id=op["id"]) for op in persone], "opzioni": {}})


def test_rappresentazione_circolare_mostrata_con_avviso():
    m = _modello(DEFUNTO,
                 P("p_aaa0001", ruolo="erede", cognome="A", nome="Uno", codice_fiscale="AAAUNO70A01H501A", grado_parentela="04",
                   tipo_soggetto="1", rappresentato_cf="BBBDUE70A01H501B", rappresentato_grado="02"),
                 P("p_bbb0001", ruolo="erede", cognome="B", nome="Due", codice_fiscale="BBBDUE70A01H501B", grado_parentela="04",
                   tipo_soggetto="1", rappresentato_cf="AAAUNO70A01H501A", rappresentato_grado="02"))
    nomi = {n["nome"] for k in m["rami"] for n in AG._tutti(m["rami"][k])}
    assert {"Uno", "Due"} <= nomi
    assert sum("rappresentazione circolare" in a for a in m["avvisi"]) == 2


def test_figlio_premorto_in_pratica_va_nei_discendenti():
    m = _modello(DEFUNTO,
                 P("p_pre0001", ruolo="altro", cognome="Sintetico", nome="Paolo", codice_fiscale="SNTPLA72B02H501X",
                   grado_parentela="02", data_decesso="2020-01-01"),
                 P("p_nip0001", ruolo="erede", cognome="Sintetico", nome="Giulia", grado_parentela="04", tipo_soggetto="1",
                   rappresentato_cf="SNTPLA72B02H501X"))         # grado del rappresentato non indicato nel rigo
    assert "altri" not in m["rami"]
    paolo = m["rami"]["discendenti"][0]
    assert paolo["nome"] == "Paolo" and [f["nome"] for f in paolo["figli"]] == ["Giulia"]


@pytest.mark.parametrize("grado,ramo", [("04", "discendenti"), ("15", "collaterali")])
def test_rappresentato_assente_senza_grado_dal_grado_del_nipote(grado, ramo):
    m = _modello(DEFUNTO, P("p_nip0001", ruolo="erede", cognome="Sintetico", nome="Giulia", grado_parentela=grado,
                            tipo_soggetto="1", rappresentato_cf="ZZZZZZ70A01H501Z"))
    assert list(m["rami"]) == [ramo]
    assert m["rami"][ramo][0]["figli"][0]["nome"] == "Giulia"
    assert any("grado di parentela del rappresentato non indicato" in a for a in m["avvisi"])


def _pratica_albero(sv):
    pid = sv.crea_pratica("albero")["pratica_id"]
    sv.aggiorna(pid, 1, [DEFUNTO, P("p_fig0001", ruolo="erede", cognome="Sintetico", nome="Luca", luogo_nascita="Roma",
                                    data_nascita="1970-02-02", grado_parentela="02", tipo_soggetto="1")])
    return pid


def _finta_conversione(monkeypatch):
    monkeypatch.setattr(pdfa, "converti_in_pdfa", lambda s, o, l: (shutil.copyfile(s, o), {"comando_ok": True, "stderr": ""})[1])
    monkeypatch.setattr(pdfa, "valida_pdfa", lambda p, livello: {"esito": "non_verificato"})


def test_genera_albero_con_modifica_concorrente_e_pulizia_limitata(tmp_path, monkeypatch):
    sv = _sv(tmp_path)
    pid = _pratica_albero(sv)
    _finta_conversione(monkeypatch)
    vecchio = sv.genera_albero_genealogico(pid)["allegato_id"]
    originale = sv.prepara_pdfa
    estraneo = {}

    def prepara_con_concorrenza(aid, **k):
        r = originale(aid, **k)
        # durante la generazione: un'altra modifica della pratica (GUI) e un albero di una generazione concorrente
        # registrato ma non ancora collegato
        sv.aggiorna(pid, sv.leggi(pid)["revisione"], [{"op": "set", "sezione": "note", "campi": {"x": "y"}}])
        p = tmp_path / "altro.pdf"
        crea_pdf(p, 2)
        with sv.arch.transazione() as c:
            estraneo["id"] = sv._registra(c, pid, AG.NOME_FILE, p, "originale", None, AG.TIPO_EG, AG.FINALITA, None,
                                          {"generato": {"modulo": AG.MARCATORE, "impronta": "z"}})["allegato_id"]
        return r

    sv.prepara_pdfa = prepara_con_concorrenza
    r = sv.genera_albero_genealogico(pid, forza=True)               # prima: ConflittoRevisione
    assert r["esito"] == "generato"
    ids = {a["id"] for a in sv.elenca_allegati(pid)}
    assert vecchio not in ids                                       # albero precedente non usato: rimosso
    assert estraneo["id"] in ids                                    # albero della generazione concorrente: resta
    eg6 = [x for x in sv.leggi(pid)["dati"]["documenti_ref"] if x["tipo_eg"] == AG.TIPO_EG]
    assert [x["allegato_id"] for x in eg6] == [r["allegato_id"]]
    assert _riferimenti_pendenti(sv, pid) == []


# ------------------------------------------------------------------------------------------------------------ punto 5
def test_esportazioni_contemporanee_temporanei_univoci(tmp_path, monkeypatch):
    """Due esportazioni (GUI e MCP) dello stesso contenuto: ognuna usa un proprio file temporaneo nella stessa cartella."""
    from types import SimpleNamespace
    from successioni.telematico import esporta as ES
    from successioni.telematico import xsd as XS
    sv = _sv(tmp_path)
    sv2 = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("export")["pratica_id"]
    xml = b"<?xml version='1.0'?><prova/>"
    barriera = threading.Barrier(2, timeout=20)
    monkeypatch.setattr(ES, "esporta_xml", lambda dati, ctx: SimpleNamespace(
        xml=xml, completo=False, errori=[], non_supportato=[], avvisi=[], quadri_mancanti=[], versione="x", ambito="prova"))
    monkeypatch.setattr(XS, "valida_xsd", lambda b: [])
    temporanei = []
    scrivi = type(tmp_path).write_bytes

    def write_bytes(self, dati):
        if self.name.endswith(".tmp"):
            temporanei.append(self.name)
            barriera.wait()                 # entrambe le esportazioni stanno scrivendo il temporaneo nello stesso istante
        return scrivi(self, dati)

    monkeypatch.setattr(type(tmp_path), "write_bytes", write_bytes)
    errori = []

    def esporta(s):
        try:
            s.esporta(pid, cf_fornitore="SNTMRA40A01H501X", scopo="bozza_tecnica")
        except Exception as e:      # noqa: BLE001
            errori.append(e)

    ts = [threading.Thread(target=esporta, args=(x,)) for x in (sv, sv2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(60)
    assert errori == []
    assert len(temporanei) == 2 and len(set(temporanei)) == 2
    cart = tmp_path / "d" / "elaborati" / pid
    assert [p.read_bytes() for p in cart.glob("*.xml")] == [xml]
    assert list(cart.glob("*.tmp")) == []
