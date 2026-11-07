"""Salvataggi delle impostazioni in parallelo (le richieste web girano in thread): nessun errore e nessuna modifica persa."""
import threading

from successioni import impostazioni


def test_salvataggi_paralleli_non_si_perdono(tmp_path, monkeypatch):
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "configurazione.json"))
    errori = []

    def salva(chiave, valore):
        try:
            for _ in range(10):
                impostazioni.salva({}, interfaccia={chiave: valore})
        except Exception as e:      # noqa: BLE001 - il test deve vedere qualunque errore
            errori.append(e)

    t = [threading.Thread(target=salva, args=a) for a in (("larghezza_nav", 300), ("larghezza_pannello", 420))]
    for x in t:
        x.start()
    for x in t:
        x.join()
    assert not errori
    finale = impostazioni.stato()["interfaccia"]
    assert finale["larghezza_nav"] == 300 and finale["larghezza_pannello"] == 420
