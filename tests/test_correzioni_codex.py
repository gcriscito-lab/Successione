"""Regressioni CE01, CE03-CE09: solo dati sintetici, nessun servizio esterno."""
import copy
import hashlib
import json
import sys
import shutil
import subprocess
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
from telematico_casi import ALLEGATI_A10, CF_ANNA, CF_LUCA, caso_a10, contesto_caso_a10
from test_elaborati import ops_da_caso
from successioni.archivio import Archivio
from successioni.errori import DatiNonValidi, RipristinoNonAmmesso
from successioni.servizio import Servizio
from successioni.telematico.esporta import esporta_xml
from successioni.web import crea_app


def caso_tempestivo():
    d = caso_a10()
    d['persone'][0]['data_decesso'] = '2026-03-10'
    return d


def pratica_con_allegati(tmp_path, intermediario=False):
    s = Servizio(Archivio(tmp_path / 'dati'))
    d = caso_tempestivo()
    d['documenti_ref'] = []
    d['opzioni']['fornitore'] = {'cf': CF_LUCA if intermediario else CF_ANNA,
        'tipo': '10' if intermediario else '1',
        **({'impegno_codice': '1', 'data_impegno': '2026-10-30'} if intermediario else {})}
    pid = s.crea_pratica('Caso sintetico tempestivo', iniziali=ops_da_caso(d))['pratica_id']
    ops = []
    for i, a in enumerate(ALLEGATI_A10.values()):
        al = s.acquisisci_file(pid, a['percorso'])
        ops.append({'op': 'upsert', 'coll': 'documenti_ref', 'id': f'dr_test000{i}',
                    'campi': {'allegato_id': al['allegato_id'],
                              'tipo_eg': 'AlberoGenealogico' if i == 0 else 'DocumentiPassivita'}})
    if intermediario:
        ops.append({'op': 'upsert', 'coll': 'documenti_ref', 'id': 'dr_identita',
                    'campi': {'allegato_id': ops[0]['campi']['allegato_id'], 'tipo_eg': 'DocumentiIdentita'}})
    s.aggiorna(pid, 1, ops)
    return s, pid


@pytest.mark.parametrize('intermediario', [False, True])
def test_ce01_export_completo_da_servizio_e_api(tmp_path, intermediario):
    s, pid = pratica_con_allegati(tmp_path, intermediario)
    with TestClient(crea_app(s, token='sintetico', ammetti_host_di_prova=True)) as cl:
        r = cl.post(f'/api/pratiche/{pid}/esporta?t=sintetico', json={})
    assert r.status_code == 200, r.text
    r = r.json()
    assert r['generato'] and r['completo'] and not r['errori'], r
    assert r['avvisi']  # avvertenze PDF/A e dati interni non spariscono
    xml = (s.arch.base / r['percorso']).read_bytes()
    assert b'ImageData' in xml
    assert (b'ImpegnoATrasmettere' in xml) == intermediario


def test_ce01_rifiuta_allegato_di_altra_pratica_e_file_alterato(tmp_path):
    s, pid = pratica_con_allegati(tmp_path)
    aid = s.leggi(pid)['dati']['documenti_ref'][0]['allegato_id']
    altra = s.crea_pratica('Altra pratica')['pratica_id']
    with s.arch.transazione() as c:
        c.execute('UPDATE allegati SET pratica_id=? WHERE id=?', (altra, aid))
    r = s.esporta(pid)
    assert not r['generato'] and any(e['codice'] == 'ALLEGATO_NON_DISPONIBILE' for e in r['errori'])
    with s.arch.transazione() as c:
        c.execute('UPDATE allegati SET pratica_id=? WHERE id=?', (pid, aid))
    row = s._riga_allegato(aid)
    (s.arch.base / row['percorso']).write_bytes(b'ALTERAZIONE SINTETICA')
    with pytest.raises(DatiNonValidi, match='alterato'):
        s.esporta(pid)


def test_ce03_quote_non_verificate_non_finalizzabili_ma_bozza_con_avviso():
    d = caso_tempestivo()
    for p, g in [('p_anna0001', '10'), ('p_luca0001', '11')]:
        next(x for x in d['persone'] if x['id'] == p)['relazione_con_defunto'] = g
        d['opzioni']['telematico']['persone'][p]['grado_parentela'] = g
    r = esporta_xml(d, contesto_caso_a10())
    assert r.xml is None and not r.completo
    assert any(m.codice == 'QUOTE_DI_LEGGE_NON_VERIFICATE' for m in r.quadri_mancanti)
    b = esporta_xml(d, contesto_caso_a10(scopo='bozza_tecnica'))
    assert b.xml and not b.completo


