"""Voci 19 e 21 di docs/ANALISI_REPLICA_2026-11-07.md: rimedio per ogni rilievo dei controlli interni e avvisi di qualita'
dei dati anagrafici e catastali. Gli avvisi non bloccano la finalizzazione e non cambiano l'XML."""
import re
from pathlib import Path

import pytest

from successioni import qualita as QA
from successioni import rimedi as R
from successioni.telematico import identificativi as ID
from telematico_casi import caso_completo, copia

SRC = Path(__file__).resolve().parents[1] / "src" / "successioni"


def _codici(file: str, modello: str) -> set[str]:
    return set(re.findall(modello, (SRC / file).read_text(encoding="utf-8")))


def test_ogni_codice_dei_controlli_interni_ha_un_rimedio():
    """I codici prodotti da verifica_pratica (schema, quadri, sostitutiva, valore catastale, qualita') hanno tutti un rimedio."""
    errore = r'Errore\(\s*"([A-Z_]+)"'
    codici = (_codici("schema.py", errore) | _codici("quadri.py", errore) | _codici("qualita.py", errore)
              | _codici("telematico/sostitutiva.py", r'\(\s*"([A-Z_]+)",\s*_?[A-Z"]')
              | _codici("valore_catastale.py", r'"codice":\s*"([A-Z_]+)"'))
    assert {"CF_MANCANTE", "DEVOLUZIONI_INCOMPLETE", "CF_DUPLICATO", "VALORE_SOTTO_CATASTALE"} <= codici
    assert not codici - set(R.RIMEDI), sorted(codici - set(R.RIMEDI))


def test_rimedio_con_il_quadro_e_senza_segnaposto():
    assert "quadro EA" in R.rimedio("CF_MANCANTE", "EA")
    assert R.rimedio("CODICE_INESISTENTE", "EA") is None
    for cod in R.RIMEDI:
        t = R.rimedio(cod, "EC")
        assert "{" not in t and t.strip() and t.endswith((".", ")"))


def _servizio(tmp_path):
    from successioni.archivio import Archivio
    from successioni.servizio import Servizio
    return Servizio(Archivio(tmp_path / "dati"))


def _pratica(sv, d):
    from test_elaborati import ops_da_caso
    return sv.crea_pratica("Prova rimedi", iniziali=ops_da_caso(d))["pratica_id"]


def test_verifica_e_stato_quadri_riportano_il_rimedio(tmp_path):
    sv = _servizio(tmp_path)
    d = caso_completo()
    erede = next(p for p in d["persone"] if p["ruolo"] != "defunto")
    erede.pop("codice_fiscale")
    pid = _pratica(sv, d)
    v = sv.verifica(pid)
    r = next(x for x in v["rilievi"] if x["codice"] == "CF_MANCANTE")
    assert "quadro EA" in r["rimedio"] and "codice fiscale" in r["rimedio"]
    assert all("rimedio" in x for x in v["rilievi"] + v["avvisi"])
    q = sv.quadri(pid)
    assert next(x for x in q["rilievi"] if x["codice"] == "CF_MANCANTE")["rimedio"] == r["rimedio"]


# ------------------------------------------------------------------------------------------------- qualita' dei dati
def test_casi_sintetici_senza_avvisi_di_qualita():
    """Nessun falso positivo sui dati sintetici di riferimento."""
    assert QA.avvisi(caso_completo()) == []


def _cf_con_controllo(base15: str) -> str:
    return base15 + ID.carattere_controllo(base15)


@pytest.mark.parametrize("modifica, codice, campo", [
    (lambda p, d: p.update(cognome="ROSSI  ANNA"), "SPAZI_ANOMALI", "cognome"),
    (lambda p, d: p.update(nome=" MARIO"), "SPAZI_ANOMALI", "nome"),
    (lambda p, d: p.update(codice_fiscale=p["codice_fiscale"][:15] + ("A" if p["codice_fiscale"][15] != "A" else "B")),
     "CF_CONTROLLO_ERRATO", "codice_fiscale"),
    (lambda p, d: p.update(data_nascita="2099-01-01"), "NATO_DOPO_IL_DECESSO", "data_nascita"),
])
def test_avvisi_di_qualita_sulla_persona(modifica, codice, campo):
    d = copia(caso_completo())
    p = next(x for x in d["persone"] if x["ruolo"] != "defunto")
    modifica(p, d)
    a = [x for x in QA.avvisi(d) if x.codice == codice]
    assert a and a[0].percorso == f"persone[{p['id']}].{campo}", QA.avvisi(d)


