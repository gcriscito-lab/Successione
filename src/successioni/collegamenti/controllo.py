"""Controllo ufficiale SUC13: esecuzione del componente dell'Agenzia e lettura del diagnostico originale.

MODALITA' PROVATA (2026-11-01, container Linux, OpenJDK 21; vedi docs/COLLEGAMENTI.md §1):
il modulo di controllo pubblicato con `ControlliSUC13.jnlp` (versione 2.3.1 dell'11/03/2026) si esegue senza GUI
chiamando la classe `it.finanze.entrate.sco.main.MSUC13` con due argomenti, come fa la sua interfaccia AWT
(`AControlliSUC2013.run()` -> `invokeClassWithParamArrStr("MSUC13","main", {input, uscita[, dcm]})`):

    java -Djava.awt.headless=true -cp <jar del JNLP> it.finanze.entrate.sco.main.MSUC13 in/F.xml out/F.xml

Produce `out/F.dgn` (diagnostico a record fissi), `out/F_logSchema.xml` (elemento `EsitoFornitura` di
esitoFornitura_v3.xsd) e, con il terzo argomento, il file controllato `.dcm` (solo se la fornitura e' trasmissibile:
`Main.elabora` -> `DcmService.createDcm`; osservato il 2026-11-01 sul caso positivo locale A10,
tests/fixture_telematico/controllo_20261101/manifest.json; prova su Desktop Telematico da fare). Il rapporto leggibile `.wri` lo
produce la classe ufficiale `it.finanze.entrate.sco.common2013.VisualXml` con argomenti `{F.dgn, "1"}` (elenco completo),
come fa `AControlliSUC2013.visualizza()`.

Il tracciato del `.dgn` e' letto SOLO nelle parti deducibili dal componente stesso (classe
`it.finanze.entrate.sco.generale2013.Visual` di controlliXMLREG2013.jar, metodi `impostaAsterischi`,
`decodificaDiagnostico`, `coda`); i testi dei messaggi non vengono ricostruiti: fanno fede il `.wri` e il `.dgn`
originali, conservati come artefatti.

Esiti: componente reale eseguito -> `passato` (controllo positivo) / `fallito` (negativo o esecuzione non conclusa,
con diagnosi); componente non configurato -> `da_collaudare` con passaggio manuale tracciato; esecutore iniettato
(test) -> sempre `simulazione`.
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..archivio import Archivio
from ..errori import DatiNonValidi, NonTrovato
from .base import (DepositoArtefatti, Esito, RegistroJob, RisultatoAdattatore, TransizioneNonAmmessa, risultato_da_job,
                   sha256_bytes, sha256_file)

TIPO_JOB = "controllo_ufficiale"
CLASSE_CONTROLLO = "it.finanze.entrate.sco.main.MSUC13"
CLASSE_RAPPORTO = "it.finanze.entrate.sco.common2013.VisualXml"
ENV_JAVA = "SUCCESSIONI_JAVA"
ENV_JAR = "SUCCESSIONI_CONTROLLI_SUC13"
ENV_TIMEOUT = "SUCCESSIONI_CONTROLLI_TIMEOUT"
NS_ESITO = "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:common:v3"
FONTE_DGN = ("controlliXMLREG2013.jar (ControlliSUC13.jnlp, controllo SUC13 2.3.1 dell'11/03/2026), classe "
             "it.finanze.entrate.sco.generale2013.Visual: impostaAsterischi/decodificaDiagnostico/coda (javap)")
FONTE_ESITO_XSD = "esitoFornitura_v3.xsd (fonti/Specifiche tecniche/SUC13_20250702/common/xsd), elemento EsitoFornitura"

STATI_TERMINALI = ("completato", "errore_esecuzione")


def _radice_fonti() -> Path:
    env = os.environ.get("SUCCESSIONI_FONTI")
    return Path(env) if env else Path(__file__).resolve().parents[3] / "fonti"


def percorso_jnlp() -> Path:
    return _radice_fonti() / "Programma e controlli" / "ControlliSUC13.jnlp"


def percorso_xsd_esito() -> Path:
    return _radice_fonti() / "Specifiche tecniche" / "SUC13_20250702" / "common" / "xsd" / "esitoFornitura_v3.xsd"


def jar_richiesti(jnlp: Path | str | None = None) -> list[str]:
    """Nomi dei JAR elencati in <resources> del JNLP ufficiale (i commentati sono esclusi), nell'ordine dato."""
    radice = ET.parse(jnlp or percorso_jnlp()).getroot()
    return [Path(j.get("href", "")).name for j in radice.iter("jar") if j.get("href")]


# ------------------------------------------------------------------------------- lettura del .dgn
# Gravita' (record[17:19]) -> simbolo e significato: Visual.impostaAsterischi; legenda del .wri ufficiale.
SIGNIFICATO = {
    "(****)": "errore che determina lo scarto dell'intera fornitura",
    "(***)": "errore bloccante: scarto della dichiarazione, non trasmissibile",
    "(***C)": "errore rilevante: scarto della dichiarazione salvo conferma dei dati nel software di compilazione",
    "(**E)": "errore rilevante (solo mod. 730)",
    "(**)": "segnalazione per cui e' stata richiesta la conferma",
    "(*)": "anomalia di entita' ridotta: la dichiarazione puo' essere trasmessa",
    "": "gravita' non decodificata",
}


def simbolo_gravita(g: int) -> str:
    """Replica della regola di Visual.impostaAsterischi (il caso 12 vale solo per il modello 730)."""
    if g == 4:
        return "(*)"
    if g == 8:
        return "(**)"
    if g == 12:
        return "(**E)"
    if g == 14:
        return "(***C)"
    if 14 < g < 24:
        return "(***)"
    if g >= 24:
        return "(****)"
    return ""


_RIEPILOGO_DGN = {  # Visual.coda: posizioni del record di tipo 9
    "elaborate": (1, 7), "senza_segnalazioni": (7, 13), "con_anomalia": (13, 19), "con_errori_confermati": (19, 25),
    "escluse_assistenza": (25, 31), "scartate_non_rispondenza": (31, 37), "scartate_errori_bloccanti": (37, 43),
}


