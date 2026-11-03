"""Interfaccia locale: API JSON + pagina unica. Solo 127.0.0.1, token di sessione, controllo Host/Origin."""
from __future__ import annotations

import secrets
import os
import tempfile
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

from . import __version__, pdfa, quadri as Q, schema as S
from .errori import ErroreServizio, NonTrovato
from .servizio import Servizio

STATIC = Path(__file__).parent / "static"
TIPI = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".svg": "image/svg+xml"}


def crea_app(servizio: Servizio | None = None, token: str | None = None, porta: int = 8765,
             ammetti_host_di_prova: bool = False) -> Starlette:
    sv = servizio or Servizio()
    token = token or secrets.token_urlsafe(24)
    host_ok = {f"127.0.0.1:{porta}", f"localhost:{porta}"} | ({"testserver"} if ammetti_host_di_prova else set())

    def controllo(request: Request):
        if request.headers.get("host", "") not in host_ok:
            return JSONResponse({"codice": "HOST_NON_AMMESSO"}, status_code=403)
        if request.cookies.get("successioni") != token and request.query_params.get("t") != token:
            return JSONResponse({"codice": "NON_AUTORIZZATO"}, status_code=401)
        if request.method not in ("GET", "HEAD"):
            origin = request.headers.get("origin")
            if origin and origin.split("://", 1)[-1] not in host_ok:
                return JSONResponse({"codice": "ORIGINE_NON_AMMESSA"}, status_code=403)
        return None

    def api(fn):
        async def w(request: Request):
            if (r := controllo(request)) is not None:
                return r
            try:
                out = await fn(request)
                return out if hasattr(out, "status_code") else JSONResponse(out)
            except NonTrovato as e:
                return JSONResponse(e.asdict(), status_code=404)
            except ErroreServizio as e:
                return JSONResponse(e.asdict(), status_code=409 if e.codice == "CONFLITTO_REVISIONE" else 422)
            except (ValueError, KeyError, TypeError, AttributeError) as e:   # JSON malformato, campo mancante o di tipo errato
                return JSONResponse({"codice": "RICHIESTA_NON_VALIDA", "messaggio": "richiesta non valida: " + (str(e) or type(e).__name__)[:200]}, status_code=422)
        return w

    async def home(request: Request):
        if (r := controllo(request)) is not None:
            return r
        resp = HTMLResponse((STATIC / "index.html").read_text(encoding="utf-8"))
        resp.set_cookie("successioni", token, httponly=True, samesite="strict")
        return resp

    async def statico(request: Request):
        if (r := controllo(request)) is not None:
            return r
        nome = request.path_params["nome"]
        radice = STATIC.resolve()
        f = (radice / nome).resolve()
        if ("/" in nome or "\\" in nome or ":" in nome or nome.startswith(".")
                or f.parent != radice or f.suffix not in TIPI or not f.is_file()):
            return JSONResponse({"codice": "NON_TROVATO"}, status_code=404)
        return Response(f.read_bytes(), media_type=TIPI[f.suffix], headers={"Cache-Control": "no-store"})

    @api
    async def quadri(request):
        return sv.quadri(request.path_params["pid"])

    @api
    async def info(request):
        return {"versione": __version__, "pid": os.getpid(),
                "pdfa": {"ghostscript": bool(pdfa.trova_gs()), "veraPDF": bool(pdfa.trova_verapdf())}}

    @api
    async def schema_(request):
        from .collegamenti.invio import TIPI_RICEVUTA
        return {"collezioni": S.COLLEZIONI, "quadri": Q.QUADRI, "predefiniti": list(Q.PREDEFINITI), "aiuti": S.AIUTI,
                "tipi_ricevuta": TIPI_RICEVUTA,
                "province_tavolari": list(Q.PROVINCE_TAVOLARI)}

    @api
    async def elenca(request):
        return sv.elenca()

    @api
    async def crea(request):
        b = await request.json()
        return sv.crea_pratica(b["titolo"], chiave=b.get("chiave"), iniziali=b.get("iniziali"))

    @api
    async def leggi(request):
        rev = request.query_params.get("revisione")
        return sv.leggi(request.path_params["pid"], int(rev) if rev else None)

    @api
    async def aggiorna(request):
        b = await request.json()
        return sv.aggiorna(request.path_params["pid"], b["revisione_attesa"], b["operazioni"],
                           chiave=b.get("chiave"), autore="utente", canale="gui")

    @api
    async def revisioni(request):
        return sv.revisioni(request.path_params["pid"])

    @api
    async def differenze(request):
        q = request.query_params
        return sv.differenze(request.path_params["pid"], int(q["da"]), int(q["a"]))

    @api
    async def ripristina(request):
        b = await request.json()
        return sv.ripristina_revisione(request.path_params["pid"], b["revisione_attesa"], b["a_revisione"])

    @api
    async def verifica(request):
        return sv.verifica(request.path_params["pid"])

    @api
    async def allegati(request):
        return sv.elenca_allegati(request.path_params["pid"])

    @api
    async def carica(request):
        form = await request.form()
        f = form["file"]
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / Path(f.filename).name
            p.write_bytes(await f.read())
            return sv.acquisisci_file(request.path_params["pid"], p, tipo_eg=form.get("tipo_eg") or None,
                                      finalita=form.get("finalita") or None, nome=Path(f.filename).name)

    @api
    async def esporta(request):
        b = await request.json() if (await request.body()) else {}
        return sv.esporta(request.path_params["pid"], cf_fornitore=b.get("cf_fornitore"), scopo=b.get("scopo", "completo"))

    @api
    async def elaborati(request):
        return sv.stato_elaborati(request.path_params["pid"])

    @api
    async def scarica_xml(request):
        xml, j = sv.file_export(request.path_params["pid"], request.query_params.get("job"))
        return Response(xml, media_type="application/xml", headers={"Content-Disposition":
                        f'attachment; filename="successione_rev{j["input"]["revisione"]}.xml"', "Cache-Control": "no-store"})

    @api
    async def stampa(request):
        from .stampa import prospetto
        pid = request.path_params["pid"]
        xml, j = sv.file_export(pid, request.query_params.get("job"))
        r = j["risultato"]
        return HTMLResponse(prospetto(xml, titolo=sv.leggi(pid)["titolo"], revisione=j["input"]["revisione"],
                                     sha256=r["xml_sha256"], completo=r["completo"]), headers={"Cache-Control": "no-store"})

    @api
    async def scarica_copia(request):
        from .collegamenti.base import DepositoArtefatti
        ad = sv._adattatore_invio("manuale")
        j = ad.job.leggi(request.path_params["cid"], "invio_copia")
        a = next(a for a, m in zip(j["risultato"]["artefatti"], j["input"]["manifest"]) if m["ruolo"] == "telematico")
        return Response(DepositoArtefatti(sv.arch).leggi(a), media_type="application/xml",
                        headers={"Content-Disposition": 'attachment; filename="copia_congelata.xml"', "Cache-Control": "no-store"})

    @api
    async def controllo_ufficiale_api(request):
        return sv.controllo_ufficiale_pratica(request.path_params["pid"])

    @api
    async def suddividi(request):
        return sv.suddividi_allegato(request.path_params["aid"])

    @api
    async def converti(request):
        return sv.prepara_pdfa(request.path_params["aid"])

    @api
    async def importa(request):
        dati = await request.body()
        if not dati:
            raise ValueError("file vuoto")
        if len(dati) > 20_000_000:
            raise ValueError("file troppo grande")
        return sv.importa_xml_telematico(dati, titolo=request.query_params.get("titolo") or None)

    async def corpo(request):
        return await request.json() if (await request.body()) else {}

    @api
    async def cf_decodifica(request):
        from .codice_fiscale import decodifica
        return decodifica(request.query_params.get("cf", ""), ruolo=request.query_params.get("ruolo"))

    @api
    async def invio_stato(request):
        return sv.invio_stato(request.path_params["pid"])

    @api
    async def invio_prepara(request):
        b = await corpo(request)
        return sv.invio_prepara(request.path_params["pid"], chiave=b.get("chiave_richiesta"))

    @api
    async def invio_conferma(request):
        b = await corpo(request)
        return sv.invio_conferma(request.path_params["cid"], str(b.get("impronta", "")), utente=str(b.get("utente") or "utente"),
                                 canale="gui")

    @api
    async def invio_trasmetti(request):
        b = await corpo(request)
        return sv.invio_trasmetti(request.path_params["cid"], str(b.get("chiave_richiesta", "")),
                                  modalita=b.get("modalita", "simulata"), canale="gui")

    @api
    async def invio_riconcilia(request):
        b = await corpo(request)
        return sv.invio_riconcilia(request.path_params["tid"], b.get("evidenze"), modalita=b.get("modalita"))

    @api
    async def ricevute(request):
        pid, tid = request.path_params["pid"], request.path_params["tid"]
        if request.method == "GET":
            return sv.ricevute_stato(pid, tid)
        q = request.query_params
        return sv.ricevuta_acquisisci(pid, tid, await request.body(), nome=q.get("nome", "ricevuta"),
                                     tipo=q["tipo"], esito=q.get("esito") or None)

    @api
    async def ricevuta_file(request):
        from .collegamenti.base import DepositoArtefatti
        pid, tid = request.path_params["pid"], request.path_params["tid"]
        stato = sv.ricevute_stato(pid, tid)
        if not any(d["job_id"] == request.path_params["rid"] for d in stato["documenti"]):
            raise NonTrovato("ricevuta non appartenente al protocollo")
        j = sv._adattatore_invio("manuale").job.leggi(request.path_params["rid"], "ricevuta_suc13")
        a = j["risultato"]["artefatti"][0]
        from urllib.parse import quote
        return Response(DepositoArtefatti(sv.arch).leggi(a), media_type="application/octet-stream",
                        headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(a["nome"], safe=""),
                                 "Cache-Control": "no-store"})

    P = "/api/pratiche/{pid}"
    return Starlette(routes=[
        Route("/api/codice-fiscale", cf_decodifica), Route("/api/importa", importa, methods=["POST"]),
        Route(P + "/invio", invio_stato), Route(P + "/invio/prepara", invio_prepara, methods=["POST"]),
        Route(P + "/ricevute/{tid}", ricevute, methods=["GET", "POST"]),
        Route(P + "/ricevute/{tid}/file/{rid}", ricevuta_file),
        Route("/api/invio/{cid}/conferma", invio_conferma, methods=["POST"]),
        Route("/api/invio/{cid}/file", scarica_copia),
        Route("/api/invio/{cid}/trasmetti", invio_trasmetti, methods=["POST"]),
        Route("/api/invio/tentativi/{tid}/riconcilia", invio_riconcilia, methods=["POST"]),
        Route("/", home), Route("/static/{nome}", statico), Route("/api/info", info),
        Route("/api/pratiche/{pid}/quadri", quadri), Route("/api/schema", schema_),
        Route("/api/pratiche", elenca), Route("/api/pratiche", crea, methods=["POST"]),
        Route(P, leggi), Route(P + "/aggiorna", aggiorna, methods=["POST"]),
        Route(P + "/revisioni", revisioni), Route(P + "/differenze", differenze),
        Route(P + "/ripristina", ripristina, methods=["POST"]),
        Route(P + "/esporta", esporta, methods=["POST"]), Route(P + "/elaborati", elaborati),
        Route(P + "/file.xml", scarica_xml), Route(P + "/stampa", stampa),
        Route(P + "/controllo-ufficiale", controllo_ufficiale_api, methods=["POST"]), Route(P + "/verifica", verifica),
        Route(P + "/allegati", allegati), Route(P + "/allegati", carica, methods=["POST"]),
        Route("/api/allegati/{aid}/pdfa", converti, methods=["POST"]),
        Route("/api/allegati/{aid}/suddividi", suddividi, methods=["POST"]),
    ])


def avvia(porta: int = 8765, apri_browser: bool = True):
    import threading
    import webbrowser
    import uvicorn
    token = secrets.token_urlsafe(24)
    app = crea_app(token=token, porta=porta)
    url = f"http://127.0.0.1:{porta}/?t={token}"
    print(f"Successioni: {url}")
    if apri_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=porta, log_level="warning", use_colors=False)
