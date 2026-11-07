"""Rimedio per ogni rilievo dei controlli interni: dice dove intervenire e con quale comando.

Il testo non contiene regole fiscali: indica solo il quadro, la scheda o il comando da usare. Le regole restano nei
controlli che producono il rilievo (schema.py, quadri.py, telematico/). Un codice non elencato non ha rimedio (None):
l'interfaccia mostra soltanto il messaggio del controllo.
"""
from __future__ import annotations

_DATO_NON_NOTO = "Per un dato non noto scrivi «?» (da confermare), «assente», «zero» o «non applicabile»."

RIMEDI: dict[str, str] = {
    "CF_MANCANTE": "Apri il soggetto nel quadro {quadro} e inserisci il codice fiscale. " + _DATO_NON_NOTO,
    "DEFUNTO_NON_UNICO": "Nel quadro AN deve esserci un solo soggetto con ruolo «defunto»: inseriscilo se manca, "
                         "oppure correggi il ruolo dei soggetti in piu'.",
    "DEVOLUZIONI_ECCEDENTI": "Nel quadro DV riduci le quote delle righe di questo bene e diritto: insieme non possono "
                             "superare 1/1. La somma per bene si vede nella scheda del bene.",
    "DEVOLUZIONI_INCOMPLETE": "Nel quadro DV aggiungi la riga dell'erede o legatario mancante, oppure correggi le quote "
                              "fino a 1/1. La somma per bene si vede nella scheda del bene.",
    "IDENTIFICATIVI_CATASTALI_INCOMPLETI": "Nella scheda dell'immobile (quadro {quadro}) indica foglio e particella come "
                                           "risultano dalla visura.",
    "VALORE_NON_VALIDO": "Correggi il campo indicato nel quadro {quadro}. " + _DATO_NON_NOTO,
    "DATO_MANCANTE": "Compila il campo indicato nel quadro {quadro}.",
    "CAMPO_SCONOSCIUTO": "Il campo non fa parte dello schema della pratica: toglilo con aggiorna_pratica (operazione "
                         "remove) dal client MCP che lo ha scritto.",
    "VISURA_SENZA_DATA": "Nella scheda dell'immobile (quadro {quadro}) indica la data della visura catastale usata.",
    "VISURA_VECCHIA": "Scarica una visura catastale aggiornata, controlla i dati dell'immobile e aggiorna la data della "
                      "visura nella scheda (quadro {quadro}). Il limite in giorni si cambia in Impostazioni.",
    "QUADRO_NON_SUPPORTATO": "Se il quadro {quadro} non serve, deselezionalo dalla sua pagina. Se serve, la dichiarazione "
                             "va completata con un altro strumento: il programma conserva la bozza.",
    "DATI_IN_QUADRO_NON_ATTIVO": "Seleziona il quadro {quadro} se quei dati vanno dichiarati, altrimenti elimina le righe "
                                 "dal quadro.",
    "ALLEGATO_OBBLIGATORIO_MANCANTE": "Carica il documento in «File e invio», preparalo in PDF/A e collegalo nel quadro EG "
                                      "al rigo indicato nel messaggio.",
    "ALLEGATO_NON_CONFORME": "Riprepara il documento in PDF/A da «File e invio» e ripeti la verifica del file.",
    "QUADRO_OBBLIGATORIO_NON_SUPPORTATO": "Compila i dati da cui il programma genera il quadro {quadro} (vedi il "
                                          "messaggio); se il caso non e' supportato la dichiarazione va completata con un "
                                          "altro strumento.",
    "VALORE_SOTTO_CATASTALE": "Nella scheda dell'immobile (quadro {quadro}) controlla il valore: «Usa il valore catastale» "
                              "inserisce il minimo proposto, altrimenti resta il valore indicato da te.",
    # avvisi di qualita' dei dati (qualita.py)
    "SPAZI_ANOMALI": "Riscrivi il campo nel quadro {quadro} senza spazi doppi, iniziali o finali.",
    "CF_CONTROLLO_ERRATO": "Ricopia il codice fiscale dal documento o dalla tessera sanitaria (quadro {quadro}).",
    "CF_INCOERENTE": "Controlla sul documento quale dato e' giusto e correggi il codice fiscale o il campo indicato "
                     "(quadro {quadro}).",
    "CF_DUPLICATO": "Lo stesso soggetto e' inserito due volte: elimina la riga in piu' nel quadro {quadro} e collega le sue "
                    "devoluzioni alla riga che resta.",
    "NATO_DOPO_IL_DECESSO": "Controlla la data di nascita nel quadro {quadro}; se e' corretta (concepito) l'avviso si puo' "
                            "ignorare.",
    "DATE_INCOERENTI": "Controlla data di nascita e data del decesso del defunto nel quadro AN.",
    "PROVINCIA_INCOERENTE": "Correggi la provincia o il codice comune nella scheda dell'immobile (quadro {quadro}).",
    "QUOTE_DI_LEGGE_NON_VERIFICATE": "Indica nel quadro DV le quote di ciascun erede come risultano dalla devoluzione: "
                                     "il programma non le ricava per questa configurazione di eredi.",
}


def rimedio(codice: str, quadro: str | None) -> str | None:
    """Testo del rimedio per il codice del rilievo, con il quadro in cui intervenire."""
    t = RIMEDI.get(codice)
    if t is None:
        return None
    return t.format(quadro=quadro or "AN")
