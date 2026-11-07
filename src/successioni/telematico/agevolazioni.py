"""Agevolazioni A, C, D, E, G, H, M, N del campo Agevolazioni della sezione devoluzione (le altre sono in ``prima_casa.py``
per P, X, Y, Z e in ``riduzioni_art25.py`` per L, Q, R, F e i codici 1-5).

Ogni regola cita la fonte (annotazione XSD di ``fornituraSUC13_v1.xsd`` SUC13_20250702, Fascicolo I pagina PDF, guida di calcolo
«All. Specifiche tecniche»). Nessuna regola dalla memoria. Dettaglio e casi esclusi: ``docs/regole/agevolazioni.md``.

EFFETTI (Fascicolo I p. PDF 57, quadro sinottico; I = ipotecaria, C = catastale, S = successione):
  A  S esente; resta nella base proporzionale di EF1/EF9; esclusa dal totale immobili di EE (annotazione TotaleValoreImmobili)
  N  S esente; resta nella base proporzionale di EF1/EF9
  C  I, C, S esenti          D  I, C, S esenti          E  I, C, S esenti          H  I, C, S esenti
  G  I fissa (EF2), C e S esenti         M  I fissa (EF3), C esente, S dovuta
  La guida di calcolo (p. 1) esclude dalla QE i righi con A, D, C, G, N, E, H; non M.
"""
from __future__ import annotations

from fractions import Fraction

from . import fonti as FO
from . import formati as F
from .. import valori as V
from . import supplemento as SUP

CODICI = ("A", "C", "D", "E", "G", "H", "M", "N")
#: codici che esentano dall'imposta di successione (guida p. 1: QE «con esclusione delle quote con agevolazione A, D, C, G, N, E, H»)
ESENTI_SUCCESSIONE = ("A", "C", "D", "E", "G", "H", "N")
#: righi esclusi dalla base proporzionale EF1/EF9 (annotazione ImpostaProporzionale_Imponibile: restano solo spazio, A, L, R, F, N, Q)
FUORI_BASE_PROPORZIONALE = ("C", "D", "E", "G", "H", "M")
#: misura fissa per le successioni aperte dal 2014-01-01 (Fascicolo I p. 39); dal 2006-10-03 al 2013-12-31 e' 168: la misura per data
#: e' ``quadri_efgh.imposta_fissa`` (annotazioni AgevolazioneG_Imposta e AgevolazioneM_Imposta: «168 ... 200 dal 01/01/2014»)
IMPOSTA_FISSA = 200
#: righi esclusi dal numero di circoscrizioni del rigo EF16 (bollo): annotazione SezioneIV_ImpostaBollo/Circoscrizioni_Numero
#: «agevolazioni diverse da 'C', 'M' o 'G' o 'E'» (H e' escluso per bene anche da EF15); Fascicolo I pp. PDF 45-46
FUORI_CIRCOSCRIZIONI_BOLLO = ("C", "E", "G", "M")

EL_AGEV = "QuadroEC/Modulo/Fabbricati/DevoluzioneEC/Devoluzione/Agevolazioni"
#: quadri in cui l'XSD ammette il codice (annotazione di Devoluzione/Agevolazioni: «H ... EC, EM»; «G ... EB, EC, EL, EM, EN»;
#: «N ... EB, EL»; «C, D, E, M, N, F, R, G non ... EP, EQ e ER»; «EN ... solo D, G, Q»; «EO ... solo D, Q»; «ER ... solo A (AB, BI) e L»)
QUADRI_XSD = {"A": ("EB", "EC", "EL", "EM", "EP", "EQ", "ER"),
              "C": ("EB", "EC", "EL", "EM"),
              "D": ("EB", "EC", "EL", "EM", "EN", "EO"),
              "E": ("EB", "EC", "EL", "EM"),
              "G": ("EB", "EC", "EL", "EM", "EN"),
              "H": ("EC", "EM"),
              "M": ("EB", "EC", "EL", "EM"),
              "N": ("EB", "EL")}
#: quadri supportati da questa versione (i fabbricati/terreni tavolari EL ed EM non sono provati con queste agevolazioni).
#: EO: l'annotazione ammette solo D e Q (Q e' in riduzioni_art25.py); D = «quote sociali e azioni» (Fascicolo I p. PDF 56 e 58,
#: cod. D: esenti da imposta di successione, ipotecaria e catastale; EH sez. IV FlagD per il dichiarante, altrimenti EG10)
QUADRI_SUPPORTATI = {"A": ("EB", "EC"), "C": ("EB",), "D": ("EB", "EC", "EN", "EO"), "E": ("EB",), "G": ("EN",), "H": ("EC",),
                     "M": ("EB", "EC"), "N": ("EB",)}
