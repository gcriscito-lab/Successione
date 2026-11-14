"""Carta intestata comune delle stampe e brogliaccio per la stampa (14/11/2026). Dati SINTETICI."""
import io
import json

from pypdf import PdfReader

from successioni import brogliaccio as B
from successioni import carta_intestata as CI
from successioni import impostazioni
from successioni.fascicolo import _copertina

STUDIO = {"nome": "Studio Prova", "indirizzo": "Via Roma 1", "cap_comune": "00100 Roma (RM)", "telefono": "06 123",
          "email": "studio@esempio.it", "pec": "", "cf_piva": "01234567890"}


def test_righe_studio_saltano_le_voci_vuote():
    assert CI.righe_studio(STUDIO) == ["Studio Prova", "Via Roma 1", "00100 Roma (RM)", "Tel. 06 123 – studio@esempio.it",
                                       "C.F./P.IVA 01234567890"]
    assert CI.righe_studio({}) == [] and CI.righe_studio({"nome": "Solo nome"}) == ["Solo nome"]


def test_dati_studio_ripiega_sul_nome_dello_studio(tmp_path, monkeypatch):
    monkeypatch.delenv("SUCCESSIONI_CONFIG", raising=False)
    (tmp_path / "configurazione.json").write_text(json.dumps({"interfaccia": {"nome_studio": "Studio dal file"}}), encoding="utf-8")
    monkeypatch.delattr(impostazioni, "intestazione_studio", raising=False)
    d = CI.dati_studio(tmp_path)
    assert set(d) == set(CI.CHIAVI_STUDIO) and d["nome"] == "Studio dal file" and d["indirizzo"] == ""
    # con la funzione delle impostazioni (contratto concordato): i suoi valori, il nome dal file solo se manca
    monkeypatch.setattr(impostazioni, "intestazione_studio", lambda c=None: {"nome": "", "indirizzo": "Via X 2", "altro": "no"},
                        raising=False)
    d = CI.dati_studio(tmp_path)
    assert d["nome"] == "Studio dal file" and d["indirizzo"] == "Via X 2" and "altro" not in d
    monkeypatch.setattr(impostazioni, "intestazione_studio", lambda c=None: 1 / 0, raising=False)
    assert CI.dati_studio(tmp_path)["nome"] == "Studio dal file"          # un errore non blocca la stampa


def test_pagina_testo_in_escape_e_numeri_di_pagina():
    h = CI.pagina(titolo_finestra='Pratica </style><script>x</script> "a"', studio={"nome": "<b>S</b>"},
                  riferimento=["Doc", "del 01/01/2026"], corpo="<p>corpo</p>")
    assert "<script>" not in h and h.count("</style>") == 1 and "&lt;b&gt;S&lt;/b&gt;" in h
    assert 'counter(page) " di " counter(pages)' in h and "size:A4;" in h
    assert "landscape" in CI.pagina(titolo_finestra="t", studio={}, riferimento=[], corpo="", orizzontale=True)


def test_accenti():
    assert CI.accenti("Proprieta'") == "Proprietà" and CI.accenti("nuda proprieta', usufrutto") == "nuda proprietà, usufrutto"
    assert CI.accenti("dell'erede") == "dell'erede" and CI.accenti("") == ""


def _dati():
    return {"persone": [{"id": "p1", "ruolo": "erede", "cognome": "ROSSI", "nome": "ANNA", "codice_fiscale": "RSSNNA70A41H501J"}],
            "beni": [{"id": "b1", "tipo": "fabbricato", "comune": "ROMA", "provincia": "RM", "foglio": "100", "particella": "200",
                      "subalterno": "3", "categoria": "A2", "valore": "126000", "rendita": "1000.00", "consistenza": "5.50",
                      "diritto": "1", "quota_defunto": "1/1", "data_visura": "2025-01-20", "indirizzo": "VIA ESEMPIO 1"},
                     {"id": "b2", "tipo": "terreno", "comune": "ROMA", "foglio": "10", "particella": "20", "valore": "15000",
                      "reddito_dominicale": "12.34", "diritto": "1", "quota_defunto": "1/2"}],
            "devoluzioni": [{"id": "d1", "bene_id": "b1", "persona_id": "p1", "diritto": "1", "quota": "1/2"}]}


def test_brogliaccio_su_carta_intestata_orizzontale():
    h = B.html(_dati(), titolo="Prova", revisione=2, studio=STUDIO)
    assert "Studio Prova" in h and "Brogliaccio di lavoro" in h and "landscape" in h and "revisione 2" in h
    for breve in ("Fg.", "Part.", "Sub.", "Cat.", "Cons.", "Rendita / R.D."):
        assert f">{breve}</th>" in h
    assert 'title="Foglio"' in h                                   # nome intero nel suggerimento
    assert "Proprietà" in h and "Proprieta'" not in h
    assert "126.000" in h and "1.000,00" in h and "5,50" in h and "12,34" in h and "20/01/2025" in h
    assert "Totale dei beni" in h and "141.000" in h               # somma dei valori inseriti, solo da leggere
    assert "manca 1/2" in h and 'class="esito no"' in h            # quota del fabbricato incompleta
    assert "VIA ESEMPIO 1" in h and "Terreno" in h                 # descrizione, o il tipo se manca


def test_brogliaccio_senza_studio_e_valori_non_numerici():
    d = _dati()
    d["beni"][1]["valore"] = {"stato": "da_confermare"}
    h = B.html(d, titolo="Prova", studio="")
    assert "alcuni valori non indicati" in h and "[da confermare]" in h


def test_copertina_del_fascicolo_con_lo_studio():
    pdf = _copertina("Pratica di prova", [("Modello", 3)], [], CI.righe_studio(STUDIO))
    testo = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    assert "Studio Prova" in testo and "Via Roma 1" in testo and "Fascicolo per il cliente" in testo
    assert "Studio Prova" not in PdfReader(io.BytesIO(_copertina("Pratica", [], []))).pages[0].extract_text()
