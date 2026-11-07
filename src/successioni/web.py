"""Interfaccia locale: API JSON + pagina unica. Solo 127.0.0.1, token di sessione, controllo Host/Origin."""
from __future__ import annotations

import secrets
import os
import tempfile
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from . import __version__, pdfa, quadri as Q, schema as S
from .errori import DatiNonValidi, ErroreServizio, NonTrovato
from .servizio import Servizio

STATIC = Path(__file__).parent / "static"
TIPI = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".svg": "image/svg+xml", ".woff2": "font/woff2"}


# Limiti di dimensione dei corpi in ingresso, verificati leggendo a blocchi (il corpo non viene caricato tutto prima del controllo).
# - allegati (documenti del quadro EG, scansioni comprese): 100 MB per caricamento; il programma poi li converte, riduce o
#   suddivide per il limite telematico di 5 MB per file;
# - import di un file telematico SUC13: 60 MB (i file reali con allegati EG arrivano a 24 MB; gli allegati non si importano,
#   ma il file va letto per intero);
# - ricevute dell'Agenzia: 20 MB (stesso limite del servizio).
LIMITE_ALLEGATO = 100 * 1024 * 1024
LIMITE_IMPORT_XML = 60 * 1024 * 1024
LIMITE_RICEVUTA = 20_000_000
_CARATTERI_VIETATI = set(':*?"<>|/\\') | {chr(i) for i in range(32)}
_NOMI_RISERVATI = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


class RichiestaRifiutata(Exception):
    """Richiesta respinta prima di arrivare al servizio (dimensione, nome di file), con stato HTTP e messaggio per l'utente."""

    def __init__(self, stato: int, codice: str, messaggio: str):
        super().__init__(messaggio)
        self.stato, self.codice, self.messaggio = stato, codice, messaggio


def nome_file_valido(nome: str | None) -> str:
    """Nome del file caricato, senza cartelle; rifiuta nomi vuoti o non validi per Windows (anche «x.pdf:ads», flusso NTFS)."""
    nome = (nome or "").replace("\\", "/").rsplit("/", 1)[-1]
    if not nome.strip(" ."):
        raise RichiestaRifiutata(400, "NOME_FILE_NON_VALIDO", "nome del file mancante: scegli di nuovo il file da caricare")
    vietati = sorted({c for c in nome if c in _CARATTERI_VIETATI})
    if vietati:
        leggibili = " ".join(c if ord(c) >= 32 else "carattere di controllo" for c in vietati)
        raise RichiestaRifiutata(400, "NOME_FILE_NON_VALIDO", f"il nome del file contiene caratteri non ammessi da Windows ({leggibili}): "
                                 "rinomina il file e riprova")
    if nome.endswith((" ", ".")) or nome.split(".", 1)[0].strip().upper() in _NOMI_RISERVATI:
        raise RichiestaRifiutata(400, "NOME_FILE_NON_VALIDO", "nome del file non ammesso da Windows (nome riservato o finale con "
                                 "punto o spazio): rinomina il file e riprova")
    return nome


def _troppo_grande(massimo: int, cosa: str) -> RichiestaRifiutata:
    return RichiestaRifiutata(413, "FILE_TROPPO_GRANDE", f"{cosa} troppo grande: il limite e' {massimo // (1024 * 1024)} MB")


def _controlla_lunghezza(request: Request, massimo: int, cosa: str):
    try:
        dichiarata = int(request.headers.get("content-length") or 0)
    except ValueError:
        raise RichiestaRifiutata(400, "RICHIESTA_NON_VALIDA", "intestazione Content-Length non valida") from None
    if dichiarata > massimo:
        raise _troppo_grande(massimo, cosa)


async def corpo_limitato(request: Request, massimo: int, cosa: str) -> bytes:
    """Legge il corpo a blocchi e si ferma appena supera `massimo`."""
    _controlla_lunghezza(request, massimo, cosa)
    parti, n = [], 0
    async for blocco in request.stream():
        n += len(blocco)
        if n > massimo:
            raise _troppo_grande(massimo, cosa)
        parti.append(blocco)
    return b"".join(parti)


