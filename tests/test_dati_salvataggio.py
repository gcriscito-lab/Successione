"""Correzioni dei problemi di dati e salvataggio del collaudo GUI (docs/analisi/collaudo_gui.md, n. 2, 3, 5, 6, 10, 12).
Solo dati sintetici."""
import re
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from successioni import codici as C
from successioni import quadri as Q
from successioni import schema as S
from successioni import valori as V
from successioni.archivio import Archivio
from successioni.errori import DatiNonValidi
from successioni.servizio import Servizio
from successioni.telematico.esporta import codice_enum
from successioni.telematico.quadri_efgh import _flag
from successioni.web import crea_app, strutturati_completi

JS = (Path(__file__).parent.parent / "src" / "successioni" / "static" / "app.js").read_text(encoding="utf-8")


@pytest.fixture
def sv(tmp_path):
    return Servizio(Archivio(tmp_path / "d"))


def op(coll, id=None, **campi):
    return {"op": "upsert", "coll": coll, **({"id": id} if id else {}), "campi": campi}


# --------------------------------------------------------------- n.3 messaggi leggibili
def test_messaggio_quota_senza_gergo():
    with pytest.raises(V.ValoreNonValido) as e:
        V.parse_quota("abc")
    assert "num/den" not in str(e.value) and "1/2" in str(e.value)
    for cattiva in ({"num": 1, "den": 0}, {"num": 3, "den": 2}, {"num": 1.5, "den": 2}):
        with pytest.raises(V.ValoreNonValido) as e:
            V.parse_quota(cattiva)
        assert "1/2" in str(e.value)


def test_messaggio_importo_indica_il_formato():
    with pytest.raises(V.ValoreNonValido) as e:
        V.parse_importo("12,5")
    assert "punto" in str(e.value) and "1234.50" in str(e.value)
    with pytest.raises(V.ValoreNonValido) as e:
        V.parse_importo("12x")
    assert "1234.50" in str(e.value)


def test_messaggi_data_e_codice_fiscale_indicano_il_formato():
    (e,) = S.valida_campo("data", "10/02/1970", "p", {})
    assert "GG/MM/AAAA" in e.messaggio and "AAAA-MM-GG" in e.messaggio
    (e,) = S.valida_campo("data", "1970-02-31", "p", {})
    assert "inesistente" in e.messaggio and "GG/MM/AAAA" in e.messaggio
    (e,) = S.valida_campo("cf", "ABC123", "p", {})
    assert "16 caratteri" in e.messaggio and "senza spazi" in e.messaggio
    assert S.valida_campo("data", "1970-02-10", "p", {}) == []


