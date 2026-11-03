import pytest
from successioni.quadri import quadro_di, attivi, quadro_per_percorso
from successioni.schema import valida_campo, Errore

# ---------------------------------------------------------------------------
# Tests for quadro_di (mapping from collection + entity to quadro id)
# ---------------------------------------------------------------------------

def test_quadro_di_persone_roles():
    assert quadro_di("persone", {"ruolo": "defunto"}) == "AN"
    assert quadro_di("persone", {"ruolo": "presentatore"}) == "AN"
    assert quadro_di("persone", {"ruolo": "erede"}) == "EA"
    # ruolo non riconosciuto o assente -> EA
    assert quadro_di("persone", {"ruolo": "altro"}) == "EA"
    assert quadro_di("persone", {}) == "EA"


def test_quadro_di_beni_tipi():
    mapping = {
        "terreno": "EB",
        "fabbricato": "EC",
        "titolo": "EO",
        "aeromobile": "EP",
        "nave": "EQ",
        "azienda": "EN",
    }
    for tipo, expected in mapping.items():
        assert quadro_di("beni", {"tipo": tipo}) == expected
    # tipo non previsto -> ER
    assert quadro_di("beni", {"tipo": "altro"}) == "ER"
    assert quadro_di("beni", {}) == "ER"


def test_quadro_di_altre_collezioni():
    assert quadro_di("passivita", {}) == "ED"
    assert quadro_di("documenti_ref", {}) == "EG"
    assert quadro_di("devoluzioni", {}) == "DV"
    # collezione sconosciuta restituisce None
    assert quadro_di("qualcosa", {}) is None


def test_quadro_per_percorso_direct_and_indirect():
    # Direct access via quadro[ID]
    assert quadro_per_percorso({}, "quadro[EO]") == "EO"
    # Path that does not match regex – fallback to AN for persone, None otherwise
    assert quadro_per_percorso({"persone": []}, "persone[123]") == "AN"
    assert quadro_per_percorso({}, "altra[xyz]") == "AN"
    # Path with entity present – persone
    dati = {"persone": [{"id": "p1", "ruolo": "defunto"}]}
    assert quadro_per_percorso(dati, "persone[p1]") == "AN"
    # Path with entity present – beni
    dati = {"beni": [{"id": "b1", "tipo": "fabbricato"}]}
    assert quadro_per_percorso(dati, "beni[b1]") == "EC"
    # Devoluzioni always map to DV, even if not present in data
    assert quadro_per_percorso({}, "devoluzioni[qualcosa]") == "DV"

# ---------------------------------------------------------------------------
# Tests for attivi (calcolo dei quadri attivi)
# ---------------------------------------------------------------------------

def test_attivi_default():
    dati = {}
    result = attivi(dati)
    # Deve contenere tutti i PREDEFINITI più i SEMPRE_ATTIVI
    from successioni.quadri import PREDEFINITI, SEMPRE_ATTIVI
    expected = set(PREDEFINITI) | set(SEMPRE_ATTIVI)
    assert result == expected
    # Verifica che i quadri sempre attivi siano presenti
    for q in SEMPRE_ATTIVI:
        assert q in result


def test_attivi_with_selection_and_unknown():
    dati = {"opzioni": {"quadri_attivi": ["EO", "EB", "ZZ"]}}
    result = attivi(dati)
    # ZZ non è una sigla valida, deve essere ignorata
    assert "EO" in result and "EB" in result
    assert "ZZ" not in result
    # I quadri sempre attivi devono comunque comparire
    from successioni.quadri import SEMPRE_ATTIVI
    for q in SEMPRE_ATTIVI:
        assert q in result
    # Nessun altro PREDEFINITO deve comparire
    from successioni.quadri import PREDEFINITI
    for q in PREDEFINITI:
        if q not in {"EO", "EB"}:
            assert q not in result


def test_attivi_empty_selection():
    dati = {"opzioni": {"quadri_attivi": []}}
    result = attivi(dati)
    # Solo i quadri sempre attivi
    from successioni.quadri import SEMPRE_ATTIVI
    assert result == set(SEMPRE_ATTIVI)

# ---------------------------------------------------------------------------
# Tests for schema.valida_campo – new fields and generic validation
# ---------------------------------------------------------------------------