def decodifica(b: bytes) -> str:
    """Testo dei file del componente: UTF-8 se valido, altrimenti cp1252 (Java su Windows), mai errori."""
    for enc in ("utf-8", "cp1252"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("latin-1")


def _intero(s: str) -> int | None:
    s = s.strip()
    return int(s) if s.isdigit() else None


def leggi_dgn(testo: str) -> dict:
    """Legge il diagnostico a record fissi (106 caratteri con il fine riga). Non interpreta i codici messaggio."""
    out: dict = {"intestazione": [], "versione_controllo": None, "data_versione": None, "file_controllato": None,
                 "diagnostici": [], "riepilogo": None, "righe_non_riconosciute": [], "fonte": FONTE_DGN}
    for riga in testo.splitlines():
        if not riga.strip():
            continue
        tipo = riga[0]
        if tipo == "0":
            out["intestazione"].append(riga.rstrip())
            m = re.search(r"(\d+\.\d+\.\d+)\s+(\d{2}/\d{2}/\d{4})", riga)
            if m and not out["versione_controllo"]:
                out["versione_controllo"], out["data_versione"] = m.group(1), m.group(2)
            elif riga[1:17] == "*" * 16:
                out["file_controllato"] = riga[17:].strip() or None
        elif tipo == "1" and len(riga) >= 23:
            g = _intero(riga[17:19])
            simb = simbolo_gravita(g) if g is not None else ""
            out["diagnostici"].append({
                "soggetto": riga[1:17].strip(), "gravita": g, "simbolo": simb, "significato": SIGNIFICATO[simb],
                "codice": riga[19:23].strip(), "campo": riga[23:39].strip(),
                "valori": [v for v in (riga[39:55].strip(), riga[55:71].strip(), riga[71:84].strip(),
                                       riga[84:100].strip()) if v],
                "identificativo": riga[100:105].strip() or None, "record": riga.rstrip(),
            })
        elif tipo == "9":
            out["riepilogo"] = {k: _intero(riga[a:b]) for k, (a, b) in _RIEPILOGO_DGN.items()}
            out["riepilogo"]["solo_entratel"] = riga[85:86] == "1"
        else:
            out["righe_non_riconosciute"].append(riga.rstrip())
    return out


# ------------------------------------------------------------------------- lettura del _logSchema.xml
def _testo(e, nome):
    x = e.find(f"{{{NS_ESITO}}}{nome}")
    return x.text if x is not None else None


def _bool(v):
    return None if v is None else v.strip() == "true"


def _diag(e) -> dict:
    d = {k: _testo(e, k) for k in ("ReturnCode", "Message", "MessageKey", "Path", "Line", "Col",
                                   "FieldName", "FieldValue", "CalcValue")}
    return {k: v for k, v in d.items() if v is not None}


_SCHEMA_ESITO = None


def _schema_esito():
    """Compila esitoFornitura_v3.xsd delle fonti (sola lettura).

    Lo schema importa due volte lo stesso namespace common:v2 (typesDati_v2.xsd e fornitura_v2.xsd); libxml2 considera
    solo il primo import e non trova `Identificativo_Type`. Un involucro in memoria importa prima fornitura_v2.xsd
    (che include typesDati_v2.xsd) e poi lo schema degli esiti: i file ufficiali non vengono modificati.
    """
    global _SCHEMA_ESITO
    if _SCHEMA_ESITO is None:
        from lxml import etree
        d = percorso_xsd_esito().parent
        involucro = (
            '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
            f'<xs:import namespace="urn:www.agenziaentrate.gov.it:specificheTecniche:common:v2" '
            f'schemaLocation="{(d / "fornitura_v2.xsd").as_uri()}"/>'
            f'<xs:import namespace="{NS_ESITO}" schemaLocation="{percorso_xsd_esito().as_uri()}"/>'
            '</xs:schema>')
        _SCHEMA_ESITO = etree.XMLSchema(etree.fromstring(involucro.encode()))
    return _SCHEMA_ESITO


def leggi_esito_fornitura(xml: bytes, *, valida: bool = True) -> dict:
    """Legge `EsitoFornitura` (esitoFornitura_v3.xsd). Con `valida` controlla il file sullo schema delle fonti."""
    from lxml import etree

    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    doc = etree.fromstring(xml, parser)
    out: dict = {"fonte": FONTE_ESITO_XSD, "conforme_xsd": None, "errori_xsd": []}
    if valida and percorso_xsd_esito().exists():
        try:
            schema = _schema_esito()
            out["conforme_xsd"] = schema.validate(doc)
            out["errori_xsd"] = [f"{e.line}: {e.message}" for e in schema.error_log][:20]
        except etree.XMLSchemaParseError as e:  # pragma: no cover - dipende dalla versione di libxml2
            out["errori_xsd"] = [f"schema non compilabile: {e}"]
    if doc.tag != f"{{{NS_ESITO}}}EsitoFornitura":
        raise DatiNonValidi("il file non contiene un elemento EsitoFornitura", radice=doc.tag)
    out["identificativo_fornitura"] = _testo(doc, "IdentificativoFornitura")
    ex = doc.find(f"{{{NS_ESITO}}}EsitoXsd")
    if ex is not None:
        diag = []
        for sez in ("EsitoIntestazione", "EsitoDatiGenerali", "EsitoDocumento"):
            for s in ex.findall(f"{{{NS_ESITO}}}{sez}"):
                for d in s.findall(f"{{{NS_ESITO}}}DiagnosticoXsd"):
                    diag.append({"sezione": sez, "identificativo": _testo(s, "Identificativo"), **_diag(d)})
        out["esito_xsd"] = {"identificativo_xsd": _testo(ex, "IdentificativoXsd"),
                            "ben_formato": _bool(_testo(ex, "WellFormed")), "valido": _bool(_testo(ex, "Valid")),
                            "completo": _bool(_testo(ex, "Completo")), "diagnostici": diag}
    out["esito_hash"] = _bool(_testo(doc, "EsitoHash"))
    ec = doc.find(f"{{{NS_ESITO}}}EsitoControllo")
    if ec is not None:
        docs = [{"identificativo": _testo(d, "Identificativo"), "stato": _testo(d, "Stato"),
                 "diagnostici": [_diag(x) for x in d.findall(f"{{{NS_ESITO}}}DiagnosticoControllo")]}
                for d in ec.findall(f"{{{NS_ESITO}}}EsitoDocumento")]
        rp = ec.find(f"{{{NS_ESITO}}}Riepilogo")
        out["esito_controllo"] = {"documenti": docs, "riepilogo": None if rp is None else {
            k: _intero(_testo(rp, k) or "") for k in ("DocElaborati", "DocCorretti", "DocScartati", "DocNoRisp",
                                                      "DocConfermati", "DocSegnalati")}}
    return out


# ------------------------------------------------------------------------------ lettura del .wri
_RIGHE_WRI = {
    "elaborate": r"Totale dichiarazioni elaborate\s*:\s*(\d+)",
    "scartate_errori_bloccanti": r"scartate per errori bloccanti\s*:\s*(\d+)",
    "scartate_non_rispondenza": r"scartate per non rispondenza\s*:\s*(\d+)",
    "con_errori_confermati": r"con errori confermati\s*:\s*(\d+)",
    "con_anomalia": r"con segnalazione di anomalia\s*:\s*(\d+)",
    "senza_segnalazioni": r"senza segnalazioni\s*:\s*(\d+)",
}
_MARCATORE = re.compile(r"^\((\*{1,4}|\*\*\*C|\*\*E)\)\s*$")


def leggi_wri(testo: str) -> dict:
    """Riepilogo e blocchi (simbolo + testo) del rapporto leggibile prodotto da VisualXml. Il testo resta originale."""
    rp = {}
    for k, rx in _RIGHE_WRI.items():
        m = re.search(rx, testo)
        rp[k] = int(m.group(1)) if m else None
    blocchi, corrente = [], None
    inizio = testo.find("Dichiarazione relativa a:")
    for riga in (testo[inizio:] if inizio >= 0 else "").splitlines():
        if _MARCATORE.match(riga.strip()):
            corrente = {"simbolo": riga.strip(), "testo": []}
            blocchi.append(corrente)
        elif corrente is not None:
            if riga.strip().startswith(("La dichiarazione", "*****", "=====")):
                corrente = None
            elif riga.strip():
                corrente["testo"].append(riga.strip())
    v = re.search(r"Versione\s+(\d+\.\d+\.\d+)\s+del\s+(\d{2}/\d{2}/\d{4})", testo)
    return {"riepilogo": rp if any(x is not None for x in rp.values()) else None,
            "blocchi": [{"simbolo": b["simbolo"], "testo": " ".join(b["testo"])} for b in blocchi],
            "versione_controllo": v.group(1) if v else None, "data_versione": v.group(2) if v else None}


# ------------------------------------------------------------------------------------ valutazione
def valuta(dgn: dict | None, esito_fornitura: dict | None) -> tuple[str, list[str]]:
    """Stato del controllo (specifica §10) dai soli diagnostici originali:
    positivo | negativo | da_verificare | non_verificabile.

    `da_verificare`: nessun motivo di scarto, ma il .dgn contiene righe non riconosciute o diagnostici con gravita'
    illeggibile/non decodificata: il programma non puo' concludere che il controllo sia positivo."""
    motivi: list[str] = []
    if not dgn and not esito_fornitura:
        return "non_verificabile", ["nessun diagnostico prodotto"]
    ex = (esito_fornitura or {}).get("esito_xsd") or {}
    if ex.get("ben_formato") is False:
        motivi.append("fornitura non ben formata (EsitoXsd/WellFormed=false)")
    if ex.get("valido") is False:
        motivi.append("fornitura non conforme allo schema (EsitoXsd/Valid=false)")
    if dgn:
        rp = dgn.get("riepilogo")
        if rp is None:
            motivi.append("diagnostico senza record di riepilogo (tipo 9)")
        else:
            if not rp.get("elaborate"):
                motivi.append("nessuna dichiarazione elaborata")
            if rp.get("scartate_errori_bloccanti"):
                motivi.append(f"dichiarazioni scartate per errori bloccanti: {rp['scartate_errori_bloccanti']}")
            if rp.get("scartate_non_rispondenza"):
                motivi.append(f"dichiarazioni scartate per non rispondenza: {rp['scartate_non_rispondenza']}")
        gravi = [d for d in dgn.get("diagnostici", []) if (d.get("gravita") or 0) >= 14]
        if gravi:
            motivi.append(f"diagnostici di gravita' (***C) o superiore: {len(gravi)}")
    elif not motivi:
        return "non_verificabile", ["manca il diagnostico .dgn: il solo esito di schema non basta"]
    if motivi:
        return "negativo", motivi
    dubbi: list[str] = []
    if dgn:
        if dgn.get("righe_non_riconosciute"):
            dubbi.append(f"righe del .dgn non riconosciute: {len(dgn['righe_non_riconosciute'])}")
        illeggibili = [d for d in dgn.get("diagnostici", []) if not d.get("simbolo")]
        if illeggibili:
            dubbi.append(f"diagnostici con gravita' illeggibile o non decodificata: {len(illeggibili)}")
    if dubbi:
        return "da_verificare", dubbi + ["verificare il rapporto .wri originale: esito non dichiarabile positivo"]
    return "positivo", []


# ---------------------------------------------------------------------------------- configurazione
@dataclass
class ConfigControllo:
    java: str | None = None
    cartella_jar: Path | None = None
    timeout_s: int = 600
    jnlp: Path = field(default_factory=percorso_jnlp)

    @classmethod
    def da_ambiente(cls, env: dict | None = None) -> "ConfigControllo":
        env = os.environ if env is None else env
        java = env.get(ENV_JAVA) or shutil.which("java")
        cart = env.get(ENV_JAR)
        try:
            timeout = int(env.get(ENV_TIMEOUT) or 600)
        except ValueError:
            timeout = 600
        return cls(java=java, cartella_jar=Path(cart) if cart else None, timeout_s=timeout)


@dataclass
class Processo:
    codice_uscita: int | None
    stdout: bytes
    stderr: bytes
    durata_s: float
    scaduto: bool = False


Esecutore = Callable[[list[str], Path, int], Processo]


def esecutore_reale(argv: list[str], cwd: Path, timeout: int) -> Processo:
    t0 = time.monotonic()
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=timeout, check=False)
        return Processo(p.returncode, p.stdout, p.stderr, round(time.monotonic() - t0, 3))
    except subprocess.TimeoutExpired as e:
        return Processo(None, e.stdout or b"", e.stderr or b"", round(time.monotonic() - t0, 3), scaduto=True)


