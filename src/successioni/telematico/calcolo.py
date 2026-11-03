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

Perimetro: QE, QDN, QP, AN, FR, QN, PR, QTI, AL, ISL, ISN e totale. NON supportati (stato ``non_supportato``):
agevolazioni e riduzioni (L, Q, R, F, art. 25), detrazione dell'imposta estera, trust, stesso soggetto su piu' righi
EA (franchigia unica da ripartire), quadri EL-EQ, dichiarazioni sostitutive, decessi anteriori al 2025-01-01.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from fractions import Fraction

from lxml import etree

from ..schema import Errore
from . import fonti as FO

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


def _leggi(xml: bytes) -> tuple[dict, list[Errore]]:
    """Estrae i dati rilevanti per il calcolo. Restituisce (dati, motivi di non supporto)."""
    root = etree.fromstring(xml, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    dich = root.find(f".//{SUC}Dichiarazione")
    ns: list[Errore] = []
    fr = dich.find(SUC + "Frontespizio")
    dd = fr.find(f"{SUC}DatiDefunto/{SUC}UlterioriDati/{SUC}DataDecesso").text
    data_decesso = date(int(dd[4:]), int(dd[2:4]), int(dd[:2]))
    if fr.find(f"{SUC}TipoDichiarazione/{SUC}PrimaDichiarazione") is None:
        ns.append(Errore("CALCOLO_NON_SUPPORTATO", "Frontespizio/TipoDichiarazione", "dichiarazione sostitutiva o "
                         "integrativa non supportata dal calcolo", _g(8, "riferimento a EF18-bis")))
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
        for riga in (x for mod in quad.findall(SUC + "Modulo") for x in mod):
            if q == "ER" and _testo(riga, "TipoCespite"):
                tipo_cespite = _testo(riga, "TipoCespite")
                bi = bi or tipo_cespite == "BI"
            for nome in ("ValorePrecSucc", "ImpostaVersataEstero", "BeniEsteri", "BeneAziendale", "DirittoAbitazione"):
                if riga.find(SUC + nome) is not None:
                    ns.append(Errore("CALCOLO_NON_SUPPORTATO", f"Quadro{q}/{nome}", f"{nome}: riduzioni, beni esteri o "
                                     "agevolazioni non supportati dal calcolo", _g(5, "riduzioni") + "; " +
                                     _g(7, "imposta estera")))
            for dv in riga.iter(SUC + "Devoluzione"):
                if dv.find(SUC + "Agevolazioni") is not None or dv.find(SUC + "Riduzioni") is not None:
                    ns.append(Errore("CALCOLO_NON_SUPPORTATO", f"Quadro{q}/Devoluzione", "agevolazioni/riduzioni "
                                     "non supportate dal calcolo", _g(5, "riduzioni e agevolazioni")))
                ide = dv.find(SUC + "IdentificazioneSoggetto")
                pos = (int(_testo(ide, "Modulo")), int(_testo(ide, "Rigo")))
                qv = dv.find(f"{SUC}Quota/{SUC}QuotaValore")
                devs.append((pos, q, tipo_cespite if q == "ER" else None, _num(qv.text if qv is not None else None)))
    passivo = []
    for rip in dich.iter(SUC + "Ripartizione"):
        ide = rip.find(SUC + "IdentificazioneSoggetto")
        pos = (int(_testo(ide, "Modulo")), int(_testo(ide, "Rigo")))
        qv = rip.find(f"{SUC}Quota/{SUC}QuotaValore")
        passivo.append((pos, _num(qv.text if qv is not None else None)))
    return {"data_decesso": data_decesso, "carica": carica, "soggetti": soggetti, "devoluzioni": devs,
            "passivo": passivo, "bi": bi}, ns


# ------------------------------------------------------------------------------------------- calcolo
def calcola_da_xml(xml: bytes) -> RisultatoCalcolo:
    d, motivi = _leggi(xml)
    if d["data_decesso"] < DECORRENZA:
        motivi.append(Errore("CALCOLO_NON_APPLICABILE", "Frontespizio/DatiDefunto/UlterioriDati/DataDecesso",
                             "successione aperta prima del 2025-01-01: l'imposta e' liquidata dall'ufficio",
                             _g(1, "premessa") + "; " + FO.fonte_fasc1(46, "Rigo EF18bis")))
    cfs = [s["cf"] for s in d["soggetti"]]
    if len(set(cfs)) != len(cfs):
        motivi.append(Errore("CALCOLO_NON_SUPPORTATO", "QuadroEA", "stesso soggetto su piu' righi: franchigia unica da "
                             "scomputare in sequenza, ordine non definito dalla guida", _g(3, "qualifiche diverse")))
    if d["carica"] == "9" or any(s["trust"] or s["tipo"] == "5" for s in d["soggetti"]):
        motivi.append(Errore("CALCOLO_NON_SUPPORTATO", "QuadroEA", "trust non supportato dal calcolo",
                             FO.fonte_fasc1(46, "trust")))
    if any(s["rinuncia"] for s in d["soggetti"]):
        motivi.append(Errore("CALCOLO_NON_SUPPORTATO", "QuadroEA", "soggetti rinunciatari non supportati dal calcolo",
                             _g(1, "soggetti del quadro EA")))
    for s in d["soggetti"]:
        try:
            aliquota(s["grado"])
        except ValueError as e:
            motivi.append(Errore("CALCOLO_NON_SUPPORTATO", f"QuadroEA {s['pos']}", str(e), _g(9, "appendice")))
    if motivi:
        return RisultatoCalcolo(stato="non_supportato", motivi=motivi)

    ris = RisultatoCalcolo(stato="completato")
    tot_esatto = Fraction(0)
    tot_comp = Fraction(0)
    for s in sorted(d["soggetti"], key=lambda x: x["pos"]):
        pos = s["pos"]
        qe = sum((v for p, q, tc, v in d["devoluzioni"] if p == pos and tc != "DN"), Fraction(0))
        qdn = sum((v for p, q, tc, v in d["devoluzioni"] if p == pos and tc == "DN"), Fraction(0))
        qp = sum((v for p, v in d["passivo"] if p == pos), Fraction(0))
        an = max(qe + qdn - qp, Fraction(0))
        fr, fonte_fr = franchigia(s["grado"], s["handicap"])
        qn = max(an - fr, Fraction(0))
        applica_pr = not d["bi"] and s["tipo"] != "2"
        pr = max(Fraction(1, 10) * (qn - qdn) - qdn, Fraction(0)) if applica_pr else Fraction(0)
        qti = qn + pr
        al, fonte_al = aliquota(s["grado"])
        isl = qti * al
        isn = max(isl, Fraction(0))  # RID = 0 e DET = 0 nel perimetro
        # candidato 'componente_ispezionato': PR e ISL a 2 decimali HALF_UP (CalcolaImpostaSuccessione)
        pr_c = max(_half_up(Fraction(1, 10) * (qn - qdn), 2) - qdn, Fraction(0)) if applica_pr else Fraction(0)
        isl_c = _half_up((qn + pr_c) * al, 2)
        isn_c = max(isl_c, Fraction(0))
        tot_esatto += isn
        tot_comp = _half_up(tot_comp + isn_c, 2)
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
            Passaggio("RID", "riduzioni: nessuna nel perimetro supportato", "0", _g(7, "RID")),
            Passaggio("DET", "detrazione imposta estera: nessuna nel perimetro supportato", "0", _g(8, "DET.estero")),
            Passaggio("ISN", "ISL - RID - DET", esatto(isn), _g(8, "ISN")),
        ]
        ris.beneficiari.append(QuotaBeneficiario(f"{pos[0]}/{pos[1]}", s["cf"], s["tipo"], s["grado"], passi,
                                                 esatto(isn), esatto(isn_c)))
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
