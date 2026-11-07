"""Revisione 2 dell'interfaccia web: cookie per porta, token dell'indirizzo solo sulla pagina principale, limiti di dimensione
e nomi di file non validi. Dati sintetici."""
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni import web
from successioni.web import crea_app

T = "tok-rev2"
JS = (Path(__file__).parent.parent / "src" / "successioni" / "static" / "app.js").read_text(encoding="utf-8")


def client(tmp_path, porta=8765, nome="d"):
    sv = Servizio(Archivio(tmp_path / nome))
    return sv, TestClient(crea_app(sv, token=T, porta=porta), base_url=f"http://127.0.0.1:{porta}", follow_redirects=False)


# ---------------------------------------------------------------- punti 3 e 4: cookie e token
def test_token_nell_indirizzo_diventa_cookie_e_redirect_senza_query(tmp_path):
    _, c = client(tmp_path)
    r = c.get("/", params={"t": T})
    assert r.status_code == 303 and r.headers["location"] == "/"
    sc = r.headers["set-cookie"]
    assert sc.startswith("successioni_8765=") and "httponly" in sc.lower() and "samesite=strict" in sc.lower()
    r2 = c.get("/")                                     # il cookie basta: pagina senza token nell'indirizzo
    assert r2.status_code == 200 and "Successioni" in r2.text
    assert c.get("/api/pratiche").status_code == 200


def test_token_errato_o_assente_sulla_pagina(tmp_path):
    _, c = client(tmp_path)
    assert c.get("/", params={"t": "sbagliato"}).status_code == 401
    r = c.get("/")
    assert r.status_code == 401 and "Avvia-pratica-reale.cmd" in r.text


def test_token_nell_indirizzo_rifiutato_sulle_api(tmp_path):
    _, c = client(tmp_path)
    assert c.get("/api/pratiche", params={"t": T}).status_code == 401
    assert c.post("/api/pratiche", params={"t": T}, json={"titolo": "x"}).status_code == 401
    assert c.get("/static/app.js", params={"t": T}).status_code == 401
    # il lanciatore verifica la sessione attiva con /api/info?t=... (scripts/windows/avvia_successioni.py)
    assert c.get("/api/info", params={"t": T}).status_code == 200
    assert c.get("/api/info", params={"t": "no"}).status_code == 401
    # intestazione per client non browser
    assert c.get("/api/pratiche", headers={"x-successioni-token": T}).status_code == 200


def test_due_interfacce_su_porte_diverse_non_si_scollegano(tmp_path):
    sv1 = Servizio(Archivio(tmp_path / "prova"))
    sv2 = Servizio(Archivio(tmp_path / "reale"))
    a1 = crea_app(sv1, token="uno", porta=8765)
    a2 = crea_app(sv2, token="due", porta=8766)
    # un solo «browser»: stesso contenitore di cookie per 127.0.0.1, porte diverse
    c1 = TestClient(a1, base_url="http://127.0.0.1:8765", follow_redirects=False)
    c2 = TestClient(a2, base_url="http://127.0.0.1:8766", follow_redirects=False)
    c1.get("/", params={"t": "uno"})
    c2.cookies = c1.cookies                             # condivisi: il cookie della prima porta e' visto anche dalla seconda
    c2.get("/", params={"t": "due"})
    c1.cookies = c2.cookies
    assert {"successioni_8765", "successioni_8766"} <= set(c1.cookies.keys())
    assert c1.get("/api/pratiche").status_code == 200
    assert c2.get("/api/pratiche").status_code == 200


# ---------------------------------------------------------------- punto 7: dimensioni e nomi
@pytest.fixture
def cl(tmp_path):
    sv, c = client(tmp_path)
    c.get("/", params={"t": T})
    pid = c.post("/api/pratiche", json={"titolo": "Allegati"}).json()["pratica_id"]
    return sv, c, pid