def diagnostica_ambiente(config: ConfigControllo, esecutore: Esecutore = esecutore_reale) -> dict:
    """Verifica Java e JAR senza eseguire il controllo. Restituisce problemi e azioni comprensibili."""
    problemi: list[str] = []
    out: dict = {"java": config.java, "java_versione": None, "cartella_jar": str(config.cartella_jar or ""),
                 "jar": [], "jar_mancanti": [], "jnlp": str(config.jnlp), "os": platform.platform()}
    try:
        richiesti = jar_richiesti(config.jnlp)
    except (OSError, ET.ParseError) as e:
        richiesti = []
        problemi.append(f"JNLP dei controlli non leggibile ({e}): impossibile sapere quali JAR servono")
    manca_java = f"Java non trovato: installare un runtime Java (il JNLP richiede 1.7+) e/o impostare {ENV_JAVA}"
    if not config.java:
        problemi.append(manca_java)
    else:
        try:
            p = esecutore([config.java, "-version"], Path.cwd(), 60)
        except OSError:
            p = None
            problemi.append(manca_java + f" (provato: {config.java})")
        if p is not None:
            righe = [r for r in (p.stderr + p.stdout).decode("utf-8", "replace").splitlines()
                     if r and not r.startswith("Picked up")]
            out["java_versione"] = " | ".join(righe[:3]) or None
            if p.codice_uscita != 0:
                problemi.append("Java presente ma 'java -version' non termina correttamente")
    if not config.cartella_jar:
        problemi.append(f"cartella dei JAR del controllo SUC13 non configurata ({ENV_JAR})")
    elif not config.cartella_jar.is_dir():
        problemi.append(f"cartella dei JAR inesistente: {config.cartella_jar}")
    else:
        for n in richiesti:
            p = config.cartella_jar / n
            if p.is_file():
                out["jar"].append({"nome": n, "sha256": sha256_file(p), "bytes": p.stat().st_size})
            else:
                out["jar_mancanti"].append(n)
        if out["jar_mancanti"]:
            problemi.append("JAR mancanti: " + ", ".join(out["jar_mancanti"]))
    out["problemi"] = problemi
    out["pronto"] = not problemi
    return out


