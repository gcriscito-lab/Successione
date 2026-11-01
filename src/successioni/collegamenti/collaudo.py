"""Comandi di collaudo riprendibili dei collegamenti (docs/COLLAUDO_RIPRENDIBILE.md).

    python -m successioni.collegamenti.collaudo ambiente
    python -m successioni.collegamenti.collaudo scarica-jar --dest CARTELLA
    python -m successioni.collegamenti.collaudo controllo --xml FILE [--dcm] [--archivio CARTELLA]
    python -m successioni.collegamenti.collaudo registra-diagnostico --job ID --dgn F.dgn --log F_logSchema.xml [--wri F.wri]
    python -m successioni.collegamenti.collaudo catasto-avvia --pratica ID --cf CODICEFISCALE
    python -m successioni.collegamenti.collaudo catasto-registra --job ID --file FILE --formato NOME
    python -m successioni.collegamenti.collaudo riconcilia --tentativo ID (--protocollo P --verificato-su TESTO | --esi F.esi)
    python -m successioni.collegamenti.collaudo ricevuta --protocollo P --tipo T [--esito E] --file F
    python -m successioni.collegamenti.collaudo stato --job ID

Ogni comando stampa un JSON con `esito` (passato | fallito | da_collaudare | simulazione) e scrive nel medesimo
archivio dell'app (SUCCESSIONI_DATA o --archivio). Nessun comando trasmette dichiarazioni o legge credenziali.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from ..archivio import Archivio
from .base import RegistroJob, sha256_bytes
from .controllo import ConfigControllo, ControlloJar, ControlloManuale, controllo_ufficiale, diagnostica_ambiente, \
    jar_richiesti, percorso_jnlp

CODEBASE = "https://jws.agenziaentrate.it/jws/registro/2013/"
# Impronte dei JAR scaricati dal codebase del JNLP il 2026-11-01 (controllo SUC13 2.3.1 dell'11/03/2026).
# Un'impronta diversa indica una versione diversa (es. aggiornamento uffici), non necessariamente un errore.
IMPRONTE_20261101 = {
    "controlliXMLREG2013.jar": "0b42dfc37e673a4cee65f696bbf84612fee0c898a7a3b0456b661d17dece6a10",
    "ResSUC13.jar": "2332c71fb3f6db61ed7fe68e7f2f56c18e85015c96aea3c7df905d58dfaf24b5",
    "print-model-1.2.jar": "a54591289504939e59cf1c3285f3002a1cb3296e65a7fca4d412fc216ef2ff29",
    "XMLConverterREG.jar": "2b860db1872937e45be4ec6ff849532c0456a88fe57bb1065c4ad7254cc4d4b5",
    "XMLConverter_PropertiesREG2013.jar": "e396845477cbc0b7628d75d46782748ec5d1452380e21a59af810ed95709f712",
    "esito.jar": "00202a3a7a8aa8462d7f74e66af9e56a276e3f44b4bc40c6aef5de2cb2429e12",
    "gson-2.8.9.jar": "cfd7d9ea81a8114325f6d42d0d81570334affce6c02739ce9fba695477d8beb2",
    "Supporto.jar": "2695c093b2f7542c695ebecbeba47d2467c5d27ba20c01f295c33235129172ca",
    "checkCF_PIVA.jar": "6069cee20d98e8d23e46c097abc9072d7f9256902c354f74b723fe4c3c7238be",
    "SUCdom.jar": "f6977bf664ae13650128f264ac3fc1cd2b561e6e7c9d58102efe5f1fffe84c55",
    "converter-1.1.jar": "ad1a0d583aaed0150b135a7ae6d188b3c02139f8258c56fc733cba581e04f3f3",
    "suc-converter-1.0.jar": "63b6031083b274a1ed4450326082d1a0bc084eafc0bc9b79ed13f91037e2ac07",
    "jdom.jar": "ee8f26c77772d7a9704f6600554e8daa7f70242ae6ddc779f74da0e8be0afafa",
    "xmlbeans-2.3.0.jar": "27be44d92d51602cb29127b09ffb4235d378721a87e62856e5396a8e3a27e552",
    "file-detector-1.0.jar": "0369ab843995bd30f9a827960969b6bd55ebab7b45a10231d353a0aa229baf21",
}


def _href_jar(jnlp: Path) -> list[str]:
    import xml.etree.ElementTree as ET
    return [j.get("href") for j in ET.parse(jnlp).getroot().iter("jar") if j.get("href")]


def scarica_jar(dest: Path, codebase: str = CODEBASE) -> list[dict]:
    """Scarica i JAR elencati nel JNLP ufficiale dal suo codebase (su richiesta esplicita dell'utente)."""
    dest.mkdir(parents=True, exist_ok=True)
    out = []
    for href in _href_jar(percorso_jnlp()):
        url = urllib.parse.urljoin(codebase, href)
        nome = Path(href).name
        with urllib.request.urlopen(url, timeout=120) as r:  # noqa: S310 - URL dal JNLP ufficiale
            dati = r.read()
        (dest / nome).write_bytes(dati)
        h = sha256_bytes(dati)
        rif = IMPRONTE_20261101.get(nome)
        out.append({"nome": nome, "url": url, "sha256": h, "bytes": len(dati),
                    "come_al_20261101": h == rif if rif else None})
    return out


def _arch(a) -> Archivio:
    return Archivio(a.archivio) if a.archivio else Archivio()


def _stampa(obj) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=1, default=str) + "\n")


