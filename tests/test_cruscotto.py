"""«Prossime azioni» della pagina iniziale (src/successioni/cruscotto.py): tappe, azione e termine, dati SINTETICI."""
from datetime import date

from starlette.testclient import TestClient

from successioni import cruscotto as C
from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.web import crea_app
from test_correzioni_codex import pratica_con_allegati


def test_pratica_nuova_si_ferma_ai_dati_con_il_campo(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    sv.crea_pratica("Successione Prova", iniziali=[{"op": "upsert", "coll": "persone", "id": "p_defunto1",
                                                   "campi": {"ruolo": "defunto", "cognome": "Prova", "data_decesso": "2025-12-01"}}])
    c = C.cruscotto(sv, oggi=date(2026, 11, 7))
    v = c["pratiche"][0]
    assert v["tappe"] == {"dati": "corrente", "file": "da_fare", "controllo": "da_fare", "invio": "da_fare", "ricevute": "da_fare"}
    assert v["azione"]["testo"] and v["azione"]["dove"]["sel"]
    assert v["termine"] == {"data": "2026-12-01", "giorni": 24, "base": "decesso", "dal": "2025-12-01"}
    assert [t["nome"] for t in c["tappe"]] == ["Dati", "File", "Controllo", "Invio", "Ricevute"]


def test_pratica_completa_passa_al_file_e_poi_al_controllo(tmp_path):
    sv, pid = pratica_con_allegati(tmp_path)
    v = next(x for x in C.cruscotto(sv)["pratiche"] if x["pratica_id"] == pid)
    assert v["tappe"]["dati"] == "fatto" and v["tappe"]["file"] == "corrente" and v["azione"]["dove"] == {"sel": "FILE"}
    assert sv.esporta(pid)["completo"]
    v = next(x for x in C.cruscotto(sv)["pratiche"] if x["pratica_id"] == pid)
    assert v["tappe"]["file"] == "fatto" and v["tappe"]["controllo"] == "corrente" and "controllo" in v["azione"]["testo"].lower()


def test_ordine_per_termine_e_termine_superato(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    for t, dd in (("Lontana", "2026-10-01"), ("Superata", "2025-06-01"), ("Vicina", "2025-12-01")):
        sv.crea_pratica(t, iniziali=[{"op": "upsert", "coll": "persone", "id": "p_defunto1",
                                      "campi": {"ruolo": "defunto", "cognome": t, "data_decesso": dd}}])
    c = C.cruscotto(sv, oggi=date(2026, 11, 7))
    assert [v["titolo"] for v in c["pratiche"]] == ["Superata", "Vicina", "Lontana"]
    assert c["pratiche"][0]["termine"]["giorni"] < 0


def test_rotta_web(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    sv.crea_pratica("Una")
    cl = TestClient(crea_app(sv, token="tk", porta=8765), base_url="http://127.0.0.1:8765", follow_redirects=False)
    assert cl.get("/api/cruscotto").status_code == 401
    cl.get("/", params={"t": "tk"})
    r = cl.get("/api/cruscotto")
    assert r.status_code == 200 and r.json()["pratiche"][0]["titolo"] == "Una"


# ---------------------------------------------------------------- review 07/11/2026 (sera): Prossime azioni
class _SvFinto:
    """Servizio ridotto alle letture usate dal cruscotto, con stati di invio e ricevute scelti dal test."""
    def __init__(self, pratiche, trasmissione=None, registrazione=None):
        self.p, self.tr, self.reg = pratiche, trasmissione or {"stato": "non_preparata"}, registrazione

    def elenca(self):
        return [{"id": i, "titolo": t, "data_decesso": dd, "aggiornata": None} for i, t, dd in self.p]

    def stato_elaborati(self, pid):
        return {"export": {"stato": "aggiornato", "completo": True}, "controllo_ufficiale": {"stato": "positivo"},
                "trasmissione": self.tr}

    def quadri(self, pid):
        return {"rilievi": []}

    def leggi(self, pid):
        return {"dati": {"opzioni": {}}}

    def invio_stato(self, pid):
        return {"copie": [{"dettaglio": {"tentativo_corrente": "tn_1"}}]}

    def ricevute_stato(self, pid, tid):
        return {"registrazione": self.reg, "pagamento": "non_applicabile", "volture": "non_applicabile"}


def _una(sv):
    return C.cruscotto(sv, oggi=date(2026, 11, 7))["pratiche"][0]


def test_a_urgente_ma_ferma_non_sparisce(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    ferma = sv.crea_pratica("Urgente ferma", iniziali=[{"op": "upsert", "coll": "persone", "id": "p_defunto1",
                                                        "campi": {"ruolo": "defunto", "cognome": "U", "data_decesso": "2025-11-20"}}])["pratica_id"]
    for i in range(4):     # modificate dopo, termine lontano
        sv.crea_pratica(f"Recente {i}", iniziali=[{"op": "upsert", "coll": "persone", "id": "p_defunto1",
                                                   "campi": {"ruolo": "defunto", "cognome": f"R{i}", "data_decesso": "2026-10-01"}}])
    with sv.arch.transazione() as c:     # ferma da mesi: la meno recente dell'elenco
        c.execute("UPDATE pratiche SET aggiornata=? WHERE id=?", ("2026-01-01T00:00:00", ferma))
    assert sv.elenca()[-1]["titolo"] == "Urgente ferma"
    c = C.cruscotto(sv, limite=3, oggi=date(2026, 11, 7))
    assert c["pratiche"][0]["titolo"] == "Urgente ferma" and len(c["pratiche"]) == 3
    assert c["totale"] == 5 and c["altre"] == 2 and c["altre_da_lavorare"] == 2


def test_b_termine_dalla_decorrenza(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("Con decorrenza", iniziali=[{"op": "upsert", "coll": "persone", "id": "p_defunto1",
                                                       "campi": {"ruolo": "defunto", "cognome": "D", "data_decesso": "2025-12-01"}}])["pratica_id"]
    v = _una(sv)
    assert v["termine"]["base"] == "decesso" and v["termine"]["data"] == "2026-12-01"
    sv.aggiorna(pid, sv.leggi(pid)["revisione"], [{"op": "set", "sezione": "opzioni", "campi": {
        "telematico": {"dichiarazione": {"presentatore": {"data_decorrenza": "2026-03-01"}}}}}])
    v = _una(sv)
    assert v["termine"] == {"data": "2027-03-01", "giorni": 114, "base": "decorrenza", "dal": "2026-03-01"}
    assert "decorrenza" in C.cruscotto(sv)["nota"]
    # una decorrenza anteriore al decesso non vale (frontespizio.py, REGOLA_DECORRENZA_TERMINE): resta il decesso
    sv.aggiorna(pid, sv.leggi(pid)["revisione"], [{"op": "set", "sezione": "opzioni", "campi": {
        "telematico": {"dichiarazione": {"presentatore": {"data_decorrenza": "2025-01-01"}}}}}])
    assert _una(sv)["termine"]["base"] == "decesso"


def test_c_file_non_generabile_dice_il_motivo_e_porta_al_quadro(tmp_path):
    sv, pid = pratica_con_allegati(tmp_path)
    d = sv.leggi(pid)
    eg6 = next(r for r in d["dati"]["documenti_ref"] if r["tipo_eg"] == "AlberoGenealogico")
    sv.aggiorna(pid, d["revisione"], [{"op": "remove", "coll": "documenti_ref", "id": eg6["id"]}])
    v = next(x for x in C.cruscotto(sv)["pratiche"] if x["pratica_id"] == pid)
    assert v["tappe"]["dati"] == "fatto" and v["tappe"]["file"] == "problema"
    assert "non si può ancora generare" in v["azione"]["testo"] and "EG6" in v["azione"]["testo"]
    assert v["azione"]["livello"] == "problema" and v["azione"]["dove"]["sel"] == "EG"
    # dopo una generazione (non completa) il motivo viene dall'ultima esportazione, identico
    sv.esporta(pid)
    v2 = next(x for x in C.cruscotto(sv)["pratiche"] if x["pratica_id"] == pid)
    assert v2["azione"]["testo"] == v["azione"]["testo"]
    # senza fornitore: il primo motivo e' il fornitore
    sv.aggiorna(pid, sv.leggi(pid)["revisione"], [{"op": "set", "sezione": "opzioni", "campi": {"fornitore": None}}])
    v3 = next(x for x in C.cruscotto(sv)["pratiche"] if x["pratica_id"] == pid)
    assert v3["tappe"]["dati"] == "fatto" and v3["tappe"]["file"] == "problema"
    assert "fornitore" in v3["azione"]["testo"] and v3["azione"]["dove"] == {"sel": "FILE"}


def test_c_file_generabile_resta_genera(tmp_path):
    sv, pid = pratica_con_allegati(tmp_path)
    v = next(x for x in C.cruscotto(sv)["pratiche"] if x["pratica_id"] == pid)
    assert v["azione"]["testo"] == "Genera il file telematico" and "livello" not in v["azione"] and v["tappe"]["file"] == "corrente"
    assert not list((sv.arch.base / "elaborati").glob("**/*.xml"))          # la prova non salva file


def test_d_stati_della_copia_distinti():
    attesi = {"preparata": ("conferma e invia", None), "confermata": ("registra l'esito", None),
              "in_invio": ("registra l'esito", None), "rifiutata": ("prepara di nuovo", "problema"),
              "obsoleta": ("prepara di nuovo", "problema")}
    for stato, (frase, livello) in attesi.items():
        v = _una(_SvFinto([("pr_1", "Una", "2026-01-10")], {"stato": stato, "modalita": "manuale"}))
        assert v["tappe"]["invio"] in ("corrente", "problema"), stato
        assert frase in v["azione"]["testo"] and v["azione"].get("livello") == livello, (stato, v["azione"])
        assert ("conferma e invia" in v["azione"]["testo"]) == (stato == "preparata"), stato
    v = _una(_SvFinto([("pr_1", "Una", "2026-01-10")], {"stato": "rifiutata", "modalita": "manuale"}))
    assert "correggi" in v["azione"]["testo"] and v["tappe"]["invio"] == "problema"


def test_e_registrazione_negativa_e_un_problema():
    tr = {"stato": "trasmessa", "modalita": "manuale"}
    v = _una(_SvFinto([("pr_1", "Una", "2026-01-10")], tr, registrazione="attesa"))
    assert v["azione"]["testo"] == "Ricevuta di registrazione attesa" and "livello" not in v["azione"]
    v = _una(_SvFinto([("pr_1", "Una", "2026-01-10")], tr, registrazione="scartata"))
    assert "scartata" in v["azione"]["testo"] and v["azione"]["livello"] == "problema" and v["tappe"]["ricevute"] == "problema"
    assert not v["completata"]
    v = _una(_SvFinto([("pr_1", "Una", "2026-01-10")], tr, registrazione="contraddittorio: registrata, scartata"))
    assert v["azione"]["livello"] == "problema"
    v = _una(_SvFinto([("pr_1", "Una", "2026-01-10")], tr, registrazione="registrata"))
    assert v["completata"] and v["azione"]["testo"] == "Pratica completata"