@pytest.mark.parametrize('tempistica', ['1', '2'])
def test_ce04_tardiva_con_imposta_non_finalizzabile(tempistica):
    d = caso_a10()
    d['beni'][0]['valore'] = '3000000'
    d['opzioni']['telematico']['dichiarazione']['tempistica_pagamento'] = tempistica
    r = esporta_xml(d, contesto_caso_a10(data_riferimento=date(2026, 11, 1)))
    assert not r.completo and r.xml is None
    assert any('tardiv' in m.messaggio.lower() for m in r.quadri_mancanti)


def test_ce04_pagamento_differito_tempestivo_conserva_calcolo():
    d = caso_tempestivo()
    d['beni'][0]['valore'] = '3000000'
    d['opzioni']['telematico']['dichiarazione']['tempistica_pagamento'] = '1'
    r = esporta_xml(d, contesto_caso_a10())
    assert r.completo and r.xml
    assert r.mappa['calcolo:EF18bis']['imposta'] == 44132
    assert b'<suc:TotaleDaVersare>90655,00</suc:TotaleDaVersare>' in r.xml


def test_ce05_export_rifiuta_allegato_oltre_entrambi_limiti_mb(tmp_path):
    p = tmp_path / 'oltre_limite.pdf'
    p.write_bytes(Path(ALLEGATI_A10['al_albero']['percorso']).read_bytes() + b' ' * 6000000)
    c = contesto_caso_a10()
    c.allegati = copy.deepcopy(c.allegati)
    c.allegati['al_albero']['percorso'] = str(p)
    r = esporta_xml(caso_tempestivo(), c)
    assert r.xml is None and not r.completo
    assert any(e.codice == 'ALLEGATO_OLTRE_LIMITE' for e in r.errori)


def test_ce05_limite_fornitura_misura_xml_reale_e_blocca_export(monkeypatch):
    from successioni.documenti import dimensioni
    originale = dimensioni.verifica_fornitura
    xml_misurato = []

    def limite_ridotto(manifest, **kw):
        xml_misurato.append(manifest['xml'])
        # La stessa verifica reale, con soglia bassa per evitare un corpus da 40 MB.
        return originale(manifest, limite_compresso=100, **kw)

    monkeypatch.setattr(dimensioni, 'verifica_fornitura', limite_ridotto)
    r = esporta_xml(caso_tempestivo(), contesto_caso_a10())
    assert xml_misurato and b'ImageData' in xml_misurato[0]
    assert r.xml is None and not r.completo
    assert any(e.codice == 'FORNITURA_OLTRE_LIMITE' for e in r.errori)


@pytest.mark.parametrize('alterato', [False, True])
def test_ce06_backup_incompleto_o_alterato_non_popola_destinazione(tmp_path, alterato):
    s, pid = pratica_con_allegati(tmp_path)
    backup = s.arch.backup(tmp_path / 'backup')
    row = s.elenca_allegati(pid)[0]
    p = backup / row['percorso']
    if alterato:
        p.write_bytes(b'ALTERAZIONE SINTETICA')
    else:
        p.unlink()
    dest = Archivio(tmp_path / 'ripristino')
    with pytest.raises(RipristinoNonAmmesso):
        dest.ripristina(backup)
    assert dest.e_vuoto()


def test_ce06_errore_copia_ripristino_ripetibile(tmp_path):
    s, pid = pratica_con_allegati(tmp_path)
    backup = s.arch.backup(tmp_path / 'backup')
    dest = Archivio(tmp_path / 'ripristino')
    with patch('shutil.copytree', side_effect=OSError('guasto sintetico')):
        with pytest.raises(RipristinoNonAmmesso):
            dest.ripristina(backup)
    assert dest.e_vuoto()
    dest.ripristina(backup)
    assert Servizio(dest).leggi(pid) == s.leggi(pid)


def test_ce06_backup_senza_xml_del_job_non_ripristinabile(tmp_path):
    s, pid = pratica_con_allegati(tmp_path)
    es = s.esporta(pid)
    assert es['generato']
    backup = s.arch.backup(tmp_path / 'backup')
    (backup / es['percorso']).unlink()
    dest = Archivio(tmp_path / 'ripristino')
    with pytest.raises(RipristinoNonAmmesso, match='documento mancante'):
        dest.ripristina(backup)
    assert dest.e_vuoto()


def test_ce06_ripristino_non_cancella_file_estranei_in_destinazione(tmp_path):
    s, _ = pratica_con_allegati(tmp_path)
    backup = s.arch.backup(tmp_path / 'backup')
    dest = Archivio(tmp_path / 'ripristino')
    altro = dest.base / 'annotazioni.txt'
    altro.write_text('Documento sintetico da conservare')
    with pytest.raises(RipristinoNonAmmesso, match='altri file'):
        dest.ripristina(backup)
    assert altro.read_text() == 'Documento sintetico da conservare'
    assert dest.e_vuoto()


