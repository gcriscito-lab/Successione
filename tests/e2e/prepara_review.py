"""Prepara SOLO fixture nel deposito sintetico del server tests/e2e/server.py."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.collegamenti.invio import InvioAdattatore
from test_collegamenti_invio import confermata
from test_correzioni_codex import pratica_con_allegati

arch = Archivio(ROOT / 'build/gui_fix_data')
s = Servizio(arch)
pid = s.crea_pratica('Invio manuale sintetico')['pratica_id']
ctx = {'arch': arch, 'sv': s, 'pid': pid,
       'xml': ROOT / 'tests/fixture_telematico/controllo_20261101/a10_positivo.xml',
       'pdf': ROOT / 'tests/fixture_telematico/allegati/albero_genealogico.pdf'}
ad = InvioAdattatore(arch)
cp = confermata(ctx, ad)  # doppio del controllo: non prova un controllo ufficiale
ad.trasmetti(cp.job_id, chiave_richiesta='gui-' + pid)
with patch('test_correzioni_codex.Archivio', return_value=arch):
    sv, export_pid = pratica_con_allegati(ROOT / 'build/gui_fix_data')
ex = sv.esporta(export_pid)
assert ex['completo']
(ROOT / 'build/gui_review_fixture.json').write_text(json.dumps({'manuale': pid, 'export': export_pid,
                                                             'job': ex['job_id'], 'sha256': ex['xml_sha256']}))
print('Fixture sintetiche pronte; nessun controllo o invio ufficiale eseguito.')
