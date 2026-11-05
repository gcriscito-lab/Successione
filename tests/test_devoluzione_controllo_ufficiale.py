"""Quote di legge per configurazioni di eredi oltre figli/coniuge (Allegato 5, Fascicolo I pp. 69-70) verificate con il
controllo ufficiale locale SUC13 2.3.1: i positivi devono essere accettati, le quote alterate respinte. Dati sintetici.
Prova locale: non e' un invio ne' una verifica con l'Agenzia."""
import copy
from datetime import date
from fractions import Fraction

import pytest
from lxml import etree

from successioni.telematico.devoluzione_legge import quote_di_legge
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.identificativi import genera_cf_sintetico
from telematico_casi import caso_a10, contesto_caso_a10
from test_telematico_controllo import _esegui, _motivo_salto

C, F, G, GER, UNI = '01', '02', '03', '10', '11'
NIP = '04'   # nipote in linea retta (succede per rappresentazione)
RELAZIONE = {C: 'coniuge', F: 'figlio', G: 'genitore', GER: 'fratello', UNI: 'fratello unilaterale', NIP: 'nipote'}
SESSO = {C: 'F', F: 'M', G: 'M', GER: 'M', UNI: 'F', NIP: 'F'}
NASCITA = {C: '1942-04-04', F: '1970-01-01', G: '1915-05-05', GER: '1945-06-06', UNI: '1948-07-07', NIP: '2000-08-08'}


def caso_con_eredi(gradi: list[str], stato_civile: str, valori: dict | None = None,
                   rappresentati: dict[int, int] | None = None) -> tuple[dict, dict[str, Fraction]]:
    """``caso_a10`` con gli eredi indicati (grado del quadro EA), devoluzioni secondo ``quote_di_legge``."""
    d = copy.deepcopy(caso_a10())
    d['persone'] = [p for p in d['persone'] if p['ruolo'] == 'defunto']
    tel = d['opzioni']['telematico']
    tel['persone'] = {'p_defunto1': tel['persone']['p_defunto1']}
    ids = []
    # rappresentati: indice dell'erede -> numero del figlio/fratello premorto che rappresenta (CF sintetico dedicato)
    # CF distinti (data di nascita diversa): le stirpi si distinguono dal CF del rappresentato
    premorti = {n: genera_cf_sintetico('Rossi', f'Premorto{n}', 'M', f'196{n}-03-0{n}', 'H501') for n in set((rappresentati or {}).values())}
    rapp_ids = {}
    for i, g in enumerate(gradi):
        pid = f'p_erede{i:03d}'
        nome = f'Erede{"ABCDEFGH"[i]}'
        cf = genera_cf_sintetico('Rossi', nome, SESSO[g], NASCITA[g], 'H501')
        d['persone'].append({'id': pid, '_origine': {}, 'cognome': 'Rossi', 'nome': nome, 'codice_fiscale': cf,
                             'data_nascita': NASCITA[g], 'luogo_nascita': 'Roma', 'ruolo': 'erede',
                             'relazione_con_defunto': RELAZIONE[g]})
        tel['persone'][pid] = {'sesso': SESSO[g], 'provincia_nascita': 'RM', 'grado_parentela': g}
        if i in (rappresentati or {}):
            tel['persone'][pid].update(rappresentato_cf=premorti[rappresentati[i]], rappresentato_grado='02')
            rapp_ids[pid] = (premorti[rappresentati[i]], '02')
        ids.append(pid)
    quote = quote_di_legge(dict(zip(ids, gradi)), {i: '1' for i in ids}, rapp_ids or None)
    assert quote is not None
    dich = tel['dichiarazione']
    dich['stato_civile'] = stato_civile
    dich['presentatore']['persona_id'] = ids[0]
    cf0 = next(p['codice_fiscale'] for p in d['persone'] if p['id'] == ids[0])
    dich['versamento']['cf_titolare'] = cf0
    d['devoluzioni'] = [{'id': f'd_{b[2:6]}{i[-3:]}', '_origine': {}, 'bene_id': b, 'persona_id': i,
                         'quota': {'num': q.numerator, 'den': q.denominator}, 'diritto': dir_}
                        for b, dir_ in (('b_casa0001', '1'), ('b_terr0001', 'proprieta'), ('b_conto001', '1'))
                        for i, q in quote.items()]
    d['passivita'][0]['persona_id'] = ids[0]
    # importi divisibili per tutte le quote usate (nessun arrotondamento: il Fascicolo non ne indica il criterio)
    valori = valori or {'b_casa0001': '126000', 'b_terr0001': '18900', 'b_conto001': '18000', 'ps_mutuo01': '90000'}
    for b in d['beni']:
        b['valore'] = valori[b['id']]
    for ps in d['passivita']:
        if ps['id'] == 'ps_mutuo01':
            ps['importo'] = valori['ps_mutuo01']
    if len(ids) > 3:
        # limite dell'esportatore, non della regola sulle quote: ripartizione ED oltre tre soggetti non supportata
        d['passivita'] = [ps for ps in d['passivita'] if ps['id'] != 'ps_mutuo01']
        del tel['passivita']['ps_mutuo01']
    else:
        tel['passivita']['ps_mutuo01']['ripartizione'] = [
            {'persona_id': i, 'quota': {'num': q.numerator, 'den': q.denominator}} for i, q in quote.items()]
    return d, quote


