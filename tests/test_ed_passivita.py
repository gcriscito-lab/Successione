"""Quadro ED e passivita' (pacchetto 8): ripartizione fra piu' di tre soggetti con Continuazione, tipi di passivita', titoli esenti.
Ogni positivo e' stato verificato col controllo ufficiale SUC13 2.3.1 locale (dati sintetici; prova locale, non un invio)."""
import copy
from fractions import Fraction

import pytest
from lxml import etree

from successioni.telematico.identificativi import genera_cf_sintetico
from telematico_casi import caso_a10
from test_devoluzione_controllo_ufficiale import F, NIP, VALORI_12_7, caso_con_eredi, esporta
from test_telematico_controllo import _esegui, _motivo_salto

# multipli comuni: 4 figli (1/4), 5 figli (1/5), 7 figli (1/7)
VALORI_7 = {'b_casa0001': '126000', 'b_terr0001': '18200', 'b_conto001': '21000', 'ps_mutuo01': '84000'}
VALORI = {4: None, 5: None, 7: VALORI_7}


def caso_ed(n_figli: int, gradi=None, stato='4', valori=None, rappresentati=None):
    """caso_a10 con eredi per legge (n figli o i ``gradi`` indicati) e il mutuo (ps_mutuo01) ripartito fra tutti secondo le
    quote di legge."""
    n_figli = n_figli or len(gradi)
    d, quote = caso_con_eredi(gradi or [F] * n_figli, stato, valori or VALORI.get(n_figli), rappresentati)
    for p in d['persone']:
        if p['id'] == 'p_erede004':       # 'EredeE' ha le stesse consonanti di 'EredeA': stesso codice fiscale sintetico
            p['nome'] = 'EredeP'
            p['codice_fiscale'] = genera_cf_sintetico('Rossi', 'EredeP', 'M', '1970-01-01', 'H501')
    base = caso_a10()
    if not any(p['id'] == 'ps_mutuo01' for p in d['passivita']):       # caso_con_eredi lo toglie oltre tre eredi
        mutuo = copy.deepcopy(next(p for p in base['passivita'] if p['id'] == 'ps_mutuo01'))
        mutuo.pop('persona_id', None)
        mutuo['importo'] = (valori or VALORI.get(n_figli) or {'ps_mutuo01': '90000'})['ps_mutuo01']
        d['passivita'].append(mutuo)
        tel = d['opzioni']['telematico']
        tel['passivita']['ps_mutuo01'] = {**copy.deepcopy(base['opzioni']['telematico']['passivita']['ps_mutuo01']),
                                          'ripartizione': [{'persona_id': i, 'quota': {'num': q.numerator, 'den': q.denominator}}
                                                           for i, q in quote.items()]}
    return d, quote


def righe_ed(es):
    doc = etree.fromstring(es.xml)
    ns = {k: v for k, v in doc.nsmap.items() if k}
    return doc.xpath('//suc:QuadroED/suc:Modulo/suc:Passivita', namespaces=ns), ns


@pytest.mark.parametrize('n,righe_attese,soggetti_per_rigo', [(4, 2, [3, 1]), (5, 2, [3, 2]), (7, 3, [3, 3, 1])])
def test_ripartizione_oltre_tre_soggetti_con_continuazione(n, righe_attese, soggetti_per_rigo):
    d, quote = caso_ed(n)
    es = esporta(d)
    assert es.completo and es.errori == [], ([e.asdict() for e in es.errori], es.non_supportato)
    righe, ns = righe_ed(es)
    mutuo = [r for r in righe if r.xpath('suc:Tipo/text()', namespaces=ns) == ['3']]
    assert len(mutuo) == 1
    # le righe del mutuo e le sue continuazioni sono consecutive: il primo ha i dati identificativi, i seguenti solo la ripartizione
    inizio = righe.index(mutuo[0])
    gruppo = righe[inizio:inizio + righe_attese]
    assert [len(r.xpath('suc:RipartizioneED/suc:Ripartizione', namespaces=ns)) for r in gruppo] == soggetti_per_rigo
    assert [bool(r.xpath('suc:RipartizioneED/suc:Continuazione', namespaces=ns)) for r in gruppo] == \
        [True] * (righe_attese - 1) + [False]
    assert all(not r.xpath('suc:Tipo', namespaces=ns) for r in gruppo[1:])
    quota = Fraction(1, n)
    qv = [Fraction(x) for x in doc_quote_valore(es, righe_attese, ns)]
    assert sum(qv) == int(d['passivita'][-1]['importo']) and len(set(qv)) == 1 and qv[0] == int(d['passivita'][-1]['importo']) * quota