def _riassunto_controllo(arch: Archivio, job_id: str) -> dict:
    j = RegistroJob(arch).leggi(job_id)
    r = j["risultato"]
    return {"job_id": job_id, "stato": j["stato"], "esito": r.get("esito"), "stato_controllo": r.get("stato_controllo"),
            "motivi": r.get("motivi"), "avvertenze": r.get("avvertenze"), "versione_controllo": r.get("versione_controllo"),
            "data_versione": r.get("data_versione"), "riepilogo": r.get("riepilogo"),
            "xml_sha256": j["input"].get("xml_sha256"), "ambiente": {k: (r.get("ambiente") or {}).get(k) for k in
                                                                     ("java", "java_versione", "os", "cartella_jar")},
            "artefatti": [{k: a[k] for k in ("ruolo", "nome", "sha256", "percorso")} for a in r.get("artefatti", [])],
            "azione_richiesta": r.get("azione_richiesta"),
            "rapporto": [f"{b['simbolo']} {b['testo']}" for b in (r.get("rapporto") or {}).get("blocchi", [])]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="successioni.collegamenti.collaudo", description=__doc__.split("\n\n")[0])
    ap.add_argument("--archivio", help="cartella dati dell'app (predefinita: SUCCESSIONI_DATA o cartella utente)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ambiente")
    s = sub.add_parser("scarica-jar")
    s.add_argument("--dest", required=True)
    s = sub.add_parser("controllo")
    s.add_argument("--xml", required=True)
    s.add_argument("--dcm", action="store_true", help="chiede anche il file controllato .dcm")
    s.add_argument("--pratica")
    s = sub.add_parser("registra-diagnostico")
    s.add_argument("--job", required=True)
    s.add_argument("--dgn", required=True)
    s.add_argument("--log", required=True)
    s.add_argument("--wri")
    s.add_argument("--ambiente-dichiarato", default="{}")
    s.add_argument("--conferma-associazione", action="store_true",
                   help="il diagnostico non contiene riferimenti verificabili: l'utente dichiara che e' di quel file")
    s = sub.add_parser("catasto-avvia")
    s.add_argument("--pratica", required=True)
    s.add_argument("--cf", required=True)
    s.add_argument("--catasto", default="entrambi")
    s = sub.add_parser("catasto-registra")
    s.add_argument("--job", required=True)
    s.add_argument("--file", required=True)
    s.add_argument("--formato", required=True)
    s = sub.add_parser("riconcilia")
    s.add_argument("--tentativo", required=True)
    s.add_argument("--protocollo")
    s.add_argument("--verificato-su")
    s.add_argument("--esi")
    s = sub.add_parser("ricevuta")
    s.add_argument("--protocollo", required=True)
    s.add_argument("--tipo", required=True)
    s.add_argument("--esito")
    s.add_argument("--file", required=True)
    s.add_argument("--pratica")
    s = sub.add_parser("stato")
    s.add_argument("--job", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "ambiente":
        cfg = ConfigControllo.da_ambiente()
        _stampa({"controllo_suc13": diagnostica_ambiente(cfg), "jar_richiesti": jar_richiesti()})
    elif a.cmd == "scarica-jar":
        _stampa(scarica_jar(Path(a.dest)))
    elif a.cmd == "controllo":
        arch = _arch(a)
        ad = controllo_ufficiale(arch)
        kw = {"pratica_id": a.pratica}
        r = ad.esegui(a.xml, produci_dcm=a.dcm, **kw) if isinstance(ad, ControlloJar) else ad.esegui(a.xml, **kw)
        _stampa(_riassunto_controllo(arch, r.job_id))
    elif a.cmd == "registra-diagnostico":
        arch = _arch(a)
        r = ControlloManuale(arch).registra_diagnostico(
            a.job, dgn=Path(a.dgn).read_bytes(), log_schema=Path(a.log).read_bytes(),
            wri=Path(a.wri).read_bytes() if a.wri else None, ambiente_dichiarato=json.loads(a.ambiente_dichiarato),
            conferma_associazione=a.conferma_associazione)
        _stampa(_riassunto_controllo(arch, r.job_id))
    elif a.cmd in ("catasto-avvia", "catasto-registra"):
        from .catasto import CatastoEntratelAdattatore
        ad = CatastoEntratelAdattatore(_arch(a))
        if a.cmd == "catasto-avvia":
            r = ad.avvia(a.pratica, {"soggetto_cf": a.cf, "catasto": a.catasto})
        else:
            r = ad.registra_originale(a.job, Path(a.file).read_bytes(), formato=a.formato, fonte=Path(a.file).name)
        _stampa(r.asdict())
    elif a.cmd == "riconcilia":
        from .invio import InvioAdattatore
        ev = {}
        if a.protocollo:
            ev = {"protocollo": a.protocollo, "verificato_su": a.verificato_su}
        elif a.esi:
            ev = {"esi": Path(a.esi).read_text(encoding="utf-8", errors="replace")}
        _stampa(InvioAdattatore(_arch(a)).riconcilia(a.tentativo, evidenze=ev).asdict())
    elif a.cmd == "ricevuta":
        from .invio import InvioAdattatore
        p = Path(a.file)
        _stampa(InvioAdattatore(_arch(a)).associa(protocollo=a.protocollo, tipo=a.tipo, esito=a.esito,
                                                  contenuto=p.read_bytes(), nome=p.name, pratica_id=a.pratica).asdict())
    elif a.cmd == "stato":
        _stampa(RegistroJob(_arch(a)).leggi(a.job))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