# virgolette e caratteri di controllo arrivano gia' codificati dal browser (%22, %01): si verificano con nome_file_valido
@pytest.mark.parametrize("nome", ["x.pdf:ads", "a*b.pdf", "a?.pdf", "a<b>.pdf", "a|b.pdf", "CON.pdf", "x.pdf."])
def test_nome_allegato_non_valido_400(cl, nome):
    _, c, pid = cl
    r = c.post(f"/api/pratiche/{pid}/allegati", files={"file": (nome, b"%PDF-1.4 x", "application/pdf")})
    assert r.status_code == 400 and r.json()["codice"] == "NOME_FILE_NON_VALIDO", r.text
    assert "rinomina" in r.json()["messaggio"]


def test_nome_allegato_vuoto_400_non_500(cl):
    _, c, pid = cl
    body = (b'--B\r\nContent-Disposition: form-data; name="file"; filename=""\r\nContent-Type: application/pdf\r\n\r\n'
            b'%PDF-1.4\r\n--B--\r\n')
    r = c.post(f"/api/pratiche/{pid}/allegati", content=body, headers={"content-type": "multipart/form-data; boundary=B"})
    assert r.status_code == 400, r.text
    r = c.post(f"/api/pratiche/{pid}/allegati", files={"altro": ("a.pdf", b"x")})
    assert r.status_code == 400 and r.json()["codice"] == "FILE_MANCANTE"


def test_allegato_oltre_il_limite_413_letto_a_blocchi(cl, monkeypatch):
    _, c, pid = cl
    monkeypatch.setattr(web, "LIMITE_ALLEGATO", 10_000)
    # crea_app legge il limite a ogni richiesta dal modulo
    r = c.post(f"/api/pratiche/{pid}/allegati", files={"file": ("grande.pdf", b"%PDF" + b"0" * 20_000, "application/pdf")})
    assert r.status_code == 413 and r.json()["codice"] == "FILE_TROPPO_GRANDE"
    assert c.get(f"/api/pratiche/{pid}/allegati").json() == []


def test_limite_anche_senza_content_length():
    """Corpo a blocchi senza Content-Length: la ricezione si interrompe appena supera il limite."""
    import asyncio
    from starlette.requests import Request

    blocchi = [b"a" * 400] * 10
    letti = []

    async def receive():
        b = blocchi.pop(0)
        letti.append(b)
        return {"type": "http.request", "body": b, "more_body": bool(blocchi)}

    req = Request({"type": "http", "method": "POST", "headers": [], "path": "/", "query_string": b""}, receive)
    with pytest.raises(web.RichiestaRifiutata) as e:
        asyncio.run(web.corpo_limitato(req, 1000, "file"))
    assert e.value.stato == 413 and len(letti) == 3          # non legge il resto del corpo


def test_import_xml_limite_60_mb_e_content_length(cl):
    _, c, _ = cl
    assert web.LIMITE_IMPORT_XML == 60 * 1024 * 1024
    r = c.post("/api/importa", content=b"", headers={"content-type": "application/xml"})
    assert r.status_code == 422                  # come prima (test_telematico_importa)
    r = c.post("/api/importa", content=b"<x/>", headers={"content-type": "application/xml",
                                                         "content-length": str(70 * 1024 * 1024)})
    assert r.status_code == 413 and "60 MB" in r.json()["messaggio"]


def test_import_xml_24_mb_letto(cl):
    """Un file di 24 MB (come quelli reali con allegati EG) non e' respinto per la dimensione."""
    _, c, _ = cl
    r = c.post("/api/importa", content=b"<x>" + b" " * (24 * 1024 * 1024) + b"</x>", headers={"content-type": "application/xml"})
    assert r.status_code != 413 and r.json().get("codice") != "FILE_TROPPO_GRANDE"


def test_ricevuta_oltre_il_limite_413(cl):
    _, c, pid = cl
    r = c.post(f"/api/pratiche/{pid}/ricevute/tx?tipo=registrazione", content=b"x",
               headers={"content-length": str(21_000_000)})
    assert r.status_code == 413
    r = c.post(f"/api/pratiche/{pid}/ricevute/tx?tipo=registrazione&nome=a:b.pdf", content=b"x")
    assert r.status_code == 400 and r.json()["codice"] == "NOME_FILE_NON_VALIDO"