def doc_quote_valore(es, n_righe, ns):
    doc = etree.fromstring(es.xml)
    righe = doc.xpath('//suc:QuadroED/suc:Modulo/suc:Passivita', namespaces=ns)
    mutuo = next(r for r in righe if r.xpath('suc:Tipo/text()', namespaces=ns) == ['3'])
    inizio = righe.index(mutuo)
    out = []
    for r in righe[inizio:inizio + n_righe]:
        out += r.xpath('suc:RipartizioneED/suc:Ripartizione/suc:Quota/suc:QuotaValore/text()', namespaces=ns)
    return [v.replace(',00', '') for v in out]


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or '')
@pytest.mark.parametrize('n', [4, 5, 7])
@pytest.mark.java
def test_controllo_ufficiale_accetta_la_continuazione_ed(n, tmp_path):
    d, _ = caso_ed(n)
    es = esporta(d)
    assert es.completo
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == 'positivo', (dgn['diagnostici'], wri[:900])
    assert [x['codice'] for x in dgn['diagnostici']] == ['3345']


def test_mappa_registra_le_righe_di_continuazione():
    d, _ = caso_ed(7)
    es = esporta(d)
    ref = es.mappa['ps_mutuo01']
    assert ref['quadro'] == 'ED' and len(ref['righi_continuazione']) == 2


# ---- rappresentazione: la ripartizione della passivita' segue le quote per stirpi (4 destinatari -> continuazione) ----------
def caso_stirpi_quattro():
    return caso_ed(0, gradi=[NIP, NIP, NIP, NIP], stato='4', valori=VALORI_12_7, rappresentati={0: 1, 1: 1, 2: 1, 3: 2})


def test_ripartizione_per_stirpi_oltre_tre_soggetti():
    d, quote = caso_stirpi_quattro()
    es = esporta(d)
    assert es.completo and es.errori == [], ([e.asdict() for e in es.errori], es.non_supportato)
    ref = es.mappa['ps_mutuo01']
    assert len(ref['righi_continuazione']) == 1
    assert sorted(quote.values()) == [Fraction(1, 6)] * 3 + [Fraction(1, 2)]


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or '')
@pytest.mark.java
def test_controllo_ufficiale_stirpi_con_continuazione(tmp_path):
    es = esporta(caso_stirpi_quattro()[0])
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == 'positivo', (dgn['diagnostici'], wri[:900])


def test_quote_della_passivita_diverse_da_quelle_di_legge_rifiutate():
    d, quote = caso_ed(0, gradi=[F, NIP, NIP], valori=VALORI_12_7, rappresentati={1: 1, 2: 1})
    rip = d['opzioni']['telematico']['passivita']['ps_mutuo01']['ripartizione']
    rip[0]['quota'], rip[1]['quota'] = rip[1]['quota'], rip[0]['quota']       # 1/4 al figlio e 1/2 a un nipote: sbagliato
    es = esporta(d)
    assert es.xml is None and any(e.codice == 'QUOTA_DI_LEGGE' for e in es.errori), [e.codice for e in es.errori]


# Nota (prova del 2026-11-05): il controllo ufficiale 2.3.1 NON verifica le quote della ripartizione delle passivita' rispetto
# alle quote di legge (accetta anche quote scambiate fra soggetti); il vincolo viene dall'annotazione XSD di
# RipartizioneED/Ripartizione/Quota («il campo quota deve essere compilato in base al grado di parentela») ed e' imposto
# dall'esportazione (test sopra), non dal controllo.


# ---- tipi di passivita' (CodiciPassivita 1-12): tutti accettati dal controllo ufficiale locale -----------------------------
LIBERI = {'1', '2', '11', '12'}      # senza obbligo di seguire le quote di legge (annotazioni di Ripartizione_Type/Quota)
BENE_PER_TIPO = {'4': 'b_conto001', '5': 'b_conto001', '7': 'b_conto001'}     # tipi 3, 4, 5, 7: cespite di riferimento obbligatorio


def caso_tipo(tipo: str):
    d = copy.deepcopy(caso_a10())
    tel = d['opzioni']['telematico']
    d['passivita'].append({'id': 'ps_prova01', '_origine': {}, 'descrizione': f'Passivita tipo {tipo} (sintetica)', 'importo': '1000'})
    t = {'tipo': tipo, 'estremi_documento': 'Doc 1', 'data_documento': '2025-02-01'}
    if tipo != '11':
        t['possesso'] = '1/1'            # tipo 11: il possesso non va valorizzato (Fascicolo I p. 38)
    if tipo in LIBERI:
        d['passivita'][-1]['persona_id'] = 'p_anna0001'
    else:
        t['ripartizione'] = [{'persona_id': 'p_anna0001', 'quota': '1/2'}, {'persona_id': 'p_luca0001', 'quota': '1/2'}]
    if tipo in BENE_PER_TIPO:
        t['bene_id'] = BENE_PER_TIPO[tipo]
    tel['passivita']['ps_prova01'] = t
    return d


