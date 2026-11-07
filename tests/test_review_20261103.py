"""Regressioni della review: dati sintetici, nessun invio reale."""
import copy
from pathlib import Path

import pytest
from lxml import etree

from successioni.telematico.importa import importa_xml, XmlNonImportabile
from successioni.telematico.xsd import valida_xsd
from successioni.collegamenti import invio as I
from successioni.errori import DatiNonValidi
from test_collegamenti_invio import ctx, confermata
from test_telematico_esporta import _quattro_figli, _bozza
from test_telematico_importa import _xml, CTX

NS = {"suc": "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:suc:v1"}


# «Agevolazioni» ora si importa (revisione 2, 07/11/2026): la regressione sui campi sconosciuti la copre CampoNonConosciuto
@pytest.mark.parametrize("tag", ["ValorePrecSucc", "CampoNonConosciuto"])
def test_nessuna_perdita_silenziosa_dei_campi_xml(tag):
    root = etree.fromstring(_xml())
    dv = root.xpath('//suc:QuadroEC//suc:Devoluzione', namespaces=NS)[0]
    etree.SubElement(dv, '{' + NS['suc'] + '}' + tag).text = 'P' if tag == 'Agevolazioni' else '100'
    xml = etree.tostring(root)
    if tag == 'Agevolazioni':
        assert not valida_xsd(xml)
    with pytest.raises(XmlNonImportabile, match=tag):
        importa_xml(xml)


@pytest.mark.parametrize("figli", [4, 7])
def test_continuazioni_raggruppate_anche_tra_moduli(figli):
    d = _quattro_figli()
    if figli == 7:
        from successioni.telematico.identificativi import genera_cf_sintetico
        for i, nome in enumerate(['Paolo', 'Gianni', 'Livia'], 5):
            p = copy.deepcopy(d['persone'][-1]); p['id'] = f'p_figlio00{i}'; p['nome'] = nome
            p['codice_fiscale'] = genera_cf_sintetico('Rossi', nome, 'M', '1975-01-01', 'H501')
            d['persone'].append(p)
            d['opzioni']['telematico']['persone'][p['id']] = {'sesso': 'M', 'provincia_nascita': 'RM', 'grado_parentela': '02'}
            for b in d['beni']:
                d['devoluzioni'].append({'id': f'd_new{i}{b["id"][2:]}', '_origine': {}, 'bene_id': b['id'],
                                        'persona_id': p['id'], 'quota': '1/7', 'diritto': '1'})
        for dv in d['devoluzioni']:
            dv['quota'] = '1/7'
    exp = _bozza(d)
    assert exp.xml, exp.errori
    imp = importa_xml(exp.xml)
    beni = [o for o in imp['operazioni'] if o.get('coll') == 'beni']
    dev = [o for o in imp['operazioni'] if o.get('coll') == 'devoluzioni']
    assert len(beni) == 3
    assert len({o['id'] for o in dev}) == 3 * figli
    assert all(sum(v['campi']['bene_id'] == b['id'] for v in dev) == figli for b in beni)
    from successioni.servizio import nuovi_dati, Servizio
    dati = nuovi_dati()
    for n, op in enumerate(imp['operazioni']):
        Servizio._applica(dati, op, 'acquisito', 'gui', n)
    from successioni.telematico.esporta import esporta_xml
    assert _bozza(dati).xml == exp.xml


def test_continuazione_mancante_rifiutata():
    root = etree.fromstring(_bozza(_quattro_figli()).xml)
    righe = root.xpath('//suc:QuadroEC/suc:Modulo/suc:Fabbricati', namespaces=NS)
    righe[-1].getparent().remove(righe[-1])
    with pytest.raises(XmlNonImportabile, match='continuazione'):
        importa_xml(etree.tostring(root))


def test_simulazione_non_blocca_manuale(ctx):
    sim = I.InvioAdattatore(ctx['arch'], I.TrasportoSimulato())
    copia = confermata(ctx, sim)
    sim.trasmetti(copia.job_id, chiave_richiesta='prova')
    manuale = I.InvioAdattatore(ctx['arch'])
    reale = confermata(ctx, manuale)
    t = manuale.trasmetti(reale.job_id, chiave_richiesta='operativo')
    assert t.stato == I.ATTESA_INVIO_MANUALE
    assert manuale.leggi_tentativo(sim.job.id_da_chiave(I.TIPO_TENTATIVO, 'prova')).esito.value == 'simulazione'
    with pytest.raises(DatiNonValidi, match='modalita'):
        sim.riconcilia(t.job_id)


def test_esito_e_copia_aggiornati_atomicamente(ctx, monkeypatch):
    ad = I.InvioAdattatore(ctx['arch'], I.TrasportoSimulato())
    copia = confermata(ctx, ad)
    originale = ad.job.transizione
    def interruzione(job_id, da, a, **kw):
        if job_id == copia.job_id and a == I.TRASMESSA:
            raise OSError('interruzione tra le due scritture')
        return originale(job_id, da, a, **kw)
    monkeypatch.setattr(ad.job, 'transizione', interruzione)
    with pytest.raises(OSError):
        ad.trasmetti(copia.job_id, chiave_richiesta='crash')
    tid = ad.job.id_da_chiave(I.TIPO_TENTATIVO, 'crash')
    assert ad.job.leggi(tid)['stato'] == I.IN_TRASMISSIONE
    assert ad.leggi_copia(copia.job_id).stato == I.IN_INVIO
    monkeypatch.setattr(ad.job, 'transizione', originale)
    ad.riconcilia(tid)
    assert ad.leggi_copia(copia.job_id).stato == I.TRASMESSA
    assert ad.trasporto.chiamate_trasmetti == 1


@pytest.mark.parametrize('stato,atteso', [(I.TRASMESSO, I.TRASMESSA), (I.RIFIUTATO, I.RIFIUTATA),
                                        (I.NON_TRASMESSO, I.CONFERMATA)])
def test_ripresa_archivio_precedente_con_due_stati_disallineati(ctx, stato, atteso):
    ad = I.InvioAdattatore(ctx['arch'], I.TrasportoSimulato(guasto='timeout_prima'))
    c = confermata(ctx, ad); t = ad.trasmetti(c.job_id, chiave_richiesta='vecchio')
    ad.job.transizione(t.job_id, [I.ESITO_INCERTO], stato, patch={'protocollo': 'SIM000001'})
    ad.riconcilia(t.job_id)
    assert ad.leggi_copia(c.job_id).stato == atteso
    assert ad.trasporto.chiamate_trasmetti == 1
