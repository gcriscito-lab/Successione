"""Interfaccia locale: API JSON + pagina unica. Solo 127.0.0.1, token di sessione, controllo Host/Origin."""
from __future__ import annotations

import secrets
import tempfile
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from . import __version__, pdfa, schema as S
from .errori import ErroreServizio, NonTrovato
from .servizio import Servizio

PAGINA = (Path(__file__).parent / "static" / "index.html")


def crea_app(servizio: Servizio | None = None, token: str | None = None, porta: int = 8765) -> Starlette:
    sv = servizio or Servizio()
    token = token or secrets.token_urlsafe(24)
    host_ok = {f"127.0.0.1:{porta}", f"localhost:{porta}", "testserver"}

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
        return w

    async def home(request: Request):
        if (r := controllo(request)) is not None:
            return r
        resp = HTMLResponse(PAGINA.read_text(encoding="utf-8"))
        resp.set_cookie("successioni", token, httponly=True, samesite="strict")
        return resp

    @api
    async def info(request):
        return {"versione": __version__, "pdfa": {"ghostscript": bool(pdfa.trova_gs()), "veraPDF": bool(pdfa.trova_verapdf())}}

    @api
    async def schema_(request):
        return {"collezioni": S.COLLEZIONI}

    @api
    async def elenca(request):
        return sv.elenca()

    @api
    async def crea(request):
        b = await request.json()
        return sv.crea_pratica(b["titolo"], chiave=b.get("chiave"))

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
    async def converti(request):
        return sv.prepara_pdfa(request.path_params["aid"])

    P = "/api/pratiche/{pid}"
    return Starlette(routes=[
        Route("/", home), Route("/api/info", info), Route("/api/schema", schema_),
        Route("/api/pratiche", elenca), Route("/api/pratiche", crea, methods=["POST"]),
        Route(P, leggi), Route(P + "/aggiorna", aggiorna, methods=["POST"]),
        Route(P + "/revisioni", revisioni), Route(P + "/differenze", differenze),
        Route(P + "/ripristina", ripristina, methods=["POST"]), Route(P + "/verifica", verifica),
        Route(P + "/allegati", allegati), Route(P + "/allegati", carica, methods=["POST"]),
        Route("/api/allegati/{aid}/pdfa", converti, methods=["POST"]),
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
    uvicorn.run(app, host="127.0.0.1", port=porta, log_level="warning")