ISTRUZIONI_MANUALI = (
    "Passaggio manuale tracciato del controllo ufficiale SUC13:\n"
    "1. Esportare dal programma il file indicato (impronta SHA-256 riportata) senza modificarlo.\n"
    "2. Aprire il controllo 'Dichiarazione di successione' (Desktop Telematico > Controlli atti del registro, oppure "
    "ControlliSUC13.jnlp) e controllare quel file, salvando il diagnostico nella cartella proposta.\n"
    "3. Registrare nel programma i file prodotti dal controllo: <nome>.dgn e <nome>_logSchema.xml (obbligatori) e "
    "<nome>.wri se generato con 'Visualizza diagnostici'.\n"
    "4. Indicare versione del controllo e ambiente (Windows, Desktop Telematico/Java). Il programma verifica che il "
    "diagnostico si riferisca alla stessa dichiarazione (codice fiscale del defunto e identificativo).\n"
    "Requisito di automazione: resta aperto finche' il componente non e' configurato per l'esecuzione diretta "
    f"({ENV_JAVA}, {ENV_JAR})."
)


def _cf_defunto(xml: bytes) -> str | None:
    m = re.search(rb"<(?:\w+:)?CodiceFiscaleDefunto>\s*([A-Z0-9]{11,16})\s*<", xml)
    return m.group(1).decode() if m else None


def _identificativi(xml: bytes) -> set[str]:
    return {m.decode() for m in re.findall(rb"<(?:\w+:)?Dichiarazione\b[^>]*\bidentificativo=\"(\d{5})\"", xml)}


# Nomi con cui il programma consegna lo stesso file (elaborati.py, web.py): archivio `<sha16>.xml`, scaricamento
# `successione_revN[_bozza].xml`, copia di lavoro del componente `<ctl_job>.xml` e file controllato `<ctl_job>.dcm`.
_RX_SHA16 = re.compile(r"^([0-9a-f]{16})\.xml$")
_RX_REV = re.compile(r"^successione_rev(\d+)(?:_bozza)?\.xml$")
_RX_CTL = re.compile(r"^(ctl_[0-9a-f]{24})\.(?:xml|dcm)$")


def nomi_noti(job: dict) -> set[str]:
    """Nomi (minuscoli) con cui il file del job di controllo puo' comparire nel .dgn prodotto dall'utente."""
    inp = job.get("input", {})
    sha, nome = inp.get("xml_sha256") or "", (inp.get("xml_nome") or "").lower()
    out = {n for n in (nome, f"{sha[:16]}.xml" if sha else "", f"{job['job_id']}.xml", f"{job['job_id']}.dcm") if n}
    if inp.get("revisione") is not None:
        out |= {f"successione_rev{inp['revisione']}.xml", f"successione_rev{inp['revisione']}_bozza.xml"}
    return out