def esporta(d):
    cf = next(p['codice_fiscale'] for p in d['persone'] if p['id'] == d['opzioni']['telematico']['dichiarazione']['presentatore']['persona_id'])
    # fornitore = dichiarante (nessun documento d'identita' EG7 richiesto)
    return esporta_xml(d, contesto_caso_a10(cf_fornitore=cf, data_riferimento=date(2026, 3, 9)))


def genera(gradi, stato_civile, valori=None, rappresentati=None):
    d, quote = caso_con_eredi(gradi, stato_civile, valori, rappresentati)
    return esporta(d), quote


# multipli comuni dei denominatori 12 e 7 (quote 8/12, 3/12, 1/12 e 4/7, 3/7)
VALORI_12_7 = {'b_casa0001': '126000', 'b_terr0001': '16800', 'b_conto001': '21000', 'ps_mutuo01': '84000'}
CONFIGURAZIONI = {
    'coniuge_genitore': ([C, G], '2'),
    'coniuge_due_fratelli': ([C, GER, UNI], '2'),
    'genitore_unico_germano': ([G, GER], '4'),
    'due_genitori_unilaterale': ([G, G, UNI], '4'),
    'coniuge_genitore_germano': ([C, G, GER], '2', VALORI_12_7),          # 8/12, 3/12, 1/12 (p. 69)
    'due_genitori_germano_unilaterale': ([G, G, GER, UNI], '4', VALORI_12_7),  # genitori 4/7, fratelli 3/7 (p. 70)
    # rappresentazione (Fascicolo I pp. 18-19): i nipoti 04 succedono ai figli premorti, quote per stirpi
    'rapp_A_ministeriale': ([NIP, NIP, NIP, NIP], '4', VALORI_12_7, {0: 1, 1: 1, 2: 1, 3: 2}),   # 1/6 x3 e 1/2
    'rapp_B_figlio_e_due_nipoti': ([F, NIP, NIP], '4', VALORI_12_7, {1: 1, 2: 1}),                # 1/2, 1/4, 1/4
    'rapp_C_coniuge_figlio_due_nipoti': ([C, F, NIP, NIP], '2', VALORI_12_7, {2: 1, 3: 1}),       # 1/3, 1/3, 1/6, 1/6
}


@pytest.mark.parametrize('nome', sorted(CONFIGURAZIONI))
def test_export_completo_e_valido(nome):
    es, quote = genera(*CONFIGURAZIONI[nome])
    assert es.errori == [] and es.completo, ([e.asdict() for e in es.errori], es.non_supportato)
    assert not any(a.codice == 'QUOTE_DI_LEGGE_NON_VERIFICATE' for a in es.avvisi)
    from successioni.telematico.xsd import valida_xsd
    assert valida_xsd(es.xml) == []


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or '')
@pytest.mark.parametrize('nome', sorted(CONFIGURAZIONI))
def test_controllo_ufficiale_accetta_le_quote_di_legge(nome, tmp_path):
    es, quote = genera(*CONFIGURAZIONI[nome])
    assert es.xml is not None, [e.asdict() for e in es.errori]
    stato, dgn, wri, dcm = _esegui(es.xml, tmp_path)
    assert stato == 'positivo', (nome, {i: str(q) for i, q in quote.items()}, dgn['diagnostici'])
    assert [d['codice'] for d in dgn['diagnostici']] == ['3345'], dgn['diagnostici']


def altera_quote(xml: bytes) -> bytes:
    """Scambia le Quota del primo e dell'ultimo beneficiario in ogni sezione Devoluzione (stesso totale, quote sbagliate)."""
    doc = etree.fromstring(xml)
    cambiati = 0
    for sez in doc.xpath('//*[local-name()="Devoluzione"][*[local-name()="Quota"]]/..'):
        devs = [d for d in sez if etree.QName(d).localname == 'Devoluzione']
        if len(devs) < 2:
            continue
        qa = devs[0].xpath('*[local-name()="Quota"]')[0]
        qb = devs[-1].xpath('*[local-name()="Quota"]')[0]
        ia, ib = devs[0].index(qa), devs[-1].index(qb)
        devs[0].remove(qa)
        devs[-1].remove(qb)
        devs[0].insert(ia, qb)
        devs[-1].insert(ib, qa)
        cambiati += 1
    assert cambiati, 'nessuna devoluzione alterata'
    return etree.tostring(doc, xml_declaration=True, encoding='UTF-8')


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or '')
@pytest.mark.parametrize('nome', ['coniuge_genitore', 'due_genitori_unilaterale', 'coniuge_due_fratelli'])
def test_controllo_ufficiale_respinge_quote_sbagliate(nome, tmp_path):
    es, quote = genera(*CONFIGURAZIONI[nome])
    assert es.xml is not None
    assert _esegui(es.xml, tmp_path / 'ok')[0] == 'positivo'
    stato, dgn, wri, _ = _esegui(altera_quote(es.xml), tmp_path / 'alterato')
    assert stato == 'negativo', (nome, dgn['diagnostici'])
    assert 'Dati di devoluzione non coerenti' in wri and {d['codice'] for d in dgn['diagnostici']} == {'3117', '3345'}, wri[-1500:]


