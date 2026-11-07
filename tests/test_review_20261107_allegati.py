"""Revisione 2026-11-07 degli allegati (dati SINTETICI, archivi temporanei).

1. riordina_allegati applica la stessa regola di prepara_pdfa (``originale_sostituibile``): derivato non conforme o con
   avvisi di rischio -> originale conservato, motivo riportato; i righi EG passano al PDF/A solo se non e' non conforme.
2. Seconda prepara_pdfa (ramo "gia' convertito") con derivato non conforme: originale conservato.
3. Il file del deposito non si cancella se l'impronta e' citata da un artefatto di job (DepositoArtefatti).
4. Copia nel deposito atomica; un file gia' presente ma troncato viene riscritto.
5. MCP: successioni_prepara_pdfa annotato come distruttivo.
"""
import asyncio

from successioni.archivio import SCHEMA_VERSIONE, Archivio
from successioni.collegamenti.base import DepositoArtefatti, RegistroJob
from successioni.integrita import verifica_copia
from successioni.servizio import Servizio
from test_pdfa import crea_pdf


def _pratica(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("EG")["pratica_id"]
    f = sv.cartella_ingresso / "albero.pdf"
    crea_pdf(f, 1)
    a = sv.acquisisci_da_ingresso(pid, "albero.pdf", tipo_eg="AlberoGenealogico")
    rev = sv.leggi(pid)["revisione"]
    sv.aggiorna(pid, rev, [{"op": "upsert", "coll": "documenti_ref", "id": "dr_albero1",
                            "campi": {"allegato_id": a["allegato_id"], "tipo_eg": "AlberoGenealogico"}}])
    return sv, pid, a["allegato_id"]


def _derivato_finto(sv, pid, aid, tmp_path, *, esito="non_verificato", avvisi=()):
    """Registra un derivato di conversione con il rapporto voluto (simula l'esito del validatore senza Ghostscript)."""
    p = tmp_path / f"derivato_{esito}_{len(avvisi)}.pdf"
    crea_pdf(p, 2)
    rapporto = {"conversione": {"comando_ok": True}, "validazione": {"esito": esito}, "avvisi": list(avvisi),
                "livello": "1b"}
    with sv.arch.transazione() as c:
        d = sv._registra(c, pid, "albero_pdfa.pdf", p, "derivato", aid, "AlberoGenealogico", None, None, {}, rapporto)
    return d["allegato_id"]


def _ids(sv, pid):
    return {x["id"] for x in sv.elenca_allegati(pid)}


# ---------------------------------------------------------------------------------------------- punto 1
def test_riordina_conserva_originale_se_derivato_non_conforme(tmp_path):
    sv, pid, aid = _pratica(tmp_path)
    did = _derivato_finto(sv, pid, aid, tmp_path, esito="non_conforme")
    r = sv.riordina_allegati(pid)
    assert _ids(sv, pid) == {aid, did}
    assert r["rimossi"] == [] and r["righi_eg_aggiornati"] == 0
    assert [x["allegato_id"] for x in r["originali_conservati"]] == [aid]
    assert "non e' conforme" in r["originali_conservati"][0]["motivo"]
    assert sv.leggi(pid)["dati"]["documenti_ref"][0]["allegato_id"] == aid


def test_riordina_conserva_originale_firmato(tmp_path):
    sv, pid, aid = _pratica(tmp_path)
    did = _derivato_finto(sv, pid, aid, tmp_path,
                          avvisi=["l'originale era firmato: il derivato NON conserva la firma"])
    r = sv.riordina_allegati(pid)
    assert _ids(sv, pid) == {aid, did}
    assert r["originali_conservati"][0]["derivato_id"] == did and "firmato" in r["originali_conservati"][0]["motivo"]
    # il PDF/A conforme va nel quadro EG; l'originale firmato resta fra i file non usati, da eliminare solo a mano
    assert sv.leggi(pid)["dati"]["documenti_ref"][0]["allegato_id"] == did and r["righi_eg_aggiornati"] == 1


def test_riordina_sostituisce_se_derivato_senza_rischi(tmp_path):
    sv, pid, aid = _pratica(tmp_path)
    did = _derivato_finto(sv, pid, aid, tmp_path)
    r = sv.riordina_allegati(pid)
    assert _ids(sv, pid) == {did} and r["rimossi"] == [aid] and r["originali_conservati"] == []
    assert sv.leggi(pid)["dati"]["documenti_ref"][0]["allegato_id"] == did


def test_regola_unica_originale_sostituibile():
    f = Servizio.originale_sostituibile
    assert f({"validazione": {"esito": "conforme"}, "avvisi": []}) == (True, None)
    assert f({"validazione": {"esito": "non_verificato"}, "avvisi": ["altro"]})[0] is True
    assert f({"validazione": {"esito": "non_conforme"}, "avvisi": []})[0] is False
    for a in ("testo divergente sulle pagine 1", "differenze visive da controllare alle pagine [1]"):
        assert f({"validazione": {"esito": "conforme"}, "avvisi": [a]})[0] is False
    assert f(None)[0] is False


# ---------------------------------------------------------------------------------------------- punto 2
def test_seconda_prepara_pdfa_con_derivato_non_conforme_conserva_originale(tmp_path):
    sv, pid, aid = _pratica(tmp_path)
    did = _derivato_finto(sv, pid, aid, tmp_path, esito="non_conforme")
    r = sv.prepara_pdfa(aid, sostituisci_originale=True)
    assert r["gia_convertito"] and r["derivato"]["allegato_id"] == did
    assert r["originale_rimosso"] is False and r["righi_eg_aggiornati"] == 0
    assert "non e' conforme" in r["motivo_originale_conservato"]
    assert _ids(sv, pid) == {aid, did}
    assert sv.leggi(pid)["dati"]["documenti_ref"][0]["allegato_id"] == aid


def test_seconda_prepara_pdfa_senza_rischi_sostituisce(tmp_path):
    sv, pid, aid = _pratica(tmp_path)
    did = _derivato_finto(sv, pid, aid, tmp_path)
    r = sv.prepara_pdfa(aid, sostituisci_originale=True)
    assert r["originale_rimosso"] is True and r["righi_eg_aggiornati"] == 1
    assert _ids(sv, pid) == {did}


# ---------------------------------------------------------------------------------------------- punto 3
def test_artefatto_con_stessa_impronta_non_cancellato_e_backup_verificato(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("EG")["pratica_id"]
    f = sv.cartella_ingresso / "ricevuta.pdf"
    crea_pdf(f, 1)
    a = sv.acquisisci_da_ingresso(pid, "ricevuta.pdf")
    dep = DepositoArtefatti(sv.arch)
    art = dep.salva_bytes(f.read_bytes(), "ricevuta.pdf", "ricevuta_suc13")
    assert art["sha256"] == a["sha256"]
    RegistroJob(sv.arch).crea("ricevuta_suc13", pid, {"prova": 1}, stato="ricevuta_acquisita",
                              risultato={"artefatti": [art]})
    sv.elimina_allegato(a["allegato_id"])
    assert sv.elenca_allegati(pid) == []
    assert dep.leggi(art) == f.read_bytes()
    dest = sv.arch.backup(tmp_path / "bk")
    verifica_copia(dest, SCHEMA_VERSIONE)


def test_blob_non_referenziato_cancellato(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("EG")["pratica_id"]
    crea_pdf(sv.cartella_ingresso / "x.pdf", 1)
    a = sv.acquisisci_da_ingresso(pid, "x.pdf")
    p = sv.arch.percorso_allegato(a["sha256"])
    assert p.is_file()
    sv.elimina_allegato(a["allegato_id"])
    assert not p.exists()


def test_doppia_acquisizione_stesso_contenuto_conserva_file(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("EG")["pratica_id"]
    crea_pdf(sv.cartella_ingresso / "x.pdf", 1)
    a1 = sv.acquisisci_da_ingresso(pid, "x.pdf")
    a2 = sv.acquisisci_da_ingresso(pid, "x.pdf")
    sv.elimina_allegato(a1["allegato_id"])
    assert (sv.arch.base / sv._riga_allegato(a2["allegato_id"])["percorso"]).is_file()


# ---------------------------------------------------------------------------------------------- punto 4
def test_file_troncato_nel_deposito_riscritto(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("EG")["pratica_id"]
    f = sv.cartella_ingresso / "x.pdf"
    crea_pdf(f, 2)
    a = sv.acquisisci_da_ingresso(pid, "x.pdf")
    p = sv.arch.percorso_allegato(a["sha256"])
    p.write_bytes(f.read_bytes()[:50])          # simula una copia interrotta
    b = sv.acquisisci_da_ingresso(pid, "x.pdf")
    assert b["sha256"] == a["sha256"] and b["bytes"] == f.stat().st_size
    assert p.read_bytes() == f.read_bytes()
    assert not list(p.parent.glob("*.tmp"))


# ---------------------------------------------------------------------------------------------- punto 5
def test_mcp_prepara_pdfa_distruttivo(tmp_path):
    from mcp.client import Client
    from successioni.mcp_server import costruisci

    async def elenco():
        async with Client(costruisci(Servizio(Archivio(tmp_path / "d")))) as c:
            return {t.name: t for t in (await c.list_tools()).tools}
    ann = asyncio.run(elenco())["successioni_prepara_pdfa"].annotations
    assert ann.destructive_hint is True and ann.read_only_hint is False
