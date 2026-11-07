"""Valore catastale dei fabbricati e dei terreni (src/successioni/valore_catastale.py), dati SINTETICI.

Regole e fonti: docs/regole/valore_catastale.md (L. 662/1996 art. 3 c. 48 e 51; D.Lgs. 141/2026 art. 309 c. 6-8;
Fascicolo I p. PDF 26 per la prima casa estesa agli altri beneficiari)."""
import pytest

from successioni import valore_catastale as VC
from telematico_casi import caso_completo, caso_prima_casa, copia


def _fab(**kw):
    b = {"id": "b_x", "tipo": "fabbricato", "categoria": "A/2", "rendita": "1000.00", "diritto": "1", "quota_defunto": "1/1"}
    b.update(kw)
    return b


def _dati(beni, decesso="2025-03-10", devoluzioni=()):
    return {"persone": [{"id": "p_d", "ruolo": "defunto", "data_decesso": decesso}], "beni": list(beni),
            "devoluzioni": list(devoluzioni)}


@pytest.mark.parametrize("categoria,atteso", [
    ("A/2", "126000"),      # 1000 x 1,05 x 120 (lettera f)
    ("A/10", "63000"),      # x 60 (lettera d)
    ("D/1", "63000"),
    ("B/1", "176400"),      # x 168 (lettera b)
    ("C/1", "42840"),       # x 40,80 (lettera c)
    ("E/3", "42840"),
    ("C/6", "126000"),      # altre categorie (lettera f)
])
def test_moltiplicatori_per_categoria(categoria, atteso):
    r = VC.calcola(_dati([_fab(categoria=categoria)]), _fab(categoria=categoria))
    assert r["calcolabile"] and r["valore"] == atteso, r


def test_quota_e_arrotondamento_per_eccesso():
    b = _fab(rendita="333.33", quota_defunto="1/3")
    r = VC.calcola(_dati([b]), b)
    # 333,33 x 1,05 x 120 / 3 = 13999,86 -> 14000 (il valore dichiarato deve essere non inferiore)
    assert r["valore"] == "14000"


def test_prima_casa_basta_un_beneficiario():
    b = _fab()
    devs = [{"id": "d1", "bene_id": "b_x", "persona_id": "p1", "agevolazioni": "P"},
            {"id": "d2", "bene_id": "b_x", "persona_id": "p2"}]
    r = VC.calcola(_dati([b], devoluzioni=devs), b)
    assert r["valore"] == "115500" and "lettera e" in r["formula"]     # 1000 x 1,05 x 110


def test_prima_casa_non_vale_per_le_pertinenze_c():
    b = _fab(categoria="C/6")
    devs = [{"id": "d1", "bene_id": "b_x", "persona_id": "p1", "agevolazioni": "P"}]
    assert VC.calcola(_dati([b], devoluzioni=devs), b)["valore"] == "126000"


def test_terreno_agricolo_e_edificabile():
    t = {"id": "t1", "tipo": "terreno", "natura": "T", "tipologia_terreno": "3", "reddito_dominicale": "100.00",
         "diritto": "1", "quota_defunto": "1/2"}
    r = VC.calcola(_dati([t]), t)
    assert r["valore"] == "5625"           # 100 x 1,25 x 90 / 2
    t2 = {**t, "tipologia_terreno": "1"}
    r2 = VC.calcola(_dati([t2]), t2)
    assert not r2["calcolabile"] and "edificabile" in r2["motivo"]


@pytest.mark.parametrize("modifica,parola", [
    ({"diritto": "2"}, "piena proprieta'"),
    ({"categoria": "F/3"}, "fittizia"),
    ({"rendita": None}, "rendita"),
    ({"quota_defunto": None}, "quota"),
    ({"provincia": "EE"}, "estero"),
])
def test_casi_non_calcolati_con_motivo(modifica, parola):
    b = _fab(**modifica)
    r = VC.calcola(_dati([b]), b)
    assert not r["calcolabile"] and parola in r["motivo"], r


def test_successioni_prima_del_2007_non_calcolate():
    b = _fab()
    r = VC.calcola(_dati([b], decesso="2005-06-01"), b)
    assert not r["calcolabile"] and "2007" in r["motivo"]


def test_confronto_con_il_dichiarato_e_avviso():
    b = _fab(valore="100000")
    d = _dati([b])
    r = VC.calcola(d, b)
    assert r["inferiore"] and r["dichiarato"] == "100000"
    av = VC.avvisi(d)
    assert av and av[0]["codice"] == "VALORE_SOTTO_CATASTALE" and av[0]["percorso"] == "beni[b_x].valore"
    assert not VC.avvisi(_dati([_fab(valore="200000")]))     # valore venale piu' alto: nessun avviso


def test_casi_sintetici_esistenti_coerenti():
    """Il caso completo dichiara 126000 su rendita 1000 A/2: coincide con il valore catastale."""
    d = caso_completo()
    risultati = VC.calcola_pratica(d)     # il diritto e' scritto «proprieta»: si riconosce come il codice 1
    fab = [r for r in risultati if r["tipo"] == "fabbricato" and r["calcolabile"]]
    assert fab and fab[0]["valore"] == "126000" and not fab[0]["inferiore"]
    assert VC.calcola_pratica(copia(caso_prima_casa()))      # non solleva


def test_servizio_mcp_e_avviso_in_verifica(tmp_path):
    from successioni.archivio import Archivio
    from successioni.servizio import Servizio
    sv = Servizio(Archivio(tmp_path / "dati"))
    d = caso_completo()
    b = next(x for x in d["beni"] if x["tipo"] == "fabbricato")
    b["valore"] = "1000"
    from test_elaborati import ops_da_caso
    pid = sv.crea_pratica("Prova valore catastale", iniziali=ops_da_caso(d))["pratica_id"]
    vc = sv.valori_catastali(pid)
    assert any(x["bene_id"] == b["id"] and x["inferiore"] for x in vc["beni"])
    assert any(a["codice"] == "VALORE_SOTTO_CATASTALE" for a in sv.verifica(pid)["avvisi"])
    assert sv.leggi(pid)["dati"]["beni"][[x["id"] for x in sv.leggi(pid)["dati"]["beni"]].index(b["id"])]["valore"] == "1000"