def test_nostra_esportazione_rifiuta_quote_diverse_da_quelle_di_legge():
    d, quote = caso_con_eredi(*CONFIGURAZIONI['coniuge_genitore'])
    for dev in d['devoluzioni']:
        dev['quota'] = {'num': 1, 'den': 2}
    es = esporta(d)
    assert es.xml is None and es.errori


def test_quote_attese_dalle_tabelle_per_le_due_configurazioni_aggiunte():
    _, q5 = caso_con_eredi(*CONFIGURAZIONI['coniuge_genitore_germano'])
    assert sorted(q5.values()) == [Fraction(1, 12), Fraction(3, 12), Fraction(8, 12)]
    _, q6 = caso_con_eredi(*CONFIGURAZIONI['due_genitori_germano_unilaterale'])
    assert sorted(q6.values()) == [Fraction(1, 7), Fraction(2, 7), Fraction(2, 7), Fraction(2, 7)]


ATTESE_RAPPRESENTAZIONE = {
    'rapp_A_ministeriale': [Fraction(1, 6)] * 3 + [Fraction(1, 2)],
    'rapp_B_figlio_e_due_nipoti': [Fraction(1, 2), Fraction(1, 4), Fraction(1, 4)],
    'rapp_C_coniuge_figlio_due_nipoti': [Fraction(1, 3), Fraction(1, 3), Fraction(1, 6), Fraction(1, 6)],
}


@pytest.mark.parametrize('nome', sorted(ATTESE_RAPPRESENTAZIONE))
def test_quote_per_stirpi_attese(nome):
    _, quote = caso_con_eredi(*CONFIGURAZIONI[nome])
    assert [quote[k] for k in sorted(quote)] == ATTESE_RAPPRESENTAZIONE[nome]


def scambia_minima_con_massima(xml: bytes) -> bytes:
    """Per ogni bene (quote che sommano a 1, anche se spezzate in piu' sezioni da tre soggetti) scambia la prima quota
    minima con la prima massima: il nipote di una stirpe riceve la quota del nipote unico e viceversa."""
    doc = etree.fromstring(xml)
    nodi = doc.xpath('//*[local-name()="Devoluzione"]/*[local-name()="Quota"]')
    def frazione(q):
        return Fraction(int(q.xpath('string(.//*[local-name()="QuotaNumeratore"])')),
                        int(q.xpath('string(.//*[local-name()="QuotaDenominatore"])')))
    gruppi, corrente, somma = [], [], Fraction(0)
    for q in nodi:
        corrente.append(q)
        somma += frazione(q)
        if somma == 1:
            gruppi.append(corrente)
            corrente, somma = [], Fraction(0)
    assert gruppi and not corrente, 'quote dei beni non ricomponibili'
    for g in gruppi:
        fr = [frazione(q) for q in g]
        a, b = g[fr.index(min(fr))], g[fr.index(max(fr))]
        assert min(fr) != max(fr)
        for nome in ('QuotaNumeratore', 'QuotaDenominatore', 'QuotaValore'):
            ea, eb = a.xpath(f'.//*[local-name()="{nome}"]')[0], b.xpath(f'.//*[local-name()="{nome}"]')[0]
            ea.text, eb.text = eb.text, ea.text
    return etree.tostring(doc, xml_declaration=True, encoding='UTF-8')


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or '')
def test_controllo_ufficiale_respinge_scambio_fra_nipote_e_nipote_unico(tmp_path):
    es, quote = genera(*CONFIGURAZIONI['rapp_A_ministeriale'])
    assert es.xml is not None
    assert _esegui(es.xml, tmp_path / 'ok')[0] == 'positivo'
    # scambio fra il primo nipote (1/6) e il nipote unico dell'altro figlio (1/2)
    stato, dgn, wri, _ = _esegui(scambia_minima_con_massima(es.xml), tmp_path / 'alterato')
    assert stato == 'negativo', dgn['diagnostici']
    assert 'Dati di devoluzione non coerenti' in wri, wri[-1500:]


def test_grado_04_senza_rappresentato_cf_da_dato_mancante():
    d, _ = caso_con_eredi(*CONFIGURAZIONI['rapp_B_figlio_e_due_nipoti'])
    for pid, dati in d['opzioni']['telematico']['persone'].items():
        dati.pop('rappresentato_cf', None)
        dati.pop('rappresentato_grado', None)
    es = esporta(d)
    assert es.xml is None
    assert any(e.codice == 'DATO_MANCANTE' and e.percorso.endswith('.rappresentato_cf') for e in es.errori),         [e.asdict() for e in es.errori]