def test_codice_fiscale_duplicato():
    d = copia(caso_completo())
    altri = [x for x in d["persone"] if x["ruolo"] != "defunto"]
    if len(altri) < 2:
        altri.append({**altri[0], "id": "p_doppio"}); d["persone"].append(altri[-1])
    altri[1]["codice_fiscale"] = altri[0]["codice_fiscale"]
    a = [x for x in QA.avvisi(d) if x.codice == "CF_DUPLICATO"]
    assert len(a) == 1 and a[0].percorso == f"persone[{altri[1]['id']}].codice_fiscale"


def test_codice_fiscale_incoerente_con_sesso_e_nascita():
    d = copia(caso_completo())
    p = next(x for x in d["persone"] if x["ruolo"] != "defunto")
    p["codice_fiscale"] = _cf_con_controllo("RSSMRA80A01H501")    # maschio, nato il 01/01/80
    p["sesso"], p["data_nascita"] = "F", "1980-01-02"
    cod = {(x.codice, x.percorso.split(".")[-1]) for x in QA.avvisi(d)}
    assert ("CF_INCOERENTE", "sesso") in cod and ("CF_INCOERENTE", "data_nascita") in cod
    p["sesso"], p["data_nascita"] = "M", "1980-01-01"
    assert not [x for x in QA.avvisi(d) if x.codice == "CF_INCOERENTE"]


def test_provincia_incoerente_solo_con_le_tabelle_dei_comuni(monkeypatch):
    d = copia(caso_completo())
    b = next(x for x in d["beni"] if x["tipo"] == "fabbricato")
    b["codice_comune"], b["provincia"] = "H501", "MI"
    monkeypatch.setattr(QA.CF, "cerca_comune", lambda c: None)            # componente non configurato: nessun avviso
    assert not [x for x in QA.avvisi(d) if x.codice == "PROVINCIA_INCOERENTE"]
    monkeypatch.setattr(QA.CF, "cerca_comune", lambda c: {"nome": "ROMA", "provincia": "RM"})
    a = [x for x in QA.avvisi(d) if x.codice == "PROVINCIA_INCOERENTE"]
    assert a and a[0].percorso == f"beni[{b['id']}].provincia"
    b["provincia"] = "rm"
    assert not [x for x in QA.avvisi(d) if x.codice == "PROVINCIA_INCOERENTE"]


def test_avvisi_leggono_anche_opzioni_telematico(monkeypatch):
    # review del 07/11/2026 sera: sesso delle persone e provincia/codice comune dei beni salvati in opzioni.telematico
    d = copia(caso_completo())
    p = next(x for x in d["persone"] if x["id"] == "p_anna0001")
    assert "sesso" not in p and d["opzioni"]["telematico"]["persone"]["p_anna0001"]["sesso"] == "F"
    p["codice_fiscale"] = _cf_con_controllo("RSSMRA80A01H501")    # maschio
    a = [x for x in QA.avvisi(d) if x.codice == "CF_INCOERENTE" and x.percorso.endswith(".sesso")]
    assert a and a[0].percorso == "persone[p_anna0001].sesso"
    b = d["beni"][0]
    assert "codice_comune" not in b and "provincia" not in b
    d["opzioni"]["telematico"]["beni"][b["id"]]["provincia"] = "MI"
    monkeypatch.setattr(QA.CF, "cerca_comune", lambda c: {"nome": "ROMA", "provincia": "RM"} if c == "H501" else None)
    a = [x for x in QA.avvisi(d) if x.codice == "PROVINCIA_INCOERENTE"]
    assert [x.percorso for x in a] == [f"beni[{b['id']}].provincia"]
    d["opzioni"]["telematico"]["beni"][b["id"]]["indirizzo"] = "Via  Esempio 1"
    assert any(x.codice == "SPAZI_ANOMALI" and x.percorso == f"beni[{b['id']}].indirizzo" for x in QA.avvisi(d))


def test_avvisi_di_qualita_non_bloccano_e_non_cambiano_l_xml(tmp_path):
    sv = _servizio(tmp_path)
    d = caso_completo()
    pid_ok = _pratica(sv, d)
    d2 = copia(caso_completo())
    next(x for x in d2["persone"] if x["ruolo"] != "defunto")["cognome"] += "  "
    pid = _pratica(sv, d2)
    v_ok, v = sv.verifica(pid_ok), sv.verifica(pid)
    assert v["esito"] == v_ok["esito"] and len(v["rilievi"]) == len(v_ok["rilievi"])
    a = next(x for x in v["avvisi"] if x["codice"] == "SPAZI_ANOMALI")
    assert "spazi" in a["rimedio"]
