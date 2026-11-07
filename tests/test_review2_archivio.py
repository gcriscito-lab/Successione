"""Revisione 2: archivio, impostazioni e server MCP (dati sintetici, nessun servizio esterno).

1. sola lettura di Claude fail-closed con configurazione illeggibile/non valida;
2. idempotenza di importa_xml_telematico e acquisisci_allegato (chiave_richiesta e impronta);
3. annotazione distruttiva di aggiorna_pratica;
4. creazione concorrente dell'archivio;
5. ripristino con voci automatiche, configurazione nel backup e piccoli errori di servizio.
"""
import asyncio
import json
import sqlite3
import threading
from datetime import date

import pytest
from mcp.client import Client

from successioni import impostazioni
from successioni.archivio import Archivio
from successioni.errori import ChiaveRiutilizzata, DatiNonValidi, NonTrovato, RipristinoNonAmmesso
from successioni.mcp_server import costruisci
from successioni.servizio import Servizio
from successioni.telematico.esporta import esporta_xml
from telematico_casi import caso_a10, contesto_caso_a10
from test_pdfa import crea_pdf

CF_STUDIO = "RSSMRA40A01H501K"


@pytest.fixture(autouse=True)
def _isola(monkeypatch, tmp_path):
    monkeypatch.delenv("SUCCESSIONI_MCP_SOLA_LETTURA", raising=False)
    monkeypatch.delenv("SUCCESSIONI_CONFIG", raising=False)
    monkeypatch.setenv("SUCCESSIONI_DATA", str(tmp_path / "dati"))


def chiama(sv, nome, args=None):
    async def scenario():
        async with Client(costruisci(sv)) as c:
            return await c.call_tool("successioni_" + nome, args or {})
    return asyncio.run(scenario())


def dati(res):
    sc = res.structured_content
    if sc is not None:
        return sc.get("result", sc) if isinstance(sc, dict) else sc
    return json.loads(res.content[0].text)


def strumenti(sv):
    async def elenco():
        async with Client(costruisci(sv)) as c:
            return {t.name.removeprefix("successioni_"): t for t in (await c.list_tools()).tools}
    return asyncio.run(elenco())


@pytest.fixture
def sv(tmp_path):
    return Servizio(Archivio(tmp_path / "dati"))


# ------------------------------------------------------------------------------------------ 1. sola lettura fail-closed
@pytest.mark.parametrize("contenuto", ["{non json", "[1, 2]", '{"preferenze": "si"}',
                                       '{"preferenze": {"mcp_sola_lettura": "si"}}'])
def test_configurazione_non_valida_mette_claude_in_sola_lettura(sv, contenuto):
    (sv.arch.base / "configurazione.json").write_text(contenuto, encoding="utf-8")
    n = len(sv.elenca())
    r = chiama(sv, "crea_pratica", {"titolo": "Non deve nascere", "chiave_richiesta": "k-ro"})
    assert r.is_error
    testo = r.content[0].text
    assert "SOLA_LETTURA" in testo and "sola lettura" in testo and "configurazione" in testo
    assert len(sv.elenca()) == n
    cap = dati(chiama(sv, "capacita"))
    assert cap["sola_lettura"] is True and "configurazione" in cap["motivo_sola_lettura"]
    assert not chiama(sv, "elenca_pratiche").is_error           # la lettura resta disponibile


def test_configurazione_illeggibile_sola_lettura(sv, monkeypatch):
    f = sv.arch.base / "configurazione.json"
    f.write_text('{"preferenze": {"mcp_sola_lettura": false}}', encoding="utf-8")
    vero = type(f).read_text

    def guasto(self, *a, **k):
        if self.name == "configurazione.json":
            raise PermissionError("accesso negato (sintetico)")
        return vero(self, *a, **k)
    monkeypatch.setattr(type(f), "read_text", guasto)
    valori, problema = impostazioni.leggi_preferenze(sv.arch.base)
    assert valori["mcp_sola_lettura"] is False and "non e' leggibile" in problema
    assert chiama(sv, "backup_archivio").is_error