@pytest.mark.parametrize("nome", ['a".pdf', "a\x01.pdf", "a\tb.pdf", "", "  ", "nul.txt"])
def test_nome_file_valido_rifiuta(nome):
    with pytest.raises(web.RichiestaRifiutata) as e:
        web.nome_file_valido(nome)
    assert e.value.stato == 400


def test_nome_file_valido_casi_ammessi():
    assert web.nome_file_valido("C:\\Documenti\\visura catastale (1).pdf") == "visura catastale (1).pdf"
    assert web.nome_file_valido("carta d'identità.pdf") == "carta d'identità.pdf"


# ---------------------------------------------------------------- punti dell'interfaccia (controllo del sorgente; prove reali in e2e)
def test_sorgente_interfaccia_revisione2():
    assert "W.chiave = crypto.randomUUID()" in JS and 'chiave: W.chiave' in JS        # punto 1
    assert "function occupato(nome, fn)" in JS and "occupato('esporta'" in JS          # punto 2
    assert 'chiama("prepara"' in JS and "chiavePrep" in JS
    assert "Il programma non risponde" in JS and "unhandledrejection" in JS            # punto 5
    assert "JSON.stringify(d.profilo" not in JS and "motivoLeggibile" in JS             # punto 6
    assert 'confirm("Eliminare la riga?")' not in JS                                   # punto 8
    assert "8000" in JS                                                                 # punto 9


def test_prepara_invio_stessa_chiave_stessa_copia(tmp_path):
    """La GUI ripete «Prepara invio» con la stessa chiave finche' i dati non cambiano: il servizio restituisce la stessa copia."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from unittest.mock import patch
    from test_correzioni_codex import pratica_con_allegati
    arch = Archivio(tmp_path / "d")
    with patch("test_correzioni_codex.Archivio", return_value=arch):
        sv, pid = pratica_con_allegati(tmp_path / "d")
    ex = sv.esporta(pid)
    assert ex["completo"]
    c = TestClient(crea_app(sv, token=T, porta=8765), base_url="http://127.0.0.1:8765")
    c.get("/", params={"t": T})
    chiave = f"prep-{pid}-r{sv.leggi(pid)['revisione']}-{ex['job_id']}-non_eseguito"
    a = c.post(f"/api/pratiche/{pid}/invio/prepara", json={"chiave_richiesta": chiave})
    b = c.post(f"/api/pratiche/{pid}/invio/prepara", json={"chiave_richiesta": chiave})
    assert a.status_code == b.status_code == 200, (a.text, b.text)
    assert a.json()["job_id"] == b.json()["job_id"]
    assert len([x for x in c.get(f"/api/pratiche/{pid}/invio").json()["copie"] if x["stato"] == "preparata"]) == 1


# ---------------------------------------------------------------- esito del controllo eseguito a mano (rotta collegata)
def test_esito_controllo_manuale_richiede_i_file(tmp_path):
    sv, c = client(tmp_path)
    c.get("/", params={"t": T})
    pid = sv.crea_pratica("Prova esito manuale")["pratica_id"]
    r = c.post(f"/api/pratiche/{pid}/controllo-ufficiale/diagnostico", files={"wri": ("x.wri", b"x")},
               headers={"Origin": "http://127.0.0.1:8765"})
    assert r.status_code == 400 and r.json()["codice"] == "FILE_MANCANTE"
    r = c.post(f"/api/pratiche/{pid}/controllo-ufficiale/diagnostico",
               files={"dgn": ("x.dgn", b"x"), "log_schema": ("x_logSchema.xml", b"<a/>")}, headers={"Origin": "http://127.0.0.1:8765"})
    assert r.status_code in (404, 409, 422) and r.json().get("codice")     # nessun controllo in attesa: errore di servizio chiaro
