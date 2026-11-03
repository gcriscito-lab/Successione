"""Decodifica del codice fiscale: sesso, data di nascita, omocodia, secolo, luogo dalle tabelle del componente ufficiale (finto nei test)."""
import zipfile
from datetime import date

import pytest
from starlette.testclient import TestClient

from successioni import codice_fiscale as CF
from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.telematico import identificativi as ID
from successioni.web import crea_app

OGGI = date(2026, 11, 3)
SOSTITUZIONI = "LMNPQRSTUV"


def _cf(sesso="M", nascita="1940-01-01", comune="H501", cognome="Rossi", nome="Mario"):
    return ID.genera_cf_sintetico(cognome, nome, sesso, nascita, comune)


def _con_omocodia(cf: str, posizioni) -> str:
    s = list(cf[:15])
    for p in posizioni:
        s[p] = SOSTITUZIONI[int(s[p])]
    base = "".join(s)
    return base + ID.carattere_controllo(base)


@pytest.fixture
def jar_finto(tmp_path, monkeypatch):
    jar = tmp_path / "controlliXMLREG2013.jar"
    prefisso = "it/finanze/entrate/sco/resources/"
    with zipfile.ZipFile(jar, "w") as z:
        z.writestr(prefisso + "comuni_conservatorie.res", "#123\nROMA*H501*M1AA*RM*RM10\nBOLZANO*A952*E2AA*BZ*-\nTORINO*L219*X*TO*TO00\nDOPPIO*K001*U*-*-\nDOPPIO*K001*U*MI*MI00\n".encode("latin-1"))
        z.writestr(prefisso + "comuni_ccat_13.res", "#456\nROMA*H501*0\nSOPPRESSO*B001*1\n".encode("latin-1"))
    monkeypatch.setenv("SUCCESSIONI_CONTROLLI_SUC13", str(tmp_path))
    CF._comuni.cache_clear()
    yield jar
    CF._comuni.cache_clear()


@pytest.mark.parametrize("sesso,nascita", [("M", "1940-01-01"), ("F", "1970-01-01"), ("F", "1985-12-31"), ("M", "2000-02-29"),
                                           ("F", "1991-06-15"), ("M", "1952-10-07"), ("F", "1963-09-30")])
def test_andata_e_ritorno_con_il_generatore_verificato(sesso, nascita, jar_finto):
    r = CF.decodifica(_cf(sesso, nascita), oggi=OGGI)
    assert r["valido"] is True and r["motivi"] == []
    assert r["campi"]["sesso"] == sesso and r["campi"]["data_nascita"] == nascita
    assert r["campi"]["luogo_nascita"] == "ROMA" and r["campi"]["provincia_nascita"] == "RM"


def test_il_giorno_oltre_40_indica_una_donna_e_non_altera_la_data():
    r = CF.decodifica(_cf("F", "1975-03-09"), oggi=OGGI)
    assert r["campi"]["sesso"] == "F" and r["campi"]["data_nascita"] == "1975-03-09"


@pytest.mark.parametrize("posizioni", [(6,), (14,), (6, 7, 9, 10, 12, 13, 14), (9, 10)])
def test_omocodia_stessi_dati_e_avviso(posizioni):
    base = _cf("M", "1968-05-12")
    omo = _con_omocodia(base, posizioni)
    assert omo != base
    r = CF.decodifica(omo, oggi=OGGI)
    assert r["valido"] is True and r["dettaglio"]["omocodia"] is True
    assert r["campi"]["data_nascita"] == "1968-05-12" and r["campi"]["sesso"] == "M"
    assert any("omocodia" in a for a in r["avvisi"])


def test_senza_omocodia_nessun_avviso():
    r = CF.decodifica(_cf(), oggi=OGGI)
    assert r["dettaglio"]["omocodia"] is False and not any("omocodia" in a for a in r["avvisi"])


def test_carattere_di_controllo_errato():
    cf = _cf()
    sbagliato = cf[:15] + ("A" if cf[15] != "A" else "B")
    r = CF.decodifica(sbagliato, oggi=OGGI)
    assert r["valido"] is False and any("carattere di controllo errato" in m for m in r["motivi"])
    assert r["campi"]["data_nascita"] == "1940-01-01"          # i dati si ricavano lo stesso: la decisione e' dell'utente


@pytest.mark.parametrize("cf,frammento", [("", "16 caratteri"), ("ABC", "16 caratteri"), ("RSSMRA40A01H501", "16 caratteri"),
                                          ("RSSMRA40A01H501KK", "16 caratteri"), ("12345678901", "11 cifre"),
                                          ("RSSMRA40A01H501!", "16 caratteri")])
def test_formato_non_valido(cf, frammento):
    r = CF.decodifica(cf, oggi=OGGI)
    assert r["valido"] is False and r["campi"] == {} and frammento in r["motivi"][0]


def test_minuscole_e_spazi_sono_tollerati():
    r = CF.decodifica("  " + _cf().lower() + " ", oggi=OGGI)
    assert r["valido"] is True and r["dettaglio"]["codice_fiscale"] == _cf()


def test_data_impossibile_non_valida():
    base = "RSSMRA40B31H501"                                     # 31 febbraio
    r = CF.decodifica(base + ID.carattere_controllo(base), oggi=OGGI)
    assert r["valido"] is False and any("data di nascita impossibile" in m for m in r["motivi"])
    assert "data_nascita" not in r["campi"]


def test_lettera_del_mese_non_valida():
    base = "RSSMRA40F01H501"                                     # F non e' una lettera di mese
    r = CF.decodifica(base + ID.carattere_controllo(base), oggi=OGGI)
    assert any("lettera del mese" in m for m in r["motivi"])