def test_configurazione_assente_o_valida_non_blocca(sv):
    assert impostazioni.leggi_preferenze(sv.arch.base) == (impostazioni.PREFERENZE_DEFAULT, None)
    cap = dati(chiama(sv, "capacita"))
    assert cap["sola_lettura"] is False and cap["motivo_sola_lettura"] is None
    (sv.arch.base / "configurazione.json").write_text('{"preferenze": {"mcp_sola_lettura": true}}', encoding="utf-8")
    cap = dati(chiama(sv, "capacita"))
    assert cap["sola_lettura"] is True and "preferenza" in cap["motivo_sola_lettura"]


def test_stato_impostazioni_segnala_il_problema(tmp_path):
    f = tmp_path / "dati" / "configurazione.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    assert impostazioni.stato()["problema_configurazione"] is None
    f.write_text("{rotto", encoding="utf-8")
    st = impostazioni.stato()
    assert st["preferenze"] == impostazioni.PREFERENZE_DEFAULT        # l'interfaccia continua con i predefiniti
    assert "JSON" in st["problema_configurazione"]


# ------------------------------------------------------------------------------------------------- 2. idempotenza MCP
def test_importa_xml_con_chiave_non_duplica(sv):
    xml = esporta_xml(caso_a10(), contesto_caso_a10(data_riferimento=date(2025, 9, 1))).xml
    (sv.cartella_ingresso / "dich.xml").write_bytes(xml)
    a = dati(chiama(sv, "importa_xml_telematico", {"nome_file": "dich.xml", "chiave_richiesta": "imp-1"}))
    b = dati(chiama(sv, "importa_xml_telematico", {"nome_file": "dich.xml", "chiave_richiesta": "imp-1"}))
    assert a["pratica_id"] == b["pratica_id"] and b["ripetuta"] is True
    assert len(sv.elenca()) == 1
    r = chiama(sv, "importa_xml_telematico", {"nome_file": "dich.xml", "chiave_richiesta": "imp-1", "titolo": "Altro"})
    assert r.is_error and "CHIAVE_RICHIESTA_RIUTILIZZATA" in r.content[0].text
    # la chiave dell'importazione non si confonde con crea_pratica
    with pytest.raises(ChiaveRiutilizzata):
        sv.crea_pratica("x", chiave="imp-1")
    # senza chiave il comportamento resta quello di prima (nuova pratica)
    assert not chiama(sv, "importa_xml_telematico", {"nome_file": "dich.xml"}).is_error
    assert len(sv.elenca()) == 2


def test_acquisisci_allegato_idempotente(sv):
    pid = sv.crea_pratica("EG")["pratica_id"]
    crea_pdf(sv.cartella_ingresso / "x.pdf", 1)
    a = dati(chiama(sv, "acquisisci_allegato", {"pratica_id": pid, "nome_file": "x.pdf", "chiave_richiesta": "al-1"}))
    b = dati(chiama(sv, "acquisisci_allegato", {"pratica_id": pid, "nome_file": "x.pdf", "chiave_richiesta": "al-1"}))
    assert a["allegato_id"] == b["allegato_id"] and b["ripetuta"] is True
    c = dati(chiama(sv, "acquisisci_allegato", {"pratica_id": pid, "nome_file": "x.pdf"}))   # impronta: stesso allegato
    assert c["allegato_id"] == a["allegato_id"] and c["gia_presente"] is True
    assert len(sv.elenca_allegati(pid)) == 1
    d = dati(chiama(sv, "acquisisci_allegato", {"pratica_id": pid, "nome_file": "x.pdf", "tipo_eg": "AlberoGenealogico"}))
    assert d["allegato_id"] != a["allegato_id"]                  # altri metadati: allegato distinto
    assert len(sv.elenca_allegati(pid)) == 2
    r = chiama(sv, "acquisisci_allegato", {"pratica_id": pid, "nome_file": "x.pdf", "chiave_richiesta": "al-1",
                                           "persona_id": "p_abcd1234"})
    assert r.is_error and "CHIAVE_RICHIESTA_RIUTILIZZATA" in r.content[0].text


