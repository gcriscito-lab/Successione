#!/usr/bin/env python3
"""Lanciatore di compiti per agenti gratuiti (servizi con API compatibile OpenAI, es. FreeLLMAPI).

Uso:
  FREELLMAPI_KEY=... FREELLMAPI_BASE_URL=https://host/v1 FREELLMAPI_MODEL=nome \
      python scripts/agenti_gratuiti/lancia.py C4 [--max-iter 3] [--dry-run]

Il modello NON esegue comandi e NON tocca il repository: restituisce solo modifiche in JSON. Il lanciatore le applica in una
copia isolata (git worktree), rifiuta qualsiasi file non elencato nel compito, esegue le verifiche con i propri comandi e
scrive la patch e un CONSEGNA.md con gli esiti REALI delle verifiche (non quelli dichiarati dal modello).
La chiave si legge dall'ambiente e non viene mai stampata né scritta. Nessun dato reale: il repository e' sintetico.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
DOC_COMPITI = RADICE / "docs" / "COMPITI_PER_AGENTI_GRATUITI.md"
LIMITE_FILE_BYTE = 200_000
LIMITE_CONTESTO_BYTE = 160_000

# Verifiche eseguite dal lanciatore (mai dal modello), per compito. Comandi senza shell.
VERIFICHE: dict[str, list[list[str]]] = {
    "C1": [["node", "--check", "src/successioni/static/app.js"]],
    "C2": [], "C3": [], "C5": [],
    "C4": [[sys.executable, "-m", "pytest", "-q", "tests/test_valori_schema_extra.py"]],
    "C6": [["node", "--check", "src/successioni/static/app.js"]],
    "C8": [[sys.executable, "-m", "pytest", "-q", "tests/test_supplemento_extra.py"]],
    "C9": [[sys.executable, "-m", "pytest", "-q", "tests/test_invio_lettori_extra.py"]],
    "C10": [[sys.executable, "-m", "pytest", "-q", "tests/test_formati_extra.py"]],
    "C12": [[sys.executable, "-m", "pytest", "-q", "tests/test_quadri_schema_extra.py"]],
    "C13": [[sys.executable, "-m", "pytest", "-q", "tests/test_invio_web_mcp.py"]],
    "C14": [[sys.executable, "-m", "pytest", "-q", "tests/test_devoluzione_legge_extra.py"]],
    "C15": [[sys.executable, "-m", "pytest", "-q", "tests/test_identificativi_extra.py"]],
    "C18": [[sys.executable, "-m", "pytest", "-q", "tests/test_quadri_nuovi_servizio.py"]],
    "C19": [[sys.executable, "-m", "pytest", "-q", "tests/test_matrice_coerenza.py"]],
    "C16": [[sys.executable, "scripts/verifica_doc_quadri.py", "docs/GUIDA_QUADRI.md"]],
    "C21": [[sys.executable, "scripts/verifica_doc_quadri.py", "docs/QUADRI_DISPONIBILI.md"]],
    "C22": [[sys.executable, "-m", "pytest", "-q", "tests/test_pdfa_rilevamento_extra.py"]],
    "C23": [[sys.executable, "-m", "pytest", "-q", "tests/test_supplemento_chiavi_extra.py"]],
    "C24": [[sys.executable, "-m", "pytest", "-q", "tests/test_invio_stati_extra.py"]],
}

REGOLE_SISTEMA = (
    "Sei un agente di sviluppo che lavora a un progetto Python (applicazione locale per dichiarazioni di successione). "
    "Rispondi ESCLUSIVAMENTE con un oggetto JSON, senza testo fuori dal JSON, con questa forma: "
    '{"modifiche": [{"file": "percorso", "contenuto": "contenuto COMPLETO del file"} oppure '
    '{"file": "percorso", "vecchio": "testo esatto da sostituire (unico nel file)", "nuovo": "testo sostitutivo"}], '
    '"note": "cosa hai fatto e cosa non hai potuto verificare"}. '
    "Regole: tocca SOLO i file consentiti; dati solo sintetici; nessuna regola fiscale inventata (se serve, scrivilo in note e non farlo); "
    "non saltare né indebolire test; nessuna chiave o credenziale nel codice."
)


def leggi_compito(cid: str) -> dict:
    testo = DOC_COMPITI.read_text(encoding="utf-8")
    m = re.search(rf"^## {re.escape(cid)}\.(.*?)(?=^## |\Z)", testo, re.S | re.M)
    if not m:
        raise SystemExit(f"compito {cid} non trovato in {DOC_COMPITI.name}")
    blocco = m.group(0)
    riga = re.search(r"\*\*File(?: consentiti)?:\*\*(.*)", blocco)
    if not riga:
        raise SystemExit(f"compito {cid}: manca l'elenco dei file consentiti")
    ammessi = re.findall(r"`([^`]+)`", riga.group(1))
    ammessi = [a for a in ammessi if "/" in a or "." in a]
    nuovi = {a for a in ammessi if re.search(rf"`{re.escape(a)}`\s*\(nuov[oi]\)", riga.group(1))}
    ctx = re.search(r"\*\*Contesto(?: di sola lettura)?:\*\*(.*)", blocco)
    contesto = [c for c in re.findall(r"`([^`]+)`", ctx.group(1)) if "/" in c or "." in c] if ctx else []
    return {"id": cid, "testo": blocco, "ammessi": ammessi, "nuovi": nuovi, "contesto": contesto}


def percorso_sicuro(rel: str, ammessi: list[str]) -> str | None:
    """Restituisce il percorso normalizzato solo se e' esattamente uno dei file consentiti."""
    if not isinstance(rel, str) or not rel or "\x00" in rel or rel.startswith(("/", "\\")) or ":" in rel:
        return None
    norm = Path(rel.replace("\\", "/")).as_posix()
    if ".." in Path(norm).parts or norm not in ammessi:
        return None
    return norm


