"""A11/A12 sul corpus SINTETICO (successioni.documenti.corpus_sintetico).

Le prove sono controlli locali: senza veraPDF nessun esito 'conforme' e A11 resta 'da_collaudare'; la firma del corpus
e' simulata. Nulla di quanto segue dimostra compatibilita' con i servizi dell'Agenzia.
"""
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

import pytest

from successioni import pdfa
from successioni.documenti.corpus_sintetico import collaudo_a11, genera_corpus
from successioni.documenti.dimensioni import confronta_testo
from successioni.documenti.dimensioni import testo_pagine as estrai_pagine
from successioni.documenti.pdfa_strutturale import verifica_strutturale_pdfa

gs_ok = pytest.mark.skipif(not pdfa.trova_gs() or not pdfa._icc(), reason="Ghostscript non disponibile")
PDF = ("ordinario.pdf", "font_non_incorporati.pdf", "immagini_grandi.pdf", "multipagina_grande.pdf", "cifrato.pdf",
       "protetto_senza_password.pdf", "troncato.pdf", "firmato_simulato.pdf", "falso_pdfa.pdf", "javascript.pdf",
       "trasparenza.pdf", "non_pdf.pdf")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    d = tmp_path_factory.mktemp("corpus")
    voci = genera_corpus(d)
    return d, voci


@pytest.fixture
def senza_verapdf(monkeypatch):
    monkeypatch.setattr(pdfa, "trova_verapdf", lambda: None)


def test_corpus_completo_e_sintetico(corpus):
    d, voci = corpus
    for n in PDF:
        assert n in voci, n
    indice = json.loads((d / "corpus.json").read_text(encoding="utf-8"))
    assert indice["sintetico"] is True and "simulata" in indice["nota"]
    assert voci["immagini_grandi.pdf"]["bytes"] > 5_242_880        # oltre 5 MB in entrambe le unita'
    for n, v in voci.items():
        assert sha(v["percorso"]) == v["sha256"]


def test_analisi_esiti_espliciti(corpus):
    d, voci = corpus
    for n, v in voci.items():
        a = pdfa.analizza_pdf(v["percorso"])
        assert a["esito"] == v["atteso"]["analisi"], (n, a)
        if a["esito"] in ("protetto", "danneggiato"):
            assert a["dettaglio"]
    f = pdfa.analizza_pdf(d / "firmato_simulato.pdf")
    assert f["firme_digitali"] == 1 and any("firma" in x for x in f["avvisi"])
    falso = pdfa.analizza_pdf(d / "falso_pdfa.pdf")
    assert falso["dichiara_pdfa"] == "1b" and any("non e' verificata" in x for x in falso["avvisi"])
    assert pdfa.analizza_pdf(d / "protetto_senza_password.pdf")["apribile_senza_password"] is True


def test_strutturale_originali_respinti_con_motivi(corpus):
    d, voci = corpus
    for n in PDF:
        v = verifica_strutturale_pdfa(d / n)
        assert v["esito"] == voci[n]["atteso"]["strutturale_originale"], (n, v["motivi"])
        assert v["esito"] in ("indicativo_ok", "indicativo_ko")            # mai "conforme"
    codici = lambda n: {m["codice"] for m in verifica_strutturale_pdfa(d / n)["motivi"]}
    # i metadati PDF/A da soli non bastano
    assert {"PDFA_FONT", "PDFA_OUTPUTINTENT"} <= codici("falso_pdfa.pdf")
    assert "PDFA_XMP_PDFAID" not in codici("falso_pdfa.pdf")
    assert "PDFA_JAVASCRIPT" in codici("javascript.pdf")
    assert "PDFA_TRASPARENZA" in codici("trasparenza.pdf")
    assert "PDFA_CIFRATURA" in codici("cifrato.pdf")
    assert "PDFA_HEADER" in codici("non_pdf.pdf")
    assert codici("troncato.pdf") & {"PDFA_LEGGIBILITA", "PDFA_TRAILER_ID"}


@gs_ok
def test_a11_ordinario_convertito_pagine_testo_originale(corpus, tmp_path, senza_verapdf):
    d, _ = corpus
    src, dst = d / "ordinario.pdf", tmp_path / "ordinario_pdfa.pdf"
    h0 = sha(src)
    r = pdfa.converti_in_pdfa(src, dst)
    assert r["comando_ok"], r["stderr"]
    assert sha(src) == h0                                                     # originale invariato
    assert pdfa.analizza_pdf(dst)["pagine"] == 3                              # nessuna pagina persa
    t_src, t_dst = estrai_pagine(src), estrai_pagine(dst)
    assert len(t_dst) == 3 and all(f"Pagina {i} di 3" in t_dst[i - 1] for i in (1, 2, 3))
    assert "è così" in t_src[0]
    conf = confronta_testo(t_src, t_dst)
    assert conf["divergenti"] == []
    if "è così" not in t_dst[0]:
        # LIMITE NOTO (Ghostscript 10.02.1): ToUnicode del TrueType incorporato non conservato; deve emergere
        # come differenza minore segnalata, mai in silenzio.
        assert conf["differenze"] and conf["differenze"][0]["pagina"] == 1 and conf["differenze"][0]["caratteri_persi"]
    v = pdfa.valida_pdfa(dst)
    assert v["esito"] == "non_verificato" and v["esito_collaudo"] == "da_collaudare"
    assert v["verifica_indicativa"]["esito"] == "indicativo_ok", v["verifica_indicativa"]["motivi"]
    from successioni.documenti.anteprima import confronta_visivo
    assert confronta_visivo(src, dst)["esito"] == "simili"


