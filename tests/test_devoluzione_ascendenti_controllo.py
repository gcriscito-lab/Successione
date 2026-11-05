"""Ascendenti oltre i genitori (nonni 5A/5B, bisavi 7A/7B) nella devoluzione per legge: l'export completo deve essere accettato dal
controllo ufficiale locale SUC13 2.3.1 e le quote alterate respinte. Dati sintetici. Prova locale: non e' una verifica con l'Agenzia.
Riusa i costruttori di casi di test_devoluzione_controllo_ufficiale.py (aggiungendo i codici degli ascendenti)."""
import pytest

import test_devoluzione_controllo_ufficiale as T
from successioni.telematico.xsd import valida_xsd
from test_telematico_controllo import _esegui, _motivo_salto

# anagrafica sintetica degli ascendenti: nati prima del defunto (1940), come richiede l'annotazione XSD di GradoParentela
for _g, _rel, _sesso, _nasc in (("5A", "nonno paterno", "M", "1912-02-02"), ("5B", "nonna materna", "F", "1913-03-03"),
                                ("7A", "bisavo paterno", "M", "1890-04-04"), ("7B", "bisavo materno", "F", "1891-05-05")):
    T.RELAZIONE[_g], T.SESSO[_g], T.NASCITA[_g] = _rel, _sesso, _nasc

C, GER, UNI = T.C, T.GER, T.UNI
CONFIGURAZIONI = {
    "quattro_nonni": (["5A", "5A", "5B", "5B"], "4"),                  # 1/4 ciascuno (esempio 1 dell'Allegato 5)
    "tre_nonni_uno_materno": (["5A", "5A", "5B"], "4"),                # 1/4, 1/4, 1/2 (esempio 2)
    "solo_nonni_paterni": (["5A", "5A"], "4"),                         # 1/2 ciascuno (esempio 3: il bisnonno non eredita)
    "bisavi_due_linee": (["7A", "7B"], "4"),                           # 1/2 ciascuno
    "coniuge_e_nonni": ([C, "5A", "5B"], "2"),                         # 2/3, 1/6, 1/6
    "nonno_e_germano": (["5A", GER], "4"),                             # 1/2, 1/2 (riga «Ascendente/i + 1 fratello germano»)
    "nonno_e_unilaterale": (["5A", UNI], "4"),                         # 2/3, 1/3 (riga «Ascendente/i + 1 fratello unilaterale»)
    "coniuge_nonno_germano": ([C, "5A", GER], "2", T.VALORI_12_7),     # 8/12, 3/12, 1/12 (p. 69)
    # piu' ascendenti insieme a fratelli: la tabella di p. 70 dice solo «Ascendente/i»; il gruppo vale come un solo genitore
    "due_nonni_e_germano": (["5A", "5B", GER], "4"),                   # ascendenti 1/2 (1/4 + 1/4), germano 1/2
    "tre_nonni_e_unilaterale": (["5A", "5A", "5B", UNI], "4"),         # ascendenti 2/3, unilaterale 1/3
    "coniuge_due_nonni_germano": ([C, "5A", "5B", GER], "2", T.VALORI_12_7),   # 8/12, 3/12 (1/8 + 1/8), 1/12
}