def estrai_json(testo: str) -> dict:
    t = testo.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    i, f = t.find("{"), t.rfind("}")
    if i < 0 or f < i:
        raise ValueError("nessun oggetto JSON nella risposta")
    return json.loads(t[i:f + 1])


def applica(lavoro: Path, proposta: dict, ammessi: list[str]) -> tuple[list[str], list[str]]:
    """Applica le modifiche nella copia di lavoro. Restituisce (file_toccati, errori). Nulla fuori dall'elenco."""
    toccati, errori = [], []
    for i, mod in enumerate(proposta.get("modifiche") or []):
        rel = percorso_sicuro(mod.get("file"), ammessi)
        if rel is None:
            errori.append(f"modifica {i}: file non consentito o non valido ({str(mod.get('file'))[:80]!r}): ignorata")
            continue
        p = lavoro / rel
        try:
            if "contenuto" in mod:
                nuovo = mod["contenuto"]
            else:
                if not p.is_file():
                    raise ValueError("il file non esiste: usare 'contenuto' per crearlo")
                attuale = p.read_text(encoding="utf-8")
                if attuale.count(mod.get("vecchio", "\x00")) != 1:
                    raise ValueError("'vecchio' deve comparire esattamente una volta nel file")
                nuovo = attuale.replace(mod["vecchio"], mod["nuovo"], 1)
            if not isinstance(nuovo, str) or len(nuovo.encode("utf-8")) > LIMITE_FILE_BYTE:
                raise ValueError("contenuto non valido o troppo grande")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(nuovo, encoding="utf-8", newline="\n")
            toccati.append(rel)
        except (ValueError, KeyError, TypeError, OSError) as e:
            errori.append(f"modifica {i} su {rel}: {e}")
    return toccati, errori