def test_acquisizione_con_deposito_rovinato_non_riusa(sv):
    pid = sv.crea_pratica("EG")["pratica_id"]
    f = sv.cartella_ingresso / "x.pdf"
    crea_pdf(f, 2)
    a = sv.acquisisci_da_ingresso(pid, "x.pdf", riusa_identico=True)
    p = sv.arch.percorso_allegato(a["sha256"])
    p.write_bytes(f.read_bytes()[:50])
    b = sv.acquisisci_da_ingresso(pid, "x.pdf", riusa_identico=True)
    assert b["allegato_id"] != a["allegato_id"] and p.read_bytes() == f.read_bytes()


# ------------------------------------------------------------------------------------------------- 3. annotazione
def test_aggiorna_pratica_distruttivo(sv):
    t = strumenti(sv)["aggiorna_pratica"]
    assert t.annotations.destructive_hint is True and t.annotations.read_only_hint is False
    assert "revisioni" in t.description


# ------------------------------------------------------------------------------------- 4. creazione concorrente archivio
def test_creazione_concorrente_archivio(tmp_path):
    for giro in range(5):
        base = tmp_path / f"nuovo{giro}"
        barriera, errori = threading.Barrier(6), []

        def apri():
            barriera.wait()
            try:
                Archivio(base)
            except Exception as e:          # noqa: BLE001
                errori.append(e)
        th = [threading.Thread(target=apri) for _ in range(6)]
        [t.start() for t in th]
        [t.join() for t in th]
        assert errori == []
        with sqlite3.connect(base / "archivio.sqlite3") as c:
            assert c.execute("PRAGMA user_version").fetchone()[0] == 1


def test_schema_parziale_senza_versione_completato(tmp_path):
    base = tmp_path / "parziale"
    base.mkdir()
    with sqlite3.connect(base / "archivio.sqlite3") as c:       # tabella gia' creata, versione non scritta
        c.execute("CREATE TABLE pratiche(id TEXT PRIMARY KEY, titolo TEXT NOT NULL, creata TEXT NOT NULL, "
                  "aggiornata TEXT NOT NULL, revisione INTEGER NOT NULL, dati TEXT NOT NULL)")
    Servizio(Archivio(base)).crea_pratica("ok")


# ------------------------------------------------------------------------------------------------- 5. ripristino e altro
def test_ripristino_ammette_voci_automatiche_e_porta_la_configurazione(sv, tmp_path):
    impostazioni.salva({}, profilo={"cf": CF_STUDIO, "tipo": "1"}, preferenze_nuove={"mcp_sola_lettura": True})
    cfg = sv.arch.base / "configurazione.json"
    contenuto = json.loads(cfg.read_text(encoding="utf-8"))
    contenuto["password_scritta_a_mano"] = "segreto-sintetico"          # chiave non nota: non deve finire nel backup
    contenuto["SUCCESSIONI_DATA"] = str(sv.arch.base)
    cfg.write_text(json.dumps(contenuto), encoding="utf-8")
    pid = sv.crea_pratica("Da ripristinare")["pratica_id"]
    bk = sv.arch.backup(tmp_path / "bk")
    copia = json.loads((bk / "configurazione.json").read_text(encoding="utf-8"))
    assert copia["profilo"]["cf"] == CF_STUDIO and copia["preferenze"]["mcp_sola_lettura"] is True
    assert "password_scritta_a_mano" not in copia and "SUCCESSIONI_DATA" not in copia

    dest_sv = Servizio(Archivio(tmp_path / "nuova"))
    dati(chiama(dest_sv, "capacita"))                                   # crea da solo la cartella «ingresso»
    assert (dest_sv.arch.base / "ingresso").is_dir()
    esito = dest_sv.arch.ripristina(bk)
    assert esito["configurazione"] == "ripristinata"
    assert Servizio(Archivio(tmp_path / "nuova")).leggi(pid)["titolo"] == "Da ripristinare"
    assert impostazioni.profilo_studio(tmp_path / "nuova") == {"cf": CF_STUDIO, "tipo": "1"}
    assert impostazioni.preferenze(tmp_path / "nuova")["mcp_sola_lettura"] is True