@gs_ok
@pytest.mark.parametrize("nome", ["font_non_incorporati.pdf", "javascript.pdf", "trasparenza.pdf",
                                  "firmato_simulato.pdf", "falso_pdfa.pdf", "immagini_grandi.pdf"])
def test_a11_derivati_strutturalmente_puliti(corpus, tmp_path, nome, senza_verapdf):
    d, _ = corpus
    dst = tmp_path / "out.pdf"
    assert pdfa.converti_in_pdfa(d / nome, dst)["comando_ok"]
    assert pdfa.analizza_pdf(dst)["pagine"] == pdfa.analizza_pdf(d / nome)["pagine"]
    v = pdfa.valida_pdfa(dst)
    assert v["esito"] == "non_verificato"
    assert v["verifica_indicativa"]["esito"] == "indicativo_ok", v["verifica_indicativa"]["motivi"]


def test_a11_non_conforme_respinto_e_mai_conforme_senza_validatore(corpus, senza_verapdf):
    d, voci = corpus
    for n in ("font_non_incorporati.pdf", "falso_pdfa.pdf", "javascript.pdf"):
        v = pdfa.valida_pdfa(d / n)
        assert v["esito"] == "non_verificato" and v["verifica_indicativa"]["esito"] == "indicativo_ko"
    if "gia_pdfa.pdf" in voci:                      # anche un PDF/A strutturalmente pulito non e' "conforme"
        v = pdfa.valida_pdfa(d / "gia_pdfa.pdf")
        assert v["esito"] == "non_verificato" and v["verifica_indicativa"]["esito"] == "indicativo_ok"


def _finto_verapdf(tmp_path, xml: str, rc: int = 0) -> str:
    """SIMULAZIONE dell'eseguibile veraPDF: stampa un rapporto MRR preparato (solo per provare l'adattatore)."""
    rapporto = tmp_path / "rapporto.xml"
    rapporto.write_text(xml, encoding="utf-8")
    script = tmp_path / "finto_verapdf.py"
    script.write_text(f"import sys\nif '--version' in sys.argv:\n    print('veraPDF FINTO (simulazione)')\n"
                      f"    sys.exit(0)\nsys.stdout.write(open({str(rapporto)!r}, encoding='utf-8').read())\n"
                      f"sys.exit({rc})\n", encoding="utf-8")
    if os.name == "nt":
        cmd = tmp_path / "finto_verapdf.cmd"
        cmd.write_text(f'@"{sys.executable}" "{script}" %*\n')
    else:
        cmd = tmp_path / "finto_verapdf"
        cmd.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n')
        cmd.chmod(cmd.stat().st_mode | stat.S_IEXEC)
    return str(cmd)


MRR = ('<?xml version="1.0" encoding="utf-8"?><report><jobs><job><validationReport profileName="PDF/A-1B '
       'validation profile" statement="{stato}" isCompliant="{c}"><details>{regole}</details></validationReport>'
       '</job></jobs></report>')
REGOLA = ('<rule specification="ISO 19005-1:2005" clause="6.3.4" testNumber="1" status="failed"><description>'
          'The font programs for all fonts used within a conforming file shall be embedded</description></rule>')


def test_adattatore_verapdf_simulato(corpus, tmp_path, monkeypatch):
    """Adattatore con un veraPDF SIMULATO: prova l'interpretazione del rapporto, non la conformita' reale."""
    d, _ = corpus
    (tmp_path / "ok").mkdir()
    monkeypatch.setenv("SUCCESSIONI_VERAPDF", _finto_verapdf(tmp_path / "ok", MRR.format(
        stato="PDF file is compliant", c="true", regole="")))
    v = pdfa.valida_pdfa(d / "ordinario.pdf")
    assert v["esito"] == "conforme" and "FINTO" in v["versione_validatore"]
    (tmp_path / "ko").mkdir()
    monkeypatch.setenv("SUCCESSIONI_VERAPDF", _finto_verapdf(tmp_path / "ko", MRR.format(
        stato="PDF file is not compliant", c="false", regole=REGOLA), rc=1))
    v = pdfa.valida_pdfa(d / "font_non_incorporati.pdf")
    assert v["esito"] == "non_conforme" and v["regole_fallite"][0]["clausola"] == "6.3.4"
    (tmp_path / "rotto").mkdir()
    monkeypatch.setenv("SUCCESSIONI_VERAPDF", _finto_verapdf(tmp_path / "rotto", "non e' XML", rc=7))
    v = pdfa.valida_pdfa(d / "ordinario.pdf")
    assert v["esito"] == "non_verificato" and "non interpretabile" in v["motivo"]