def confronta_nome(nome: str, job: dict, registro: RegistroJob | None = None) -> tuple[str, str]:
    """('coincide' | 'diverso' | 'sconosciuto', spiegazione). 'diverso': il nome segue uno schema del programma ma
    indica un ALTRO file (altra impronta, altra revisione, altro controllo su file diverso)."""
    n = Path((nome or "").replace("\\", "/")).name.strip().lower()
    if not n:
        return "sconosciuto", "nessun nome di file nel .dgn"
    if n in nomi_noti(job):
        return "coincide", f"nome {n} fra quelli noti per questo file"
    inp = job.get("input", {})
    m = _RX_SHA16.match(n)
    if m:
        return "diverso", f"{n}: impronta {m.group(1)} diversa da {(inp.get('xml_sha256') or '')[:16]}"
    m = _RX_REV.match(n)
    if m and inp.get("revisione") is not None:
        return "diverso", f"{n}: revisione {m.group(1)}, il file controllato e' della revisione {inp['revisione']}"
    m = _RX_CTL.match(n)
    if m:
        try:
            altro = registro.leggi(m.group(1), TIPO_JOB) if registro else None
        except NonTrovato:
            altro = None
        if altro is None:   # controllo di un altro archivio o di una postazione diversa: nome non verificabile
            return "sconosciuto", f"{n}: controllo {m.group(1)} non presente in questo archivio"
        if altro["input"].get("xml_sha256") == inp.get("xml_sha256"):
            return "coincide", f"{n}: controllo {m.group(1)} sullo stesso file (stessa impronta)"
        return "diverso", f"{n}: controllo {m.group(1)} eseguito su un file diverso (altra impronta)"
    return "sconosciuto", f"{n}: nome non riconducibile a questo file"


# ------------------------------------------------------------------------------------- adattatori
class _BaseControllo:
    def __init__(self, archivio: Archivio):
        self.arch = archivio
        self.job = RegistroJob(archivio)
        self.deposito = DepositoArtefatti(archivio)

    def _input(self, xml_path: Path | str, kw: dict, modalita: str) -> tuple[bytes, dict]:
        p = Path(xml_path)
        if not p.is_file():
            raise NonTrovato("file da controllare inesistente", percorso=str(p))
        dati = p.read_bytes()
        inp = {"xml_nome": p.name, "xml_sha256": sha256_bytes(dati), "xml_bytes": len(dati), "modalita": modalita,
               "pratica_id": kw.get("pratica_id"), "revisione": kw.get("revisione"),
               "impronta_dichiarativa": kw.get("impronta_dichiarativa")}
        return dati, inp

    def leggi(self, job_id: str) -> RisultatoAdattatore:
        """Rilettura (anche da un altro processo) del tentativo e del suo esito registrato."""
        j = self.job.leggi(job_id, TIPO_JOB)
        r = j["risultato"]
        return risultato_da_job(j, r.get("esito", Esito.DA_COLLAUDARE), artefatti=r.get("artefatti", []),
                                azione_richiesta=r.get("azione_richiesta"),
                                stato_controllo=r.get("stato_controllo", "non_eseguito"),
                                xml_sha256=j["input"].get("xml_sha256"))

    riprendi = leggi

    def aperto_per(self, inp: dict) -> dict | None:
        """Ultimo job manuale in attesa del diagnostico per lo stesso file (impronta) e gli stessi dati dichiarativi."""
        for j in reversed(self.job.elenca(TIPO_JOB, inp.get("pratica_id"), stati=["attesa_diagnostico"])):
            i = j["input"]
            if (i.get("xml_sha256") == inp["xml_sha256"] and i.get("modalita") == "manuale_tracciato"
                    and i.get("impronta_dichiarativa") == inp.get("impronta_dichiarativa")
                    and i.get("pratica_id") == inp.get("pratica_id")):
                return j
        return None

    def registra_diagnostico(self, job_id: str, *, dgn: bytes, log_schema: bytes, wri: bytes | None = None,
                             ambiente_dichiarato: dict | None = None,
                             conferma_associazione: bool = False) -> RisultatoAdattatore:
        """Registra i file originali del controllo eseguito dall'utente e ne verifica il riferimento al file.

        Il riferimento si verifica su codice fiscale del defunto e identificativi dei record diagnostici, sul numero di
        dichiarazioni elaborate e sul nome del file nell'intestazione del .dgn. Un diagnostico senza record (es.
        positivo) e con nome diverso non e' verificabile: serve `conferma_associazione=True`, registrata come
        dichiarazione dell'utente."""
        j = self.job.leggi(job_id, TIPO_JOB)
        if j["stato"] != "attesa_diagnostico":
            return self.leggi(job_id)
        if not dgn or not log_schema:
            raise DatiNonValidi("servono il file .dgn e il file _logSchema.xml prodotti dal controllo ufficiale")
        try:   # un file troncato o non XML si rifiuta con un messaggio chiaro; il job resta in attesa
            leggi_esito_fornitura(log_schema, valida=False)
        except Exception as e:   # lxml XMLSyntaxError, DatiNonValidi
            raise DatiNonValidi("il file _logSchema.xml non e' leggibile (troncato o non prodotto dal controllo): "
                                "non registrato", dettaglio=str(e)[:300]) from None
        art_in = next((a for a in j["risultato"].get("artefatti", []) if a.get("ruolo") == "input_controllo"),
                      j["risultato"]["artefatti"][0])
        xml = self.deposito.leggi(art_in)
        d = leggi_dgn(decodifica(dgn))
        cf, ids = _cf_defunto(xml), _identificativi(xml)
        sogg = {x["soggetto"] for x in d["diagnostici"] if x["soggetto"] and not x["soggetto"].startswith("VALIDAZ")}
        id_dgn = {x["identificativo"] for x in d["diagnostici"] if x["identificativo"]}
        incoerenze = []
        if sogg and cf and sogg != {cf}:
            incoerenze.append(f"il diagnostico riguarda {sorted(sogg)}, il file il defunto {cf}")
        if id_dgn and ids and not id_dgn <= ids:
            incoerenze.append(f"identificativi del diagnostico {sorted(id_dgn)} assenti nel file {sorted(ids)}")
        elaborate = (d.get("riepilogo") or {}).get("elaborate")
        if elaborate and ids and elaborate != len(ids):
            incoerenze.append(f"dichiarazioni elaborate {elaborate}, nel file {len(ids)}")
        if incoerenze:
            raise DatiNonValidi("il diagnostico non e' riferibile al file controllato: non registrato",
                                incoerenze=incoerenze)
        nome_dgn = Path((d.get("file_controllato") or "").replace("\\", "/")).name
        esito_nome, spiega_nome = confronta_nome(nome_dgn, j, self.job)
        if esito_nome == "diverso":   # mai accettato, nemmeno con la conferma: e' il diagnostico di un altro file
            raise DatiNonValidi("il diagnostico riguarda un altro file o un'altra revisione: non registrato",
                                incoerenze=[spiega_nome], nomi_attesi=sorted(nomi_noti(j)))
        verificata = bool((sogg and cf) or (id_dgn and ids)) or esito_nome == "coincide"
        if not verificata and not conferma_associazione:
            raise DatiNonValidi("associazione del diagnostico al file non verificabile (nessun record con codice "
                                "fiscale e nome file non riconosciuto): confermarla esplicitamente",
                                nome_nel_dgn=nome_dgn, nomi_attesi=sorted(nomi_noti(j)))
        artefatti = list(j["risultato"].get("artefatti", []))
        for b, nome, ruolo in ((dgn, "diagnostico.dgn", "diagnostico_dgn"),
                               (log_schema, "diagnostico_logSchema.xml", "esito_schema"),
                               (wri, "diagnostico.wri", "rapporto_wri")):
            if b:
                artefatti.append(self.deposito.salva_bytes(b, nome, ruolo, provenienza="fornito_utente"))
        extra = {"modalita": "manuale_tracciato", "requisito_automazione": "aperto",
                 "ambiente_dichiarato": ambiente_dichiarato or {},
                 "associazione": {"cf_defunto": cf, "identificativi": sorted(ids), "nome_nel_dgn": nome_dgn,
                                  "confronto_nome": spiega_nome,
                                  "metodo": ("codice fiscale, identificativi, numero di dichiarazioni e nome del file "
                                             "confrontati con il file conservato") if verificata else
                                  "dichiarata dall'utente (non verificabile dal contenuto)"}}
        patch = self._completa_con_diagnostici(j, dgn_b=dgn, log_b=log_schema, wri_b=wri, reale=True, extra=extra,
                                               artefatti=artefatti, avvertenze=[])
        if not verificata:  # mai 'passato' su un'associazione solo dichiarata: non sblocca la conferma dell'invio
            patch["esito"] = Esito.DA_COLLAUDARE.value
            patch["avvertenze"].append("associazione al file dichiarata dall'utente: esito non verificato")
        self.job.transizione(job_id, ["attesa_diagnostico"], "completato", patch=patch, nota=patch["stato_controllo"])
        return self.leggi(job_id)

    def _completa_con_diagnostici(self, j: dict, *, dgn_b: bytes | None, log_b: bytes | None, wri_b: bytes | None,
                                  reale: bool, extra: dict, artefatti: list, avvertenze: list) -> dict:
        illeggibili: list[str] = []
        dgn = ef = wri = None
        for chiave, b, lettore in (("dgn", dgn_b, lambda x: leggi_dgn(decodifica(x))),
                                   ("_logSchema.xml", log_b, leggi_esito_fornitura),
                                   ("wri", wri_b, lambda x: leggi_wri(decodifica(x)))):
            if not b:
                continue
            try:   # un file troncato (Java interrotto) non deve lasciare il job a meta'
                v = lettore(b)
            except Exception as e:   # lxml XMLSyntaxError, DatiNonValidi, decodifica
                illeggibili.append(f"file {chiave} del componente illeggibile ({type(e).__name__}: {str(e)[:200]})")
                continue
            if chiave == "dgn":
                dgn = v
            elif chiave == "wri":
                wri = v
            else:
                ef = v
        stato, motivi = valuta(dgn, ef)
        if illeggibili:
            stato, motivi = "non_verificabile", illeggibili + motivi
        if wri and dgn and wri.get("riepilogo") and dgn.get("riepilogo"):
            for k, v in wri["riepilogo"].items():
                if v is not None and dgn["riepilogo"].get(k) not in (None, v):
                    avvertenze.append(f"riepilogo .wri e .dgn discordanti su {k}")
        if ef and ef.get("conforme_xsd") is False:
            avvertenze.append("il _logSchema.xml non e' conforme a esitoFornitura_v3.xsd delle fonti")
        if not reale:
            esito = Esito.SIMULAZIONE
        elif stato == "positivo":
            esito = Esito.PASSATO
        elif stato == "da_verificare":   # diagnostico non interamente leggibile: ne' passato ne' fallito
            esito = Esito.DA_COLLAUDARE
        else:
            esito = Esito.FALLITO
        patch = {"esito": esito.value, "stato_controllo": stato, "motivi": motivi, "avvertenze": avvertenze,
                 "file_illeggibili": illeggibili,
                 "versione_controllo": (dgn or {}).get("versione_controllo") or (wri or {}).get("versione_controllo"),
                 "data_versione": (dgn or {}).get("data_versione") or (wri or {}).get("data_versione"),
                 "riepilogo": (dgn or {}).get("riepilogo") or (wri or {}).get("riepilogo"),
                 "diagnostici": (dgn or {}).get("diagnostici", []),
                 "esito_fornitura": ef, "rapporto": wri, "artefatti": artefatti, "azione_richiesta": None, **extra}
        return patch


