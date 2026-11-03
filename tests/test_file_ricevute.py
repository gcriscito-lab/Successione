import hashlib
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from successioni.errori import DatiNonValidi
from successioni.web import crea_app
from successioni.collegamenti.invio import InvioAdattatore
from test_collegamenti_invio import ctx, confermata
from test_correzioni_codex import pratica_con_allegati


def test_download_stampa_stessa_versione_e_integrita(tmp_path):
    s, pid = pratica_con_allegati(tmp_path)
    ex = s.esporta(pid)
    assert ex['completo']
    url = f'/api/pratiche/{pid}'
    with TestClient(crea_app(s, token='x', ammetti_host_di_prova=True)) as cl:
        assert cl.get(url + '/file.xml').status_code == 401
        xml = cl.get(url + '/file.xml?t=x&job=' + ex['job_id'])
        assert xml.status_code == 200
        assert hashlib.sha256(xml.content).hexdigest() == ex['xml_sha256']
        stampa = cl.get(url + '/stampa?t=x&job=' + ex['job_id'])
        assert stampa.status_code == 200
        assert ex['xml_sha256'] in stampa.text and 'non è il modello ministeriale' in stampa.text
        assert 'RSSMRA40A01H501K' in stampa.text and '<td>4435,00</td>' in stampa.text
        assert 'JVBER' not in stampa.text
        altra = s.crea_pratica('Altra')['pratica_id']
        assert cl.get(f'/api/pratiche/{altra}/file.xml?t=x&job=' + ex['job_id']).status_code == 422
        (s.arch.base / ex['percorso']).write_bytes(b'alterato')
        assert cl.get(url + '/file.xml?t=x').status_code == 422


def test_ricevute_originali_stati_separati_e_appartenenza(ctx):
    ad = InvioAdattatore(ctx['arch'])
    copia = confermata(ctx, ad)
    t = ad.trasmetti(copia.job_id, chiave_richiesta='manuale')
    sv, pid = ctx['sv'], ctx['pid']
    with TestClient(crea_app(sv, token='x', ammetti_host_di_prova=True)) as cl:
        base = f'/api/pratiche/{pid}/ricevute/{t.job_id}'
        # Prima del riscontro l'associazione non e' ammessa.
        assert cl.post(base+'?t=x&tipo=registrazione&esito=registrata',content=b'originale').status_code==422
        # La modalita' viene ricavata dal record persistente, non dalla scelta del client.
        r=cl.post(f'/api/invio/tentativi/{t.job_id}/riconcilia?t=x',json={'evidenze':{'protocollo':'TEST0001','verificato_su':'fixture sintetica'}})
        assert r.status_code==200 and r.json()['modalita']=='manuale'
        doc=cl.post(base+'?t=x&tipo=registrazione&esito=registrata&nome=originale.pdf',content=b'originale')
        assert doc.status_code==200
        rid=doc.json()['dettaglio']['job_id']
        assert cl.get(base+'/file/'+rid+'?t=x').content==b'originale'
        assert cl.post(base+'?t=x&tipo=pagamento&esito=negativo',content=b'negativo').status_code==200
        stato=cl.get(base+'?t=x').json()
        assert stato['registrazione']=='registrata' and stato['pagamento']=='negativo'
        assert len(stato['documenti'])==2
        altra=sv.crea_pratica('Altra')['pratica_id']
        with pytest.raises(DatiNonValidi):
            sv.ricevute_stato(altra,t.job_id)
        # Lo stato nell'interfaccia mostra istruzioni e dettagli del tentativo, senza perdere la prova.
        copie=sv.invio_stato(pid)['copie']
        assert copie[0]['tentativi'][0]['dettaglio']['protocollo']=='TEST0001'
        congelata=cl.get('/api/invio/'+copia.job_id+'/file?t=x')
        assert congelata.content==ctx['xml'].read_bytes()
