"""Dichiarazione sostitutiva codici 1 e 2 (src/successioni/telematico/sostitutiva.py). Dati sintetici."""
import pytest
from lxml import etree

from successioni.errori import DatiNonValidi
from test_correzioni_codex import pratica_con_allegati


D = '/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione'


def _ns(root):
    # i prefissi si ricavano dal documento (tm e suc)
    out = {}
    for el in root.iter():
        if isinstance(el.tag, str):
            for k, v in (el.nsmap or {}).items():
                out.setdefault(k, v)
    return out


def configura(s, pid, **dich):
    rev = s.leggi(pid)['revisione']
    tel = (s.leggi(pid)['dati']['opzioni'].get('telematico') or {})
    d = dict(tel.get('dichiarazione') or {})
    d.update(dich)
    s.aggiorna(pid, rev, [{'op': 'set', 'sezione': 'opzioni', 'campi': {
        'tipo_dichiarazione': 'sostitutiva', 'telematico': {**tel, 'dichiarazione': d}}}])


BASE = dict(prima_anno='2026', prima_volume='88888', prima_numero='123')


def xml_di(s, pid):
    r = s.esporta(pid)
    assert r['generato'] and r['completo'], r['errori'] + [{'nsup': r['non_supportato']}]
    assert not r['xsd_errori'], r['xsd_errori']
    return etree.fromstring(s.file_export(pid)[0])


def _t(doc, xp):
    return doc.xpath(xp, namespaces=_ns(doc))


def test_codice2_riliquida_senza_circoscrizioni(tmp_path):
    s, pid = pratica_con_allegati(tmp_path)
    configura(s, pid, codice_sostitutiva='2', ipotecaria_versata='2000', catastale_versata='1000', **BASE)
    doc = xml_di(s, pid)
    fr = f'{D}/suc:Frontespizio/suc:TipoDichiarazione'
    assert not _t(doc, f'{fr}/suc:PrimaDichiarazione')
    assert _t(doc, f'{fr}/suc:DichiarazioneSostitutiva/text()') == ['2']
    assert _t(doc, f'{fr}/suc:EstremiPrimaDichiarazione/*/text()') == ['2026', '88888', '123']
    ef = f'{D}/suc:QuadroEF'
    assert _t(doc, f'{ef}/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaDovuta/text()') == ['2820']
    assert _t(doc, f'{ef}/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaVersata/text()') == ['2000']
    assert _t(doc, f'{ef}/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaDaVersare/text()') == ['820']
    assert _t(doc, f'{ef}/suc:SezioneII_ImpostaCatastale/suc:ImpostaCatastaleDaVersare/text()') == ['410']
    # codice 2: nessuna nuova trascrizione/voltura -> sezioni III e IV non compilate
    assert not _t(doc, f'{ef}/suc:SezioneIII_TassaIpotecaria')
    assert not _t(doc, f'{ef}/suc:SezioneIV_ImpostaBollo')
    assert _t(doc, f'{ef}/suc:TotaleDaVersare/text()') == ['1230,00']
    assert _t(doc, f'{D}/suc:Frontespizio/suc:ImportoDaVersare/text()') == ['1230,00']


def test_codice1_minimo_fisso_e_circoscrizioni(tmp_path):
    s, pid = pratica_con_allegati(tmp_path)
    # imposta ipotecaria gia' versata pari al dovuto: con il codice 1 resta comunque la misura fissa (200)
    configura(s, pid, codice_sostitutiva='1', ipotecaria_versata='2820', catastale_versata='500', **BASE)
    doc = xml_di(s, pid)
    ef = f'{D}/suc:QuadroEF'
    assert _t(doc, f'{ef}/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaDaVersare/text()') == ['200']
    assert _t(doc, f'{ef}/suc:SezioneII_ImpostaCatastale/suc:ImpostaCatastaleDaVersare/text()') == ['910']
    assert _t(doc, f'{ef}/suc:SezioneIII_TassaIpotecaria/*/text()') == ['1', '120']
    assert _t(doc, f'{ef}/suc:SezioneIV_ImpostaBollo/*/text()') == ['1', '85']
    assert _t(doc, f'{ef}/suc:TotaleDaVersare/text()') == ['1315,00']


@pytest.mark.parametrize('dich,codice', [
    (dict(codice_sostitutiva='2', prima_anno='2026', prima_volume='88888'), 'DATO_MANCANTE'),          # manca il numero
    (dict(codice_sostitutiva='2', prima_anno='2013', prima_volume='88888', prima_numero='5'), 'VALORE_NON_VALIDO'),
    (dict(codice_sostitutiva='2', prima_anno='2025', prima_volume='88888', prima_numero='5'), 'VALORE_NON_VALIDO'),  # decesso 2026
    (dict(codice_sostitutiva='2', prima_anno='2026', prima_volume='1', prima_numero='5'), 'VALORE_NON_VALIDO'),
    (dict(codice_sostitutiva='2', ipotecaria_versata='10.5', **BASE), 'VALORE_NON_VALIDO'),
    (dict(codice_sostitutiva='3', **BASE), 'SOSTITUTIVA_NON_SUPPORTATA'),
    (dict(**BASE), 'DATO_MANCANTE'),                                                                # manca il codice
])
def test_dati_non_validi_bloccano_export_e_verifica(tmp_path, dich, codice):
    s, pid = pratica_con_allegati(tmp_path)
    configura(s, pid, **dich)
    r = s.esporta(pid)
    assert not r['generato'] and not r['completo']
    assert codice in {e['codice'] for e in r['errori']}, r['errori']
    assert codice in {e['codice'] for e in s.verifica(pid)['rilievi']}
    with pytest.raises(DatiNonValidi):
        s.invio_prepara(pid)


def test_originaria_invariata(tmp_path):
    s, pid = pratica_con_allegati(tmp_path)
    doc = xml_di(s, pid)
    assert _t(doc, f'{D}/suc:Frontespizio/suc:TipoDichiarazione/suc:PrimaDichiarazione/text()') == ['1']
    assert not _t(doc, f'{D}/suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaVersata')


# ---- controllo ufficiale locale (componente SUC13 2.3.1): stesso metodo di test_telematico_controllo.py ----------------
from test_telematico_controllo import _esegui, _motivo_salto  # noqa: E402


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or '')
@pytest.mark.parametrize('codice,extra', [('2', dict(ipotecaria_versata='2000', catastale_versata='1000')),
                                          ('1', dict(ipotecaria_versata='2820', catastale_versata='500'))])
def test_controllo_ufficiale_locale_sostitutiva(tmp_path, codice, extra):
    s, pid = pratica_con_allegati(tmp_path / 'dati')
    configura(s, pid, codice_sostitutiva=codice, **extra, **BASE)
    xml_di(s, pid)
    stato, dgn, wri, dcm = _esegui(s.file_export(pid)[0], tmp_path / 'ctl')
    assert stato == 'positivo', (stato, dgn['diagnostici'], wri)
    assert [d['codice'] for d in dgn['diagnostici']] == ['3345']   # solo l'avviso sull'attestazione, come nel caso A10
    assert dcm