class ControlloJar(_BaseControllo):
    """Esegue il JAR ufficiale (Java e percorso da variabili d'ambiente) e conserva input/output/ambiente."""

    def __init__(self, archivio: Archivio, config: ConfigControllo | None = None,
                 esecutore: Esecutore | None = None):
        super().__init__(archivio)
        self.config = config or ConfigControllo.da_ambiente()
        self._esec = esecutore or esecutore_reale
        self.simulato = esecutore is not None  # qualunque esecutore iniettato produce solo 'simulazione'

    def diagnostica(self) -> dict:
        return diagnostica_ambiente(self.config, self._esec)

    def esegui(self, xml_path: Path | str, *, chiave: str | None = None, produci_dcm: bool = False,
               rapporto_wri: bool = True, **kw) -> RisultatoAdattatore:
        dati, inp = self._input(xml_path, kw, "esecuzione_jar")
        inp["produci_dcm"] = bool(produci_dcm)
        j, nuovo = self.job.crea(TIPO_JOB, kw.get("pratica_id"), inp, stato="creato", chiave=chiave)
        return self._esegui_job(j["job_id"], dati, rapporto_wri)

    def riprendi(self, job_id: str) -> RisultatoAdattatore:
        """Riprende solo il controllo locale interrotto, dai byte congelati; nessun invio."""
        return self._esegui_job(job_id, None, True)

    def _esegui_job(self, job_id: str, dati: bytes | None, rapporto_wri: bool) -> RisultatoAdattatore:
        from ..blocchi import blocco_file
        j = self.job.leggi(job_id, TIPO_JOB)
        with blocco_file(self.arch.base / 'lavoro' / 'lock' / (job_id + '.lock')) as acquisito:
            if not acquisito:
                return self.leggi(job_id)  # il processo precedente e' ancora vivo
            j = self.job.leggi(job_id, TIPO_JOB)
            if j['stato'] == 'in_esecuzione':
                j = self.job.transizione(job_id, ['in_esecuzione'], 'interrotto', patch={
                    'stato_controllo': 'non_verificabile',
                    'esito': (Esito.SIMULAZIONE if self.simulato else Esito.FALLITO).value,
                    'azione_richiesta': 'Controllo interrotto: recupero dai byte originali congelati.'},
                    nota='processo interrotto, lock rilasciato dal sistema')
            if j['stato'] not in ('creato', 'interrotto'):
                return self.leggi(job_id)
            if dati is None:
                art = next((a for a in j['risultato'].get('artefatti', []) if a.get('ruolo') == 'input_controllo'), None)
                if art is None:  # job della vecchia beta: esegui(stesso XML, stessa chiave) puo' recuperarlo
                    self.job.transizione(job_id, [j['stato']], 'interrotto', patch={
                        'stato_controllo': 'non_verificabile', 'esito': Esito.DA_COLLAUDARE.value,
                        'azione_richiesta': 'Input del vecchio job non conservato: rieseguire il controllo sullo stesso XML con la stessa chiave.'},
                        nota='input necessario al recupero')
                    return self.leggi(job_id)
                dati = self.deposito.leggi(art)
            if sha256_bytes(dati) != j['input']['xml_sha256']:
                raise DatiNonValidi('input del controllo alterato: recupero non eseguito')
            return self._esegui_acquisito(j, dati, rapporto_wri)

    def _esegui_acquisito(self, j: dict, dati: bytes, rapporto_wri: bool) -> RisultatoAdattatore:
        inp = j['input']
        produci_dcm = inp.get('produci_dcm', False)
        art_in = self.deposito.salva_bytes(dati, inp["xml_nome"], "input_controllo")
        self.job.annota(j['job_id'], {'artefatti': [art_in]}, nota='input congelato prima del controllo')
        amb = self.diagnostica()
        if not amb["pronto"]:
            az = ("Componente di controllo non eseguibile qui: " + "; ".join(amb["problemi"]) + ".\n"
                  + ISTRUZIONI_MANUALI)
            j = self.job.transizione(j["job_id"], ["creato", "interrotto"], "attesa_diagnostico", patch={
                "esito": Esito.DA_COLLAUDARE.value, "stato_controllo": "non_eseguito", "ambiente": amb,
                "artefatti": [art_in], "azione_richiesta": az, "modalita": "manuale_tracciato",
                "requisito_automazione": "aperto"}, nota="componente non disponibile")
            return self.leggi(j["job_id"])
        # Un Java orfano potrebbe terminare dopo il client: ogni esecuzione ha output
        # separati, cosi' non puo' contaminare il tentativo ripreso.
        lavoro = self.arch.base / "lavoro" / "controlli" / (j["job_id"] + '-' + uuid.uuid4().hex[:12])
        for d in ("in", "out", "tmp"):
            (lavoro / d).mkdir(parents=True, exist_ok=True)
        nome = f"{j['job_id']}.xml"
        (lavoro / "in" / nome).write_bytes(dati)
        cp = os.pathsep.join(str(self.config.cartella_jar / n["nome"]) for n in amb["jar"])
        base = [self.config.java, "-Djava.awt.headless=true", f"-Djava.io.tmpdir={lavoro / 'tmp'}", "-cp", cp]
        argv = base + [CLASSE_CONTROLLO, f"in/{nome}", f"out/{nome}"]
        if produci_dcm:
            argv.append(f"out/{j['job_id']}.dcm")
        j = self.job.transizione(j["job_id"], ["creato", "interrotto"], "in_esecuzione", patch={
                                 "ambiente": amb, "argv": argv[-3:], "pid_esecutore": os.getpid(),
                                 "cartella_lavoro": lavoro.relative_to(self.arch.base).as_posix()},
                                 nota="avvio del componente ufficiale")
        try:
            self._esegui_e_registra(j, inp, lavoro, argv, base, nome, produci_dcm, rapporto_wri, art_in)
        except Exception as e:
            # Qualunque errore dopo l'avvio (lettura delle uscite, deposito, ...) chiude il job con un esito esplicito:
            # mai un job lasciato 'in_esecuzione' ne' un'eccezione grezza a GUI/MCP.
            motivo = f"{type(e).__name__}: {str(e)[:300]}"
            try:
                self.job.transizione(j["job_id"], ["in_esecuzione"], "errore_esecuzione", patch={
                    "stato_controllo": "non_verificabile",
                    "esito": (Esito.SIMULAZIONE if self.simulato else Esito.FALLITO).value,
                    "motivi": [f"errore nell'elaborazione delle uscite del componente ({motivo})"],
                    "azione_richiesta": "Controllo non concluso: rieseguire il controllo ufficiale; se si ripete, "
                                        "verificare Java e i JAR del componente."},
                    nota="errore dopo l'avvio del componente", errore=motivo)
            except TransizioneNonAmmessa:  # pragma: no cover - gia' concluso
                pass
        finally:
            # input, uscite, stdout/stderr sono nel deposito (con impronta): la cartella di lavoro non serve piu'
            shutil.rmtree(lavoro, ignore_errors=True)
        return self.leggi(j["job_id"])

    def _esegui_e_registra(self, j: dict, inp: dict, lavoro: Path, argv: list[str], base: list[str], nome: str,
                           produci_dcm: bool, rapporto_wri: bool, art_in: dict) -> None:
        try:
            p = self._esec(argv, lavoro, self.config.timeout_s)
        except OSError as e:  # Java rimosso o non avviabile dopo la diagnostica
            p = Processo(None, b"", f"avvio non riuscito: {e}".encode(), 0.0)
        artefatti = [art_in]
        avvertenze: list[str] = []
        stderr_t = p.stderr.decode("utf-8", "replace")
        if "javax/annotation/PostConstruct" in stderr_t:
            avvertenze.append("inizializzazione del modulo di stampa (print-model) fallita su questo Java: il controllo "
                              "prosegue; equivalenza con l'ambiente ufficiale (Desktop Telematico) da collaudare")
        if "could not locate enum table" in stderr_t:
            avvertenze.append("XMLBeans: tabella di enumerazione non trovata (messaggio del componente)")
        for nome_out, ruolo, b in (("stdout.txt", "stdout_controllo", p.stdout), ("stderr.txt", "stderr_controllo",
                                                                                   p.stderr)):
            artefatti.append(self.deposito.salva_bytes(b, nome_out, ruolo))
        out = lavoro / "out"
        dgn_p, log_p = out / f"{j['job_id']}.dgn", out / f"{j['job_id']}_logSchema.xml"
        wri_p, dcm_p = out / f"{j['job_id']}.wri", out / f"{j['job_id']}.dcm"
        if rapporto_wri and dgn_p.exists():
            p2 = self._esec(base + [CLASSE_RAPPORTO, f"out/{j['job_id']}.dgn", "1"], lavoro, self.config.timeout_s)
            if not wri_p.exists():
                avvertenze.append(f"rapporto .wri non prodotto da VisualXml (uscita {p2.codice_uscita})")
        letti = {}
        for pp, ruolo in ((dgn_p, "diagnostico_dgn"), (log_p, "esito_schema"), (wri_p, "rapporto_wri"),
                          (dcm_p, "file_controllato_dcm")):
            if pp.exists():
                letti[ruolo] = pp.read_bytes()
                artefatti.append(self.deposito.salva_bytes(letti[ruolo], pp.name, ruolo))
        copia_input = lavoro / "in" / nome
        hash_dopo = sha256_file(copia_input) if copia_input.exists() else None
        # Con produzione DCM il componente ufficiale puo' consumare la copia di
        # lavoro dopo il controllo positivo. L'originale resta nel deposito.
        consumata = hash_dopo is None and produci_dcm and "file_controllato_dcm" in letti
        deposito_invariato = sha256_bytes(self.deposito.leggi(art_in)) == inp['xml_sha256']
        extra = {"modalita": "esecuzione_jar", "codice_uscita": p.codice_uscita, "durata_s": p.durata_s,
                 "scaduto": p.scaduto, "input_modificato_dal_componente": not consumata and hash_dopo != inp["xml_sha256"],
                 "copia_lavoro_consumata": consumata, "input_deposito_invariato": deposito_invariato,
                 "classe": CLASSE_CONTROLLO, "dcm_prodotto": "file_controllato_dcm" in letti,
                 "simulato": self.simulato}
        patch = self._completa_con_diagnostici(j, dgn_b=letti.get("diagnostico_dgn"), log_b=letti.get("esito_schema"),
                                               wri_b=letti.get("rapporto_wri"), reale=not self.simulato, extra=extra,
                                               artefatti=artefatti, avvertenze=avvertenze)
        if patch.get("file_illeggibili"):   # es. _logSchema.xml troncato da un Java interrotto
            patch["azione_richiesta"] = ("Uscite del componente illeggibili (" + "; ".join(patch["file_illeggibili"])
                                         + "): rieseguire il controllo ufficiale.")
            stato_job = "errore_esecuzione"
        elif p.scaduto or "diagnostico_dgn" not in letti or not deposito_invariato or extra['input_modificato_dal_componente']:
            patch["motivi"] = patch["motivi"] + [("tempo massimo superato" if p.scaduto else
                                                 "input alterato o copia di lavoro scomparsa senza DCM" if not deposito_invariato or extra['input_modificato_dal_componente'] else
                                                 f"il componente non ha prodotto il .dgn (uscita {p.codice_uscita})")]
            patch["stato_controllo"] = "non_verificabile"
            patch["esito"] = (Esito.SIMULAZIONE if self.simulato else Esito.FALLITO).value
            stato_job = "errore_esecuzione"
        else:
            stato_job = "completato"
        self.job.transizione(j["job_id"], ["in_esecuzione"], stato_job, patch=patch, nota=patch["stato_controllo"])


