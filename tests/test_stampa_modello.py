"""Stampa del modello ministeriale con il codice Java del componente di controllo (collegamenti/stampa.py). Dati sintetici."""
import io

import pytest
from pypdf import PdfReader

from successioni.collegamenti import stampa as ST
from successioni.errori import DatiNonValidi
from test_correzioni_codex import pratica_con_allegati

SALTO = ST.disponibile()


def test_senza_ambiente_errore_esplicito():
    assert "non disponibile" in str(pytest.raises(DatiNonValidi, ST.genera, b"<x/>", env={}).value)


def test_stampa_richiede_file_completo_e_aggiornato(tmp_path):
    s, pid = pratica_con_allegati(tmp_path)
    with pytest.raises(DatiNonValidi):                       # nessun export ancora
        s.stampa_modello(pid)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
def test_stampa_modello_dallo_stesso_xml(tmp_path):
    s, pid = pratica_con_allegati(tmp_path)
    assert s.esporta(pid)['completo']
    r = s.stampa_modello(pid)
    assert r['generato'] and r['pagine'] >= 8
    pdf, _ = s.file_stampa_modello(pid)
    leggi = PdfReader(io.BytesIO(pdf))
    testo = "\n".join(p.extract_text() or "" for p in leggi.pages)
    assert "DICHIARAZIONE" in testo.upper()
    # i valori dell'XML compaiono sul modello (il testo e' sovrapposto ai PDF ufficiali): defunto, eredi, immobili, totali EF
    compatto = "".join(testo.split())
    for atteso in ("RSSMRA40A01H501K", "RSSNNA70A41H501J", "RSSLCU72B02H501O", "ROSSI", "ANNA", "LUCA", "126000", "15000",
                   "141000", "2820", "1410", "4435"):
        assert atteso in compatto, f"{atteso} non compare nella stampa"
    assert s.stato_elaborati(pid)['stampa_modello']['stato'] == 'aggiornata'
    # i dati cambiano -> l'export diventa obsoleto e la stampa non e' piu' corrente
    rev = s.leggi(pid)['revisione']
    s.aggiorna(pid, rev, [{'op': 'set', 'sezione': 'opzioni', 'campi': {'quadri_attivi': s.leggi(pid)['dati']['opzioni'].get('quadri_attivi', [])}}])
    st = s.stato_elaborati(pid)
    assert st['stampa_modello']['stato'] in ('aggiornata', 'obsoleta')
    # alterazione del PDF sul disco: il download lo rifiuta
    (s.arch.base / r['percorso']).write_bytes(b'%PDF-alterato')
    with pytest.raises(DatiNonValidi):
        s.file_stampa_modello(pid)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
def test_controllo_ufficiale_dal_servizio_produce_dcm(tmp_path):
    """Prova generale 2026-11-05: il servizio deve chiedere il .dcm, altrimenti il componente cancella la copia di lavoro e un
    controllo positivo sembra un input alterato."""
    s, pid = pratica_con_allegati(tmp_path)
    assert s.esporta(pid)['completo']
    c = s.controllo_ufficiale_pratica(pid)
    assert c['stato_controllo'] == 'positivo' and c['esito'] == 'passato', c
    dcm, m = s.file_controllato_dcm(pid)
    assert len(dcm) > 1000 and m['nome'].endswith('.dcm')