def test_ripristino_conserva_configurazione_della_destinazione(sv, tmp_path):
    sv.crea_pratica("x")
    (sv.arch.base / "configurazione.json").write_text('{"preferenze": {"mcp_sola_lettura": true}}', encoding="utf-8")
    bk = sv.arch.backup(tmp_path / "bk")
    dest = Archivio(tmp_path / "nuova")
    (dest.base / "configurazione.json").write_text('{"preferenze": {"pulizia_ore": 48}}', encoding="utf-8")
    assert dest.ripristina(bk)["configurazione"] == "conservata_destinazione"
    assert json.loads((dest.base / "configurazione.json").read_text()) == {"preferenze": {"pulizia_ore": 48}}


def test_ripristino_rifiuta_ingresso_con_file(sv, tmp_path):
    sv.crea_pratica("x")
    bk = sv.arch.backup(tmp_path / "bk")
    dest = Servizio(Archivio(tmp_path / "nuova"))
    (dest.cartella_ingresso / "documento.pdf").write_bytes(b"%PDF sintetico")
    with pytest.raises(RipristinoNonAmmesso, match="altri file"):
        dest.arch.ripristina(bk)
    assert (dest.cartella_ingresso / "documento.pdf").read_bytes() == b"%PDF sintetico"
    assert dest.arch.e_vuoto()


@pytest.mark.parametrize("limite", [-1, 0, "100", True])
def test_suddividi_limite_non_valido(sv, limite):
    pid = sv.crea_pratica("EG")["pratica_id"]
    crea_pdf(sv.cartella_ingresso / "x.pdf", 1)
    a = sv.acquisisci_da_ingresso(pid, "x.pdf")
    with pytest.raises(DatiNonValidi, match="limite_byte"):
        sv.suddividi_allegato(a["allegato_id"], limite)


def test_suddividi_limite_negativo_via_mcp_ha_codice(sv):
    pid = sv.crea_pratica("EG")["pratica_id"]
    crea_pdf(sv.cartella_ingresso / "x.pdf", 1)
    a = sv.acquisisci_da_ingresso(pid, "x.pdf")
    r = chiama(sv, "suddividi_allegato", {"allegato_id": a["allegato_id"], "limite_byte": -5})
    assert r.is_error and "DATI_NON_VALIDI" in r.content[0].text


def test_riduci_o_suddividi_limite_negativo(tmp_path):
    from successioni.documenti.dimensioni import riduci_o_suddividi
    crea_pdf(tmp_path / "x.pdf", 1)
    with pytest.raises(DatiNonValidi):
        riduci_o_suddividi(tmp_path / "x.pdf", -10, cartella_uscita=tmp_path / "o")


def test_elenca_allegati_pratica_inesistente(sv):
    with pytest.raises(NonTrovato):
        sv.elenca_allegati("pr_inesistente0")
    r = chiama(sv, "elenca_allegati", {"pratica_id": "pr_inesistente0"})
    assert r.is_error and "NON_TROVATO" in r.content[0].text


@pytest.mark.parametrize("operazioni", [["non un oggetto"], [42], [{"op": "set", "sezione": "note", "campi": [1]}], "upsert"])
def test_operazione_non_dizionario(sv, operazioni):
    pid = sv.crea_pratica("x")["pratica_id"]
    with pytest.raises(DatiNonValidi):
        sv.aggiorna(pid, 1, operazioni)
    assert sv.leggi(pid)["revisione"] == 1


def test_ripristina_revisione_riapplica_valida_forma(sv):
    pid = sv.crea_pratica("x")["pratica_id"]
    sv.aggiorna(pid, 1, [{"op": "set", "sezione": "note", "campi": {"a": "b"}}])
    guasti = json.loads(json.dumps(sv.leggi(pid, 1)["dati"]))
    guasti["persone"].append({"id": "p_abcd1234", "_origine": {}, "campo_inventato": "x"})
    with sv.arch.transazione() as c:                    # revisione storica non piu' conforme alle regole attuali
        c.execute("UPDATE revisioni SET dati=? WHERE pratica_id=? AND n=1", (json.dumps(guasti), pid))
    with pytest.raises(DatiNonValidi, match="controlli di forma"):
        sv.ripristina_revisione(pid, 2, 1)
    assert sv.leggi(pid)["revisione"] == 2
    with pytest.raises(NonTrovato):
        sv.ripristina_revisione("pr_inesistente0", 1, 1)
