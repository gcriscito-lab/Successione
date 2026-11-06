"""Prospetto per il cliente: legge solo il file generato (dati SINTETICI)."""
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
import telematico_casi as T  # noqa: E402
from successioni import prospetto_cliente as P  # noqa: E402
from successioni.archivio import Archivio  # noqa: E402
from successioni.servizio import Servizio  # noqa: E402
from successioni.telematico.calcolo import calcola_da_xml  # noqa: E402
from successioni.telematico.esporta import esporta_xml  # noqa: E402
from successioni.web import crea_app  # noqa: E402


@pytest.fixture(scope="module")
def xml():
    es = esporta_xml(T.caso_completo(), T.contesto(scopo="bozza_tecnica"))
    assert es.xml is not None
    return es.xml


def test_somme_per_erede_coincidono_con_i_totali_del_file(xml):
    d = P.leggi(xml)
    assert d["defunto"]["nome"] == "Rossi Mario" and d["defunto"]["decesso"] == "10/03/2025" and d["defunto"]["per_legge"]
    assert [s["nome"] for s in d["soggetti"].values()] == ["Rossi Anna", "Rossi Luca"]
    t = d["totali"]
    assert sum(s["attivo"] for s in d["soggetti"].values()) == t["TotaleAttivo"] == Decimal(161000)
    assert sum(s["passivo"] for s in d["soggetti"].values()) == t["TotalePassivo"] == Decimal(32000)
    assert t["TotaleValoreAsseEreditarioNetto"] == Decimal(129000)
    assert [b["gruppo"] for b in d["beni"]] == ["Terreni", "Fabbricati", "Altri beni e crediti"]
    casa = d["beni"][1]
    assert "Via Esempio 1" in casa["descrizione"] and "cat. A/2" in casa["descrizione"] and "sub. 3" in casa["descrizione"]
    assert d["beni"][0]["possesso"] == "1/2"                        # il defunto possedeva meta' del terreno
    assert dict(d["imposte"])["Imposta ipotecaria"] == Decimal(2820)
    assert d["importo_da_versare"] == Decimal("4435.00")


def test_html_leggibile_con_importi_italiani_e_avvisi(xml):
    h = P.html(xml, titolo="Successione <Rossi>", studio="Studio Prova", revisione=3, completo=False, obsoleto=True,
               oggi=date(2026, 11, 7))
    assert "Successione di Rossi Mario" in h and "Studio Prova" in h and "07/11/2026" in h
    assert "161.000 €" in h and "129.000 €" in h and "4.435,00 €" in h
    assert "Bozza" in h and "rigenera il file" in h and "Non sostituisce la dichiarazione" in h
    assert "&lt;Rossi&gt;" in h and "<Rossi>" not in h                 # testo dell'utente sempre in escape
    assert "Il defunto ne possedeva 1/2" in h and "Rossi Anna 1/2 (7.500,00 €)" in h
    assert "con addebito sul conto" in h
    assert "·" not in h


def test_imposta_per_erede_dal_calcolo_del_programma(xml):
    # gli stessi eredi come parenti senza franchigia (grado 12): imposta di successione dovuta
    root = etree.fromstring(xml)
    for g in root.iter("{%s}GradoParentela" % P.NS):
        g.text = "12"
    alt = etree.tostring(root)
    r = calcola_da_xml(alt)
    if r.stato != "completato":
        pytest.skip(f"calcolo non completato sul caso alterato: {r.stato}")
    per, nota = P.isn_per_erede(alt)
    assert nota is None and set(per) == {("1", "1"), ("1", "2")}
    assert abs(sum(per.values()) - r.imposta_ef18bis) <= 1
    assert all(v > 0 for v in per.values())


def test_euro():
    assert P.euro(Decimal("1234567.5")) == "1.234.567,50 €"
    assert P.euro(Decimal("999"), decimali=False) == "999 €"
    assert P.euro(Decimal("-2000")) == "−2.000,00 €"
    assert P.euro(None) == "—"


def test_api_prospetto_cliente(tmp_path):
    from test_elaborati import CF_FORN, ops_da_caso
    sv = Servizio(Archivio(tmp_path / "d"))
    c = TestClient(crea_app(sv, token="tok", ammetti_host_di_prova=True), base_url="http://testserver")
    pid = sv.crea_pratica("Caso", iniziali=ops_da_caso(T.caso_completo()))["pratica_id"]
    assert c.get(f"/api/pratiche/{pid}/prospetto-cliente", params={"t": "tok"}).status_code == 422   # nessun file ancora
    sv.esporta(pid, cf_fornitore=CF_FORN, scopo="bozza_tecnica")
    r = c.get(f"/api/pratiche/{pid}/prospetto-cliente", params={"t": "tok"})
    assert r.status_code == 200 and "Successione di Rossi Mario" in r.text and "rigenera il file" not in r.text
    rev = sv.leggi(pid)["revisione"]
    sv.aggiorna(pid, rev, [{"op": "upsert", "coll": "beni", "id": "b_casa0001", "campi": {"valore": "130000"}}])
    assert "rigenera il file" in c.get(f"/api/pratiche/{pid}/prospetto-cliente", params={"t": "tok"}).text