def richiesta_limitata(request: Request, massimo: int, cosa: str) -> Request:
    """Stessa richiesta, ma la ricezione del corpo (anche durante l'analisi multipart) si interrompe oltre `massimo`."""
    _controlla_lunghezza(request, massimo, cosa)
    ricevuti = 0

    async def receive():
        nonlocal ricevuti
        m = await request.receive()
        if m.get("type") == "http.request":
            ricevuti += len(m.get("body", b""))
            if ricevuti > massimo:
                raise _troppo_grande(massimo, cosa)
        return m
    return Request(request.scope, receive)


def strutturati_completi() -> dict:
    """Campi a scelta guidata: i codici ufficiali generati dagli XSD (`codici.py`) e, con precedenza, le voci scritte a mano."""
    from . import codici
    return {**codici.strutturati(), **S.STRUTTURATI}


def crea_app(servizio: Servizio | None = None, token: str | None = None, porta: int = 8765,
             ammetti_host_di_prova: bool = False) -> Starlette:
    sv = servizio or Servizio()
    token = token or secrets.token_urlsafe(24)
    host_ok = {f"127.0.0.1:{porta}", f"localhost:{porta}"} | ({"testserver"} if ammetti_host_di_prova else set())

    # Il cookie porta il numero di porta: due interfacce aperte (es. archivio di prova 8765 e reale 8766) non si sovrascrivono
    # il cookie a vicenda (i cookie valgono per 127.0.0.1 a prescindere dalla porta).
    cookie = f"successioni_{porta}"

    def token_valido(request: Request, query_ammessa: bool = False) -> bool:
        if secrets.compare_digest(request.cookies.get(cookie, ""), token):
            return True
        if secrets.compare_digest(request.headers.get("x-successioni-token", ""), token):
            return True
        # Token nell'indirizzo (?t=): solo sulla pagina principale (che imposta il cookie e reindirizza) e su /api/info, letto dal
        # lanciatore per sapere se la sessione e' attiva. Con l'host di prova di TestClient («testserver», mai usato da un browser
        # reale) resta accettato ovunque per le prove automatiche.
        if query_ammessa or (ammetti_host_di_prova and request.headers.get("host") == "testserver"):
            return secrets.compare_digest(request.query_params.get("t", ""), token)
        return False

    def controllo(request: Request, query_ammessa: bool = False):
        if request.headers.get("host", "") not in host_ok:
            return JSONResponse({"codice": "HOST_NON_AMMESSO"}, status_code=403)
        if not token_valido(request, query_ammessa):
            return JSONResponse({"codice": "NON_AUTORIZZATO", "messaggio": "sessione non valida: riapri il programma con "
                                 "Avvia-pratica-reale.cmd"}, status_code=401)
        if request.method not in ("GET", "HEAD"):
            origin = request.headers.get("origin")
            if origin and origin.split("://", 1)[-1] not in host_ok:
                return JSONResponse({"codice": "ORIGINE_NON_AMMESSA"}, status_code=403)
        return None

    def api(fn, query_ammessa: bool = False):
        async def w(request: Request):
            if (r := controllo(request, query_ammessa)) is not None:
                return r
            try:
                out = await fn(request)
                return out if hasattr(out, "status_code") else JSONResponse(out)
            except RichiestaRifiutata as e:
                return JSONResponse({"codice": e.codice, "messaggio": e.messaggio}, status_code=e.stato)
            except NonTrovato as e:
                return JSONResponse(e.asdict(), status_code=404)
            except ErroreServizio as e:
                return JSONResponse(e.asdict(), status_code=409 if e.codice == "CONFLITTO_REVISIONE" else 422)
            except (ValueError, KeyError, TypeError, AttributeError) as e:   # JSON malformato, campo mancante o di tipo errato
                return JSONResponse({"codice": "RICHIESTA_NON_VALIDA", "messaggio": "richiesta non valida: " + (str(e) or type(e).__name__)[:200]}, status_code=422)
        return w

    def imposta_cookie(resp):
        resp.set_cookie(cookie, token, httponly=True, samesite="strict", path="/")
        return resp

    async def home(request: Request):
        if request.headers.get("host", "") not in host_ok:
            return JSONResponse({"codice": "HOST_NON_AMMESSO"}, status_code=403)
        if "t" in request.query_params:
            # il token dell'indirizzo diventa cookie e sparisce dalla barra degli indirizzi e dalla cronologia
            if not (secrets.compare_digest(request.query_params.get("t", ""), token) or token_valido(request)):
                return pagina_non_autorizzata()
            return imposta_cookie(RedirectResponse("/", status_code=303, headers={"Cache-Control": "no-store"}))
        if not token_valido(request):
            return pagina_non_autorizzata()
        resp = HTMLResponse((STATIC / "index.html").read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})
        return imposta_cookie(resp)

    def pagina_non_autorizzata():
        return HTMLResponse("<!doctype html><meta charset=utf-8><title>Successioni</title><p>Sessione non valida o scaduta. "
                            "Apri il programma con <b>Avvia-pratica-reale.cmd</b> (o il collegamento sul Desktop): "
                            "si aprira' da solo l'indirizzo corretto.</p>", status_code=401)

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

    async def info(request):
        from .versioni import versioni
        return {"versione": __version__, "versioni": versioni(), "archivio": str(sv.arch.base), "pid": os.getpid(),
                "pdfa": {"ghostscript": bool(pdfa.trova_gs()), "veraPDF": bool(pdfa.trova_verapdf())}}
    info = api(info, query_ammessa=True)   # il lanciatore verifica la sessione con /api/info?t=...

    @api
    async def schema_(request):
        from .collegamenti.invio import TIPI_RICEVUTA
        from . import codici, etichette as E
        return {**E.per_api(), "collezioni": S.COLLEZIONI, "quadri": Q.QUADRI, "predefiniti": list(Q.PREDEFINITI), "aiuti": {**S.AIUTI, **S.AIUTI_INTERFACCIA},
                "strutturati": strutturati_completi(), "suggerimenti": codici.suggerimenti(), "tipi_ricevuta": TIPI_RICEVUTA,
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
        form = await richiesta_limitata(request, LIMITE_ALLEGATO, "documento").form()
        try:
            f = form.get("file")
            if f is None or isinstance(f, str):
                raise RichiestaRifiutata(400, "FILE_MANCANTE", "nessun file nella richiesta: scegli il file da caricare")
            nome = nome_file_valido(f.filename)
            with tempfile.TemporaryDirectory() as t:
                p = Path(t) / nome
                with p.open("wb") as out:
                    while blocco := await f.read(1024 * 1024):
                        out.write(blocco)
                if p.stat().st_size == 0:
                    raise RichiestaRifiutata(400, "FILE_VUOTO", f"il file «{nome}» e' vuoto")
                return sv.acquisisci_file(request.path_params["pid"], p, tipo_eg=form.get("tipo_eg") or None,
                                          finalita=form.get("finalita") or None, nome=nome)
        finally:
            await form.close()

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
                        f'attachment; filename="successione_rev{j["input"]["revisione"]}{"" if j["risultato"].get("completo") else "_bozza"}.xml"', "Cache-Control": "no-store"})

    @api
    async def stampa(request):
        from .stampa import prospetto
        pid = request.path_params["pid"]
        xml, j = sv.file_export(pid, request.query_params.get("job"))
        r = j["risultato"]
        return HTMLResponse(prospetto(xml, titolo=sv.leggi(pid)["titolo"], revisione=j["input"]["revisione"],
                                     sha256=r["xml_sha256"], completo=r["completo"]), headers={"Cache-Control": "no-store"})

    @api
    async def prospetto_cliente_api(request):
        """Riepilogo stampabile per gli eredi, letto dall'ultimo file generato (stessi importi della dichiarazione)."""
        import json as _json
        from . import impostazioni
        from .prospetto_cliente import html as prospetto_html
        pid = request.path_params["pid"]
        xml, j = sv.file_export(pid)
        stato = sv.stato_elaborati(pid)["export"]
        try:
            conf = _json.loads(impostazioni.file_configurazione().read_text(encoding="utf-8-sig"))
            studio = impostazioni.preferenze_interfaccia(conf if isinstance(conf, dict) else {}).get("nome_studio", "")
        except (OSError, ValueError, DatiNonValidi):
            studio = ""
        return HTMLResponse(prospetto_html(xml, titolo=sv.leggi(pid)["titolo"], studio=studio, revisione=j["input"]["revisione"],
                                           completo=bool(j["risultato"].get("completo")), obsoleto=stato.get("stato") == "obsoleto"),
                            headers={"Cache-Control": "no-store"})

    @api
    async def brogliaccio_csv(request):
        """Brogliaccio dei beni e delle quote in CSV per Excel (voce 23 dell'analisi del 07/11/2026)."""
        from . import brogliaccio as BR
        d = sv.leggi(request.path_params["pid"])
        return Response(BR.csv_testo(d["dati"]).encode("utf-8"), media_type="text/csv; charset=utf-8", headers={
            "Content-Disposition": f'attachment; filename="brogliaccio_rev{d["revisione"]}.csv"', "Cache-Control": "no-store"})

    @api
    async def brogliaccio_html(request):
        from . import brogliaccio as BR
        d = sv.leggi(request.path_params["pid"])
        return HTMLResponse(BR.html(d["dati"], titolo=d["titolo"], revisione=d["revisione"]), headers={"Cache-Control": "no-store"})

    @api
    async def diagnosi_api(request):
        from . import strumenti
        return strumenti.diagnosi(sv.arch)

    @api
    async def pulizia_api(request):
        from . import pulizia
        return pulizia.pulisci(sv.arch.base, forzata=True)

    @api
    async def backup_crea(request):
        return sv.backup_archivio("manuale")

    @api
    async def backup_elenco(request):
        return sv.elenco_backup()

    @api
    async def scarica_dcm(request):
        dcm, m = sv.file_controllato_dcm(request.path_params["pid"])
        return Response(dcm, media_type="application/octet-stream", headers={"Content-Disposition":
                        f'attachment; filename="{m["nome"] or "file_controllato.dcm"}"', "Cache-Control": "no-store"})

    @api
    async def stampa_modello_api(request):
        return sv.stampa_modello(request.path_params["pid"])

    @api
    async def scarica_stampa_modello(request):
        pdf, j = sv.file_stampa_modello(request.path_params["pid"])
        return Response(pdf, media_type="application/pdf", headers={"Content-Disposition":
                        f'inline; filename="modello_successione_{j["id"]}.pdf"', "Cache-Control": "no-store"})

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
    async def diagnostico_controllo(request):
        """Esito del controllo eseguito a mano con il programma dell'Agenzia: .dgn, _logSchema.xml e .wri (facoltativo)."""
        form = await richiesta_limitata(request, 3 * LIMITE_RICEVUTA, "esito del controllo").form()
        try:
            async def leggi(campo, obbligatorio=True):
                f = form.get(campo)
                if f is None or isinstance(f, str):
                    if obbligatorio:
                        raise RichiestaRifiutata(400, "FILE_MANCANTE", f"manca il file «{campo}» dell'esito del controllo")
                    return None
                nome_file_valido(f.filename)
                return await f.read()
            return sv.registra_diagnostico_controllo(
                request.path_params["pid"], dgn=await leggi("dgn"), log_schema=await leggi("log_schema"),
                wri=await leggi("wri", False), conferma_associazione=form.get("conferma_associazione") in ("1", "true", "on"))
        finally:
            await form.close()

    @api
    async def suddividi(request):
        return sv.suddividi_allegato(request.path_params["aid"])

    @api
    async def converti(request):
        return sv.prepara_pdfa(request.path_params["aid"], sostituisci_originale=True)

    @api
    async def elimina_allegato_api(request):
        return sv.elimina_allegato(request.path_params["aid"])

    @api
    async def riordina_allegati_api(request):
        return sv.riordina_allegati(request.path_params["pid"])

    @api
    async def valori_catastali_api(request):
        return sv.valori_catastali(request.path_params["pid"])

    @api
    async def anteprima_quadri_api(request):
        return sv.anteprima_quadri(request.path_params["pid"])

    @api
    async def importa(request):
        dati = await corpo_limitato(request, LIMITE_IMPORT_XML, "file da importare")
        if not dati:
            raise ValueError("file vuoto")
        return sv.importa_xml_telematico(dati, titolo=request.query_params.get("titolo") or None)

    @api
    async def impostazioni_leggi(request):
        from . import impostazioni
        return impostazioni.stato()

    @api
    async def impostazioni_salva(request):
        from . import impostazioni
        b = await request.json()
        return impostazioni.salva(b.get("modifiche", {}), interfaccia=b.get("interfaccia"), profilo=b.get("profilo"),
                                   preferenze_nuove=b.get("preferenze"))

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
        nome = nome_file_valido(q.get("nome") or "ricevuta")
        return sv.ricevuta_acquisisci(pid, tid, await corpo_limitato(request, LIMITE_RICEVUTA, "ricevuta"), nome=nome,
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
    import threading
    from .pulizia import pulisci_silenziosa
    threading.Thread(target=pulisci_silenziosa, args=(sv.arch.base,), daemon=True, name="pulizia-avvio").start()
    return Starlette(routes=[
        Route("/api/codice-fiscale", cf_decodifica), Route("/api/importa", importa, methods=["POST"]),
        Route("/api/pulizia", pulizia_api, methods=["POST"]), Route("/api/diagnosi", diagnosi_api, methods=["POST"]), Route("/api/backup", backup_elenco), Route("/api/backup", backup_crea, methods=["POST"]),
        Route("/api/impostazioni", impostazioni_leggi), Route("/api/impostazioni", impostazioni_salva, methods=["POST"]),
        Route(P + "/invio", invio_stato), Route(P + "/invio/prepara", invio_prepara, methods=["POST"]),
        Route(P + "/ricevute/{tid}", ricevute, methods=["GET", "POST"]),
        Route(P + "/ricevute/{tid}/file/{rid}", ricevuta_file),
        Route("/api/invio/{cid}/conferma", invio_conferma, methods=["POST"]),
        Route("/api/invio/{cid}/file", scarica_copia),
        Route("/api/invio/{cid}/trasmetti", invio_trasmetti, methods=["POST"]),
        Route("/api/invio/tentativi/{tid}/riconcilia", invio_riconcilia, methods=["POST"]),
        Route("/", home), Route("/static/{nome}", statico), Route("/api/info", info), Route("/favicon.ico", lambda richiesta: Response((STATIC / "logo.svg").read_bytes(), media_type="image/svg+xml")),
        Route("/api/pratiche/{pid}/quadri", quadri), Route("/api/schema", schema_),
        Route("/api/pratiche", elenca), Route("/api/pratiche", crea, methods=["POST"]),
        Route(P, leggi), Route(P + "/aggiorna", aggiorna, methods=["POST"]),
        Route(P + "/revisioni", revisioni), Route(P + "/differenze", differenze),
        Route(P + "/ripristina", ripristina, methods=["POST"]),
        Route(P + "/esporta", esporta, methods=["POST"]), Route(P + "/elaborati", elaborati),
        Route(P + "/file.xml", scarica_xml), Route(P + "/stampa", stampa), Route(P + "/prospetto-cliente", prospetto_cliente_api),
        Route(P + "/brogliaccio.csv", brogliaccio_csv), Route(P + "/brogliaccio", brogliaccio_html),Route(P + "/stampa-modello", stampa_modello_api, methods=["POST"]),
        Route(P + "/stampa-modello.pdf", scarica_stampa_modello), Route(P + "/file.dcm", scarica_dcm),
        Route(P + "/controllo-ufficiale", controllo_ufficiale_api, methods=["POST"]),
        Route(P + "/controllo-ufficiale/diagnostico", diagnostico_controllo, methods=["POST"]), Route(P + "/verifica", verifica),
        Route(P + "/allegati", allegati), Route(P + "/allegati", carica, methods=["POST"]),
        Route("/api/allegati/{aid}/pdfa", converti, methods=["POST"]),
        Route("/api/allegati/{aid}/elimina", elimina_allegato_api, methods=["POST"]),
        Route(P + "/allegati/riordina", riordina_allegati_api, methods=["POST"]),
        Route(P + "/anteprima-quadri", anteprima_quadri_api),
        Route(P + "/valori-catastali", valori_catastali_api),
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