def test_ce07_static_non_legge_fuori_directory(tmp_path):
    s = Servizio(Archivio(tmp_path / 'dati'))
    with TestClient(crea_app(s, token='t', ammetti_host_di_prova=True)) as cl:
        assert cl.get('/static/app.js?t=t').status_code == 200
        for p in ['x%5c..%5c..%5c..%5c..%5ctests%5ce2e%5cgui_flusso.js',
                  'C:%5cWindows%5ctest.html', 'x%2f..%2fapp.js']:
            assert cl.get('/static/' + p + '?t=t').status_code == 404


def test_ce09_fixture_evidenze_hanno_byte_git_senza_conversione():
    root = Path(__file__).resolve().parent / 'fixture_telematico' / 'controllo_20261101'
    man = json.loads((root / 'manifest.json').read_text())
    for caso in man['casi'].values():
        for f, h in caso['file'].items():
            assert hashlib.sha256((root / f).read_bytes()).hexdigest() == h


@pytest.mark.skipif(not shutil.which('node'), reason='Node non disponibile per l’helper E2E')
def test_ce10_assert_e2e_negativo_termina_con_errore():
    helper = Path(__file__).parent / 'e2e' / 'verifiche.js'
    script = f"require({json.dumps(str(helper))}).ok(false, 'fallimento sintetico intenzionale')"
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=15)
    assert r.returncode != 0 and 'fallimento sintetico intenzionale' in r.stderr


def test_ce08_controllo_interrotto_riprende_da_input_congelato(tmp_path):
    import successioni.collegamenti.controllo as C
    from test_collegamenti_controllo import ambiente_finto, EsecutoreFinto, FIX, DGN_POSITIVO_SIMULATO, LOG_VALIDO

    class ArrestoSintetico(BaseException):
        pass

    class EsecutoreInterrotto(EsecutoreFinto):
        def __call__(self, args, cwd, timeout):
            if C.CLASSE_CONTROLLO in args:
                raise ArrestoSintetico()
            return super().__call__(args, cwd, timeout)

    arch = Archivio(tmp_path / 'dati')
    cfg = ambiente_finto(tmp_path)
    ctl = C.ControlloJar(arch, cfg, esecutore=EsecutoreInterrotto(None, None))
    with pytest.raises(ArrestoSintetico):
        ctl.esegui(FIX / 'frontespizio.xml', chiave='arresto')
    jid = ctl.job.id_da_chiave('controllo_ufficiale', 'arresto')
    es = EsecutoreFinto(DGN_POSITIVO_SIMULATO.encode(), LOG_VALIDO)
    nuovo = C.ControlloJar(Archivio(arch.base), cfg, esecutore=es)
    r = nuovo.riprendi(jid)
    assert r.job_id == jid and r.stato == 'completato'
    assert r.esito.value == 'simulazione'
    assert sum(C.CLASSE_CONTROLLO in a for a in es.chiamate) == 1
    assert any('interrott' in h.get('nota', '') for h in nuovo.job.leggi(jid)['risultato']['cronologia'])
    prima = len(es.chiamate)
    nuovo.esegui(FIX / 'frontespizio.xml', chiave='arresto')
    assert len(es.chiamate) == prima


def test_ce08_riprendi_non_duplica_un_controllo_ancora_attivo(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import successioni.collegamenti.controllo as C
    from test_collegamenti_controllo import ambiente_finto, EsecutoreFinto, FIX

    avviato, rilascia = Event(), Event()

    class EsecutoreLento(EsecutoreFinto):
        def __call__(self, args, cwd, timeout):
            if C.CLASSE_CONTROLLO in args:
                avviato.set()
                assert rilascia.wait(10)
            return super().__call__(args, cwd, timeout)

    arch = Archivio(tmp_path / 'dati')
    cfg = ambiente_finto(tmp_path)
    es = EsecutoreLento(None, None)
    ctl = C.ControlloJar(arch, cfg, esecutore=es)
    with ThreadPoolExecutor() as pool:
        f = pool.submit(ctl.esegui, FIX / 'frontespizio.xml', chiave='lento')
        try:
            assert avviato.wait(10)
            jid = ctl.job.id_da_chiave('controllo_ufficiale', 'lento')
            altro = C.ControlloJar(arch, cfg, esecutore=EsecutoreFinto(None, None))
            assert altro.riprendi(jid).stato == 'in_esecuzione'
            assert altro._esec.chiamate == []
        finally:
            rilascia.set()
        f.result(timeout=10)