@pytest.mark.skipif(not pdfa.trova_verapdf() or not pdfa.trova_gs(),
                    reason="collaudo A11 reale: richiede veraPDF (SUCCESSIONI_VERAPDF) e Ghostscript; vedi docs/PDFA.md")
def test_a11_collaudo_reale_verapdf(corpus, tmp_path):
    d, _ = corpus
    dst = tmp_path / "ordinario_pdfa.pdf"
    assert pdfa.converti_in_pdfa(d / "ordinario.pdf", dst)["comando_ok"]
    assert pdfa.valida_pdfa(dst)["esito"] == "conforme"
    assert pdfa.valida_pdfa(d / "font_non_incorporati.pdf")["esito"] == "non_conforme"
    assert pdfa.valida_pdfa(d / "falso_pdfa.pdf")["esito"] == "non_conforme"


@gs_ok
def test_collaudo_a11_scrive_evidenza(corpus, senza_verapdf):
    d, _ = corpus
    r = collaudo_a11(d)
    assert (d / "collaudo_a11.json").exists()
    assert r["esito_collaudo_a11"] == "da_collaudare"
    assert all(x["originale_invariato"] for x in r["risultati"])
    assert all(x["analisi_come_attesa"] for x in r["risultati"])
    assert not any(x.get("validazione_derivato") == "conforme" for x in r["risultati"])


# --------------------------------------------------------------------------------------------- A12 (servizio)

@pytest.fixture
def servizio(tmp_path):
    from successioni.archivio import Archivio
    from successioni.servizio import Servizio
    sv = Servizio(Archivio(tmp_path / "dati"))
    return sv, sv.crea_pratica("Prova A12")["pratica_id"]


def test_a12_protetto_danneggiato_nonpdf_tiff_esiti_espliciti(corpus, servizio):
    d, _ = corpus
    sv, pid = servizio
    attesi = {"cifrato.pdf": "protetto", "protetto_senza_password.pdf": "protetto", "troncato.pdf": "danneggiato",
              "non_pdf.pdf": "non_pdf", "tiff_colori_lzw.tif": "tiff"}
    for nome, esito in attesi.items():
        a = sv.acquisisci_file(pid, d / nome)
        r = sv.prepara_pdfa(a["allegato_id"])
        assert r["esito"] == esito and r["derivato"] is None, (nome, r)
        if esito != "non_pdf":
            assert r["motivo"]
        orig = [x for x in sv.elenca_allegati(pid) if x["id"] == a["allegato_id"]][0]
        assert (sv.arch.base / orig["percorso"]).read_bytes() == (d / nome).read_bytes()
    r = sv.prepara_pdfa(sv.acquisisci_file(pid, d / "tiff_colori_lzw.tif")["allegato_id"])
    assert r["verifica_tiff"]["esito"] == "indicativo_ko"
    assert [x["ruolo"] for x in sv.elenca_allegati(pid)] == ["originale"] * 6        # nessun derivato


@gs_ok
def test_a12_firmato_avviso_firma_non_conservata(corpus, servizio, senza_verapdf):
    d, _ = corpus
    sv, pid = servizio
    a = sv.acquisisci_file(pid, d / "firmato_simulato.pdf", tipo_eg="Altro", finalita="prova firma simulata")
    assert a["analisi"]["esito"] == "firmato"
    r = sv.prepara_pdfa(a["allegato_id"])
    assert r["esito"] == "non_verificato" and r["derivato"]["ruolo"] == "derivato"
    assert any("NON conserva la firma" in x for x in r["avvisi"])
    assert r["derivato"]["analisi"]["firme_digitali"] == 0                     # la firma non c'e' piu'
    assert r["derivato"]["rapporto"]["verifica_testo"]["divergenti"] == []
    lista = sv.elenca_allegati(pid)
    assert lista[1]["origine_id"] == a["allegato_id"]
    assert (sv.arch.base / lista[0]["percorso"]).read_bytes() == (d / "firmato_simulato.pdf").read_bytes()


@gs_ok
def test_a12_oltre_limite_suddiviso_e_collegato(corpus, servizio, senza_verapdf):
    d, _ = corpus
    sv, pid = servizio
    a = sv.acquisisci_file(pid, d / "multipagina_grande.pdf")
    r = sv.suddividi_allegato(a["allegato_id"], limite_byte=60_000)
    assert r["azione"] in ("suddivisione", "riduzione+suddivisione") and len(r["parti"]) >= 3
    assert sum(p["analisi"]["pagine"] for p in r["parti"]) == 40
    assert all(p["bytes"] <= 60_000 and p["ruolo"] == "derivato" for p in r["parti"])
    assert r["rapporto"]["originale_invariato"] and r["rapporto"]["verifica_testo"]["divergenti"] == []
    lista = sv.elenca_allegati(pid)
    assert {x["origine_id"] for x in lista if x["ruolo"] == "derivato"} == {a["allegato_id"]}
    intervalli = [x["rapporto"]["suddivisione"]["parte"]["pagine_sorgente"] for x in lista if x["ruolo"] == "derivato"]
    assert sorted(intervalli)[0][0] == 1 and sorted(intervalli)[-1][1] == 40
