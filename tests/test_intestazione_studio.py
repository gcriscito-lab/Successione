"""Intestazione dello studio per le stampe (carta intestata, 14/11/2026): sezione `intestazione` delle impostazioni, letta dalle
stampe con impostazioni.intestazione_studio(). Dati SINTETICI."""
import json

import pytest

from successioni import impostazioni
from successioni.errori import DatiNonValidi

CHIAVI = ("nome", "indirizzo", "cap_comune", "telefono", "email", "pec", "cf_piva")


@pytest.fixture(autouse=True)
def _config(monkeypatch, tmp_path):
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "cfg" / "configurazione.json"))


def test_vuota_restituisce_tutte_le_chiavi():
    assert impostazioni.intestazione_studio() == {k: "" for k in CHIAVI}


def test_nome_ripiega_sul_nome_dello_studio():
    impostazioni.salva({}, interfaccia={"nome_studio": "Studio Prova"})
    assert impostazioni.intestazione_studio()["nome"] == "Studio Prova"
    impostazioni.salva({}, intestazione={"nome": "Studio Prova Associati"})
    assert impostazioni.intestazione_studio()["nome"] == "Studio Prova Associati"


def test_salvataggio_rilettura_e_normalizzazione():
    r = impostazioni.salva({}, intestazione={"nome": "  Studio   Bianchi ", "indirizzo": "Via Roma 1",
                                              "cap_comune": "00100 Roma (RM)", "telefono": "06 1234567",
                                              "email": "studio@esempio.it", "pec": "studio@pec.esempio.it",
                                              "cf_piva": "12345678901"})
    i = impostazioni.intestazione_studio()
    assert i["nome"] == "Studio Bianchi" and i["cf_piva"] == "12345678901" and i["pec"] == "studio@pec.esempio.it"
    assert r["intestazione"] == i                                            # anche lo stato per l'interfaccia
    # salvata intera: un campo lasciato vuoto si toglie
    impostazioni.salva({}, intestazione={"nome": "Studio Bianchi"})
    assert impostazioni.intestazione_studio()["telefono"] == ""


def test_codice_fiscale_in_maiuscolo():
    impostazioni.salva({}, intestazione={"cf_piva": "rssmra40a01h501k"})
    assert impostazioni.intestazione_studio()["cf_piva"] == "RSSMRA40A01H501K"


@pytest.mark.parametrize("valori", [
    {"nome": "Studio\nRossi"}, {"indirizzo": "x" * 101}, {"email": "non-una-mail"}, {"pec": "a@b"},
    {"cf_piva": "123"}, {"cf_piva": "ABCDEFGHIJKLMNOPQ"}, {"password": "segreta"}, {"telefono": 123}, "testo"])
def test_valori_rifiutati_senza_scrivere(valori, tmp_path):
    with pytest.raises(DatiNonValidi):
        impostazioni.salva({}, intestazione=valori)
    assert not (tmp_path / "cfg" / "configurazione.json").exists()


def test_inclusa_nel_backup_della_configurazione():
    impostazioni.salva({}, intestazione={"nome": "Studio Bianchi"})
    conf = json.loads(impostazioni.file_configurazione().read_text(encoding="utf-8"))
    assert impostazioni.contenuto_per_backup(conf)["intestazione"] == {"nome": "Studio Bianchi"}


def test_file_rovinato_non_blocca_le_stampe(tmp_path):
    f = tmp_path / "cfg" / "configurazione.json"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps({"intestazione": {"nome": "a\nb"}}), encoding="utf-8")
    assert impostazioni.intestazione_studio() == {k: "" for k in CHIAVI}