class ControlloManuale(_BaseControllo):
    """Passaggio manuale tracciato: file e impronta conservati, istruzioni, attesa del diagnostico originale."""

    def esegui(self, xml_path: Path | str, *, chiave: str | None = None, **kw) -> RisultatoAdattatore:
        dati, inp = self._input(xml_path, kw, "manuale_tracciato")
        if chiave is None:   # stesso file, stessi dati: si riprende il passaggio manuale gia' aperto, non se ne crea un altro
            aperto = self.aperto_per(inp)
            if aperto is not None:
                return self.leggi(aperto["job_id"])
        j, nuovo = self.job.crea(TIPO_JOB, kw.get("pratica_id"), inp, stato="creato", chiave=chiave)
        if not nuovo and j["stato"] != "creato":
            return self.leggi(j["job_id"])
        art = self.deposito.salva_bytes(dati, inp["xml_nome"], "input_controllo")
        j = self.job.transizione(j["job_id"], ["creato"], "attesa_diagnostico", patch={
            "esito": Esito.DA_COLLAUDARE.value, "stato_controllo": "non_eseguito", "artefatti": [art],
            "azione_richiesta": ISTRUZIONI_MANUALI + f"\nFile: {inp['xml_nome']} — SHA-256 {inp['xml_sha256']}"
                                + "\nNomi del file riconosciuti nel .dgn: " + ", ".join(sorted(nomi_noti(j))),
            "modalita": "manuale_tracciato", "requisito_automazione": "aperto"}, nota="in attesa del diagnostico")
        return self.leggi(j["job_id"])

def controllo_ufficiale(archivio: Archivio, config: ConfigControllo | None = None) -> ControlloJar | ControlloManuale:
    """Adattatore predefinito: esecuzione diretta se Java e JAR sono configurati, altrimenti passaggio manuale."""
    cfg = config or ConfigControllo.da_ambiente()
    if cfg.java and cfg.cartella_jar and cfg.cartella_jar.is_dir():
        return ControlloJar(archivio, cfg)
    return ControlloManuale(archivio)