def test_errore_di_salvataggio_ha_percorso_e_messaggio_senza_gergo(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    with pytest.raises(DatiNonValidi) as e:
        sv.aggiorna(pid, 1, [op("beni", "b_aaaa1111", tipo="titolo", valore="12,5", quota_defunto="abc")])
    errori = e.value.dettagli["errori"]
    assert {x["percorso"] for x in errori} == {"beni[b_aaaa1111].valore", "beni[b_aaaa1111].quota_defunto"}
    assert not any("num/den" in x["messaggio"] for x in errori)


# --------------------------------------------------------------- n.12 identificativo
def test_identificativo_non_valido_dice_il_formato(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    with pytest.raises(DatiNonValidi) as e:
        sv.aggiorna(pid, 1, [op("beni", "b_fab", tipo="fabbricato")])
    m = e.value.messaggio
    assert "'b_fab'" in m and "formato atteso" in m and "p_a1b2c3d4" in m
    # l'esempio del messaggio e' davvero un identificativo valido
    assert re.fullmatch(r"[a-z]{1,4}_[a-z0-9]{4,32}", "p_a1b2c3d4")
    sv.aggiorna(pid, 1, [op("beni", "b_a1b2c3d4", tipo="fabbricato")])


# --------------------------------------------------------------- n.2 quadro non attivo
def test_riga_in_quadro_non_attivo_con_selezione_nella_stessa_scrittura(sv):
    """Le operazioni che la GUI invia: set quadri_attivi + upsert, in un'unica revisione."""
    pid = sv.crea_pratica("X")["pratica_id"]
    codici = lambda: [r["codice"] for r in sv.verifica(pid)["rilievi"]]
    sv.aggiorna(pid, 1, [op("beni", "b_aaaa1111", tipo="titolo", tipo_titolo="2")])
    assert "DATI_IN_QUADRO_NON_ATTIVO" in codici()                     # il difetto: riga senza selezione
    rev = sv.leggi(pid)["revisione"]
    sv.aggiorna(pid, rev, [{"op": "set", "sezione": "opzioni",
                            "campi": {"quadri_attivi": list(Q.PREDEFINITI) + ["EO"]}}])
    assert "DATI_IN_QUADRO_NON_ATTIVO" not in codici()
    st = {q["id"]: q for q in sv.quadri(pid)["quadri"]}
    assert st["EO"]["attivo"] and st["EO"]["stato"] != "inattivo"


def test_la_gui_attiva_il_quadro_della_nuova_riga():
    assert "daAttivare" in JS and "quadri_attivi" in JS.split("const daAttivare")[1][:900]
    assert "quadroBene(n.campi)" in JS


# --------------------------------------------------------------- n.5 alias dei menu
def test_alias_coincidono_con_l_esportazione():
    al = C.alias()
    assert set(al) == set(C.ALIAS_DESCRIZIONE)
    for chiave, m in al.items():
        tipo = C.REGOLE[chiave][0]
        assert m
        for alias, codice in m.items():
            assert codice_enum(alias, tipo, alias_descrizione=True) == codice, (chiave, alias)
    assert al["beni.diritto@immobile"].get("proprieta") == "1"


def test_gli_alias_arrivano_nei_menu_senza_cambiare_le_voci():
    s = C.strutturati()
    assert s["beni.diritto@immobile"]["alias"]["proprieta"] == "1"
    assert "alias" not in s["persone.grado_parentela"]
    assert all(set(o) == {"valore", "etichetta", "aiuto"} for o in s["beni.diritto@immobile"]["opzioni"])


def test_la_gui_riconosce_gli_alias_e_non_taglia_i_menu():
    assert "riconosciVoce" in JS and "sd.alias" in JS
    assert "text-overflow:ellipsis" in JS and "title: testoVoce" in JS


# --------------------------------------------------------------- n.6 menu e suggerimenti
def test_flag_si_no_sono_menu_coerenti_con_l_esportazione():
    s = strutturati_completi()
    for chiave in ("beni.discordanza_intestatario", "beni.passaggi_senza_atti_legali", "beni.sistema_tavolare"):
        d = s[chiave]
        assert [o["valore"] for o in d["opzioni"]] == ["si", "no"] and d["senza_codice"]
        assert S.COLLEZIONI["beni"][chiave.split(".")[1]] == "str"            # il dato resta testo
        assert _flag("si") is True and _flag("no") is False                      # come lo legge l'esportazione
        for a, v in d["alias"].items():
            assert _flag(a) == (v == "si"), (chiave, a)
    assert Q.quadro_di("beni", {"tipo": "terreno", "sistema_tavolare": "si"}) == "EL"
    assert Q.quadro_di("beni", {"tipo": "terreno", "sistema_tavolare": "no"}) == "EB"


def test_schema_web_espone_i_suggerimenti(tmp_path):
    with TestClient(crea_app(Servizio(Archivio(tmp_path / "d")), token="sintetico", ammetti_host_di_prova=True)) as cl:
        j = cl.get("/api/schema?t=sintetico").json()
    sug = j["suggerimenti"]
    assert set(sug) == set(C.SUGGERIMENTI)
    comuni = sug["beni.codice_comune_catastale"]["valori"]
    uffici = sug["dichiarazione.testamento.ufficio_registrazione"]["valori"]
    assert len(comuni) == len(set(comuni)) == len(C.voci("ComuniCatastaliTNBZ_Type")) > C.SOGLIA_MENU
    assert len(uffici) == len(set(uffici)) == len(C.voci("UfficioDiRegistrazione_Type")) > C.SOGLIA_MENU
    for v in comuni[:20]:
        assert codice_enum(v, "ComuniCatastaliTNBZ_Type") == v
    assert "listaSuggerimenti(" in JS and 'h("datalist"' in JS


def test_relazione_con_defunto_non_e_piu_una_colonna_duplicata():
    ea = Q.PER_ID["EA"]
    assert "grado_parentela" in ea["colonne"] and "relazione_con_defunto" not in ea["colonne"]
    assert "relazione_con_defunto" in ea["campi"] if ea.get("campi") else True
    assert "continue;" in JS.split('c === "relazione_con_defunto"')[1][:300]


def test_nazionalita_resta_testo_con_limite_dell_xsd():
    assert S.COLLEZIONI["beni"]["nazionalita"] == "str"
    assert "beni.nazionalita" not in strutturati_completi()
    assert '"beni.nazionalita": 20' in JS


# --------------------------------------------------------------- n.10 quadri generati
def test_quadri_generati_sono_marcati_e_non_si_selezionano():
    generati = {q["id"] for q in Q.QUADRI if q.get("generato")}
    assert generati == {"EE", "EF", "EH", "EI"}
    assert all(not Q.PER_ID[i]["supportato"] for i in generati)
    assert not generati & set(Q.PREDEFINITI)
    assert "Seleziona il quadro (blocca la finalizzazione)" in JS            # resta solo per i quadri non generati
    blocco = JS.split("function renderNonSupp")[1].split("main.append(h(\"div\", { class: \"nota\" }, \"Il quadro \" + q.id")[0]
    assert "q.generato" in blocco and "return;" in blocco and "Seleziona" not in blocco


def test_un_quadro_generato_gia_selezionato_continua_a_bloccare(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [{"op": "set", "sezione": "opzioni", "campi": {"quadri_attivi": ["EA", "EE"]}}])
    assert any(r["codice"] == "QUADRO_NON_SUPPORTATO" and "EE" in r["percorso"] for r in sv.verifica(pid)["rilievi"])


# --------------------------------------------------------------- date
def test_la_gui_converte_le_date_prima_dell_invio():
    assert "function dataIso" in JS and "function dataIt" in JS
    assert 'kind === "data") return dataIso(t)' in JS and 'GG/MM/AAAA' in JS