@pytest.mark.parametrize("nome", sorted(CONFIGURAZIONI))
def test_export_completo_e_valido(nome):
    es, quote = T.genera(*CONFIGURAZIONI[nome])
    assert es.errori == [] and es.completo, ([e.asdict() for e in es.errori], es.non_supportato)
    assert not any(a.codice == "QUOTE_DI_LEGGE_NON_VERIFICATE" for a in es.avvisi)
    assert valida_xsd(es.xml) == []


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.parametrize("nome", sorted(CONFIGURAZIONI))
def test_controllo_ufficiale_accetta_le_quote(nome, tmp_path):
    es, quote = T.genera(*CONFIGURAZIONI[nome])
    assert es.xml is not None, [e.asdict() for e in es.errori]
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (nome, {i: str(q) for i, q in quote.items()}, dgn["diagnostici"], wri[:1200])
    assert [d["codice"] for d in dgn["diagnostici"]] == ["3345"], dgn["diagnostici"]


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.parametrize("nome", ["tre_nonni_uno_materno", "coniuge_e_nonni", "nonno_e_unilaterale"])
def test_controllo_ufficiale_respinge_quote_alterate(nome, tmp_path):
    es, _ = T.genera(*CONFIGURAZIONI[nome])
    stato, dgn, _, _ = _esegui(T.altera_quote(es.xml), tmp_path)
    assert stato == "negativo", (nome, dgn["diagnostici"])
    assert any(d["codice"] in ("3117", "3118") for d in dgn["diagnostici"]), dgn["diagnostici"]


def test_export_rifiuta_quote_non_di_legge_per_i_nonni():
    d, _ = T.caso_con_eredi(["5A", "5A", "5B"], "4")
    for dev in d["devoluzioni"]:        # quote uguali (1/3) invece di 1/4, 1/4, 1/2
        dev["quota"] = {"num": 1, "den": 3}
    es = T.esporta(d)
    assert es.xml is None and any("allegato 5" in e.messaggio for e in es.errori)


def test_ascendente_piu_lontano_in_ea_non_e_coperto():
    d, _ = T.caso_con_eredi(["5A", "5A"], "4")
    # aggiungo un bisnonno che non eredita: il quadro EA non puo' contenere soggetti senza devoluzione -> quote non verificate
    from successioni.telematico.devoluzione_legge import quote_di_legge
    assert quote_di_legge({"a": "5A", "b": "7B"}, {"a": "1", "b": "1"}) is None


# ---- rinunce: il controllo calcola le quote sui soli beneficiari (accrescimento implicito), provato il 2026-11-05 ---------------
def _altera_un_terzo_due_terzi(xml: bytes) -> bytes:
    """Per ogni sezione Devoluzione con due soli beneficiari: quote 1/3 e 2/3 (somma 1) e QuotaValore coerente."""
    from lxml import etree
    doc = etree.fromstring(xml)
    for sez in doc.xpath('//*[local-name()="Devoluzione"][*[local-name()="Quota"]]/..'):
        devs = [x for x in sez if etree.QName(x).localname == 'Devoluzione']
        if len(devs) != 2:
            continue
        valori = [dev.xpath('.//*[local-name()="QuotaValore"]')[0] for dev in devs]
        totale = sum(float(v.text.replace(',', '.')) for v in valori)
        for dev, v, (n, den) in zip(devs, valori, ((1, 3), (2, 3))):
            dev.xpath('.//*[local-name()="QuotaNumeratore"]')[0].text = str(n)
            dev.xpath('.//*[local-name()="QuotaDenominatore"]')[0].text = str(den)
            v.text = f"{totale * n / den:.2f}".replace('.', ',')
    return etree.tostring(doc, xml_declaration=True, encoding='UTF-8')


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
def test_rinunciatario_le_quote_dei_restanti_seguono_i_soli_beneficiari(tmp_path):
    import test_soggetti_ea as TS
    d = TS.caso_chiamato_rinunciatario()            # due figli beneficiari + un figlio rinunciatario (tipo 3)
    es = TS.esporta(d)
    assert es.completo, [e.messaggio for e in es.errori]
    stato, dgn, _, _ = _esegui(es.xml, tmp_path / "ok")
    assert stato == "positivo", dgn["diagnostici"]                       # 1/2 + 1/2: il rinunciatario non conta
    stato2, dgn2, wri2, _ = _esegui(_altera_un_terzo_due_terzi(es.xml), tmp_path / "ko")
    assert stato2 == "negativo" and any(x["codice"] == "3117" for x in dgn2["diagnostici"])
    assert "1/2" in wri2                                                  # «Valore corretto: 1/2» secondo il controllo