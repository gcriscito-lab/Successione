"""Server MCP (stdio). Strumenti delimitati con schemi chiari; nessuna shell/SQL/lettura arbitraria.

Usa lo stesso Servizio e lo stesso archivio dell'interfaccia: lo stato vive nel file di archivio,
non nel processo del client. Le credenziali non transitano da qui.
"""
from __future__ import annotations

import functools
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import __version__, pdfa, schema as S
from .errori import DatiNonValidi, ErroreServizio
from .servizio import VERSIONE_REGOLE, Servizio

COPERTURA_NON_DISPONIBILE = [
    "copertura completa di tutti i casi SUC13", "stampa del modello ministeriale", "collaudo operativo completo",
    "acquisizione catastale Entratel", "invio automatico e download autenticato delle ricevute",
]


def _pagina(righe: list, limit: int, offset: int) -> dict:
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    parte = righe[offset:offset + limit]
    fine = offset + len(parte)
    return {"totale": len(righe), "offset": offset, "elementi": parte,
            "has_more": fine < len(righe), "next_offset": fine if fine < len(righe) else None}


def costruisci(servizio: Servizio | None = None) -> MCPServer:
    sv = servizio or Servizio()
    mcp = MCPServer("successioni", version=__version__, instructions=(
        "Compilazione di dichiarazioni di successione. Leggi sempre la pratica per ottenere la revisione, "
        "poi modifica con aggiorna_pratica passando revisione_attesa e una chiave_richiesta univoca. "
        "Importi come stringhe decimali con punto; quote come {num, den}. Usa {stato: da_confermare|assente|zero|"
        "non_applicabile} quando il dato non e' noto. I risultati di verifica_pratica sono controlli interni, "
        "non il controllo ufficiale dell'Agenzia."))

    def protetto(fn):
        @functools.wraps(fn)
        def w(*a, **k):
            try:
                return fn(*a, **k)
            except ErroreServizio as e:
                raise ToolError(f"{e.codice}: {e.messaggio} | {e.asdict()}") from None
        return w

    LETTURA = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
    SCRITTURA = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)
    LOCALE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)

    def tool(fn=None, *, ann=LETTURA):
        """Registra con prefisso di servizio (successioni_*) e annotazioni (suggerimenti, non garanzie di sicurezza)."""
        def reg(f):
            return mcp.tool(name="successioni_" + f.__name__, annotations=ann)(protetto(f))
        return reg(fn) if fn else reg

    @tool
    def capacita() -> dict[str, Any]:
        """Versione, funzioni disponibili e casi non ancora coperti (da leggere prima di iniziare)."""
        return {"versione_applicazione": __version__, "versione_regole": VERSIONE_REGOLE,
                "funzioni": ["pratiche", "soggetti/beni/devoluzioni/passivita", "revisioni e differenze",
                             "allegati e conversione PDF/A", "verifica interna", "export XML nel perimetro coperto",
                             "controllo ufficiale locale se configurato"],
                "non_disponibile": COPERTURA_NON_DISPONIBILE,
                "strumenti_pdfa": {"ghostscript": bool(pdfa.trova_gs()), "veraPDF": bool(pdfa.trova_verapdf())},
                "cartella_ingresso": str(sv.cartella_ingresso)}

    @tool
    def schema_dati() -> dict[str, Any]:
        """Collezioni, campi e tipi ammessi (str, cf, data, quota, importo, enum, ref)."""
        return {"collezioni": S.COLLEZIONI, "aiuti_campi": S.AIUTI, "sezioni": list(S.SEZIONI),
                "stati_dato": ["assente", "zero", "non_applicabile", "da_confermare"],
                "operazioni": {"upsert": "{op, coll, id?, campi}", "remove": "{op, coll, id}",
                               "set": "{op, sezione, campi}"},
                "nota": "codici di diritto/qualifica provvisori fino al legame con gli XSD"}

    @tool
    def elenca_pratiche(limit: int = 50, offset: int = 0) -> dict:
        """Pratiche presenti con revisione corrente (paginato: limit, offset; has_more/next_offset nel risultato)."""
        return _pagina(sv.elenca(), limit, offset)

    @tool(ann=SCRITTURA)
    def crea_pratica(titolo: str, chiave_richiesta: str) -> dict:
        """Crea una pratica. Ripetere con la stessa chiave non crea duplicati."""
        return sv.crea_pratica(titolo, chiave=chiave_richiesta, autore="assistente", canale="mcp")

    @tool
    def leggi_pratica(pratica_id: str, revisione: int | None = None) -> dict:
        """Dati completi e revisione. Con 'revisione' legge una versione precedente."""
        return sv.leggi(pratica_id, revisione)

    @tool(ann=SCRITTURA)
    def aggiorna_pratica(pratica_id: str, revisione_attesa: int, operazioni: list[dict], chiave_richiesta: str) -> dict:
        """Applica in modo atomico una lista di operazioni. Conflitto di revisione = nessuna modifica."""
        return sv.aggiorna(pratica_id, revisione_attesa, operazioni, chiave=chiave_richiesta,
                           autore="assistente", canale="mcp")

    @tool
    def revisioni_pratica(pratica_id: str, limit: int = 50, offset: int = 0) -> dict:
        """Cronologia delle revisioni (autore, canale, sommario), paginata."""
        return _pagina(sv.revisioni(pratica_id), limit, offset)

    @tool
    def differenze_pratica(pratica_id: str, da_revisione: int, a_revisione: int) -> list[str]:
        """Differenze tra due revisioni."""
        return sv.differenze(pratica_id, da_revisione, a_revisione)

    @tool
    def verifica_pratica(pratica_id: str) -> dict:
        """Controlli interni di forma e coerenza con percorso del dato; NON e' il controllo ufficiale."""
        return sv.verifica(pratica_id)

    @tool
    def stato_quadri(pratica_id: str) -> dict:
        """Stato di ogni quadro (vuoto, compilato, rilievi, non supportato, non selezionato) con i rilievi e il quadro di appartenenza. Dice se la pratica è finalizzabile nel perimetro supportato; non è il controllo ufficiale."""
        return sv.quadri(pratica_id)

    @tool(ann=LOCALE)
    def esporta_xml(pratica_id: str, cf_fornitore: str | None = None, scopo: str = "completo") -> dict:
        """Genera XML SUC13 con gli allegati della pratica. Profilo in opzioni.fornitore: cf, tipo (1/10), impegno_codice (1/2), data_impegno (AAAA-MM-GG). Restituisce anche avvisi. Scopo completo: nessun file se mancano dati/casi; bozza_tecnica: file di prova incompleto. La validita XSD non prova PDF/A, conformita fiscale universale o accettazione ufficiale. Non invia nulla."""
        return sv.esporta(pratica_id, cf_fornitore=cf_fornitore, scopo=scopo)

    @tool
    def stato_elaborati(pratica_id: str) -> dict:
        """Stati separati di dati, file XML, validazione di schema, controllo ufficiale e trasmissione. Un esito diventa 'obsoleto' se cambia il dichiarato; una nota interna non lo invalida."""
        return sv.stato_elaborati(pratica_id)

    @tool(ann=LOCALE)
    def controllo_ufficiale(pratica_id: str) -> dict:
        """Esegue in locale il controllo ufficiale SUC13 sul file esportato aggiornato (se Java e componenti sono configurati; altrimenti passaggio manuale tracciato, esito da_collaudare). È un controllo locale: non sostituisce la verifica con i servizi dell'Agenzia e non trasmette nulla."""
        return sv.controllo_ufficiale_pratica(pratica_id)

    @tool(ann=LOCALE)
    def invio_prepara(pratica_id: str, chiave_richiesta: str) -> dict:
        """Prepara la copia congelata per l'invio (file XML completo e aggiornato + controllo ufficiale). NON trasmette nulla e NON conferma: la conferma e la trasmissione si danno solo nell'interfaccia dell'app, dal professionista."""
        return sv.invio_prepara(pratica_id, chiave=chiave_richiesta)

    @tool
    def invio_stato(pratica_id: str) -> dict:
        """Copie congelate della pratica con stato, tentativi e prossimo passo richiesto. Una trasmissione in modalita' simulata non e' un invio all'Agenzia."""
        return sv.invio_stato(pratica_id)

    @tool
    def decodifica_codice_fiscale(codice_fiscale: str, ruolo: str | None = None) -> dict:
        """Dati anagrafici ricavabili da un codice fiscale di persona fisica (sesso, data di nascita, comune e provincia se le tabelle del componente SUC13 sono configurate), con controllo del carattere di controllo. E' un suggerimento da verificare: il secolo non e' nel codice e viene dedotto (ruolo 'defunto' per il defunto)."""
        from .codice_fiscale import decodifica
        return decodifica(codice_fiscale, ruolo=ruolo)

    @tool
    def file_in_ingresso() -> list[str]:
        """File che l'utente ha messo nella cartella d'ingresso e che possono essere acquisiti."""
        return sorted(p.name for p in sv.cartella_ingresso.iterdir() if p.is_file())

    @tool(ann=LOCALE)
    def importa_xml_telematico(nome_file: str, titolo: str | None = None) -> dict:
        """Crea una nuova pratica da XML SUC13 nella cartella d'ingresso. Rifiuta campi non conservabili; non invia."""
        p = (sv.cartella_ingresso / nome_file).resolve()
        if not p.is_relative_to(sv.cartella_ingresso.resolve()) or not p.is_file() or p.stat().st_size > 20_000_000:
            raise DatiNonValidi("file non disponibile nella cartella d'ingresso o oltre 20 MB")
        return sv.importa_xml_telematico(p.read_bytes(), titolo=titolo, autore="assistente", canale="mcp")

    @tool(ann=LOCALE)
    def acquisisci_allegato(pratica_id: str, nome_file: str, tipo_eg: str | None = None,
                            finalita: str | None = None, persona_id: str | None = None) -> dict:
        """Acquisisce un file della cartella d'ingresso come originale; tipo e finalita' li indica il chiamante."""
        return sv.acquisisci_da_ingresso(pratica_id, nome_file, tipo_eg=tipo_eg, finalita=finalita,
                                         persona_id=persona_id)

    @tool(ann=LOCALE)
    def prepara_pdfa(allegato_id: str) -> dict:
        """Crea il derivato PDF/A-1b dell'originale e lo valida. 'conforme' solo con veraPDF; altrimenti 'non_verificato'."""
        return sv.prepara_pdfa(allegato_id)

    @tool(ann=LOCALE)
    def suddividi_allegato(allegato_id: str, limite_byte: int | None = None) -> dict:
        """Riduce o suddivide un allegato oltre il limite (5 MB per file secondo le specifiche): registra le parti come derivati, l'originale resta invariato. Le parti sono rivalidate e nessuna pagina viene persa."""
        return sv.suddividi_allegato(allegato_id, limite_byte)

    @tool
    def elenca_allegati(pratica_id: str) -> list[dict]:
        """Originali e derivati con analisi e rapporto."""
        return sv.elenca_allegati(pratica_id)

    return mcp


def main():
    costruisci().run("stdio")


if __name__ == "__main__":
    main()
