"""Schema dei dati di pratica e controlli interni di coerenza.

I codici dei diritti/qualifiche sono PROVVISORI: vanno legati alle enumerazioni degli XSD
(fonti/Specifiche tecniche) nel passo di export telematico. Vedi docs/MATRICE_COPERTURA.md.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, asdict
from fractions import Fraction

from . import valori as V

CODICE_FISCALE = re.compile(r"^[A-Z0-9]{16}$")
DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

RUOLI_PERSONA = ("defunto", "erede", "legatario", "rappresentante", "presentatore", "altro")
TIPI_BENE = ("fabbricato", "terreno", "disponibilita_finanziaria", "titolo", "aeromobile", "nave", "azienda", "altro")

# kind: str | cf | data | quota | importo | enum:<a|b> | ref:<collezione>
COLLEZIONI: dict[str, dict[str, str]] = {
    "persone": {
        "cognome": "str", "nome": "str", "codice_fiscale": "cf", "data_nascita": "data",
        "luogo_nascita": "str", "ruolo": "enum:" + "|".join(RUOLI_PERSONA),
        "relazione_con_defunto": "str", "data_decesso": "data",
        # Dati richiesti dall'export XML (prima solo in opzioni.telematico): se presenti qui hanno la precedenza.
        "sesso": "enum:M|F", "provincia_nascita": "str", "tipo_soggetto": "str", "grado_parentela": "str",
        "comune_decesso": "str", "provincia_decesso": "str",
        # Successione per rappresentazione (EA): codice fiscale e grado del rappresentato (figlio 02, fratello 10/11)
        "rappresentato_cf": "str", "rappresentato_grado": "str",
        # Persona con disabilita' grave o interdetta (EH): estremi del verbale della commissione o della sentenza
        "certificatore_disabilita": "str",
    },
    "beni": {
        "tipo": "enum:" + "|".join(TIPI_BENE), "descrizione": "str",
        "comune": "str", "sezione": "str", "foglio": "str", "particella": "str", "subalterno": "str",
        "categoria": "str", "rendita": "importo", "valore": "importo",
        "diritto": "str", "quota_defunto": "quota", "provenienza": "str",
        "data_visura": "data",   # data della visura catastale da cui derivano i dati (dato interno: non esportato)
        # Beni esteri (provincia «EE» in EB/EC; casella «bene sito all'estero» in EN/EO/EP/EQ/ER) e imposta versata all'estero
        "bene_estero": "str", "imposta_estera": "importo", "codice_stato_estero": "str", "stato_estero": "str",
        "stato_federato": "str", "localita_estero": "str",
        "provincia": "str", "codice_comune": "str", "comune_amministrativo": "str", "codice_comune_amministrativo": "str",
        "indirizzo": "str", "natura": "str", "tipologia_terreno": "str", "reddito_dominicale": "importo", "classe": "str",
        "zona_censuaria": "str", "consistenza": "str", "tipo_cespite": "str",
        "tipo_titolo": "str", "quantita": "str", "codice_titolo": "str", "codice_fiscale_emittente": "str",
        "tipo_documento": "str", "data_documento": "data",
        "marca_modello": "str", "anno_costruzione": "str", "nazionalita": "str", "anno_immatricolazione": "str",
        "numero_immatricolazione": "str", "tipo_unita": "str", "sigla_ufficio_iscrizione": "str", "anno_iscrizione": "str",
        "numero_iscrizione": "str", "lunghezza": "str", "stazza": "str",
        "inventario": "str", "data_redazione_inventario": "data",
        "comune_catastale": "str", "codice_comune_catastale": "str", "partita_tavolare": "str", "corpo_tavolare": "str",
        "porzione_materiale": "str", "particella_denominatore": "str", "sistema_tavolare": "str",
        "discordanza_intestatario": "str", "passaggi_senza_atti_legali": "str",
        # Immobili particolari (docs/regole/immobili_particolari.md): rendita proposta (DOCFA) e bene aziendale (casella EB/EC)
        "rendita_proposta": "str", "bene_aziendale": "str", "diritto_abitazione": "str",
    },
    "devoluzioni": {
        "bene_id": "ref:beni", "persona_id": "ref:persone", "quota": "quota", "diritto": "str",
    },
    "passivita": {"descrizione": "str", "importo": "importo", "persona_id": "ref:persone",
                  "tipo": "str", "estremi_documento": "str", "data_documento": "data", "possesso": "quota",
                  "bene_id": "ref:beni"},
    "documenti_ref": {"allegato_id": "str", "tipo_eg": "str", "finalita": "str", "persona_id": "ref:persone"},
}
# Aiuti contestuali mostrati nell'interfaccia e restituiti dall'MCP: spiegano campi che si prestano a errori di inserimento.
AIUTI: dict[str, str] = {
    "beni.valore": "Valore in euro interi della QUOTA DEL DEFUNTO (base imponibile), non dell'intero bene. "
                   "Esempio: immobile da 200.000 euro posseduto per 1/2: indicare 100.000. Indicare l'intero valore raddoppia attivo e imposta.",
    "beni.quota_defunto": "Frazione del bene posseduta dal defunto (es. 1/2). Non è la quota dell'erede.",
    "beni.rendita": "Rendita catastale in euro, con il punto decimale (es. 1240.50).",
    "beni.graffati": "Immobili graffati al fabbricato (fino a 4 per rigo): sezione urbana, foglio, particella, subalterno. Nei dati principali si indica la sola prima particella.",
    "devoluzioni.quota": "Quota dell'erede sul diritto del defunto (es. 1/3). È un dato diverso dalla quota del defunto sul bene. "
                         "Usufrutto (08) e nuda proprietà (02): chi riceve l'intero diritto indica 1/1 (Fascicolo I p. 24).",
    "devoluzioni.diritto": "Diritto ricevuto dall'erede. Se il defunto aveva la piena proprietà (1) di un fabbricato o terreno, si "
                           "possono indicare usufrutto (08) e nuda proprietà (02): il programma calcola il valore quota con "
                           "l'età dell'usufruttuario al decesso (serve la sua data di nascita) e i coefficienti di legge.",
    "persone.sesso": "M o F, come richiesto dal file telematico.",
    "beni.data_visura": "Data della visura catastale da cui hai ricavato i dati dell'immobile. Il Fascicolo I chiede visure di non piu' di tre mesi prima della presentazione: il programma avvisa se e' piu' vecchia. Non entra nel file XML.",
    "beni.bene_estero": "Solo per aziende, titoli, aeromobili, navi e altri beni (EN, EO, EP, EQ, ER): 1 se il bene e' sito all'estero. Per gli immobili esteri si indica invece la provincia EE.",
    "beni.imposta_estera": "Imposta versata all'estero per il bene, in euro interi, per l'INTERO bene (il programma la ripartisce con la quota di devoluzione). Serve la certificazione nel rigo EG4.",
    "beni.codice_stato_estero": "Immobile estero (provincia EE): codice a 3 cifre dello Stato estero (Appendice del Modello Unico Persone fisiche), es. 029 per la Francia.",
    "beni.stato_estero": "Immobile estero: nome dello Stato (massimo 34 caratteri).",
    "persone.grado_parentela": "Codice del grado di parentela con il defunto, come nelle istruzioni del quadro EA (es. 02).",
    "persone.certificatore_disabilita": "Solo per persone con disabilita' grave o interdette (quadro EH, lettera e): estremi del verbale della commissione (L. 104/1992 art. 4) o della sentenza di interdizione/inabilitazione, al massimo 35 caratteri.",
    "persone.rappresentato_cf": "Solo per chi succede per rappresentazione (grado 04, 06, 08, 15, 20, 27): codice fiscale del rappresentato (figlio o fratello del defunto, premorto o rinunciatario).",
    "persone.rappresentato_grado": "Grado di parentela del rappresentato con il defunto: 02 (figlio/a) per i discendenti dei figli, 10 o 11 (fratello/sorella germano o unilaterale) per i discendenti dei fratelli.",
    "beni.codice_comune": "Codice catastale del comune (4 caratteri, es. H501).",
    "beni.natura": "Natura del terreno secondo le istruzioni del quadro EB (es. T).",
    "persone.codice_fiscale": "16 caratteri. Il carattere di controllo viene verificato in esportazione.",
    "passivita.importo": "Importo in euro, con il punto decimale. Indicare la parte di debito che grava sul defunto.",
}
# Nell'interfaccia gli importi si scrivono all'italiana (la conversione al punto decimale la fa app.js): testi propri per la GUI.
AIUTI_INTERFACCIA: dict[str, str] = {
    "beni.rendita": "Rendita catastale in euro (es. 1.240,50).",
    "passivita.importo": "Importo in euro (es. 12.500,00). Indicare la parte di debito che grava sul defunto.",
}
AIUTI["beni.tipo_titolo"] = ("Quadro EO: scegli il tipo di titolo. Con «esente» (3) il valore è esente e nel file va in "
                             "ValoreEsente, non in Valore. I titoli quotati richiedono il codice fiscale dell'emittente.")
AIUTI["devoluzioni.agevolazioni"] = ("Codice di agevolazione della riga di devoluzione. Prima casa (P, X, Z): solo per i "
                                     "fabbricati del quadro EC. Riduzioni dell'imposta di successione (L, Q, R, F): vedi il "
                                     "dettaglio e i quadri per ciascun codice.")


def _opz(valore: str, etichetta: str, aiuto: str) -> dict:
    return {"valore": valore, "etichetta": etichetta, "aiuto": aiuto}


#: Maschere dei dati strutturati (opzioni.telematico) che non sono campi del modello comune. Chiave = percorso:
#: «beni.<campo>» e «devoluzioni.<campo>» = supplemento per riga; «dichiarazione.<chiave>» = opzioni.telematico.dichiarazione.
#: tipo: enum (opzioni con etichetta e aiuto) | bool (si'/no). Gli aiuti riportano solo cio' che e' nelle fonti: XSD
#: fornituraSUC13_v1.xsd (SUC13_20250702), Fascicolo I, docs/regole/prima_casa.md. Coerenza con il codice di esportazione
#: verificata da tests/test_maschere_strutturati.py.
ALIAS_SINO = {"1": "si", "true": "si", "0": "no", "false": "no"}
STRUTTURATI: dict[str, dict] = {
    # righi del quadro EG (modello, quadro EG: EG1 ... EG11; XSD QuadroEG, nello stesso ordine). Il valore e' il nome dell'elemento XSD.
    "documenti_ref.tipo_eg": {
        "etichetta": "rigo del quadro EG", "tipo": "enum", "senza_codice": True,
        "aiuto": "Rigo del quadro EG in cui va il documento. Il file allegato deve essere PDF/A (si converte qui sotto).",
        "opzioni": [
            _opz("DichSost", "EG1 - Dichiarazioni sostitutive e certificati", "Dichiarazioni sostitutive di atto notorio o di certificazione."),
            _opz("Testamento", "EG2 - Testamento", "Solo con devoluzione per testamento."),
            _opz("Inventario", "EG3 - Inventario / prospetto delle attivita' e passivita'",
                 "Con questo rigo il quadro EH riporta la casella del prospetto (lettera l): serve la dichiarazione di conformita' delle copie."),
            _opz("CertificazioneImpostaVersataEstero", "EG4 - Certificazione dell'imposta versata all'estero", "Certificato dell'imposta di successione pagata all'estero, per la detrazione."),
            _opz("DocumentiPassivita", "EG5 - Documenti delle passivita'",
                 "Con questo rigo il quadro EH riporta la casella delle passivita' (lettera l)."),
            _opz("AlberoGenealogico", "EG6 - Albero genealogico", "Obbligatorio in presenza del quadro EA."),
            _opz("DocumentiIdentita", "EG7 - Documenti d'identita'",
                 "Documento del dichiarante, obbligatorio se il modello non e' trasmesso direttamente da lui."),
            _opz("Altro", "EG8 - Altro", "Altri documenti (es. attestazioni bancarie, inventari: vedi la casella degli inventari nel quadro EH)."),
            _opz("PrimaCasa", "EG9 - Prima casa (richiesta di un altro beneficiario)", "Richiesta dell'agevolazione prima casa fatta da un beneficiario diverso dal dichiarante (Fascicolo I, quadro EH, Sezione II)."),
            _opz("AgevolazioniImposteIpocatastali", "EG10 - Agevolazioni sulle imposte ipotecarie e catastali", "Richieste di agevolazione ipocatastale di un beneficiario diverso dal dichiarante."),
            _opz("RiduzioniImposteSuccessione", "EG11 - Riduzioni dell'imposta di successione", "Richieste di riduzione dell'imposta di successione di un beneficiario diverso dal dichiarante."),
        ],
    },
    "beni.tipo_titolo": {
        "etichetta": "tipo di titolo", "tipo": "enum", "aiuto": AIUTI["beni.tipo_titolo"],
        "opzioni": [
            _opz("1", "quotato in borsa o nel mercato ristretto",
                 "Richiede il codice fiscale dell'emittente (diverso da quello del defunto e dei soggetti del quadro EA); "
                 "il codice titolo si indica solo per questo tipo (XSD, annotazioni di Titoli)."),
            _opz("2", "non quotato in borsa", "Titolo non quotato: valore nel campo «valore»."),
            _opz("3", "esente compreso nell'attivo ereditario (BOT, CCT, BTP, buoni postali)",
                 "Titolo ESENTE: il valore è «esente» e viene scritto in ValoreEsente, mai in Valore (XSD, PossessoEO_Type). "
                 "Entra comunque nei totali del quadro EE (XSD, TotaleValoreTitoli). Un titolo con una parte esente e una "
                 "imponibile va diviso in due righe. Una passività collegata a un titolo esente blocca l'esportazione: le "
                 "fonti non dicono se sia deducibile."),
            _opz("4", "fondo comune d'investimento", "Fondo comune d'investimento: valore nel campo «valore»."),
        ],
    },
    # Caselle si'/no (DatoCB nell'XSD). Il modello le conserva come testo («si»/«no»): l'esportazione legge «1», «si», «true»
    # come si' (quadri_efgh._flag) e ogni altro valore come no. «alias» = scritture gia' ammesse, mostrate come la voce.
    "beni.discordanza_intestatario": {
        "etichetta": "discordanza dati intestatario", "tipo": "enum", "senza_codice": True, "alias": dict(ALIAS_SINO),
        "aiuto": "Casella del quadro EB/EC: i dati dell'intestatario in catasto non corrispondono. Genera il quadro EI.",
        "opzioni": [_opz("si", "si'", "Casella spuntata."), _opz("no", "no", "Casella non spuntata.")]},
    "beni.passaggi_senza_atti_legali": {
        "etichetta": "passaggi senza atti legali", "tipo": "enum", "senza_codice": True, "alias": dict(ALIAS_SINO),
        "aiuto": "Casella del quadro EB/EC: ci sono passaggi di proprieta' non risultanti da atti legali. Genera il quadro EI.",
        "opzioni": [_opz("si", "si'", "Casella spuntata."), _opz("no", "no", "Casella non spuntata.")]},
    "beni.rendita_proposta": {
        "etichetta": "rendita proposta (DOCFA)", "tipo": "enum", "senza_codice": True, "alias": dict(ALIAS_SINO),
        "aiuto": "Si' se in catasto l'immobile ha solo la rendita proposta con DOCFA: nel campo «rendita» va il valore proposto e si "
                 "chiede la determinazione (codice 1). La volonta' va manifestata con una dichiarazione sostitutiva allegata nel quadro EG "
                 "(rigo «Altro»). Fascicolo I pp. 29-30.",
        "opzioni": [_opz("si", "si'", "Rendita proposta: determinazione richiesta."), _opz("no", "no", "Rendita definitiva.")]},
    "beni.diritto_abitazione": {
        "etichetta": "diritto di abitazione del coniuge superstite", "tipo": "enum",
        "aiuto": "Solo per l'immobile su cui con l'apertura della successione si costituisce il diritto di abitazione del coniuge superstite "
                 "(art. 540 c.c.). Il codice dice se il coniuge chiede la prima casa (P, Z, X) o no, e se ha rinunciato all'eredita' ma non al "
                 "legato ex lege (codici 5-8: coniuge con tipo soggetto 4). Le righe di devoluzione restano quelle della proprieta' (valore "
                 "quota = valore x quota): non serve una riga per il diritto di abitazione. Con i codici 1, 2, 3, 5, 6, 7 la prima casa si "
                 "estende a tutti i beneficiari del bene (quadro EF); se il coniuge e' il dichiarante compila la Sezione II del quadro EH, "
                 "altrimenti allega la richiesta (rigo EG9) e il documento d'identita'. Fascicolo I p. 31-32.",
        "opzioni": [
            _opz("1", "prima casa: immobile principale (P)", "Il coniuge superstite chiede la prima casa sull'immobile principale."),
            _opz("2", "prima casa: immobile contiguo (Z)", "Il coniuge superstite chiede la prima casa sull'immobile contiguo."),
            _opz("3", "prima casa: pertinenza (X)", "Il coniuge superstite chiede la prima casa sulla pertinenza."),
            _opz("4", "senza prima casa", "Il coniuge superstite non chiede la prima casa."),
            _opz("5", "coniuge rinunciatario all'eredita': prima casa, principale (P)", "Ha rinunciato all'eredita' ma non al legato ex lege."),
            _opz("6", "coniuge rinunciatario all'eredita': prima casa, contiguo (Z)", "Ha rinunciato all'eredita' ma non al legato ex lege."),
            _opz("7", "coniuge rinunciatario all'eredita': prima casa, pertinenza (X)", "Ha rinunciato all'eredita' ma non al legato ex lege."),
            _opz("8", "coniuge rinunciatario all'eredita': senza prima casa", "Ha rinunciato all'eredita' ma non al legato ex lege."),
        ]},
    "beni.bene_aziendale": {
        "etichetta": "bene aziendale", "tipo": "enum", "senza_codice": True, "alias": dict(ALIAS_SINO),
        "aiuto": "Si' se l'immobile e' un bene aziendale (ditta individuale): va compilato anche il quadro EN con l'azienda a cui appartiene "
                 "e il collegamento dell'immobile. Fascicolo I pp. 21 e 29.",
        "opzioni": [_opz("si", "si'", "Immobile aziendale."), _opz("no", "no", "Immobile non aziendale.")]},
    "beni.sistema_tavolare": {
        "etichetta": "sistema tavolare", "tipo": "enum", "senza_codice": True, "alias": dict(ALIAS_SINO),
        "aiuto": "Si' se l'immobile e' nel sistema tavolare (quadri EL/EM), anche fuori dalle province tavolari.",
        "opzioni": [_opz("si", "si'", "Immobile in sistema tavolare."), _opz("no", "no", "Immobile in catasto ordinario.")]},
    "devoluzioni.agevolazioni": {
        "etichetta": "agevolazione", "tipo": "enum", "aiuto": AIUTI["devoluzioni.agevolazioni"] +
        " Si indica sulla riga del soggetto che chiede il beneficio. P, X, Z: si estende a tutti i beneficiari del bene e "
        "non cambia l'imposta di successione (restano dovute le imposte ipotecaria e catastale in misura fissa, "
        "Fascicolo I p. 57). L, Q, R, F riducono l'imposta di successione (docs/regole/riduzioni_art25.md). "
        "Gli altri codici (Y, A, C, D, E, G, H, M, N) non sono supportati.",
        "opzioni": [
            _opz("P", "prima casa",
                 "Casa di abitazione con categoria catastale diversa da A/1, A/8, A/9 (Fascicolo I p. 60); un solo immobile "
                 "per soggetto (p. 26). Se la chiede il dichiarante, compila le dichiarazioni «Prima casa» nel frontespizio."),
            _opz("X", "pertinenza",
                 "Pertinenza C/2, C/6 o C/7, una per categoria, solo se lo stesso soggetto ha anche P (Fascicolo I p. 26-27)."),
            _opz("Z", "immobile contiguo",
                 "Immobile contiguo: solo del dichiarante e solo se ha anche P; richiede l'impegno all'unione catastale "
                 "(un solo Z). Fascicolo I p. 26."),
            _opz("L", "beni culturali (art. 25 c. 2)",
                 "Beni culturali con vincolo posteriore all'apertura della successione. Quadri EB, EC, EL, EM. Riduzione con "
                 "coefficiente 0,5. Se la chiede il dichiarante compila la Sezione IV del quadro EH (numero protocollo e data); "
                 "per un altro beneficiario si compilano i righi EG11 e EG7 del quadro EG. Non convive con P, X, Z "
                 "sullo stesso bene. Non combinabile con una riduzione 1-5 sulla stessa riga."),
            _opz("Q", "aziende, quote di societa' di persone, beni strumentali in comuni montani (art. 25 c. 4-bis)",
                 "Supportato nei quadri EN ed EO. Coefficiente 0,4. Se la chiede il dichiarante, nella Sezione IV del quadro EH "
                 "si spunta il codice Q; per un altro beneficiario righi EG11 e EG7. Ammessa solo per alcuni gradi di "
                 "parentela (annotazione XSD di Agevolazioni): altrimenti l'esportazione segnala l'errore."),
            _opz("R", "fondi rustici (art. 25 c. 3)",
                 "Quadri EB, EC, EL, EM. Coefficiente 0,4, con soglia di 103.291 euro per riga. Nessuna sezione del quadro EH: "
                 "l'attestazione dell'ufficio regionale va allegata al quadro EG (rigo EG8 «Altro»). Una sola riga R per "
                 "beneficiario. Ammessa solo per alcuni gradi di parentela (annotazione XSD)."),
            _opz("F", "immobili di impresa artigiana familiare (art. 25 c. 4)",
                 "Solo quadri EC ed EM. Coefficiente 0,4, con soglia di 103.291 euro per riga. Nessuna sezione del quadro EH. "
                 "Una sola riga F per beneficiario. Ammessa solo per alcuni gradi di parentela (annotazione XSD)."),
        ],
    },
    "devoluzioni.riduzioni": {
        "etichetta": "riduzione art. 25 comma 1", "tipo": "enum",
        "aiuto": "Beni oggetto di precedenti successioni o donazioni (art. 25 c. 1). Richiede il «valore delle precedenti "
                 "successioni» sul bene collegato. Quadri EB, EC, EL, EM, EN, EO, EP, EQ, ER (non per i cespiti DN). Lo stesso "
                 "codice va indicato su tutte le righe di devoluzione del bene; non si combina con un'agevolazione sulla "
                 "stessa riga e non vale per i trust. Il dichiarante compila la Sezione IV del quadro EH; per un altro "
                 "beneficiario si compilano i righi EG11 e EG7. Fonte: docs/regole/riduzioni_art25.md.",
        "opzioni": [
            _opz("1", "precedente successione o donazione entro 1 anno", "Coefficiente di riduzione 0,5."),
            _opz("2", "precedente successione o donazione entro 2 anni", "Coefficiente di riduzione 0,4."),
            _opz("3", "precedente successione o donazione entro 3 anni", "Coefficiente di riduzione 0,3."),
            _opz("4", "precedente successione o donazione entro 4 anni", "Coefficiente di riduzione 0,2."),
            _opz("5", "precedente successione o donazione entro 5 anni", "Coefficiente di riduzione 0,1."),
        ],
    },
    "beni.valore_prec_succ": {
        "etichetta": "valore delle precedenti successioni o donazioni", "tipo": "importo",
        "aiuto": "Euro interi. Obbligatorio se la riga di devoluzione del bene ha una riduzione art. 25 c. 1 (1-5), assente "
                 "senza riduzione; positivo e non superiore al campo «valore» del bene. Non per i titoli esenti."},
    "dichiarazione.riduzioni_art25.dichiara_requisiti": {
        "etichetta": "riduzioni: dichiaro di possedere i requisiti", "tipo": "bool",
        "aiuto": "Sezione IV del quadro EH, solo se il dichiarante chiede L, Q o una riduzione 1-5: la firma attesta il possesso "
                 "dei requisiti; per esportare va confermato («si»)."},
    "dichiarazione.riduzioni_art25.l.num_protocollo": {
        "etichetta": "codice L: numero di protocollo", "tipo": "testo",
        "aiuto": "Estremi della richiesta/attestazione dei beni culturali, da 7 a 16 caratteri (controllo ufficiale eseguito in "
                 "locale, non scritto negli XSD). Serve solo se il dichiarante chiede L."},
    "dichiarazione.riduzioni_art25.l.data": {
        "etichetta": "codice L: data", "tipo": "testo", "formato": "data",
        "aiuto": "Data della richiesta/attestazione dei beni culturali (GG/MM/AAAA). Serve solo se il dichiarante chiede L."},
    "dichiarazione.riduzioni_art25.successione_precedente.ufficio": {
        "etichetta": "successione precedente: ufficio", "tipo": "testo", "suggerimenti": "dichiarazione.testamento.ufficio_registrazione",
        "aiuto": "Codice dell'ufficio territoriale della dichiarazione di successione precedente. Indicare la successione "
                 "precedente OPPURE la donazione precedente, non entrambe."},
    "dichiarazione.riduzioni_art25.successione_precedente.anno": {
        "etichetta": "successione precedente: anno", "tipo": "testo", "aiuto": "Anno a quattro cifre."},
    "dichiarazione.riduzioni_art25.successione_precedente.volume": {
        "etichetta": "successione precedente: volume", "tipo": "testo", "aiuto": "Fino a 5 cifre."},
    "dichiarazione.riduzioni_art25.successione_precedente.numero": {
        "etichetta": "successione precedente: numero", "tipo": "testo", "aiuto": "Fino a 6 cifre."},
    "dichiarazione.riduzioni_art25.donazione_precedente.ufficio": {
        "etichetta": "donazione precedente: ufficio di registrazione", "tipo": "testo",
        "suggerimenti": "dichiarazione.testamento.ufficio_registrazione",
        "aiuto": "Codice dell'ufficio di registrazione dell'atto di donazione precedente."},
    "dichiarazione.riduzioni_art25.donazione_precedente.serie": {
        "etichetta": "donazione precedente: serie", "tipo": "testo",
        "aiuto": "Cifra da 1 a 4, con una lettera facoltativa (Serie_Type, XSD)."},
    "dichiarazione.riduzioni_art25.donazione_precedente.numero": {
        "etichetta": "donazione precedente: numero di registrazione", "tipo": "testo", "aiuto": "Fino a 6 cifre."},
    "dichiarazione.riduzioni_art25.donazione_precedente.sottonumero": {
        "etichetta": "donazione precedente: sottonumero", "tipo": "testo", "aiuto": "Facoltativo, fino a 3 cifre."},
    "dichiarazione.prima_casa.dichiara_requisiti": {
        "etichetta": "prima casa: dichiaro di possedere i requisiti", "tipo": "bool",
        "aiuto": "Serve solo se il dichiarante chiede P. La Sezione II del quadro EH attesta con la firma il possesso dei "
                 "requisiti: per esportare va confermato («sì»)."},
    "dichiarazione.prima_casa.requisito_comune": {
        "etichetta": "prima casa: requisito nel comune", "tipo": "enum",
        "aiuto": "Scelta a della Sezione II del quadro EH (modello EH14). Gli altri requisiti (trasferiti all'estero, forze "
                 "armate, residenti all'estero) non sono supportati.",
        "opzioni": [
            _opz("residenza", "ha la residenza nel comune", "Residenza nel comune dell'immobile."),
            _opz("attivita", "svolge la propria attività nel comune", "Sede della propria attività nel comune dell'immobile."),
            _opz("stabilire_residenza", "intende stabilire la residenza entro 18 mesi",
                 "Intenzione di stabilire la residenza nel comune entro 18 mesi."),
        ]},
    "dichiarazione.prima_casa.nessuna_altra_casa_comune": {
        "etichetta": "prima casa: nessuna altra casa nel comune", "tipo": "bool",
        "aiuto": "Dichiarazione b: non si è titolari di altra casa di abitazione nel comune. È condizione dell'agevolazione: "
                 "con «no» l'esportazione è bloccata."},
    "dichiarazione.prima_casa.altra_casa": {
        "etichetta": "prima casa: altra casa", "tipo": "enum",
        "aiuto": "Dichiarazioni c/d della Sezione II. La corrispondenza con le lettere è dedotta dal modello e va riletta "
                 "in sede di collaudo (docs/regole/prima_casa.md).",
        "opzioni": [
            _opz("nessuna", "nessuna altra casa acquistata con le agevolazioni", "Dichiarazione c."),
            _opz("vendita", "impegno a trasferire l'altra casa entro due anni dal decesso", "Dichiarazione d."),
        ]},
    "dichiarazione.prima_casa.impegno_unione_catastale": {
        "etichetta": "prima casa: impegno all'unione catastale", "tipo": "bool",
        "aiuto": "Obbligatorio («sì») solo con il codice Z: impegno a unire catastalmente gli immobili contigui entro tre "
                 "anni (dichiarazione i; XSD, FlagContigui)."},
}
SEZIONI = {"opzioni": None, "note": None}  # sezioni libere (dict), non esportate se interne


@dataclass
class Errore:
    codice: str
    percorso: str
    messaggio: str
    fonte: str = "controllo interno"

    def asdict(self):
        return asdict(self)


def valida_campo(kind: str, valore, percorso: str, riferimenti: dict[str, set[str]]) -> list[Errore]:
    if V.e_stato(valore):
        return []
    try:
        if kind == "str":
            if not isinstance(valore, str):
                raise V.ValoreNonValido("atteso testo")
        elif kind == "cf":
            if not (isinstance(valore, str) and CODICE_FISCALE.match(valore.upper())):
                raise V.ValoreNonValido("codice fiscale di 16 caratteri alfanumerici (lettere e cifre, senza spazi)")
        elif kind == "data":
            if not (isinstance(valore, str) and DATA_ISO.match(valore)):
                raise V.ValoreNonValido("data non valida: scrivere GG/MM/AAAA (esempio 10/02/1970) oppure AAAA-MM-GG")
            try:
                datetime.date.fromisoformat(valore)
            except ValueError:
                raise V.ValoreNonValido("data inesistente nel calendario: controllare giorno e mese (formato GG/MM/AAAA)")
        elif kind == "quota":
            V.parse_quota(valore)
        elif kind == "importo":
            V.parse_importo(valore)
        elif kind.startswith("enum:"):
            if valore not in kind[5:].split("|"):
                raise V.ValoreNonValido("valore ammesso: " + ", ".join(kind[5:].split("|")))
        elif kind.startswith("ref:"):
            if valore not in riferimenti.get(kind[4:], set()):
                raise V.ValoreNonValido(f"riferimento inesistente in {kind[4:]}")
    except V.ValoreNonValido as e:
        return [Errore("VALORE_NON_VALIDO", percorso, str(e))]
    return []


def valida_forma(dati: dict) -> list[Errore]:
    """Validazione strutturale (usata a ogni scrittura): campi noti, tipi, riferimenti."""
    err: list[Errore] = []
    rif = {c: {e["id"] for e in dati.get(c, [])} for c in COLLEZIONI}
    for coll, campi in COLLEZIONI.items():
        for e in dati.get(coll, []):
            base = f"{coll}[{e['id']}]"
            for k, v in e.items():
                if k in ("id", "_origine"):
                    continue
                if k not in campi:
                    err.append(Errore("CAMPO_SCONOSCIUTO", f"{base}.{k}", "campo non previsto dallo schema"))
                    continue
                err += valida_campo(campi[k], v, f"{base}.{k}", rif)
    return err


def controlli_coerenza(dati: dict) -> list[Errore]:
    """Controlli di merito interni (non sono il controllo ufficiale dell'Agenzia)."""
    err: list[Errore] = []
    persone = dati.get("persone", [])
    if sum(1 for p in persone if p.get("ruolo") == "defunto") != 1:
        err.append(Errore("DEFUNTO_NON_UNICO", "persone", "serve esattamente un soggetto con ruolo 'defunto'"))
    for p in persone:
        if not p.get("codice_fiscale"):
            err.append(Errore("CF_MANCANTE", f"persone[{p['id']}].codice_fiscale", "dato mancante"))
    # somma delle devoluzioni per (bene, diritto) <= 1: quote del defunto e devoluzioni sono dati distinti
    somme: dict[tuple[str, str], Fraction] = {}
    for d in dati.get("devoluzioni", []):
        try:
            q = V.parse_quota(d["quota"])
        except (KeyError, V.ValoreNonValido):
            continue
        k = (d.get("bene_id", ""), d.get("diritto", ""))
        somme[k] = somme.get(k, Fraction(0)) + q
    for (bene, diritto), s in somme.items():
        if s > 1:
            err.append(Errore("DEVOLUZIONI_ECCEDENTI", f"devoluzioni[bene={bene},diritto={diritto}]",
                              f"somma quote {s.numerator}/{s.denominator} > 1"))
        elif s < 1:
            err.append(Errore("DEVOLUZIONI_INCOMPLETE", f"devoluzioni[bene={bene},diritto={diritto}]",
                              f"somma quote {s.numerator}/{s.denominator} < 1 (da confermare)"))
    for b in dati.get("beni", []):
        if b.get("tipo") in ("fabbricato", "terreno") and not (b.get("foglio") and b.get("particella")):
            err.append(Errore("IDENTIFICATIVI_CATASTALI_INCOMPLETI", f"beni[{b['id']}]", "foglio/particella mancanti"))
    return err
