"""Claude (MCP) in sola lettura: gli strumenti di scrittura sono rifiutati e non cambiano nulla; la lettura funziona;
la preferenza si rilegge a ogni chiamata; nessuno strumento resta non classificato (fail-closed)."""
import asyncio
import json

import pytest
from mcp.client import Client

from successioni import impostazioni
from successioni.errori import DatiNonValidi  # noqa: F401
from successioni.mcp_server import STRUMENTI_LETTURA, STRUMENTI_SCRITTURA, costruisci
from test_correzioni_codex import pratica_con_allegati


@pytest.fixture(autouse=True)
def _isola(monkeypatch, tmp_path):
    monkeypatch.delenv("SUCCESSIONI_MCP_SOLA_LETTURA", raising=False)
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "cfg" / "configurazione.json"))


def imposta(valore: bool):
    impostazioni.salva({}, preferenze_nuove={"mcp_sola_lettura": valore})


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


def argomenti_scrittura(pid, aid):
    """Argomenti validi per ogni strumento di scrittura: se la sola lettura non li bloccasse, farebbero qualcosa."""
    return {
        "crea_pratica": {"titolo": "Non deve nascere", "chiave_richiesta": "ro-1"},
        "aggiorna_pratica": {"pratica_id": pid, "revisione_attesa": 2, "chiave_richiesta": "ro-2",
                             "operazioni": [{"op": "set", "sezione": "opzioni", "campi": {"note": "x"}}]},
        "esporta_xml": {"pratica_id": pid},
        "controllo_ufficiale": {"pratica_id": pid},
        "backup_archivio": {},
        "stampa_modello": {"pratica_id": pid},
        "invio_prepara": {"pratica_id": pid, "chiave_richiesta": "ro-3"},
        "importa_xml_telematico": {"nome_file": "inesistente.xml"},
        "acquisisci_allegato": {"pratica_id": pid, "nome_file": "inesistente.pdf"},
        "prepara_pdfa": {"allegato_id": aid},
        "suddividi_allegato": {"allegato_id": aid},
        "riordina_allegati": {"pratica_id": pid},
        "registra_esito_controllo": {"pratica_id": pid, "file_dgn": "x.dgn", "file_log_schema": "x_logSchema.xml"},
    }


def test_ogni_strumento_registrato_e_classificato(tmp_path):
    from successioni.archivio import Archivio
    from successioni.servizio import Servizio

    async def elenco():
        async with Client(costruisci(Servizio(Archivio(tmp_path / "dati")))) as c:
            return {t.name.removeprefix("successioni_"): t for t in (await c.list_tools()).tools}
    tools = asyncio.run(elenco())
    assert not (STRUMENTI_LETTURA & STRUMENTI_SCRITTURA), "uno strumento non puo' essere insieme lettura e scrittura"
    assert set(tools) == STRUMENTI_LETTURA | STRUMENTI_SCRITTURA, (
        "strumenti non classificati (aggiungili a STRUMENTI_LETTURA o STRUMENTI_SCRITTURA): "
        f"{sorted(set(tools) ^ (STRUMENTI_LETTURA | STRUMENTI_SCRITTURA))}")
    for nome in STRUMENTI_LETTURA:
        assert tools[nome].annotations.read_only_hint is True, nome
    for nome in STRUMENTI_SCRITTURA:
        assert tools[nome].annotations.read_only_hint is False, nome


def test_sola_lettura_rifiuta_ogni_scrittura_senza_cambiare_nulla(tmp_path):
    sv, pid = pratica_con_allegati(tmp_path)
    aid = sv.leggi(pid)["dati"]["documenti_ref"][0]["allegato_id"]
    rev, n_pratiche, n_backup = sv.leggi(pid)["revisione"], len(sv.elenca()), len(sv.elenco_backup()["backup"])
    imposta(True)
    args = argomenti_scrittura(pid, aid)
    assert set(args) == STRUMENTI_SCRITTURA, "il test deve coprire tutti gli strumenti di scrittura"
    for nome, a in args.items():
        r = chiama(sv, nome, a)
        assert r.is_error, nome
        testo = r.content[0].text
        assert "SOLA_LETTURA" in testo and "sola lettura" in testo, (nome, testo)
    assert sv.leggi(pid)["revisione"] == rev
    assert len(sv.elenca()) == n_pratiche
    assert len(sv.elenco_backup()["backup"]) == n_backup
    assert sv.stato_elaborati(pid)["export"]["stato"] == "non_eseguito"        # nemmeno l'export e' partito


def test_sola_lettura_lascia_funzionare_la_lettura(tmp_path):
    sv, pid = pratica_con_allegati(tmp_path)
    imposta(True)
    assert dati(chiama(sv, "capacita"))["sola_lettura"] is True
    assert dati(chiama(sv, "leggi_pratica", {"pratica_id": pid}))["pratica_id"] == pid
    assert not chiama(sv, "elenca_pratiche").is_error
    assert not chiama(sv, "verifica_pratica", {"pratica_id": pid}).is_error
    assert not chiama(sv, "stato_quadri", {"pratica_id": pid}).is_error
    assert not chiama(sv, "stato_elaborati", {"pratica_id": pid}).is_error
    assert not chiama(sv, "revisioni_pratica", {"pratica_id": pid}).is_error
    assert not chiama(sv, "elenca_allegati", {"pratica_id": pid}).is_error
    assert not chiama(sv, "invio_stato", {"pratica_id": pid}).is_error
    assert not chiama(sv, "schema_dati").is_error
    assert not chiama(sv, "file_in_ingresso").is_error
    assert not chiama(sv, "decodifica_codice_fiscale", {"codice_fiscale": "RSSMRA40A01H501K"}).is_error


def test_disattivando_la_preferenza_tutto_torna(tmp_path):
    sv, pid = pratica_con_allegati(tmp_path)
    imposta(True)
    assert chiama(sv, "esporta_xml", {"pratica_id": pid}).is_error
    imposta(False)                                   # nessun riavvio: la preferenza si rilegge a ogni chiamata
    assert dati(chiama(sv, "capacita"))["sola_lettura"] is False
    r = chiama(sv, "esporta_xml", {"pratica_id": pid})
    assert not r.is_error and dati(r)["completo"]
    assert dati(chiama(sv, "backup_archivio"))["verificato"] is True


def test_variabile_d_ambiente_forza_la_sola_lettura(tmp_path, monkeypatch):
    sv, pid = pratica_con_allegati(tmp_path)
    monkeypatch.setenv("SUCCESSIONI_MCP_SOLA_LETTURA", "1")
    assert chiama(sv, "backup_archivio").is_error
    assert dati(chiama(sv, "capacita"))["sola_lettura"] is True