@pytest.mark.parametrize("yy,ruolo,atteso,ambiguo", [
    ("90", None, "1990", False),      # 2090 e' nel futuro
    ("05", None, "2005", False),      # 1905: oltre 110 anni
    ("40", "defunto", "1940", False),
    ("20", "defunto", "1920", True),  # 1920 (106 anni) e 2020 entrambi plausibili: il defunto e' del 1900
    ("20", None, "2020", True),       # ... gli altri soggetti sono del 2000
    ("16", None, "2016", True),       # 1916 ha 110 anni
    ("15", None, "2015", False),      # 1915 ha 111 anni
])
def test_secolo_dedotto(yy, ruolo, atteso, ambiguo, jar_finto):
    base = f"RSSMRA{yy}A01H501"
    r = CF.decodifica(base + ID.carattere_controllo(base), oggi=OGGI, ruolo=ruolo)
    assert r["campi"]["data_nascita"] == f"{atteso}-01-01"
    assert any("secolo non determinabile" in a for a in r["avvisi"]) is ambiguo


def test_data_nel_futuro_non_assume_il_2000():
    base = "RSSMRA26T01H501"                                     # dicembre 2026: dopo la data fissata
    r = CF.decodifica(base + ID.carattere_controllo(base), oggi=OGGI)
    assert r["campi"]["data_nascita"] == "1926-12-01"


def test_nato_all_estero(jar_finto):
    base = "RSSMRA70A01Z110"
    r = CF.decodifica(base + ID.carattere_controllo(base), oggi=OGGI)
    assert r["valido"] is True and r["campi"]["provincia_nascita"] == "EE" and "luogo_nascita" not in r["campi"]
    assert any("estero" in a and "Z110" in a for a in r["avvisi"])


def test_comuni_dalle_tabelle_con_ripiego(jar_finto):
    assert CF.cerca_comune("A952") == {"nome": "BOLZANO", "provincia": "BZ"}
    assert CF.cerca_comune("B001") == {"nome": "SOPPRESSO", "provincia": None}     # solo nella seconda tabella: senza provincia
    assert CF.cerca_comune("Q999") is None
    r = CF.decodifica(_cf(comune="B001"), oggi=OGGI)
    assert r["campi"]["luogo_nascita"] == "SOPPRESSO" and "provincia_nascita" not in r["campi"]


def test_stesso_comune_due_volte_vince_la_voce_con_la_provincia(jar_finto):
    assert CF.cerca_comune("K001") == {"nome": "DOPPIO", "provincia": "MI"}


def test_comune_sconosciuto_avviso(jar_finto):
    r = CF.decodifica(_cf(comune="Q999"), oggi=OGGI)
    assert "luogo_nascita" not in r["campi"] and any("Q999" in a and "non trovato" in a for a in r["avvisi"])


def test_senza_componente_ufficiale_resta_il_codice_catastale(monkeypatch):
    monkeypatch.delenv("SUCCESSIONI_CONTROLLI_SUC13", raising=False)
    r = CF.decodifica(_cf(), oggi=OGGI)
    assert r["valido"] is True and "luogo_nascita" not in r["campi"] and r["dettaglio"]["codice_catastale"] == "H501"
    assert any("tabelle dei comuni non disponibili" in a for a in r["avvisi"])


def test_cartella_senza_jar_o_jar_rotto_non_solleva(tmp_path, monkeypatch):
    monkeypatch.setenv("SUCCESSIONI_CONTROLLI_SUC13", str(tmp_path))
    assert CF.cerca_comune("H501") is None
    (tmp_path / "controlliXMLREG2013.jar").write_bytes(b"non e' uno zip")
    CF._comuni.cache_clear()
    assert CF.cerca_comune("H501") is None


def test_i_campi_decodificati_sono_campi_del_modello(jar_finto):
    from successioni.schema import COLLEZIONI
    r = CF.decodifica(_cf(), oggi=OGGI)
    assert set(r["campi"]) <= set(COLLEZIONI["persone"])


# ------------------------------------------------------------------------------------------------------------ API
def _client(tmp_path):
    return TestClient(crea_app(Servizio(Archivio(tmp_path / "dati")), token="sintetico", ammetti_host_di_prova=True))


def test_api_decodifica_e_richiede_il_token(tmp_path, jar_finto):
    cf = _cf("F", "1970-01-01")
    with _client(tmp_path) as cl:
        r = cl.get(f"/api/codice-fiscale?cf={cf}&t=sintetico")
        assert r.status_code == 200
        j = r.json()
        assert j["valido"] is True and j["campi"]["sesso"] == "F" and j["campi"]["luogo_nascita"] == "ROMA"
        assert cl.get(f"/api/codice-fiscale?cf={cf}").status_code == 401
        vuoto = cl.get("/api/codice-fiscale?t=sintetico").json()
        assert vuoto["valido"] is False and vuoto["campi"] == {}


def test_api_passa_il_ruolo_per_il_secolo(tmp_path, jar_finto):
    base = "RSSMRA20A01H501"
    cf = base + ID.carattere_controllo(base)
    with _client(tmp_path) as cl:
        d = cl.get(f"/api/codice-fiscale?cf={cf}&ruolo=defunto&t=sintetico").json()
        e = cl.get(f"/api/codice-fiscale?cf={cf}&t=sintetico").json()
    assert d["campi"]["data_nascita"].startswith("19") and e["campi"]["data_nascita"].startswith("20")
