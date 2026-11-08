"""Calcolo dell'imposta di successione in autoliquidazione (successioni aperte dal 2025-01-01).

FONTE UNICA delle regole: "All. Specifiche tecniche (passaggi calcolo imposta di successione).pdf" (10 pagine,
identico per SHA-256 alla guida pubblicata dall'Agenzia, vedi docs/regole/dubbio_arrotondamento.md), con i codici
dell'appendice (Allegato 1 aliquote/gradi, p. 9-10). Nessuna regola ricavata dalla memoria.

Il calcolo legge i dati DICHIARATI, cioe' l'XML prodotto da ``esporta`` (la guida somma i campi 'Valore Quota' della
dichiarazione), come fa il componente ufficiale. ``calcola(dati)`` esporta in bozza tecnica e poi chiama
``calcola_da_xml``.

Aritmetica: ``Fraction`` esatta. ARROTONDAMENTI: la guida non li definisce (e il suo esempio a p. 7-8 espone 82,08
per 82,0875). Il risultato riporta due candidati espliciti e li confronta:

- ``esatta``: nessun arrotondamento intermedio; totale arrotondato al centesimo e poi all'euro con la regola
  'per difetto se la frazione e' inferiore a 50 centesimi e per eccesso se non' (scritta nelle annotazioni XSD di
  altri righi del quadro EF, NON prescritta per EF18bis: ipotesi dichiarata);
- ``componente_ispezionato``: replica delle scale e degli arrotondamenti HALF_UP letti con ispezione statica (javap,
  nessuna esecuzione) del componente ufficiale ``controlliXMLREG2013.jar`` (vedi fonti.COMPONENTE_CALCOLO).
  E' un riscontro applicativo, non una regola fiscale.

Stato del calcolo (specifica §10): ``completato`` se i due candidati danno lo stesso importo intero dichiarabile
(EF18bis e' cm:DatoNP_Type, euro interi; un'eventuale differenza al centesimo e' riportata in nota e il centesimo non
e' considerato validato), ``divergenza_aperta`` se l'importo intero cambia, ``non_supportato`` per casistiche fuori perimetro, ``dati_incompleti`` se l'export
non riesce. ``esito_collaudo`` resta sempre ``da_collaudare``: nessun confronto eseguito con il software ufficiale.

Perimetro: QE, QDN, QP, AN, FR, QN, PR, QTI, AL, ISL, RID (riduzioni art. 25 c. 1 con i codici 1-5 e agevolazioni L, Q, R, F:
guida pp. 5-7, regole in ``riduzioni_art25.py`` e docs/regole/riduzioni_art25.md), DET (detrazione dell'imposta versata
all'estero, guida pp. 7-8), ISN e totale; righi esenti A, C, D, E, G, H, N esclusi dalla QE (guida p. 1); codici prima casa
P, X, Y, Z senza effetto sull'imposta di successione; stesso soggetto su piu' righi EA quando il totale non dipende
dall'ordine di scomputo della franchigia unica (guida p. 3); dichiarazioni sostitutive con codice 1 o 2.
NON supportati (stato ``non_supportato``, con il motivo): trust (carica 9 o tipo soggetto 5), integrativa con codice 3,
gradi senza aliquota nell'appendice, agevolazioni fuori dagli elenchi sopra, immobile aziendale con agevolazione diversa da D,
agevolazione L, Q, R, F e riduzione art. 25 sulla stessa riga, riduzioni su cespiti DN o su titoli esenti, valore precedenti
successioni senza codice art. 25, piu' righe R/F per lo stesso beneficiario, stesso soggetto su piu' righi con totale che
dipende dall'ordine; decessi anteriori al 2025-01-01 (``CALCOLO_NON_APPLICABILE``: l'imposta la liquida l'ufficio).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from fractions import Fraction

from lxml import etree

from ..schema import Errore
from . import fonti as FO
from . import agevolazioni as AG
from . import riduzioni_art25 as RA

DECORRENZA = date(2025, 1, 1)
VERSIONE_REGOLE = "calcolo-0.1 (guida SHA-256 2570aacc...; " + FO.VERSIONE_SPECIFICHE + ")"

# Appendice della guida p. 9-10 (Allegato 1). La guida scrive 05a/07a/09a; l'XSD (GradoParentela_Type) usa 5A/7A/9A
# con le stesse descrizioni: corrispondenza per descrizione, annotata in docs/regole/mappa_xsd.md.
GRADI_4 = {"01", "02", "03", "04", "5A", "5B", "06", "7A", "7B", "08", "9A", "9B"}
GRADI_6 = {"10", "11", "12", "13", "14", "15", "15A", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26"}
GRADI_8 = {"27", "28", "29", "30", "31", "32", "33", "34", "35"}
GRADI_ESENTI = {"36", "37", "38", "39"}
# Franchigie (guida p. 3)
FR_LINEA_RETTA = Fraction(1_000_000)   # gradi 01-09b
FR_FRATELLI = Fraction(100_000)        # gradi 10, 11
FR_HANDICAP = Fraction(1_500_000)      # a prescindere dal grado
GRADI_FR_FRATELLI = {"10", "11"}

SUC = "{" + FO.NS_SUC + "}"


def _g(p: int, voce: str) -> str:
    return FO.fonte_guida(p, voce)


@dataclass
class Passaggio:
    sigla: str
    descrizione: str
    valore: str            # valore esatto (decimale finito o frazione 'n/d')
    fonte: str


@dataclass
class QuotaBeneficiario:
    rigo_ea: str           # 'modulo/rigo'
    codice_fiscale: str
    tipo_soggetto: str
    grado_parentela: str
    passaggi: list[Passaggio]
    isn_esatta: str
    isn_componente: str


@dataclass
class RisultatoCalcolo:
    stato: str
    esito_collaudo: str = "da_collaudare"
    beneficiari: list[QuotaBeneficiario] = field(default_factory=list)
    candidati: dict[str, dict] = field(default_factory=dict)
    imposta_ef18bis: int | None = None
    motivi: list[Errore] = field(default_factory=list)
    note: list[str] = field(default_factory=list)
    versione: str = VERSIONE_REGOLE
    decorrenza: str = "successioni aperte (data del decesso) dal 2025-01-01; " + _g(1, "premessa")

    def asdict(self) -> dict:
        return asdict(self)


def esatto(f: Fraction) -> str:
    """Rappresentazione esatta: decimale finito se possibile, altrimenti 'n/d'."""
    d = f.denominator
    k = 0
    while d % 2 == 0:
        d //= 2
        k += 1
    j = 0
    while d % 5 == 0:
        d //= 5
        j += 1
    if d != 1:
        return f"{f.numerator}/{f.denominator}"
    cifre = max(k, j)
    n = f.numerator * 10 ** cifre // f.denominator  # esatto: il denominatore divide 10**cifre
    s = str(abs(n)).rjust(cifre + 1, "0")
    s = s[:-cifre] + "." + s[-cifre:] if cifre else s
    return ("-" if n < 0 else "") + s


def _half_up(f: Fraction, cifre: int) -> Fraction:
    scala = 10 ** cifre
    x = f * scala
    n, r = divmod(x.numerator, x.denominator)
    if f >= 0:
        n += 1 if Fraction(r, x.denominator) >= Fraction(1, 2) else 0
    return Fraction(n, scala)


def _num(testo: str | None) -> Fraction:
    """Importo XSD ('12345' o '123,45') -> Fraction esatta."""
    return Fraction(Decimal((testo or "0").replace(",", ".")))


def aliquota(grado: str) -> tuple[Fraction, str]:
    if grado in GRADI_4:
        return Fraction(4, 100), _g(9, "4% coniuge e parenti in linea retta")
    if grado in GRADI_6:
        return Fraction(6, 100), _g(9, "6% fratelli, sorelle, altri parenti fino al 4° grado e affini")
    if grado in GRADI_8:
        return Fraction(8, 100), _g(9, "8% altri soggetti")
    if grado in GRADI_ESENTI:
        return Fraction(0), _g(10, "non soggetti ad imposta") + "; " + _g(5, "Stato, Regioni ed Enti locali")
    raise ValueError(f"grado di parentela {grado!r} non presente nell'appendice della guida")


def franchigia(grado: str, handicap: bool) -> tuple[Fraction, str]:
    cand = [Fraction(0)]
    if grado in GRADI_4:
        cand.append(FR_LINEA_RETTA)
    if grado in GRADI_FR_FRATELLI:
        cand.append(FR_FRATELLI)
    if handicap:
        cand.append(FR_HANDICAP)
    return max(cand), _g(3, "franchigie; non si sommano, si applica la piu' alta (p. 4)") + \
        ("; nessuna franchigia elencata per questo grado" if max(cand) == 0 else "")


# ------------------------------------------------------------------------------------------- lettura XML
def _testo(el, nome: str) -> str | None:
    x = el.find(SUC + nome)
    return x.text if x is not None else None


def _motivo_riduzione(q, agev, rid, tc, valore, vps) -> str | None:
    """Motivo per cui la riga con riduzione non e' supportata dal calcolo (None se supportata)."""
    if agev and rid:
        return f"agevolazione {agev} e riduzione art. 25 ({rid}) sulla stessa riga: combinazione non coperta dalle fonti"
    if tc in ("DN", "ES"):
        return "riduzione su cespite DN o su titolo esente: trattamento non coperto dalle fonti"
    if agev and q not in RA.QUADRI_SUPPORTATI[agev]:
        return f"agevolazione {agev} nel quadro {q}: non supportata (supportati {', '.join(RA.QUADRI_SUPPORTATI[agev])})"
    if rid:
        if rid not in RA.CODICI_RID or q not in RA.QUADRI_RID:
            return f"riduzione art. 25 {rid} nel quadro {q}: non supportata"
        if vps is None or valore is None or _num(vps) <= 0 or _num(vps) > _num(valore):
            return "riduzione art. 25 senza un valore precedenti successioni valido (0 < valore prec. succ. <= valore)"
    return None