@pytest.mark.parametrize('tipo', ['2', '4', '5', '6', '7', '8', '9', '10', '11', '12'])
def test_tipi_di_passivita_esportabili(tipo):
    es = esporta(caso_tipo(tipo))
    assert es.completo and es.errori == [], ([e.asdict() for e in es.errori], es.non_supportato)


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or '')
@pytest.mark.parametrize('tipo', ['2', '4', '5', '6', '7', '8', '9', '10', '11', '12'])
@pytest.mark.java
def test_controllo_ufficiale_accetta_ogni_tipo_di_passivita(tipo, tmp_path):
    stato, dgn, wri, _ = _esegui(esporta(caso_tipo(tipo)).xml, tmp_path)
    assert stato == 'positivo', (tipo, dgn['diagnostici'], wri[:600])


def test_regole_dei_tipi_restano_applicate():
    d = caso_tipo('2')
    d['passivita'][-1]['importo'] = '1034'
    assert any(e.codice == 'REGOLA_SPESE_FUNERARIE' for e in esporta(d).errori)       # spese funerarie: massimo 1033
    d = caso_tipo('4')
    del d['opzioni']['telematico']['passivita']['ps_prova01']['bene_id']
    assert any(e.codice == 'DATO_MANCANTE' for e in esporta(d).errori)               # tipi 3, 4, 5, 7: cespite obbligatorio
    d = caso_tipo('6')
    d['opzioni']['telematico']['passivita']['ps_prova01']['bene_id'] = 'b_conto001'
    assert any(e.codice == 'REGOLA_PROGRESSIVO_CESPITE' for e in esporta(d).errori)   # altri tipi: cespite da non indicare


def test_titolo_esente_con_passivita_collegata_resta_bloccato():
    """Fascicolo I p. PDF 36: deducibili i debiti per beni compresi nell'attivo ereditario; a p. PDF 3 i titoli esenti sono
    opzionali e a valenza esclusiva nei rapporti con gli operatori finanziari. Le fonti non dicono se siano compresi nell'attivo
    ai fini della deduzione: il caso non e' supportato (vedi docs/regole/ed_passivita.md)."""
    from test_telematico_eo_esenti import caso_esente
    d = caso_esente()
    d['passivita'].append({'id': 'ps_esente1', '_origine': {}, 'descrizione': 'Debito per acquisto BOT', 'importo': '1000'})
    d['opzioni']['telematico']['passivita']['ps_esente1'] = {
        'tipo': '4', 'estremi_documento': 'Doc', 'data_documento': '2025-02-01', 'possesso': '1/1', 'bene_id': 'b_bot00001',
        'ripartizione': [{'persona_id': 'p_anna0001', 'quota': '1/2'}, {'persona_id': 'p_luca0001', 'quota': '1/2'}]}
    es = esporta(d)
    assert es.xml is None and any('titolo esente' in n for n in es.non_supportato), es.non_supportato


# ---- importazione: i righi di continuazione del quadro ED si ricompongono in una sola passivita' ---------------------------
def test_importazione_ricompone_la_ripartizione_con_continuazione(tmp_path):
    from successioni.archivio import Archivio
    from successioni.servizio import Servizio
    d, quote = caso_ed(7)
    es = esporta(d)
    assert es.completo
    sv = Servizio(Archivio(tmp_path / 'dati'))
    r = sv.importa_xml_telematico(es.xml)
    assert r['importato']['passivita'] == len(d['passivita'])          # righi di continuazione esclusi
    dati = sv.leggi(r['pratica_id'])['dati']
    mutuo = next(v for v in dati['opzioni']['telematico']['passivita'].values() if v.get('tipo') == '3')
    assert len(mutuo['ripartizione']) == 7
    assert {Fraction(v['quota']['num'], v['quota']['den']) for v in mutuo['ripartizione']} == {Fraction(1, 7)}


def test_importazione_rifiuta_continuazione_malformata():
    from successioni.telematico.importa import XmlNonImportabile, importa_xml
    es = esporta(caso_ed(4)[0])
    xml = es.xml
    # Continuazione barrata sull'ultimo rigo ED senza il rigo che segue
    doc = etree.fromstring(xml)
    ns = {k: v for k, v in doc.nsmap.items() if k}
    righe = doc.xpath('//suc:QuadroED/suc:Modulo/suc:Passivita', namespaces=ns)
    ultimo = righe[-1]
    rip = ultimo.xpath('suc:RipartizioneED', namespaces=ns)[0]
    etree.SubElement(rip, '{%s}Continuazione' % ns['suc']).text = '1'
    with pytest.raises(XmlNonImportabile):
        importa_xml(etree.tostring(doc, xml_declaration=True, encoding='UTF-8'))
