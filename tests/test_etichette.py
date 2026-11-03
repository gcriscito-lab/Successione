"""Etichette e ordine dei campi: coerenza con lo schema, con i quadri e con /api/schema."""
from successioni import etichette as E, quadri as Q, schema as S


def test_ogni_campo_ha_etichetta_senza_underscore():
    for coll, campi in S.COLLEZIONI.items():
        for c in campi:
            assert c in E.ETICHETTE[coll], f"manca etichetta {coll}.{c}"
    for coll, d in E.ETICHETTE.items():
        assert coll in S.COLLEZIONI
        for c, t in d.items():
            assert c in S.COLLEZIONI[coll], f"etichetta di un campo inesistente {coll}.{c}"
            assert "_" not in t and t.strip() and t[0].isupper(), t
    for t in list(E.ETICHETTE_QUADRO.values()) + list(E.ETICHETTE_DICHIARAZIONE.values()):
        assert "_" not in t and t[0].isupper(), t
    for d in E.NOMI_VALORI.values():
        for t in d.values():
            assert "_" not in t, t


def test_nomi_valori_coprono_gli_enum():
    for chiave, d in E.NOMI_VALORI.items():
        coll, campo = chiave.split(".")
        assert set(d) == set(S.COLLEZIONI[coll][campo][5:].split("|")), chiave
    assert E.nome_valore("beni", "tipo", "disponibilita_finanziaria") == "Disponibilità finanziaria"
    assert E.nome_valore("persone", "ruolo", "legatario") == "Legatario"
    assert E.nome_valore("beni", "tipo", "xyz") == "xyz"


def test_etichetta_per_quadro_e_fallback():
    assert E.etichetta("beni", "codice_fiscale_emittente") == "Codice fiscale dell'emittente"
    assert E.etichetta("beni", "codice_fiscale_emittente", "EO") == "Codice fiscale della societa'"
    assert E.etichetta("beni", "campo_nuovo_x") == "Campo nuovo x"


def test_ordine_senza_duplicati_e_campi_esistenti():
    for q, ordine in E.ORDINE.items():
        assert len(ordine) == len(set(ordine)), f"duplicati in {q}"
        if q == "AN.dichiarazione":
            assert set(ordine) == set(E.ETICHETTE_DICHIARAZIONE)
        else:
            assert set(ordine) <= set(S.COLLEZIONI[E.COLLEZIONE_QUADRO[q]]), q


def test_ordine_contiene_tutti_i_campi_pertinenti():
    for q in Q.QUADRI:
        if q["id"] in E.ORDINE:
            for c in q.get("colonne", []) + q.get("campi", []):
                assert c in E.ORDINE[q["id"]], (q["id"], c)
    for coll in ("devoluzioni", "passivita", "documenti_ref"):
        q = next(x for x in E.COLLEZIONE_QUADRO if E.COLLEZIONE_QUADRO[x] == coll)
        assert set(E.ORDINE[q]) == set(S.COLLEZIONI[coll])
    # ogni campo dei beni e delle persone compare in almeno un quadro
    for coll, chiavi in (("beni", ["EB", "EC", "EL", "EM", "EN", "EO", "EP", "EQ", "ER"]), ("persone", ["AN", "EA"])):
        usati = set().union(*(E.ORDINE[k] for k in chiavi))
        assert usati == set(S.COLLEZIONI[coll]), set(S.COLLEZIONI[coll]) ^ usati


def test_quadri_ordinati_come_ordine():
    for q in Q.QUADRI:
        for chiave in ("colonne", "campi"):
            if q.get(chiave):
                pos = [E.ORDINE[q["id"]].index(c) for c in q[chiave]]
                assert pos == sorted(pos), (q["id"], chiave)
    assert E.ordina("EA", ["nome", "codice_fiscale", "zzz", "cognome"]) == ["codice_fiscale", "cognome", "nome", "zzz"]
    # il codice fiscale apre il quadro EA, come nel modulo; provincia prima del comune
    assert E.ORDINE["EA"][0] == "codice_fiscale"
    assert E.ORDINE["EA"].index("provincia_nascita") < E.ORDINE["EA"].index("luogo_nascita")
    assert E.ORDINE["EB"].index("foglio") < E.ORDINE["EB"].index("particella") < E.ORDINE["EB"].index("subalterno")


def test_api_schema_espone_etichette_e_ordine(tmp_path):
    from starlette.testclient import TestClient
    from successioni.archivio import Archivio
    from successioni.servizio import Servizio
    from successioni.web import crea_app
    c = TestClient(crea_app(Servizio(Archivio(tmp_path / "d")), token="tk", ammetti_host_di_prova=True),
                   base_url="http://testserver")
    j = c.get("/api/schema", params={"t": "tk"}).json()
    assert j["ordine"]["EA"] == E.ORDINE["EA"]
    assert j["etichette"]["campi"]["beni"]["foglio"] == "Foglio"
    assert j["etichette"]["valori"]["beni.tipo"]["disponibilita_finanziaria"] == "Disponibilità finanziaria"
    assert j["etichette"]["quadro"]["EO.codice_fiscale_emittente"] == "Codice fiscale della societa'"
