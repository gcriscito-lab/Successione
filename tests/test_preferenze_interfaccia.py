import json

import pytest
from starlette.testclient import TestClient
from successioni import impostazioni as IM
from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.web import crea_app


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    p = tmp_path / 'configurazione.json'
    monkeypatch.setenv('SUCCESSIONI_CONFIG', str(p))
    return p


def test_aspetto_salvato_riletto_e_percorsi_preservati(cfg, monkeypatch):
    cfg.write_text(json.dumps({'SUCCESSIONI_JAVA': 'percorso-preesistente', 'nota_esterna': 'conservare'}))
    r = IM.salva({}, {'tema': 'scuro', 'font': 'verdana', 'dimensione': 18, 'interlinea': 'ampia'})
    assert r['interfaccia']['tema'] == 'scuro'
    IM.salva({}, {'larghezza_pannello': 540})
    riletto = IM.stato()['interfaccia']
    assert riletto == {**IM.INTERFACCIA_DEFAULT, 'tema': 'scuro', 'font': 'verdana', 'dimensione': 18,
                       'interlinea': 'ampia', 'larghezza_pannello': 540}
    assert json.loads(cfg.read_text())['SUCCESSIONI_JAVA'] == 'percorso-preesistente'
    assert json.loads(cfg.read_text())['nota_esterna'] == 'conservare'


@pytest.mark.parametrize('preferenze', [{'tema': 'inesistente'}, {'font': 'url(http://example.com)'},
    {'dimensione': 5}, {'dimensione': True}, {'dimensione': '18'}, {'larghezza_pannello': 8000},
    {'interlinea': '99'}, {'chiave_arbitraria': 'valore'}, ['scuro']])
def test_preferenze_errate_non_modificano_la_configurazione(cfg, preferenze):
    cfg.write_text('{"dato_precedente": 1}')
    with pytest.raises(IM.DatiNonValidi):
        IM.salva({}, preferenze)
    assert cfg.read_text() == '{"dato_precedente": 1}'


def test_modifiche_miste_atomiche(cfg):
    with pytest.raises(IM.DatiNonValidi):
        IM.salva({'SUCCESSIONI_JAVA': 'non-esiste.exe'}, {'tema': 'scuro'})
    assert not cfg.exists()
    cfg.write_text('{ JSON non valido')
    with pytest.raises(IM.DatiNonValidi):
        IM.salva({}, {'tema': 'chiaro'})
    assert cfg.read_text() == '{ JSON non valido'


def test_api_preferenze_richiede_token_e_persiste(cfg, tmp_path):
    with TestClient(crea_app(Servizio(Archivio(tmp_path / 'dati')), token='x', ammetti_host_di_prova=True)) as c:
        assert c.post('/api/impostazioni', json={'interfaccia': {'tema': 'scuro'}}).status_code == 401
        assert c.post('/api/impostazioni?t=x', json={'interfaccia': {'dimensione': 100}}).status_code == 422
        assert c.post('/api/impostazioni?t=x', json={'interfaccia': {'tema': 'seppia', 'dimensione': 20}}).status_code == 200
        assert c.get('/api/impostazioni?t=x').json()['interfaccia']['tema'] == 'seppia'