#: gradi di parentela ammessi (annotazione XSD di Devoluzione/Agevolazioni, righi «L'agevolazione N/D/G non puo' essere richiesta
#: da soggetti con grado di parentela diverso da ...»)
GRADI = {"N": {"01", "02", "03", "04", "5A", "5B", "06", "7A", "7B", "08", "9A", "9B"},
         "D": {"01", "02", "04", "06", "08"},
         "G": {"02", "03", "04", "5A", "5B", "06", "7A", "7B"}}
#: per ogni bene una sola fra queste tipologie (annotazione XSD: «A, C, D, E, L, M, N, P, Z, X e Y ... non possono essere presenti
#: altre agevolazioni»; F, G, Q, R possono invece convivere)
ESCLUSIVI = ("A", "C", "D", "E", "L", "M", "N", "P", "X", "Y", "Z")
FONTE_SINOTTICO = FO.fonte_fasc1(57, "quadro sinottico delle agevolazioni (I, C, S)")
FONTE_ALLEGATO2 = FO.fonte_fasc1(56, "Allegato 2: codici delle agevolazioni")
FONTE_CALCOLO = "All. Specifiche tecniche (calcolo imposta di successione) p. 1: QE senza i righi A, D, C, G, N, E, H"


def inizializza(x) -> None:
    x.ag_righe = []       # {"did", "bene_id", "persona_id", "quadro", "codice"}
    x.ag_eg10 = False     # C, D, E richiesti da un beneficiario diverso dal dichiarante (rigo EG10)
    x.ag_altro = False    # H: documentazione nel quadro EG (rigo EG8 «Altro»)


def leggi_riga(x, d: dict, b: dict, quadro: str, perc: str, pid: str) -> None:
    """Legge il codice della riga ``d`` se e' uno dei codici di questo modulo; registra ``x.agev_dev`` e ``x.ag_righe``."""
    v = SUP.attr(x.d, "devoluzioni", d, "agevolazioni")
    if v in (None, "") or V.e_stato(v):
        return
    codice = str(v).strip().upper()
    if codice not in CODICI:
        return
    fonte = FO.fonte_annotazione(EL_AGEV)
    if x.tipo_ea.get(pid) == "5":
        x.err("REGOLA_AGEVOLAZIONE_TRUST", perc + ".agevolazioni", "le agevolazioni non possono essere presenti in presenza di "
              "devoluzione a soggetti di tipo 5 (trust)", fonte)
        return
    if quadro not in QUADRI_XSD[codice]:
        x.err("REGOLA_AGEVOLAZIONE_QUADRO", perc + ".agevolazioni", f"il codice {codice} non e' ammesso nel quadro {quadro} "
              f"(ammessi: {', '.join(QUADRI_XSD[codice])})", fonte)
        return
    if quadro not in QUADRI_SUPPORTATI[codice]:
        x.ns.append(f"{perc}.agevolazioni={codice} nel quadro {quadro}: non supportato in questa versione (supportati: "
                    f"{', '.join(QUADRI_SUPPORTATI[codice])}; docs/regole/agevolazioni.md)")
        return
    if codice == "D" and quadro == "EO":
        tt = str(SUP.attr(x.d, "beni", b, "tipo_titolo") or "")
        if tt in ("3", "4"):
            # Fascicolo I p. PDF 58 (cod. D): «quote sociali e azioni»; un titolo esente (3) o un fondo comune (4) non lo e'.
            # L'XSD non lo vieta: avviso non bloccante.
            x.avv("AGEVOLAZIONE_D_TIPO_TITOLO", perc + ".agevolazioni", f"agevolazione D su un titolo di tipo {tt} (esente o "
                  "fondo comune): il Fascicolo I la riferisce a quote sociali e azioni; verificare i requisiti",
                  FO.fonte_fasc1(58, "cod. D") + "; " + fonte)
    grado = (x.soggetti_ea.get(pid) or {}).get("GradoParentela")
    if codice in GRADI and grado not in GRADI[codice]:
        x.err("REGOLA_AGEVOLAZIONE_GRADO", perc + ".agevolazioni", f"l'agevolazione {codice} non puo' essere richiesta da un "
              f"soggetto con grado di parentela {grado} (ammessi: {', '.join(sorted(GRADI[codice]))})", fonte)
        return
    if codice == "H" and grado in ("36", "37", "38", "39"):
        x.err("REGOLA_AGEVOLAZIONE_H_PERSONE_FISICHE", perc + ".agevolazioni", "il codice H e' ammesso solo a favore di persone "
              "fisiche", fonte)
        return
    x.agev_dev[d["id"]] = codice
    x.ag_righe.append({"did": d["id"], "bene_id": b["id"], "persona_id": pid, "quadro": quadro, "codice": codice})