def chiama_modello(base_url: str, chiave: str, modello: str, messaggi: list[dict], timeout: int = 180) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    corpo = json.dumps({"model": modello, "messages": messaggi, "temperature": 0.2}).encode("utf-8")
    req = urllib.request.Request(url, data=corpo, method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {chiave}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            dati = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:      # il corpo puo' contenere echi: solo stato e intestazione breve
        raise RuntimeError(f"il servizio ha risposto con HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise RuntimeError(f"servizio non raggiungibile ({type(e).__name__}): controllare indirizzo e rete consentita") from None
    return dati["choices"][0]["message"]["content"]


def elenca_modelli(base_url: str, chiave: str, timeout: int = 60) -> list[str]:
    """Nomi dei modelli esposti dal servizio (GET {base}/models), per scegliere FREELLMAPI_MODEL."""
    req = urllib.request.Request(base_url.rstrip("/") + "/models", headers={"Authorization": f"Bearer {chiave}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            dati = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"il servizio ha risposto con HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise RuntimeError(f"servizio non raggiungibile ({type(e).__name__}): e' avviato sul questo PC?") from None
    return [str(m.get("id")) for m in dati.get("data", []) if isinstance(m, dict)]


def esegui(argv: list[str], cwd: Path, timeout: int = 600) -> tuple[int, str]:
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, ((p.stdout or "") + (p.stderr or ""))[-3000:]
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, f"{type(e).__name__}: {e}"


def contesto_file(lavoro: Path, ammessi: list[str]) -> str:
    parti, tot = [], 0
    for rel in ammessi:
        p = lavoro / rel
        if p.is_file():
            t = p.read_text(encoding="utf-8")
            tot += len(t.encode("utf-8"))
            if tot > LIMITE_CONTESTO_BYTE:
                parti.append(f"### {rel}\n(troppo grande per il contesto: usa modifiche con 'vecchio'/'nuovo' solo se conosci il testo esatto)")
                continue
            parti.append(f"### {rel}\n```\n{t}\n```")
        else:
            parti.append(f"### {rel}\n(file nuovo: da creare con 'contenuto')")
    return "\n\n".join(parti)


def contesto_lettura(lavoro: Path, contesto: list[str]) -> str:
    """File di SOLA LETTURA mostrati al modello: non sono modificabili (percorso_sicuro li rifiuta)."""
    parti, tot = [], 0
    base = lavoro.resolve()
    for rel in contesto:
        p = (lavoro / rel).resolve()
        if base not in p.parents or not p.is_file():
            continue
        t = p.read_text(encoding="utf-8")
        tot += len(t.encode("utf-8"))
        if tot > LIMITE_CONTESTO_BYTE:
            break
        parti.append(f"### {rel} (SOLA LETTURA)\n```\n{t}\n```")
    return "\n\n".join(parti)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("compito", nargs="?", help="C1..C6 (vedi docs/COMPITI_PER_AGENTI_GRATUITI.md)")
    ap.add_argument("--modelli", action="store_true", help="elenca i modelli del servizio e termina")
    ap.add_argument("--max-iter", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true", help="mostra file consentiti e prompt senza chiamare il servizio")
    ap.add_argument("--out", default=str(RADICE / "build" / "agenti"))
    a = ap.parse_args(argv)
    if a.modelli:
        base, chiave = os.environ.get("FREELLMAPI_BASE_URL"), os.environ.get("FREELLMAPI_KEY")
        if not (base and chiave):
            print("Servono FREELLMAPI_BASE_URL e FREELLMAPI_KEY nell'ambiente.", file=sys.stderr)
            return 2
        try:
            for m in elenca_modelli(base, chiave):
                print(m)
        except RuntimeError as e:
            print(e, file=sys.stderr)
            return 3
        return 0
    if not a.compito:
        ap.error("indicare il compito (C1..C6) oppure --modelli")
    comp = leggi_compito(a.compito)
    base, chiave, modello = (os.environ.get("FREELLMAPI_BASE_URL"), os.environ.get("FREELLMAPI_KEY"),
                             os.environ.get("FREELLMAPI_MODEL"))
    if a.dry_run:
        print("File consentiti:", comp["ammessi"], "| nuovi:", sorted(comp["nuovi"]))
        print("Verifiche:", VERIFICHE.get(a.compito, []))
        print("Servizio configurato:", bool(base and chiave and modello), "(FREELLMAPI_BASE_URL, FREELLMAPI_KEY, FREELLMAPI_MODEL)")
        return 0
    mancanti = [n for n, v in (("FREELLMAPI_BASE_URL", base), ("FREELLMAPI_KEY", chiave), ("FREELLMAPI_MODEL", modello)) if not v]
    if mancanti:
        print("Variabili d'ambiente mancanti:", ", ".join(mancanti), file=sys.stderr)
        return 2
    out = Path(a.out) / f"{a.compito}-{datetime.now():%Y%m%d-%H%M%S}"
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="agente-") as t:
        lavoro = Path(t) / "copia"
        subprocess.run(["git", "worktree", "add", "--detach", str(lavoro), "HEAD"], cwd=RADICE, check=True, capture_output=True)
        try:
            messaggi = [{"role": "system", "content": REGOLE_SISTEMA},
                        {"role": "user", "content": comp["testo"] + "\n\nFile consentiti (e loro contenuto attuale):\n\n"
                         + contesto_file(lavoro, comp["ammessi"])
                         + ("\n\nFile di sola lettura (NON inventare nomi, funzioni, codici di errore o campi che qui non compaiono):\n\n"
                            + contesto_lettura(lavoro, comp["contesto"]) if comp["contesto"] else "")}]
            toccati, esiti, errori_tot, note = set(), [], [], ""
            for it in range(1, a.max_iter + 1):
                try:
                    risposta = chiama_modello(base, chiave, modello, messaggi)
                    proposta = estrai_json(risposta)
                except (RuntimeError, ValueError, KeyError) as e:
                    errori_tot.append(f"iterazione {it}: {e}")
                    messaggi += [{"role": "user", "content": f"Risposta non valida ({e}). Rispondi solo con il JSON richiesto."}]
                    if isinstance(e, RuntimeError):
                        break
                    continue
                messaggi.append({"role": "assistant", "content": risposta[:6000]})
                t_it, err = applica(lavoro, proposta, comp["ammessi"])
                toccati.update(t_it); errori_tot += [f"iterazione {it}: {x}" for x in err]
                note = str(proposta.get("note", ""))[:2000]
                falliti = []
                for cmd in VERIFICHE.get(a.compito, []):
                    rc, uscita = esegui(cmd, lavoro)
                    esiti.append({"iterazione": it, "comando": " ".join(cmd), "codice": rc, "uscita": uscita})
                    if rc != 0:
                        falliti.append(f"$ {' '.join(cmd)}\n{uscita}")
                if not falliti and not err and toccati:
                    break
                messaggi.append({"role": "user", "content": "Correggi. Problemi:\n" + "\n".join(err + falliti)[:5000]})
            subprocess.run(["git", "add", "-A"], cwd=lavoro, capture_output=True)
            patch = subprocess.run(["git", "diff", "--cached", "--binary"], cwd=lavoro, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
            (out / "consegna.patch").write_text(patch, encoding="utf-8")
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(lavoro)], cwd=RADICE, capture_output=True)
    ultime = {e["comando"]: e for e in esiti}
    ok = bool(patch.strip()) and all(e["codice"] == 0 for e in ultime.values())
    righe = [f"# Consegna {a.compito}", "", f"Modello: {modello}", f"Servizio: {base}", f"Iterazioni max: {a.max_iter}",
             f"File toccati (tutti dall'elenco consentito): {sorted(toccati) or 'nessuno'}", "",
             "## Verifiche eseguite dal lanciatore (esiti reali)"]
    righe += [f"- `{c}`: codice {e['codice']}" for c, e in ultime.items()] or ["- nessuna verifica automatica per questo compito: serve la lettura del coordinatore"]
    righe += ["", "## Modifiche rifiutate o errori"] + ([f"- {x}" for x in errori_tot] or ["- nessuno"])
    righe += ["", "## Note del modello (dichiarazioni non verificate)", note or "(nessuna)", "",
              f"Esito complessivo del lanciatore: {'verifiche passate' if ok else 'DA RIVEDERE'}. La revisione del coordinatore resta obbligatoria."]
    (out / "CONSEGNA.md").write_text("\n".join(righe) + "\n", encoding="utf-8")
    print(f"Consegna in {out} ({'verifiche passate' if ok else 'da rivedere'})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
