"""Somma dei 'Valore quota' non intera nei campi in euro interi del quadro EF (EF1/EF9 col. 1, EF4 col. 2). Dati SINTETICI.

Riproduce il blocco riscontrato il 2026-11-07 riesportando una sostitutiva reale (codice 1, prima casa P, tre eredi a 1/3):
ogni QuotaValore e' arrotondato al centesimo (es. 30001 x 1/3 = 10000,33), la somma delle tre righe vale 30000,99 e il quadro
EF non veniva generato. Regola: arrotondamento all'unita' di euro (annotazioni XSD del quadro EF, «per difetto se la frazione e'
inferiore a 50 centesimi e per eccesso se non inferiore»), entro la tolleranza dell'annotazione QuotaValore (1%, massimo 100
euro); riscontro col controllo ufficiale SUC13 2.3.1 locale. Vedi docs/regole/dubbio_arrotondamento.md §7.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from lxml import etree

from successioni.telematico.esporta import esporta_xml
from successioni.telematico.identificativi import genera_cf_sintetico
from successioni.telematico.xsd import valida_xsd
from telematico_casi import caso_prima_casa
from test_telematico_controllo import NS, _esegui, _motivo_salto
from test_telematico_prima_casa import CTX

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
EF = D + "/suc:QuadroEF"
EREDI = ("p_anna0001", "p_luca0001", "p_figlio003")


def caso_tre_eredi_sostitutiva() -> dict:
    """Tre figli a 1/3 per legge; casa (prima casa P della dichiarante) da 126001 e terreno da 30001: entrambe le somme dei
    valori quota hanno centesimi (126000,99 e 30000,99). Sostitutiva codice 1 con imposte gia' versate."""
    d = caso_prima_casa()
    tel = d["opzioni"]["telematico"]
    d["persone"].append({"id": "p_figlio003", "_origine": {}, "cognome": "Rossi", "nome": "Bruno",
                         "codice_fiscale": genera_cf_sintetico("Rossi", "Bruno", "M", "1975-01-01", "H501"),
                         "data_nascita": "1975-01-01", "luogo_nascita": "Roma", "ruolo": "erede"})
    tel["persone"]["p_figlio003"] = {"sesso": "M", "provincia_nascita": "RM", "grado_parentela": "02"}
    next(b for b in d["beni"] if b["id"] == "b_casa0001")["valore"] = "126001"
    next(b for b in d["beni"] if b["id"] == "b_terr0001")["valore"] = "30001"
    d["devoluzioni"] = [{"id": f"d_{bid[2:6]}{pid[2:]}", "_origine": {}, "bene_id": bid, "persona_id": pid, "quota": "1/3",
                         "diritto": "1"} for bid in ("b_casa0001", "b_terr0001", "b_conto001") for pid in EREDI]
    tel["devoluzioni"] = {"d_casaanna0001": {"agevolazioni": "P"}}
    tel["passivita"]["ps_mutuo01"]["ripartizione"] = [{"persona_id": p, "quota": "1/3"} for p in EREDI]
    d["opzioni"]["tipo_dichiarazione"] = "sostitutiva"
    tel["dichiarazione"].update(codice_sostitutiva="1", prima_anno="2025", prima_volume="88888", prima_numero="123",
                                ipotecaria_versata="500", catastale_versata="300")
    return d


def _x(es, xp):
    return etree.fromstring(es.xml).xpath(xp, namespaces=NS)


def _esporta():
    es = esporta_xml(caso_tre_eredi_sostitutiva(), CTX)
    assert es.errori == [] and es.non_supportato == [] and es.quadri_mancanti == [], (
        [e.messaggio for e in es.errori], es.non_supportato, [m.messaggio for m in es.quadri_mancanti])
    assert es.completo and valida_xsd(es.xml) == []
    return es


def test_somma_non_intera_arrotondata_all_euro():
    es = _esporta()
    qv = _x(es, D + "/suc:QuadroEB//suc:Devoluzione/suc:Quota/suc:QuotaValore/text()")
    assert qv == ["10000,33"] * 3                                                     # 30001 x 1/3, al centesimo
    s1, s2 = EF + "/suc:SezioneI_ImpostaIpotecaria", EF + "/suc:SezioneII_ImpostaCatastale"
    assert _x(es, s1 + "/suc:ImpostaProporzionale/*/text()") == ["30001", "600"]      # 30000,99 -> 30001; 2% = 600,02 -> 600
    assert _x(es, s1 + "/suc:PrimaCasa/*/text()") == ["1", "126001", "200"]           # 126000,99 -> 126001
    assert _x(es, s1 + "/suc:ImpostaIpotecariaDovuta/text()") == ["800"]
    assert _x(es, s1 + "/suc:ImpostaIpotecariaDaVersare/text()") == ["300"]           # 800 - 500
    assert _x(es, s2 + "/suc:ImpostaProporzionale/*/text()") == ["30001", "300"]      # 1% = 300,01 -> 300
    assert _x(es, s2 + "/suc:ImpostaCatastaleDovuta/text()") == ["500"]
    assert _x(es, s2 + "/suc:ImpostaCatastaleDaVersare/text()") == ["200"]            # 500 - 300 = 200 (minimo 200, codice 1)
    assert _x(es, EF + "/suc:TotaleDaVersare/text()") == ["705,00"]                   # 300 + 200 + 120 + 85
    avv = [a.messaggio for a in es.avvisi if a.codice == "ARROTONDAMENTO_SOMMA_VALORI_QUOTA"]
    assert any("30000,99 arrotondata a 30001" in m for m in avv) and any("126000,99 arrotondata a 126001" in m for m in avv)


@pytest.mark.parametrize("somma,atteso", [("104903,97", 104904), ("30000,99", 30001), ("10000,49", 10000),
                                          ("10000,50", 10001), ("10000,00", 10000)])
def test_regola_di_arrotondamento(somma, atteso):
    from successioni.telematico.quadri_efgh import _somma_in_euro

    class _X:
        avvisi = []

        def avv(self, *a):
            self.avvisi.append(a)
    x = _X()
    assert _somma_in_euro(x, Decimal(somma.replace(",", ".")), "QuadroEF", "immobili") == Decimal(atteso)
    assert bool(x.avvisi) is (somma.endswith(",00") is False)


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.java
def test_controllo_ufficiale_locale_positivo(tmp_path):
    es = _esporta()
    stato, dgn, wri, dcm = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (stato, dgn["diagnostici"], wri)
    assert dcm
    # nessun diagnostico sui righi EF (3120: imponibile diverso dalla somma attesa dal componente)
    assert not [d for d in dgn["diagnostici"] if d["codice"] == "3120"], dgn["diagnostici"]


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.java
def test_controllo_ufficiale_locale_rifiuta_l_imponibile_troncato(tmp_path):
    """Il componente vuole l'imponibile arrotondato (30001): la somma troncata dei centesimi (30000) e' scartata (3120)."""
    xml = _esporta().xml.replace(b"ImpostaProporzionale_Imponibile>30001<", b"ImpostaProporzionale_Imponibile>30000<")
    stato, dgn, _, _ = _esegui(xml, tmp_path, rapporto=False)
    assert stato == "negativo"
    assert "3120" in {d["codice"] for d in dgn["diagnostici"]}, dgn["diagnostici"]