def _run_valida(kind, valore, percorso="test", riferimenti=None):
    if riferimenti is None:
        riferimenti = {}
    return valida_campo(kind, valore, percorso, riferimenti)

def test_valida_campo_str_success_and_failure():
    assert _run_valida("str", "qualcosa") == []
    err = _run_valida("str", 123)
    assert len(err) == 1 and err[0].codice == "VALORE_NON_VALIDO"

def test_valida_campo_cf():
    # Uppercase valido
    assert _run_valida("cf", "ABCDEF12G34H567I") == []
    # Lowercase è accettato (viene convertito in upper)
    assert _run_valida("cf", "abcdef12g34h567i") == []
    # Lunghezza errata
    err = _run_valida("cf", "ABC")
    assert len(err) == 1 and err[0].codice == "VALORE_NON_VALIDO"

def test_valida_campo_data():
    assert _run_valida("data", "2023-01-15") == []
    err1 = _run_valida("data", "15-01-2023")
    err2 = _run_valida("data", "2023-02-30")
    assert len(err1) == 1 and err1[0].codice == "VALORE_NON_VALIDO"
    assert len(err2) == 1 and err2[0].codice == "VALORE_NON_VALIDO"

def test_valida_campo_quota():
    assert _run_valida("quota", {"num": 1, "den": 2}) == []
    assert _run_valida("quota", " 3 / 4 ") == []
    err_den = _run_valida("quota", {"num": 1, "den": 0})
    err_gt = _run_valida("quota", "3/2")
    assert len(err_den) == 1 and err_den[0].codice == "VALORE_NON_VALIDO"
    assert len(err_gt) == 1 and err_gt[0].codice == "VALORE_NON_VALIDO"

def test_valida_campo_importo():
    assert _run_valida("importo", "12345.67") == []
    err = _run_valida("importo", "12,34")
    assert len(err) == 1 and err[0].codice == "VALORE_NON_VALIDO"

def test_valida_campo_enum():
    enum_kind = "enum:" + "|".join(["defunto", "erede", "legatario"])
    assert _run_valida(enum_kind, "defunto") == []
    err = _run_valida(enum_kind, "altro")
    assert len(err) == 1 and err[0].codice == "VALORE_NON_VALIDO"

def test_valida_campo_ref():
    riferimenti = {"persone": {"p1", "p2"}}
    assert _run_valida("ref:persone", "p1", riferimenti=riferimenti) == []
    err = _run_valida("ref:persone", "p3", riferimenti=riferimenti)
    assert len(err) == 1 and err[0].codice == "VALORE_NON_VALIDO"

def test_valida_campo_stato_dict_is_ignored():
    # Quando il valore è un dict con chiave "stato", la funzione restituisce [] indipendentemente dal kind
    assert _run_valida("str", {"stato": "zero"}) == []
    assert _run_valida("cf", {"stato": "assente"}) == []

def test_valida_campo_new_fields_str_and_data():
    # tipo_titolo, quantita, anno_costruzione, partita_tavolare sono tutti "str" nel modello
    for field in ["tipo_titolo", "quantita", "anno_costruzione", "partita_tavolare"]:
        assert _run_valida("str", "qualcosa") == []
    # data_documento è di tipo "data"
    assert _run_valida("data", "2022-12-31") == []
    err = _run_valida("data", "31/12/2022")
    assert len(err) == 1 and err[0].codice == "VALORE_NON_VALIDO"


@pytest.mark.parametrize("prov", ["BZ", "TN", "GO", "TS", "bz", "ts"])
def test_quadro_di_tutte_le_province_tavolari(prov):
    assert quadro_di("beni", {"tipo": "terreno", "provincia": prov}) == "EL"
    assert quadro_di("beni", {"tipo": "fabbricato", "provincia": prov}) == "EM"


def test_quadro_di_altre_province_e_tipi_non_immobiliari_non_sono_tavolari():
    assert quadro_di("beni", {"tipo": "terreno", "provincia": "RM"}) == "EB"
    assert quadro_di("beni", {"tipo": "titolo", "provincia": "BZ"}) == "EO"   # la provincia conta solo per gli immobili