def valida(x) -> None:
    """Regole incrociate (dopo la costruzione dei quadri dei beni): esclusivita' per bene, richieste del dichiarante e degli altri."""
    from . import prima_casa as PC
    righe = [r for r in x.ag_righe if r["bene_id"] not in x.scartati]
    if not righe:
        return
    dich = PC._id_dichiarante(x)
    codici_bene: dict[str, set] = {}
    for r in x.agev_righe:
        codici_bene.setdefault(r["bene_id"], set()).add(r["codice"])
    for r in getattr(x, "ra_righe", []):
        if r["agev"]:
            codici_bene.setdefault(r["bene_id"], set()).add(r["agev"])
    for r in righe:
        codici_bene.setdefault(r["bene_id"], set()).add(r["codice"])
    for bid, cod in sorted(codici_bene.items()):
        if bid in x.scartati or not (cod & set(CODICI)):
            continue
        esclusivi = cod & set(ESCLUSIVI)
        if len(esclusivi) > 1 or (esclusivi and cod - set(ESCLUSIVI) - {"F", "G", "Q", "R"}):
            x.err("REGOLA_AGEVOLAZIONE_ESCLUSIVA", f"beni[{bid}]", "per uno stesso bene e' ammessa una sola fra le agevolazioni "
                  f"A, C, D, E, L, M, N, P, X, Y, Z (trovate: {', '.join(sorted(cod))})", FO.fonte_annotazione(EL_AGEV))
    for r in righe:
        if r["codice"] == "G":
            _controlla_eta_g(x, r)
        richiesta_dichiarante = r["persona_id"] == dich
        c = r["codice"]
        if c == "A":
            if richiesta_dichiarante:
                x.ra_eh.add("A")             # Sezione IV del quadro EH, AgevolazTipoA
            else:
                x.ra_eg = True               # rigo EG11 (annotazione RiduzioniImposteSuccessione: «L o A»)
        elif c in ("C", "D", "E"):
            if richiesta_dichiarante:
                x.ra_eh.add(c)               # Sezione IV, Agevolazioni/FlagC|FlagD|FlagE
            else:
                x.ag_eg10 = True             # rigo EG10 (annotazione AgevolazioniImposteIpocatastali)
        elif c == "H":
            x.ag_altro = True                # annotazione Altro: «obbligatorio in presenza di agevolazione H»


def _controlla_eta_g(x, r: dict) -> None:
    """G: «non puo' essere richiesta ... da soggetti con almeno 40 anni al momento dell'apertura della successione» (annotazione XSD
    di Devoluzione/Agevolazioni; confermato dal controllo ufficiale SUC13 2.3.1: «soggetti che hanno compiuto 40 anni»)."""
    from datetime import date
    persona = next((p for p in x.ea if p["id"] == r["persona_id"]), None)
    defunto = x.defunto or {}
    perc = f"devoluzioni[{r['did']}].agevolazioni"
    try:
        nascita = date.fromisoformat(str(persona.get("data_nascita")))
        decesso = date.fromisoformat(str(defunto.get("data_decesso")))
    except (TypeError, ValueError, AttributeError):
        x.err("DATO_MANCANTE", perc, "agevolazione G: servono la data di nascita del beneficiario e la data del decesso per "
              "verificare il limite dei 40 anni", FO.fonte_annotazione(EL_AGEV))
        return
    anni = decesso.year - nascita.year - ((decesso.month, decesso.day) < (nascita.month, nascita.day))
    if anni >= 40:
        x.err("REGOLA_AGEVOLAZIONE_G_ETA", perc, f"l'agevolazione G non puo' essere richiesta da chi ha compiuto 40 anni alla "
              f"data del decesso (il beneficiario ne aveva {anni})", FO.fonte_annotazione(EL_AGEV))


def sezione_g(x, righe_dev: list[dict]) -> dict | None:
    """EF2 (AgevolazioneG): valore delle quote con G nei quadri EB, EC, EL, EM. L'imposta fissa dipende dalla data di apertura
    (168 o 200) ed e' applicata da ``quadri_efgh.quadro_ef``."""
    sel = [r for r in righe_dev if r.get("agevolazione") == "G" and r["quadro"] in ("EB", "EC", "EL", "EM")]
    if not sel:
        return None
    return {"valore": sum((r["quota_valore"] for r in sel), 0)}


def beni_con_m(x) -> set[str]:
    """L'agevolazione M si estende a tutti i beneficiari del bene (annotazione AgevolazioneM_Valore)."""
    return {r["bene_id"] for r in x.ag_righe if r["codice"] == "M" and r["bene_id"] not in x.scartati}


def flags_agevolazioni_eh(x) -> dict:
    """Parte Agevolazioni della Sezione IV del quadro EH (FlagC, FlagD, FlagE; il FlagQ e' di ``riduzioni_art25``)."""
    return {f"Flag{c}": "1" for c in ("C", "D", "E") if c in x.ra_eh}