def _leggi(xml: bytes) -> tuple[dict, list[Errore]]:
    """Estrae i dati rilevanti per il calcolo. Restituisce (dati, motivi di non supporto)."""
    root = etree.fromstring(xml, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    dich = root.find(f".//{SUC}Dichiarazione")
    ns: list[Errore] = []
    fr = dich.find(SUC + "Frontespizio")
    dd = fr.find(f"{SUC}DatiDefunto/{SUC}UlterioriDati/{SUC}DataDecesso").text
    data_decesso = date(int(dd[4:]), int(dd[2:4]), int(dd[:2]))
    # sostitutiva codici 1 e 2: l'imposta si ricalcola su tutti i dati della dichiarazione, non sulle sole modifiche
    # (Fascicolo I p. PDF 47, EF18bis col. 2); il codice 3 non contiene i quadri del calcolo
    if (fr.find(f"{SUC}TipoDichiarazione/{SUC}PrimaDichiarazione") is None and
            fr.findtext(f"{SUC}TipoDichiarazione/{SUC}DichiarazioneSostitutiva") not in ("1", "2")):
        ns.append(Errore("CALCOLO_NON_SUPPORTATO", "Frontespizio/TipoDichiarazione", "dichiarazione integrativa (codice 3) "
                         "o tipo non riconosciuto: non supportata dal calcolo", _g(8, "riferimento a EF18-bis")))
    carica = fr.findtext(f"{SUC}Presentatore/{SUC}CodiceCarica")
    soggetti = []
    for m, mod in enumerate(dich.findall(f"{SUC}QuadroEA/{SUC}Modulo"), 1):
        for r, s in enumerate(mod.findall(SUC + "Soggetto"), 1):
            soggetti.append({"pos": (m, r), "cf": _testo(s, "CodiceFiscale"), "tipo": _testo(s, "TipoSoggetto"),
                             "grado": _testo(s, "GradoParentela"), "handicap": _testo(s, "PortatoreHandicap") == "1",
                             "rinuncia": _testo(s, "Rinuncia") == "1", "trust": s.find(SUC + "Trust") is not None})
    devs = []  # (pos EA, quadro, tipo cespite, valore quota)
    bi = False
    for q in ("EB", "EC", "EL", "EM", "EN", "EO", "EP", "EQ", "ER"):
        quad = dich.find(SUC + f"Quadro{q}")
        if quad is None:
            continue
        if q not in ("EB", "EC", "EL", "EM", "EN", "EO", "EP", "EQ", "ER"):
            ns.append(Errore("CALCOLO_NON_SUPPORTATO", f"Quadro{q}", f"quadro {q} non supportato dal calcolo",
                             _g(1, "QE")))
            continue
        tipo_cespite = None
        esente_eo = False
        val_riga, vps_riga = None, None   # Valore e ValorePrecSucc del cespite; i righi di continuazione li ereditano
        az_riga = False                   # il cespite (EB, EC, EL, EM) e' un bene aziendale
        ie_riga = None                    # ImpostaVersataEstero del cespite (intero cespite), ereditata dai righi di continuazione
        for riga in (x for mod in quad.findall(SUC + "Modulo") for x in mod):
            if q == "EO":
                # Titolo esente (TipoTitolo 3 / Possesso/ValoreEsente): il «Valore Quota» comprende il valore esente
                # (annotazione XSD DevoluzioneSingolaNonImmobili_Type/Quota) ma non e' base imponibile. I righi di
                # continuazione (senza TipoTitolo) ereditano la natura del rigo precedente.
                if _testo(riga, "TipoTitolo") is not None:
                    esente_eo = _testo(riga, "TipoTitolo") == "3" or riga.find(f"{SUC}Possesso/{SUC}ValoreEsente") is not None
                poss = riga.find(SUC + "Possesso")
                if poss is not None:
                    val_riga, vps_riga = _testo(poss, "Valore"), _testo(poss, "ValorePrecSucc")
                    ie_riga = _imposta_estera(riga)
            elif _testo(riga, "Valore") is not None:
                val_riga, vps_riga = _testo(riga, "Valore"), _testo(riga, "ValorePrecSucc")
                ie_riga = _imposta_estera(riga)
            if q == "ER" and _testo(riga, "TipoCespite"):
                tipo_cespite = _testo(riga, "TipoCespite")
                bi = bi or tipo_cespite == "BI"
            # beni esteri e imposta estera: supportati (detrazione DET.estero, guida pp. 7-8)
            if q in ("EB", "EC", "EL", "EM") and _testo(riga, "Valore") is not None:
                az_riga = riga.find(SUC + "BeneAziendale") is not None      # i righi di continuazione ereditano la casella
            # la casella DirittoAbitazione (codici 1-8) non modifica l'imposta di successione: la guida al calcolo (pp. 1 e 5) non la
            # elenca fra esclusioni e riduzioni, le righe restano valutate «valore x quota» (annotazione XSD di Quota) e la prima casa
            # incide solo sulle imposte ipotecaria e catastale (Fascicolo I p. PDF 57, quadro sinottico); docs/regole/diritto_abitazione.md
            for dv in riga.iter(SUC + "Devoluzione"):
                if az_riga and q in ("EB", "EC", "EL", "EM"):
                    # immobile aziendale: il suo valore e' compreso nel valore dell'azienda del quadro EN (Fascicolo I pp. PDF 21 e 29:
                    # «quadro EN, indicandone l'intero valore»; annotazioni di QuadroEE): non si conta due volte nella QE
                    agev_az = _testo(dv, "Agevolazioni") or None
                    if agev_az not in (None, "D"):
                        ns.append(Errore("CALCOLO_NON_SUPPORTATO", f"Quadro{q}/Devoluzione", f"immobile aziendale con agevolazione "
                                         f"{agev_az}: non supportato dal calcolo", _g(5, "riduzioni e agevolazioni")))
                    continue
                # Guida al calcolo p. 1 (QE: esclusi solo i codici A, D, C, G, N, E, H) e p. 5 (riduzioni: solo L, Q, R, F e
                # art. 25): i codici prima casa P, X, Y, Z non modificano l'imposta di successione (Fascicolo I p. PDF 57,
                # quadro sinottico: solo imposte ipotecaria e catastale fisse)
                agev, rid = _testo(dv, "Agevolazioni") or None, _testo(dv, "Riduzioni") or None
                if agev not in (None, "P", "X", "Y", "Z") + RA.CODICI_AGEV + AG.CODICI:
                    ns.append(Errore("CALCOLO_NON_SUPPORTATO", f"Quadro{q}/Devoluzione", f"agevolazione {agev} non "
                                     "supportata dal calcolo", _g(5, "riduzioni e agevolazioni")))
                tc_riga = tipo_cespite if q == "ER" else ("ES" if q == "EO" and esente_eo else None)
                if agev in RA.CODICI_AGEV or rid:
                    motivo = _motivo_riduzione(q, agev, rid, tc_riga, val_riga, vps_riga)
                    if motivo:
                        ns.append(Errore("CALCOLO_NON_SUPPORTATO", f"Quadro{q}/Devoluzione", motivo,
                                         _g(5, "riduzioni") + "; " + _g(7, "Rid.art25") + "; " + RA.FONTE_SINOTTICO))
                elif vps_riga is not None:
                    ns.append(Errore("CALCOLO_NON_SUPPORTATO", f"Quadro{q}/ValorePrecSucc", "valore precedenti successioni "
                                     "senza il codice di riduzione art. 25 nella devoluzione", _g(7, "r25")))
                ide = dv.find(SUC + "IdentificazioneSoggetto")
                pos = (int(_testo(ide, "Modulo")), int(_testo(ide, "Rigo")))
                qv = dv.find(f"{SUC}Quota/{SUC}QuotaValore")
                qe_el = dv.find(f"{SUC}Quota/{SUC}QuotaElementi")
                devs.append((pos, q, tc_riga, _num(qv.text if qv is not None else None),
                             {"agev": agev if agev in RA.CODICI_AGEV else None, "rid": rid,
                              "esente": agev in AG.ESENTI_SUCCESSIONE,      # guida p. 1: QE senza i righi A, D, C, G, N, E, H
                              "valore": _num(val_riga), "vps": _num(vps_riga),
                              "ie": ie_riga, "qn": int(_testo(qe_el, "QuotaNumeratore") or 0) if qe_el is not None else 0,
                              "qd": int(_testo(qe_el, "QuotaDenominatore") or 1) if qe_el is not None else 1}))
    passivo = []
    for rip in dich.iter(SUC + "Ripartizione"):
        ide = rip.find(SUC + "IdentificazioneSoggetto")
        pos = (int(_testo(ide, "Modulo")), int(_testo(ide, "Rigo")))
        qv = rip.find(f"{SUC}Quota/{SUC}QuotaValore")
        passivo.append((pos, _num(qv.text if qv is not None else None)))
    return {"data_decesso": data_decesso, "carica": carica, "soggetti": soggetti, "devoluzioni": devs,
            "passivo": passivo, "bi": bi}, ns


def _imposta_estera(riga) -> int | None:
    """ImpostaVersataEstero del rigo: direttamente (EB, EC) o dentro BeniEsteri (EN, EO, EP, EQ, ER); ``None`` se assente."""
    n = riga.find(SUC + "ImpostaVersataEstero")
    if n is None:
        be = riga.find(SUC + "BeniEsteri")
        n = be.find(SUC + "ImpostaVersataEstero") if be is not None else None
    return int(n.text) if n is not None and (n.text or "").strip().isdigit() else None


# ------------------------------------------------------------------------------------------- detrazione imposta estera
def detrazione_estera_esatta(righe: list[dict], isl: Fraction, qe: Fraction) -> Fraction:
    """DET.estero con aritmetica esatta. Guida al calcolo pp. 7-8: e = valore quota del bene estero x ISL / QE;
    IE = imposta versata all'estero x quota di devoluzione; DET.estero = e se IE >= e, altrimenti IE; somma sui cespiti."""
    if qe <= 0 or isl <= 0:
        return Fraction(0)
    det = Fraction(0)
    for r in righe:
        if r["ie"]:
            e = r["qv"] * isl / qe
            ie = Fraction(r["ie"]) * Fraction(r["qn"], r["qd"])
            det += e if ie >= e else ie
    return det


def detrazione_estera_componente(righe: list[dict], isl: Fraction, qe: Fraction) -> Fraction:
    """Stessa detrazione con le scale del componente ufficiale (ispezione statica di
    ``CalcolaImpostaSuccessione.setDET`` e ``calcolaImpostaEsteraDET``, controlliXMLREG2013.jar): valore quota e imposta versata
    come ``double``; e = (valore quota x (ISL / QE a 10 decimali HALF_UP)) a 4 decimali HALF_UP; quota di devoluzione =
    numeratore / denominatore a 5 decimali HALF_UP; IE = imposta x quota; DET = IE se IE < e, altrimenti e; somma sui cespiti
    con imposta estera > 0. ISN = ISL - RID - DET, non negativa."""
    if qe <= 0 or isl <= 0:
        return Fraction(0)
    r10 = _half_up(isl / qe, 10)
    det = Fraction(0)
    for r in righe:
        if r["ie"]:
            e = _half_up(_dbl(r["qv"]) * r10, 4)
            ie = _dbl(Fraction(r["ie"])) * _half_up(Fraction(r["qn"], r["qd"]), 5)
            det += ie if ie < e else e
    return det


# ------------------------------------------------------------------------------------------- riduzioni
def _dbl(f: Fraction) -> Fraction:
    """Valore letto come ``double`` e convertito con ``new BigDecimal(double)`` (residuo binario incluso)."""
    return Fraction(float(f))


#: coefficienti del componente: ``new BigDecimal(0.5d)`` ecc. (valori double, con residuo binario; ispezione statica di
#: AgevolazioniRiduzioni: mapRiduzione e coefficienti 0,5 / 0,4 delle agevolazioni)
_C_COMP_AGEV = {k: Fraction(float(v)) for k, v in RA.COEFF_AGEV.items()}
_C_COMP_25 = {k: Fraction(float(v)) for k, v in RA.COEFF_ART25.items()}
_SIGLE_RID = ("art25", "L", "Q", "R", "F")


def riduzioni_esatte(righe: list[dict], isl: Fraction, qe: Fraction) -> dict[str, Fraction]:
    """Rid.art25, Rid.agevL/Q/R/F con aritmetica esatta. Formule: guida p. 5-7 (r = valore quota agevolata x ISL / QE;
    Rid.agevL = r x 0,5; Q = r x 0,4; R e F = r x 0,4 se il valore della quota <= 103.291, altrimenti
    (103.291 x ISL / QE) x 0,4; r25 = (valore prec. succ. x valore quota / valore cespite) x ISL / QE, per il coefficiente
    0,5 / 0,4 / 0,3 / 0,2 / 0,1 dei codici 1-5)."""
    out = {k: Fraction(0) for k in _SIGLE_RID}
    if qe <= 0 or isl <= 0:
        return out
    rapporto = isl / qe
    for r in righe:
        qv = r["qv"]
        if r["agev"]:
            base = qv if r["agev"] in ("L", "Q") else min(qv, RA.SOGLIA_RF)
            out[r["agev"]] += base * rapporto * RA.COEFF_AGEV[r["agev"]]
        if r["rid"] and r["valore"] > 0:
            out["art25"] += r["vps"] * qv / r["valore"] * rapporto * RA.COEFF_ART25[r["rid"]]
    return out


def riduzioni_componente(righe: list[dict], isl: Fraction, qe: Fraction) -> dict[str, Fraction]:
    """Stesse riduzioni con le scale del componente ufficiale (ispezione statica di
    ``it.finanze.entrate.sco.modSUC.beans.AgevolazioniRiduzioni.calcolaAliquota`` e ``calcolaRiduzione``, classe di
    controlliXMLREG2013.jar, SHA-256 0b42dfc3...): rapporto ISL / QE a 10 decimali HALF_UP per L, Q, R, F (a 6 decimali per
    l'art. 25); R oltre soglia: somma riportata a 2 decimali HALF_UP; art. 25: (VPS x valore quota / valore) a 6 decimali
    HALF_UP, per il rapporto a 6 decimali, per il coefficiente, a 3 decimali HALF_UP. Valori e coefficienti sono ``double``."""
    out = {k: Fraction(0) for k in _SIGLE_RID}
    if qe <= 0 or isl <= 0:
        return out
    r10, r6 = _half_up(isl / qe, 10), _half_up(isl / qe, 6)
    for r in righe:
        qv = _dbl(r["qv"])
        a = r["agev"]
        if a in ("L", "Q"):
            out[a] += qv * r10 * _C_COMP_AGEV[a]
        elif a in ("R", "F"):
            if qv <= RA.SOGLIA_RF:
                out[a] += qv * r10 * _C_COMP_AGEV[a]
            else:
                out[a] += RA.SOGLIA_RF * r10 * _C_COMP_AGEV[a]
                if a == "R":
                    out[a] = _half_up(out[a], 2)
        if r["rid"] and r["valore"] > 0 and r["vps"] > 0:
            base = _half_up(_dbl(r["vps"]) * qv / _dbl(r["valore"]), 6) * r6
            out["art25"] += _half_up(_C_COMP_25[r["rid"]] * base, 3)
    return out


# ------------------------------------------------------------------------------------------- calcolo
def _passaggi_rid(righe: list[dict], rid_e: dict[str, Fraction]) -> list[Passaggio]:
    if not righe:
        return []
    fonti = {"art25": _g(7, "Rid.art25 = r25 x coefficiente; r25 a p. 7") + "; " + _g(6, "casella Riduzioni Art. 25"),
             "L": _g(6, "Rid.agevL = r x 0,5"), "Q": _g(6, "Rid.agevQ = r x 0,4"),
             "R": _g(6, "Rid.agevR: soglia 103.291,00"), "F": _g(6, "Rid.agevF: soglia 103.291,00")}
    nomi = {"art25": "Rid.art25", "L": "Rid.agevL", "Q": "Rid.agevQ", "R": "Rid.agevR", "F": "Rid.agevF"}
    usati = {"art25": any(r["rid"] for r in righe), **{c: any(r["agev"] == c for r in righe) for c in RA.CODICI_AGEV}}
    return [Passaggio(nomi[k], f"riduzione {nomi[k]} sui righi con la relativa richiesta", esatto(rid_e[k]), fonti[k])
            for k in _SIGLE_RID if usati[k]]


def calcola_da_xml(xml: bytes) -> RisultatoCalcolo:
    d, motivi = _leggi(xml)
    if d["data_decesso"] < DECORRENZA:
        motivi.append(Errore("CALCOLO_NON_APPLICABILE", "Frontespizio/DatiDefunto/UlterioriDati/DataDecesso",
                             "successione aperta prima del 2025-01-01: l'imposta e' liquidata dall'ufficio",
                             _g(1, "premessa") + "; " + FO.fonte_fasc1(46, "Rigo EF18bis")))
    if d["carica"] == "9" or any(s["trust"] or s["tipo"] == "5" for s in d["soggetti"]):
        motivi.append(Errore("CALCOLO_NON_SUPPORTATO", "QuadroEA", "trust non supportato dal calcolo",
                             FO.fonte_fasc1(46, "trust")))
    for s in d["soggetti"]:
        try:
            aliquota(s["grado"])
        except ValueError as e:
            motivi.append(Errore("CALCOLO_NON_SUPPORTATO", f"QuadroEA {s['pos']}", str(e), _g(9, "appendice")))
    for s in d["soggetti"]:
        for cod in ("R", "F"):
            n = sum(1 for p, q, tc, v, ex in d["devoluzioni"] if p == s["pos"] and ex["agev"] == cod)
            if n > 1:
                motivi.append(Errore("CALCOLO_NON_SUPPORTATO", f"QuadroEA {s['pos']}", f"{n} righe con codice {cod}: la guida "
                                     "applica la soglia per riga, il Fascicolo I (p. PDF 63) la riferisce al valore "
                                     "complessivo", _g(6, "Rid.agevR / Rid.agevF") + "; " + RA.FONTE_SINOTTICO))
    if motivi:
        return RisultatoCalcolo(stato="non_supportato", motivi=motivi)

    ris = RisultatoCalcolo(stato="completato")
    tot_esatto = Fraction(0)
    tot_comp = Fraction(0)
    def calcola_riga(s, fr_res=None):
        pos = s["pos"]
        # titoli esenti EO (tc "ES"): non entrano ne' in QE ne' in QDN. Fonti: Fascicolo I p. PDF 3 («ogni altro bene o
        # diritto dichiarato esente dall'imposta»; indicazione dei titoli esenti «opzionale», con valenza solo verso gli
        # operatori finanziari) e guida p. 1 (QE = valore imponibile). La guida non elenca il tipo 3 fra le esclusioni
        # A, D, C, G, N, E, H: l'esclusione e' un'interpretazione dichiarata, riportata nelle note del risultato.
        qe = sum((v for p, q, tc, v, ex in d["devoluzioni"] if p == pos and tc not in ("DN", "ES") and not ex.get("esente")),
                 Fraction(0))
        qdn = sum((v for p, q, tc, v, ex in d["devoluzioni"] if p == pos and tc == "DN"), Fraction(0))
        qp = sum((v for p, v in d["passivo"] if p == pos), Fraction(0))
        an = max(qe + qdn - qp, Fraction(0))
        fr, fonte_fr = franchigia(s["grado"], s["handicap"])
        if fr_res is not None:      # soggetto su piu' righi: franchigia unica, residuo dopo le righe gia' calcolate
            fr = fr_res
        usata = min(an, fr)
        qn = max(an - fr, Fraction(0))
        applica_pr = not d["bi"] and s["tipo"] != "2"
        pr = max(Fraction(1, 10) * (qn - qdn) - qdn, Fraction(0)) if applica_pr else Fraction(0)
        qti = qn + pr
        al, fonte_al = aliquota(s["grado"])
        isl = qti * al
        righe_rid = [{"qv": v, **{k: ex[k] for k in ("agev", "rid", "valore", "vps")}}
                     for p, q, tc, v, ex in d["devoluzioni"] if p == pos and (ex["agev"] or ex["rid"])]
        rid_e = riduzioni_esatte(righe_rid, isl, qe)
        rid = sum(rid_e.values(), Fraction(0))
        righe_det = [{"qv": v, **{k: ex[k] for k in ("ie", "qn", "qd")}}
                     for p, q, tc, v, ex in d["devoluzioni"] if p == pos and ex["ie"]]
        det = detrazione_estera_esatta(righe_det, isl, qe)
        isn = max(isl - rid - det, Fraction(0))
        # candidato 'componente_ispezionato': PR e ISL a 2 decimali HALF_UP (CalcolaImpostaSuccessione)
        pr_c = max(_half_up(Fraction(1, 10) * (qn - qdn), 2) - qdn, Fraction(0)) if applica_pr else Fraction(0)
        isl_c = _half_up((qn + pr_c) * al, 2)
        rid_c_d = riduzioni_componente(righe_rid, isl_c, qe)
        rid_c = sum(rid_c_d.values(), Fraction(0))
        det_c = detrazione_estera_componente(righe_det, isl_c, qe)
        isn_c = max(isl_c - rid_c - det_c, Fraction(0))
        passi = [
            Passaggio("QE", "somma dei Valore Quota dei cespiti EB, EC, ER (esclusi DN) devoluti al soggetto", esatto(qe),
                      _g(1, "QE")),
            Passaggio("QDN", "somma dei Valore Quota dei cespiti DN del quadro ER", esatto(qdn), _g(2, "QDN")),
            Passaggio("QP", "somma dei Valore Quota della ripartizione del quadro ED", esatto(qp), _g(2, "QP")),
            Passaggio("AN", "QE + QDN - QP (non negativo: interpretazione, vedi docs/regole/dubbio_arrotondamento.md)",
                      esatto(an), _g(3, "AN")),
            Passaggio("FR", f"franchigia per grado {s['grado']}" + (" e persona con disabilita'" if s["handicap"] else ""),
                      esatto(fr), fonte_fr),
            Passaggio("QN", "AN - FR (non negativa)", esatto(qn), _g(4, "QN")),
            Passaggio("PR", "presunzione 10% su denaro, gioielli e mobilia: [10% (QN - QDN)] - QDN, se negativa zero"
                      + ("" if applica_pr else "; non applicata (legatario o beni inventariati BI)"), esatto(pr),
                      _g(4, "PR")),
            Passaggio("QTI", "QN + PR", esatto(qti), _g(4, "QTI")),
            Passaggio("AL", f"aliquota per grado {s['grado']}", esatto(al), fonte_al),
            Passaggio("ISL", "QTI x AL", esatto(isl), _g(5, "ISL")),
            *_passaggi_rid(righe_rid, rid_e),
            Passaggio("RID", "riduzioni: Rid.art25 + Rid.agevL + Rid.agevQ + Rid.agevR + Rid.agevF" +
                      ("" if righe_rid else " (nessuna richiesta)"), esatto(rid), _g(7, "RID")),
            Passaggio("DET", "detrazione imposta estera: DET.estero = min(e, IE), e = valore quota estero x ISL / QE, "
                      "IE = imposta versata all'estero x quota di devoluzione" if righe_det else
                      "detrazione imposta estera: nessuna imposta versata all'estero", esatto(det), _g(8, "DET.estero")),
            Passaggio("ISN", "ISL - RID - DET", esatto(isn), _g(8, "ISN")),
        ]
        return {"isn": isn, "isn_c": isn_c, "usata": usata,
                "benef": QuotaBeneficiario(f"{pos[0]}/{pos[1]}", s["cf"], s["tipo"], s["grado"], passi, esatto(isn), esatto(isn_c))}

    # Soggetto su piu' righi (es. erede e legatario): «la franchigia e' unica e deve essere scomputata prima su una quota e poi il
    # restante importo deve essere sottratto dalle quote successive, fino al suo completo esaurimento» (Guida p. 3). La guida non
    # fissa quale quota per prima: si calcolano tutti gli ordini e il caso si accetta solo se il totale non ne dipende.
    from itertools import permutations
    per_cf: dict[str, list] = {}
    for s in sorted(d["soggetti"], key=lambda x: x["pos"]):
        per_cf.setdefault(s["cf"], []).append(s)
    for cf_, righe in per_cf.items():
        esiti = []
        for ordine in (permutations(righe) if len(righe) > 1 else [tuple(righe)]):
            fr_res, parziali = None, []
            for s in ordine:
                if fr_res is None:
                    fr_res = franchigia(s["grado"], s["handicap"])[0]
                r = calcola_riga(s, fr_res)
                fr_res -= r["usata"]
                parziali.append(r)
            esiti.append(sorted(parziali, key=lambda r: tuple(int(x) for x in r["benef"].rigo_ea.split("/"))))
        totali = {(sum((r["isn"] for r in e), Fraction(0)), sum((r["isn_c"] for r in e), Fraction(0))) for e in esiti}
        if len(totali) > 1:
            return RisultatoCalcolo(stato="non_supportato", motivi=[Errore(
                "CALCOLO_NON_SUPPORTATO", "QuadroEA", f"stesso soggetto ({cf_}) su piu' righi: l'imposta dipende dall'ordine con cui "
                "si scomputa la franchigia unica, che la guida non definisce", _g(3, "qualifiche diverse"))])
        for r in esiti[0]:
            tot_esatto += r["isn"]
            tot_comp = _half_up(tot_comp + r["isn_c"], 2)
            ris.beneficiari.append(r["benef"])
    ris.beneficiari.sort(key=lambda b: tuple(int(x) for x in b.rigo_ea.split("/")))
    cent_e = _half_up(tot_esatto, 2)
    euro_e = _half_up(cent_e, 0)
    euro_c = _half_up(tot_comp, 0)
    ris.candidati = {
        "esatta": {"totale_esatto": esatto(tot_esatto), "totale_centesimi": esatto(cent_e),
                   "imposta_ef18bis": int(euro_e),
                   "politica": "nessun arrotondamento intermedio; centesimo e poi euro HALF_UP sul totale (ipotesi)"},
        "componente_ispezionato": {"totale_centesimi": esatto(tot_comp), "imposta_ef18bis": int(euro_c),
                                   "politica": "PR e ISL setScale(2, HALF_UP); totale accumulato a 2 decimali HALF_UP; "
                                               "setScale(0, HALF_UP) finale",
                                   "fonte": FO.COMPONENTE_CALCOLO + " (ispezione statica, non esecuzione)"},
    }
    campo_ef = "QuadroEF/SezioneVBis_ImpostaSuccessione/ImpostaCalcolata/Imposta (cm:DatoNP_Type, euro interi)"
    if euro_e == euro_c:
        # l'importo dichiarabile (intero) non dipende dalla politica di arrotondamento
        ris.imposta_ef18bis = int(euro_e)
        if cent_e != tot_comp:
            ris.note.append(f"I candidati differiscono al centesimo ({esatto(cent_e)} / {esatto(tot_comp)}) ma non "
                            f"sull'importo intero dichiarabile in {campo_ef}: il centesimo NON e' considerato validato.")
    else:
        ris.stato = "divergenza_aperta"
        ris.motivi.append(Errore("ARROTONDAMENTO_NON_DEFINITO", campo_ef,
                                 f"i candidati di arrotondamento danno importi diversi ({int(euro_e)} / {int(euro_c)}): "
                                 "la guida non definisce gli arrotondamenti; il caso non e' finalizzabile finche' il "
                                 "criterio non e' confermato", _g(7, "esempio 82,08") +
                                 "; docs/regole/dubbio_arrotondamento.md"))
    if ris.imposta_ef18bis is not None and ris.imposta_ef18bis <= 10:
        ris.note.append("importo <= 10 euro: imposta non dovuta se l'importo complessivo (con interessi e sanzioni) "
                        "resta <= 10 euro (" + FO.fonte_fasc1(47, "EF18bis colonna 1") + "; " +
                        FO.fonte_annotazione("QuadroEF/SezioneVBis_ImpostaSuccessione/ImpostaCalcolata/ImpostaDaVersare")
                        + ")")
    if any(tc == "ES" for _, _, tc, _, _ in d["devoluzioni"]):
        ris.note.append("Titoli esenti (EO tipo 3) esclusi dalla base imponibile (QE): " + FO.fonte_fasc1(3, "titoli esenti")
                        + "; " + _g(1, "QE = valore imponibile") + ". La guida non li elenca fra le esclusioni A, D, C, G, N, E, H: "
                        "interpretazione da confermare.")
    if any(ex["agev"] or ex["rid"] for _, _, _, _, ex in d["devoluzioni"]):
        ris.note.append("Riduzioni (art. 25 c. 1 codici 1-5, agevolazioni L, Q, R, F): formule dalla guida pp. 5-7; la guida "
                        "non definisce gli arrotondamenti, il candidato 'componente_ispezionato' replica le scale lette "
                        "con ispezione statica di AgevolazioniRiduzioni (docs/regole/riduzioni_art25.md).")
    ris.note.append("Gli eredi sono tenuti in solido all'imposta complessiva; i legatari alla propria quota (" +
                    _g(8, "chiusura") + ").")
    return ris


def calcola(dati: dict, contesto=None) -> RisultatoCalcolo:
    """Calcola sulla dichiarazione esportata (bozza tecnica). Se l'esportazione non riesce: ``dati_incompleti``."""
    from .esporta import ContestoExport, esporta_xml
    if contesto is None:
        cf = None
        rif = ((dati.get("opzioni") or {}).get("telematico") or {}).get("dichiarazione", {}).get("presentatore", {}) \
            .get("persona_id")
        for p in dati.get("persone", []):
            if (rif and p["id"] == rif) or (not rif and p.get("ruolo") == "presentatore"):
                cf = p.get("codice_fiscale")
        contesto = ContestoExport(cf_fornitore=cf or "", scopo="bozza_tecnica", quadri_liquidazione=False)
    else:
        contesto = ContestoExport(**{**contesto.__dict__, "scopo": "bozza_tecnica", "quadri_liquidazione": False})
    es = esporta_xml(dati, contesto)
    if es.xml is None:
        return RisultatoCalcolo(stato="dati_incompleti", motivi=es.errori + [
            Errore("NON_SUPPORTATO", s, "dato non serializzabile: calcolo non eseguito", "esporta_xml") for s in
            es.non_supportato])
    return calcola_da_xml(es.xml)
