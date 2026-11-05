"""Esportazione della pratica nel file telematico SUC13 (perimetro iniziale dichiarato).

Contratto (docs/CONTRATTI_MODULI.md, area 1)::

    esporta_xml(dati, contesto) -> EsitoExport(xml | None, errori, non_supportato, mappa, ...)

PERIMETRO di questa versione (vedi ``PERIMETRO`` e docs/MATRICE_COPERTURA.md):
- busta tm:Messaggio / tm:Contenuto[@CodiceFornitura='SUC13'] / suc:Fornitura (Specifiche p. 4, 13-15);
- frontespizio: prima dichiarazione, devoluzione per legge, defunto residente in Italia, dichiarante erede/chiamato
  (codice carica 1) presente nel quadro EA, firma del dichiarante, impegno alla trasmissione dell'intermediario;
- EA: eredi (tipo 1) e chiamati (tipo 3) persone fisiche, senza rinuncia, rappresentazione o trust;
- EB: terreni in Italia non tavolari, natura 'T';  EC: fabbricati in Italia non tavolari con rendita;
- ER: cespiti BI, CR, DN, AB;  ED: passivita' attribuite a un solo soggetto del quadro EA;
- devoluzioni con lo stesso diritto del defunto (valore quota = valore x quota, Fascicolo I p. PDF 24);
- EE: totali calcolati dalle annotazioni XSD.
Tutto il resto finisce in ``non_supportato`` e l'XML non viene prodotto.

Quadri EF, EG, EH: per le annotazioni dello schema sono obbligatori nella quasi totalita' dei casi reali
(EF dal 2025 e con EA+immobili, EG con EA, EH salvo codici carica 5/6/7) ma NON sono generati da questa versione.
Sono riportati in ``quadri_mancanti``: ``completo`` resta False e, con ``scopo='completo'`` (predefinito), ``xml`` e'
None. Con ``scopo='bozza_tecnica'`` si ottiene l'XML valido allo schema ma dichiaratamente INCOMPLETO, utile per
prove di schema/anteprima; non va sottoposto al controllo ufficiale come dichiarazione completa ne' trasmesso.

Determinismo: stessi dati e contesto -> stessi byte. Le righe sono ordinate con chiavi derivate dai dati (non
dall'ordine delle liste), quindi riordinare le collezioni non cambia l'XML ne' la mappa id -> rigo/modulo.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from fractions import Fraction

from lxml import etree

from .. import quadri as Q
from .. import valori as V
from ..schema import Errore
from . import fonti as FO
from . import devoluzione_legge as DL
from . import formati as F
from . import identificativi as ID
from . import modello_xsd as M
from . import agevolazioni as AG
from . import prima_casa as PC
from . import riduzioni_art25 as RA
from . import quadri_efgh as EFGH
from . import frontespizio as FR
from . import sostitutiva as SO
from . import supplemento as SUP
from . import xsd as X

PERIMETRO = {
    "Frontespizio": "prima dichiarazione; devoluzione per legge; defunto residente in Italia; dichiarante con codice "
                    "carica 1 presente in EA; firma; impegno alla trasmissione se TipoFornitore=10",
    "EA": "eredi (1) e chiamati (3), persone fisiche; niente rinuncia, rappresentazione, trust, portatore handicap si",
    "EB": "terreni in Italia (provincia non tavolare), natura T, con valore",
    "EC": "fabbricati in Italia (provincia non tavolare), con rendita catastale (categorie non F) e valore",
    "ER": "tipi cespite BI, CR, DN, AB con valore; beni non esteri",
    "EL": "terreni in province tavolari (BZ, TN, GO, TS) natura T; partita tavolare obbligatoria",
    "EM": "fabbricati in province tavolari (BZ, TN, GO, TS); graffati e determinazione rendita non supportati",
    "EN": "aziende (denominazione, CF, diritto 1/2, valore); immobili aziendali, inventario, beni esteri non supportati; agevolazione Q e riduzioni art. 25 (riduzioni_art25.py)",
    "EP": "aeromobili con valore; beni esteri non supportati; riduzioni art. 25 c. 1 (codici 1-5)",
    "EQ": "navi e imbarcazioni con valore; beni esteri non supportati; riduzioni art. 25 c. 1 (codici 1-5)",
    "EO": "titoli quotati (1), non quotati (2), esenti (3, ValoreEsente), fondi (4); beni esteri non supportati",
    "ED": "passivita' con tipo, documento, possesso e ripartizione a un solo soggetto EA",
    "EE": "totali EE1, EE5, EE6, EE7, EE8 calcolati dai quadri esportati",
    "Devoluzioni": "diritto della devoluzione uguale al diritto del defunto; agevolazioni: prima casa P, X, Z in EC "
                   "(prima_casa.py) e riduzioni dell'imposta di successione L, Q, R, F e art. 25 c. 1 codici 1-5 con "
                   "valore precedenti successioni (riduzioni_art25.py, docs/regole/riduzioni_art25.md)",
}
QUADRI_ESPORTABILI = ("EA", "EB", "EC", "ED", "EE", "EF", "EG", "EH", "EL", "EM", "EN", "EO", "EP", "EQ", "ER")
SCOPI = ("completo", "bozza_tecnica")
_ID_DICH = re.compile(r"[0-9]{4}[1-9]|[0-9]{3}[1-9][0-9]|[0-9]{2}[1-9][0-9]{2}|[0-9][1-9][0-9]{3}|[1-9][0-9]{4}")


@dataclass
class ContestoExport:
    """Dati della fornitura che non appartengono alla pratica."""
    cf_fornitore: str                      # tm:Intestazione/CodiceFiscaleFornitore (Specifiche p. 13)
    tipo_fornitore: str = "1"              # suc:Intestazione/TipoFornitore: 1 o 10 (Specifiche p. 15)
    identificativo: str = "00001"          # Dichiarazione/@identificativo (fornitura_v2.xsd Identificativo_Type)
    data_riferimento: date | None = None   # 'data corrente' per DatoDT_Type; None = oggi
    impegno_codice: str | None = None      # ImpegnoATrasmettere/ImpegnoATrasmettere (reg:ImpegnoPresentazione_Type)
    data_impegno: str | None = None        # AAAA-MM-GG
    spazio_utente: str | None = None
    scopo: str = "completo"                # 'completo' | 'bozza_tecnica'
    #: file degli allegati per il quadro EG: allegato_id -> percorso, oppure {"percorso", "nome"} (dall'archivio)
    allegati: dict | None = None
    #: False: non genera EF, EG, EH (uso interno del calcolo, che legge solo i quadri dei beni e delle passivita')
    quadri_liquidazione: bool = True


@dataclass
class EsitoExport:
    xml: bytes | None
    errori: list[Errore]
    non_supportato: list[str]
    mappa: dict[str, dict]
    avvisi: list[Errore] = field(default_factory=list)
    quadri_mancanti: list[Errore] = field(default_factory=list)
    completo: bool = False
    impronta_xml: str | None = None
    versione: str = FO.VERSIONE_MODULO
    ambito: str = ("validazione di schema e regole interne del perimetro dichiarato; NON e' il controllo ufficiale "
                   "dell'Agenzia")

    def asdict(self) -> dict:
        d = asdict(self)
        d["xml"] = self.xml.decode("utf-8") if self.xml is not None else None
        return d


# --------------------------------------------------------------------------------------------- codici XSD
def _norm(s: str) -> str:
    s = s.lower().replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def codice_enum(valore, tipo: str, *, alias_descrizione: bool = False) -> str:
    """Valore ammesso dall'enumerazione XSD ``tipo``.

    Con ``alias_descrizione`` accetta anche la descrizione normalizzata (es. 'proprieta', 'nuda_proprieta',
    'usufrutto') ricavata dalla documentazione dell'enumerazione nell'XSD, e la forma a due cifre ('08' -> '8')
    usata nel Fascicolo I p. PDF 24. Nessun altro alias."""
    enum = X.enumerazioni(tipo)
    if V.e_stato(valore):
        raise F.ValoreXml(f"dato in stato '{valore['stato']}'")
    s = str(valore).strip() if valore is not None else ""
    if s in enum:
        return s
    if alias_descrizione:
        if s.isdigit() and s.lstrip("0") in enum:
            return s.lstrip("0")
        per_desc = {_norm(d): k for k, d in enum.items()}
        if _norm(s) in per_desc:
            return per_desc[_norm(s)]
    elenco = ", ".join(f"{k} ({d[:40]})" if d else k for k, d in enum.items())
    raise F.ValoreXml(f"{valore!r} non ammesso; valori ammessi ({tipo}): {elenco}")


def cf_persona(valore) -> str:
    """DatoCF_Type e, per i codici a 16 caratteri, carattere di controllo corretto (``identificativi``: replica di
    U1CheckDigit.controllaCheckDigit di checkCF_PIVA.jar, verificata eseguendo il componente). Il controllo ufficiale
    scarta (***) 'Codice Fiscale errato'. I codici numerici a 11 cifre non sono verificati qui."""
    s = F.cf(valore)
    if len(s) == 11 and not ID.piva_checksum_valida(s):
        raise F.ValoreXml(f"{s}: cifra di controllo del codice a 11 cifre errata (il controllo ufficiale scarta, 1013)")
    if len(s) == 16 and not ID.cf_persona_fisica_valido(s):
        raise F.ValoreXml(f"{s}: carattere di controllo errato (atteso {ID.carattere_controllo(s[:15])}) - "
                          + ID.FONTE_CF)
    return s


# --------------------------------------------------------------------------------------------- esportatore
class _Export:
    XP_DICH = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"

    def __init__(self, dati: dict, ctx: ContestoExport):
        self.d = dati
        self.ctx = ctx
        self.oggi = ctx.data_riferimento or date.today()
        self.errori: list[Errore] = []
        self.ns: list[str] = []
        self.avvisi: list[Errore] = []
        self.mancanti: list[Errore] = []
        self.mappa: dict[str, dict] = {}
        self.usati: dict[str, set[str]] = {}
        self.interni: dict[str, set[str]] = {}

    # ---------------------------------------------------------------- utilita'
    def err(self, codice, percorso, messaggio, fonte):
        self.errori.append(Errore(codice, percorso, messaggio, fonte))

    def avv(self, codice, percorso, messaggio, fonte):
        self.avvisi.append(Errore(codice, percorso, messaggio, fonte))

    def usa(self, ent: dict, *campi):
        self.usati.setdefault(ent["id"], set()).update(campi)

    def interno(self, ent: dict, *campi):
        self.interni.setdefault(ent["id"], set()).update(campi)

    def val(self, coll: str, ent: dict, campo: str, conv, *, elemento: str, obbl: bool = True, fonte: str | None = None):
        """Legge (entita' o supplemento), converte e registra l'uso. ``None`` se assente e facoltativo."""
        self.usa(ent, campo)
        v = SUP.attr(self.d, coll, ent, campo)
        perc = f"{coll}[{ent['id']}].{campo}"
        f = fonte or FO.fonte_xsd(elemento)
        if v is None or v == "":
            if obbl:
                self.err("DATO_MANCANTE", perc, f"dato obbligatorio per <{elemento.split('/')[-1]}>", f)
            return None
        if V.e_stato(v):
            if v["stato"] == "zero" and not obbl:
                return None
            self.err("DATO_NON_DEFINITIVO", perc, f"il dato e' in stato '{v['stato']}': non esportabile", f)
            return None
        try:
            return conv(v)
        except (F.ValoreXml, V.ValoreNonValido, KeyError, TypeError, ValueError) as e:
            self.err("VALORE_NON_VALIDO", perc, f"<{elemento.split('/')[-1]}>: {e}", f)
            return None

    # ---------------------------------------------------------------- anagrafica
    def anagrafica(self, p: dict, elemento: str) -> dict | None:
        c = "persone"
        r = {
            "Cognome": self.val(c, p, "cognome", lambda v: F.an(v, 80, tipo="AN2"), elemento=elemento + "/Cognome"),
            "Nome": self.val(c, p, "nome", lambda v: F.an(v, 80, tipo="AN2"), elemento=elemento + "/Nome"),
            "Sesso": self.val(c, p, "sesso", lambda v: codice_enum(v, "Sesso_Type"), elemento=elemento + "/Sesso"),
            "DataNascita": self.val(c, p, "data_nascita", lambda v: F.data(v, non_oltre=self.oggi),
                                    elemento=elemento + "/DataNascita"),
            "ComuneNascita": self.val(c, p, "luogo_nascita", lambda v: F.an(v, 50), elemento=elemento + "/ComuneNascita"),
            "ProvinciaNascita": self.val(c, p, "provincia_nascita", lambda v: codice_enum(str(v).upper(), "PN_Type"),
                                         elemento=elemento + "/ProvinciaNascita"),
        }
        return r if all(v is not None for v in r.values()) else None

    # ---------------------------------------------------------------- persone
    def classifica_persone(self):
        persone = self.d.get("persone", [])
        defunti = [p for p in persone if p.get("ruolo") == "defunto"]
        if len(defunti) != 1:
            self.err("DEFUNTO_NON_UNICO", "persone", "serve esattamente un soggetto con ruolo 'defunto'",
                     FO.fonte_xsd("Frontespizio/DatiDefunto"))
        self.defunto = defunti[0] if len(defunti) == 1 else None
        self.ea = [p for p in persone if p.get("ruolo") in ("erede", "legatario")]
        pres = [p for p in persone if p.get("ruolo") == "presentatore"]
        for p in persone:
            self.usa(p, "ruolo")
            if p.get("ruolo") in ("rappresentante", "altro") or p.get("ruolo") is None:
                self.scartati.add(p["id"])
                self.ns.append(f"persone[{p['id']}]: ruolo {p.get('ruolo')!r} non serializzabile in questa versione "
                               "(EA supporta eredi e chiamati; rappresentanti/altri soggetti non ancora mappati)")
        if len(pres) > 1:
            self.err("PRESENTATORE_NON_UNICO", "persone", "piu' soggetti con ruolo 'presentatore'",
                     FO.fonte_xsd("Frontespizio/Presentatore"))
        rif = SUP.presentatore_sup(self.d).get("persona_id")
        self.presentatore = None
        if rif:
            cand = [p for p in persone if p["id"] == rif]
            if not cand:
                self.err("RIFERIMENTO_INESISTENTE", "opzioni.telematico.dichiarazione.presentatore.persona_id",
                         f"persona {rif} inesistente", "docs/regole/mappa_xsd.md")
            elif pres:
                self.err("PRESENTATORE_AMBIGUO", "opzioni.telematico.dichiarazione.presentatore.persona_id",
                         "indicati sia un riferimento al presentatore sia un soggetto con ruolo 'presentatore'",
                         "docs/regole/mappa_xsd.md")
            else:
                self.presentatore = cand[0]
        elif pres:
            self.presentatore = pres[0]
        else:
            self.err("PRESENTATORE_MANCANTE", "persone", "manca il dichiarante (ruolo 'presentatore' o riferimento "
                     "opzioni.telematico.dichiarazione.presentatore.persona_id)", FO.fonte_xsd("Frontespizio/Presentatore"))

    def ordina_ea(self):
        def chiave(p):
            return ((p.get("cognome") or "").upper() if isinstance(p.get("cognome"), str) else "",
                    (p.get("nome") or "").upper() if isinstance(p.get("nome"), str) else "",
                    (p.get("codice_fiscale") or "").upper() if isinstance(p.get("codice_fiscale"), str) else "",
                    p["id"])
        self.ea.sort(key=chiave)
        self.pos_ea: dict[str, tuple[int, int]] = {}
        for i, p in enumerate(self.ea):
            self.pos_ea[p["id"]] = (i // 3 + 1, i % 3 + 1)

    def rappresentazione(self, p: dict, base: str, grado, legge: bool, el: str, cf_soggetto) -> tuple[str, str] | None:
        """Sezione «Successione per rappresentazione» (annotazioni XSD di SuccessionePerRappresentazione; Fascicolo I pp. PDF 18-19):
        obbligatoria con devoluzione per legge per i gradi 04, 15; ammessa solo per 04, 06, 08, 15, 20, 27. Il rappresentato e'
        un figlio (02) per i discendenti dei figli, un fratello (10/11) per i discendenti dei fratelli."""
        cf_r = SUP.attr(self.d, "persone", p, "rappresentato_cf")
        gr_r = SUP.attr(self.d, "persone", p, "rappresentato_grado")
        self.usa(p, "rappresentato_cf", "rappresentato_grado")
        perc = f"opzioni.telematico.persone[{p['id']}]"
        fonte = FO.fonte_annotazione(el + "/SuccessionePerRappresentazione") + "; " + DL.FONTE_RAPPRESENTAZIONE
        possibile = grado in DL.GRADI_RAPPRESENTANTE
        if cf_r in (None, "") and gr_r in (None, ""):
            if legge and grado in ("04", "15"):
                self.err("DATO_MANCANTE", perc + ".rappresentato_cf", f"grado {grado} con devoluzione per legge: indicare "
                         "codice fiscale e grado del rappresentato (sezione Successione per rappresentazione)", fonte)
            elif legge and possibile:
                self.ns.append(f"{base}: grado {grado} senza i dati del rappresentato: quote di legge non determinabili")
            return None
        if not possibile:
            self.err("VALORE_NON_VALIDO", perc + ".rappresentato_cf", f"la rappresentazione e' ammessa solo per i gradi "
                     f"{', '.join(DL.GRADI_RAPPRESENTANTE)} (grado del soggetto: {grado})", fonte)
            return None
        try:
            cf_r = F.cf(cf_r)
        except F.ValoreXml as e:
            self.err("VALORE_NON_VALIDO", perc + ".rappresentato_cf", str(e), fonte)
            return None
        atteso = ("02",) if grado in DL.GRADI_RAPPRESENTANTE_RETTA else ("10", "11")
        if str(gr_r) not in atteso:
            self.err("VALORE_NON_VALIDO", perc + ".rappresentato_grado", f"con grado {grado} il rappresentato ha grado "
                     f"{' o '.join(atteso)} (annotazione XSD di GradoParentela)", fonte)
            return None
        if cf_r == cf_soggetto or cf_r == str((self.defunto or {}).get("codice_fiscale") or "").strip().upper():
            self.err("VALORE_NON_VALIDO", perc + ".rappresentato_cf", "il rappresentato deve essere diverso dal soggetto e "
                     "dal defunto", fonte)
            return None
        return cf_r, str(gr_r)

    # ------------------------------------------------------------------ EA: residenza estera, rinuncia, denominazione
    def residenza_estera(self, p: dict, base: str, el: str) -> dict | None:
        """Sezione ``ResidenzaEstera`` del soggetto EA (Fascicolo I p. PDF 18, «Residente all'estero»; XSD Residenza_Estera_Type +
        StatoEstero): CodiceStatoEstero (3 caratteri, tabella stati esteri), StatoFederato, LocalitaEstero, IndirizzoEstero,
        StatoEstero (nome, al massimo 34 caratteri)."""
        v = SUP.attr(self.d, "persone", p, "residenza_estera")
        self.usa(p, "residenza_estera")
        if v in (None, ""):
            return None
        perc = f"opzioni.telematico.persone[{p['id']}].residenza_estera"
        fonte = FO.fonte_xsd(el + "/ResidenzaEstera") + "; " + FO.fonte_fasc1(18, "Residente all'estero")
        chiavi = {"codice_stato", "stato", "stato_federato", "localita", "indirizzo"}
        if not isinstance(v, dict) or set(v) - chiavi:
            self.err("VALORE_NON_VALIDO", perc, f"atteso un oggetto con le chiavi {sorted(chiavi)}", fonte)
            return None
        out: dict = {}
        ok = True
        for k, nome, lim, obbl in (("codice_stato", "CodiceStatoEstero", 3, True), ("stato_federato", "StatoFederato", 24, False),
                                    ("localita", "LocalitaEstero", None, False), ("indirizzo", "IndirizzoEstero", None, True),
                                    ("stato", "StatoEstero", 34, True)):
            val = v.get(k)
            if val in (None, ""):
                if obbl:
                    self.err("DATO_MANCANTE", f"{perc}.{k}", "obbligatorio per i residenti all'estero", fonte)
                    ok = False
                continue
            try:
                s = F.an(str(val), lim)
                if k == "codice_stato" and len(s) != 3:
                    raise F.ValoreXml("il codice dello Stato estero ha tre caratteri")
                out[nome] = s
            except F.ValoreXml as e:
                self.err("VALORE_NON_VALIDO", f"{perc}.{k}", str(e), fonte)
                ok = False
        if ok and "CodiceStatoEstero" in out:
            from . import stati_esteri as SE
            tab = SE.tabella()
            if tab is not None and out["CodiceStatoEstero"] not in tab:
                self.err("VALORE_NON_VALIDO", f"{perc}.codice_stato", f"codice {out['CodiceStatoEstero']} assente dalla tabella degli "
                         "Stati esteri del componente di controllo", fonte)
                ok = False
        if not ok:
            return None
        # ordine dello schema: CodiceStatoEstero, StatoFederato, LocalitaEstero, IndirizzoEstero, StatoEstero
        return {k: out[k] for k in ("CodiceStatoEstero", "StatoFederato", "LocalitaEstero", "IndirizzoEstero", "StatoEstero") if k in out}

    def estremi_registrazione(self, sez, perc: str, fonte: str) -> dict | None:
        """EstremiRegistrazione_Type da un oggetto {ufficio_registrazione, serie, numero_registrazione, sottonumero_registrazione,
        data_registrazione} (stesse regole della sezione Testamento)."""
        if not isinstance(sez, dict) or not sez:
            self.err("DATO_MANCANTE", perc, "indicare gli estremi di registrazione (ufficio, serie, numero, data)", fonte)
            return None
        ok = True
        for k in ("ufficio_registrazione", "serie", "numero_registrazione", "data_registrazione"):
            if sez.get(k) in (None, ""):
                self.err("DATO_MANCANTE", f"{perc}.{k}", "obbligatorio", fonte)
                ok = False
        if not ok:
            return None
        try:
            uff = codice_enum(sez["ufficio_registrazione"], "UfficioDiRegistrazione_Type")
        except F.ValoreXml as e:
            self.err("VALORE_NON_VALIDO", perc + ".ufficio_registrazione", str(e), fonte)
            ok = False
        if not re.fullmatch(r"[1-4][A-Z]?", str(sez["serie"])):
            self.err("VALORE_NON_VALIDO", perc + ".serie", "una cifra da 1 a 4, con lettera maiuscola facoltativa (reg:Serie_Type)", fonte)
            ok = False
        if not re.fullmatch(r"\d{1,6}", str(sez["numero_registrazione"])):
            self.err("VALORE_NON_VALIDO", perc + ".numero_registrazione", "solo cifre, al massimo 6", fonte)
            ok = False
        sn = sez.get("sottonumero_registrazione")
        if sn not in (None, "") and len(str(sn)) > 3:
            self.err("VALORE_NON_VALIDO", perc + ".sottonumero_registrazione", "al massimo 3 caratteri", fonte)
            ok = False
        try:
            data = F.data(sez["data_registrazione"], non_oltre=self.oggi)
        except F.ValoreXml as e:
            self.err("VALORE_NON_VALIDO", perc + ".data_registrazione", str(e), fonte)
            ok = False
        if not ok:
            return None
        reg = {"UfficioDiRegistrazione": uff, "Serie": str(sez["serie"]), "NumeroRegistrazione": str(sez["numero_registrazione"])}
        if sn not in (None, ""):
            reg["SottonumeroRegistrazione"] = str(sn)
        reg["DataRegistrazione"] = data
        return reg

    def denominazione(self, p: dict, base: str, grado, el: str) -> str | None:
        """Denominazione/ragione sociale al posto di cognome e nome per i soggetti diversi da persone fisiche (XSD Soggetto/Denominazione
        e annotazioni di GradoParentela: con la denominazione il grado puo' essere 35, 36, 37, 38 o 39; con i gradi 36-39 la denominazione
        e' obbligatoria). I gradi 37-39 (enti) sono esclusi dalle basi dell'imposta ipotecaria e catastale proporzionale e non
        sono soggetti a imposta di successione (Fascicolo I pp. PDF 40 e 43; Guida di calcolo p. 10)."""
        den = SUP.attr(self.d, "persone", p, "denominazione")
        self.usa(p, "denominazione")
        perc = f"opzioni.telematico.persone[{p['id']}].denominazione"
        fonte = FO.fonte_annotazione(el + "/GradoParentela") + "; " + FO.fonte_annotazione(el + "/CodiceFiscale")
        ente = grado in ("37", "38", "39")
        if den in (None, ""):
            if ente:
                self.err("DATO_MANCANTE", perc, f"con il grado {grado} la denominazione e' obbligatoria", fonte)
            return None
        if grado not in ("35", "36", "37", "38", "39"):
            self.err("VALORE_NON_VALIDO", perc, "con la denominazione il grado di parentela puo' essere solo 35, 36, 37, 38 o 39",
                     fonte)
            return None
        try:
            return F.an(str(den), 150, tipo="AN2")
        except F.ValoreXml as e:
            self.err("VALORE_NON_VALIDO", perc, str(e), fonte)
            return None

    def rinuncia(self, p: dict, base: str, tipo, grado, el: str) -> bool:
        """Rinuncia all'eredita' del soggetto EA (XSD Soggetto/Rinuncia e QuadroEH/.../Rinuncia; Fascicolo I p. PDF 17): ammessa per
        il tipo 3 (chiamato che ha rinunciato) e obbligatoria per il tipo 4 (coniuge superstite rinunciatario, grado 01); mai per
        l'erede (tipo 1). Gli estremi dell'atto di rinuncia (EH, rigo 8) sono obbligatori. Restituisce True se il soggetto e'
        rinunciatario."""
        v = SUP.attr(self.d, "persone", p, "rinuncia")
        self.usa(p, "rinuncia", "rinuncia_estremi")
        perc = f"opzioni.telematico.persone[{p['id']}]"
        fonte = FO.fonte_annotazione(el + "/Rinuncia") + "; " + FO.fonte_fasc1(17, "Tipo soggetto, codice 3 e 4")
        if v not in (None, False, True):
            self.err("VALORE_NON_VALIDO", perc + ".rinuncia", "atteso true/false", fonte)
            return False
        rinuncia = v is True or tipo == "4"
        if not rinuncia:
            if SUP.attr(self.d, "persone", p, "rinuncia_estremi") not in (None, ""):
                self.err("DATI_INCOERENTI", perc + ".rinuncia_estremi", "gli estremi della rinuncia si indicano solo per i "
                         "soggetti rinunciatari", fonte)
            return False
        if tipo == "4" and grado != "01":
            self.err("REGOLA_TIPO_SOGGETTO", base + ".tipo_soggetto", "il tipo soggetto 4 (coniuge superstite rinunciatario) "
                     "richiede il grado di parentela 01", FO.fonte_annotazione(el + "/GradoParentela"))
        if tipo not in ("3", "4"):
            self.err("REGOLA_TIPO_SOGGETTO", perc + ".rinuncia", "la rinuncia e' ammessa per il chiamato (tipo 3, che ha gia' "
                     "rinunciato) e per il coniuge superstite rinunciatario (tipo 4); non per l'erede (tipo 1) ne' per il "
                     "legatario in questa versione", fonte)
            return False
        if self.presentatore is not None and p["id"] == self.presentatore.get("id"):
            self.err("REGOLA_RINUNCIA", perc + ".rinuncia", "il dichiarante non puo' essere indicato come rinunciatario nel "
                     "quadro EH", FO.fonte_annotazione("QuadroEH/PrimoModulo/SezioneI_DichSost/Rinuncia/PresenzaRinuncia/"
                                                      "IdentificazioneSoggetto"))
        reg = self.estremi_registrazione(SUP.attr(self.d, "persone", p, "rinuncia_estremi"), perc + ".rinuncia_estremi",
                                         FO.fonte_annotazione("QuadroEH/PrimoModulo/SezioneI_DichSost/Rinuncia/PresenzaRinuncia")
                                         + "; " + FO.fonte_fasc1(17, "Rinuncia"))
        self.rinunce[p["id"]] = reg
        return True

    def controlla_soggetti_multi_riga(self, cf_visti: dict) -> None:
        """Soggetto presente su piu' righi del quadro EA (es. erede e legatario): annotazioni XSD di CodiceFiscale e TipoSoggetto.
        Il grado di parentela e la disabilita' devono coincidere su tutti i righi, il tipo soggetto deve essere diverso, e il
        chiamato (3), l'erede (1) e il coniuge rinunciatario (4) non possono coesistere fra loro per lo stesso soggetto."""
        el = "QuadroEA/Modulo/Soggetto"
        for cf_, ids in cf_visti.items():
            if len(ids) < 2:
                continue
            fonte = FO.fonte_annotazione(el + "/CodiceFiscale") + "; " + FO.fonte_annotazione(el + "/TipoSoggetto") + \
                "; " + FO.fonte_fasc1(17, "Tipo soggetto: erede e legatario su due righi")
            perc = f"persone[{', '.join(ids)}]"
            tipi = [self.tipo_ea.get(i) for i in ids]
            if None in tipi or any(self.grado_ea.get(i) is None for i in ids):
                continue                                           # gia' segnalato sul singolo soggetto
            if len(set(tipi)) != len(tipi):
                self.err("REGOLA_SOGGETTO_MULTI_RIGA", perc, "lo stesso soggetto su piu' righi deve avere tipi soggetto diversi", fonte)
            if len({self.grado_ea[i] for i in ids}) > 1:
                self.err("REGOLA_SOGGETTO_MULTI_RIGA", perc, "il grado di parentela deve coincidere su tutti i righi dello stesso "
                         "soggetto (in assenza di rappresentazione o trust)", fonte)
            if len({self.handicap_ea[i] for i in ids}) > 1:
                self.err("REGOLA_SOGGETTO_MULTI_RIGA", perc, "la disabilita' deve coincidere su tutti i righi dello stesso soggetto", fonte)
            insieme = set(tipi)
            if "3" in insieme and insieme & {"1", "4"} or {"1", "4"} <= insieme:
                self.err("REGOLA_SOGGETTO_MULTI_RIGA", perc, "i tipi soggetto 1 (erede), 3 (chiamato) e 4 (coniuge rinunciatario) non "
                         "possono coesistere per lo stesso soggetto", fonte)
            if not insieme <= {"1", "2", "3", "4"}:
                self.ns.append(f"{perc}: soggetto su piu' righi con tipi {sorted(insieme)} non supportato")

    def quadro_ea(self) -> dict | None:
        if not self.ea:
            return None
        # le regole sui gradi valgono solo con devoluzione per legge: con il testamento (senza legge) non si applicano
        legge = SUP.dich(self.d, "devoluzione_per_legge") is True or SUP.dich(self.d, "devoluzione_per_testamento") is not True
        stato_civile = SUP.dich(self.d, "stato_civile")
        soggetti, cf_visti, coniugi = [], {}, 0
        self.tipo_ea: dict[str, str] = {}
        self.grado_ea: dict[str, str] = {}
        self.rapp_ea: dict[str, tuple[str, str]] = {}   # rappresentante -> (CF rappresentato, grado del rappresentato)
        self.handicap_ea: dict[str, bool] = {}
        self.soggetti_ea: dict[str, dict] = {}
        for p in self.ea:
            base = f"persone[{p['id']}]"
            el = "QuadroEA/Modulo/Soggetto"
            cfv = self.val("persone", p, "codice_fiscale", cf_persona, elemento=el + "/CodiceFiscale")
            if cfv:
                cf_visti.setdefault(cfv, []).append(p["id"])
            ruolo = p.get("ruolo")
            tipo = SUP.attr(self.d, "persone", p, "tipo_soggetto")
            self.usa(p, "tipo_soggetto")
            if ruolo == "legatario":
                if SUP.dich(self.d, "devoluzione_per_testamento") is not True:
                    self.err("DATI_INCOERENTI", f"persone[{p['id']}].ruolo", "legatario (tipo soggetto 2) ammesso solo con "
                             "devoluzione per testamento (o legge estera, non ancora mappata)",
                             FO.fonte_annotazione(el + "/TipoSoggetto"))
                tipo = "2"
            elif tipo is None:
                tipo = "1"
            else:
                try:
                    tipo = codice_enum(tipo, "TipoSoggetto_Type")
                except F.ValoreXml as e:
                    self.err("VALORE_NON_VALIDO", base + ".tipo_soggetto", str(e), FO.fonte_xsd(el + "/TipoSoggetto"))
                    tipo = None
                if tipo == "5":
                    self.ns.append(f"{base}: tipo soggetto 5 (trust) non supportato: servono le sezioni Trust del quadro EA, TrustDisab ed "
                                   "EF3bis, il dichiarante con codice carica 9, l'atto istitutivo in EG e la verifica del perimetro "
                                   "del modello telematico (Fascicolo I p. PDF 17), non ancora provate col controllo ufficiale")
                elif tipo == "6":
                    self.ns.append(f"{base}: tipo soggetto 6 (altro) non supportato: con questo tipo non possono esserci altri soggetti nel "
                                   "quadro EA (annotazione XSD di TipoSoggetto), caso non provato col controllo ufficiale")
            grado = SUP.attr(self.d, "persone", p, "grado_parentela")
            self.usa(p, "grado_parentela", "relazione_con_defunto")
            rel = p.get("relazione_con_defunto")
            rel_codice = isinstance(rel, str) and rel.strip() in X.enumerazioni("GradoParentela_Type")
            if grado is None and rel_codice:
                grado = rel.strip()
            elif rel_codice and str(grado).strip() != rel.strip():
                self.err("DATI_INCOERENTI", base + ".relazione_con_defunto", f"il codice {rel.strip()!r} e' diverso dal "
                         f"grado di parentela indicato {grado!r}", FO.fonte_xsd(el + "/GradoParentela"))
            elif rel not in (None, "") and not rel_codice:
                self.interno(p, "relazione_con_defunto")
            if grado is None:
                self.err("DATO_MANCANTE", base + ".grado_parentela", "grado di parentela (codice dell'allegato 1, es. "
                         "'02' figlio) obbligatorio", FO.fonte_xsd(el + "/GradoParentela"))
            else:
                try:
                    grado = codice_enum(grado, "GradoParentela_Type")
                except F.ValoreXml as e:
                    self.err("VALORE_NON_VALIDO", base + ".grado_parentela", str(e), FO.fonte_xsd(el + "/GradoParentela"))
                    grado = None
            if grado == "01":
                coniugi += 1
                if stato_civile not in ("2", "3", "5", "7"):
                    self.err("REGOLA_GRADO_CONIUGE", base + ".grado_parentela", "grado '01' ammesso solo con stato civile "
                             "del defunto 2, 3, 5 o 7", FO.fonte_annotazione("QuadroEA/Modulo/Soggetto/GradoParentela"))
            if legge and grado in ("12", "13", "14", "17", "18", "19", "23", "24", "25", "26", "35", "37", "38", "39"):
                self.err("REGOLA_GRADO_LEGGE", base + ".grado_parentela", f"con devoluzione per legge il grado {grado} "
                         "non e' ammesso (affini, estranei, enti)", FO.fonte_annotazione(el + "/GradoParentela"))
            rapp = self.rappresentazione(p, base, grado, legge, el, cfv)
            if legge and grado == "36" and len(self.ea) > 1:
                self.err("REGOLA_GRADO_LEGGE", base + ".grado_parentela", "grado 36 (Stato) ammesso solo se unico "
                         "soggetto del quadro", FO.fonte_annotazione(el + "/GradoParentela"))
            if grado == "36":
                self.ns.append(f"{base}: grado 36 (Stato) non supportato: l'annotazione XSD vieta di indicare il soggetto nelle "
                               "devoluzioni, e senza devoluzioni il quadro dei beni non e' compilabile (caso non provato col controllo)")
            ph = SUP.attr(self.d, "persone", p, "portatore_handicap")
            self.usa(p, "portatore_handicap")
            if ph not in (None, False, True):
                self.err("VALORE_NON_VALIDO", base + ".portatore_handicap", "atteso true/false",
                         FO.fonte_xsd(el + "/PortatoreHandicap"))
            if p.get("data_decesso") not in (None, ""):
                self.ns.append(f"{base}.data_decesso: soggetto EA deceduto (rappresentazione/trasmissione) non supportato")
                self.usa(p, "data_decesso")
            den = self.denominazione(p, base, grado, el)
            ana = den if den else self.anagrafica(p, el + "/DatiAnagrafici")
            rinunciatario = self.rinuncia(p, base, tipo, grado, el)
            s = {"CodiceFiscale": cfv, "TipoSoggetto": tipo}
            if rinunciatario:
                s["Rinuncia"] = "1"
            s["GradoParentela"] = grado
            if ph is True:
                s["PortatoreHandicap"] = "1"
            if den:
                s["Denominazione"] = den
            else:
                s["DatiAnagrafici"] = ana
            res_estera = self.residenza_estera(p, base, el)
            if res_estera:
                s["ResidenzaEstera"] = res_estera
            if rapp:
                s["SuccessionePerRappresentazione"] = {"CodiceFiscaleSoggettoRappresentato": rapp[0], "GradoParentela": rapp[1]}
                self.rapp_ea[p["id"]] = rapp
            self.tipo_ea[p["id"]] = tipo
            self.soggetti_ea[p["id"]] = s
            self.grado_ea[p["id"]] = grado
            self.handicap_ea[p["id"]] = ph is True
            soggetti.append(s)
            m, r = self.pos_ea[p["id"]]
            self.mappa[p["id"]] = {"coll": "persone", "quadro": "EA", "modulo": m, "rigo": r,
                                   "xpath": f"{_XP_DICH}/suc:QuadroEA/suc:Modulo[{m}]/suc:Soggetto[{r}]"}
        if coniugi > 1:
            self.err("REGOLA_GRADO_CONIUGE", "persone", "ammesso un solo rigo con grado di parentela '01'",
                     FO.fonte_annotazione("QuadroEA/Modulo/Soggetto/GradoParentela"))
        self.controlla_soggetti_multi_riga(cf_visti)
        tipi4 = [i for i, t in self.tipo_ea.items() if t == "4"]
        if len(tipi4) > 1:
            self.err("REGOLA_TIPO_SOGGETTO", "persone", "ammesso un solo rigo con tipo soggetto 4 (coniuge superstite "
                     "rinunciatario)", FO.fonte_annotazione("QuadroEA/Modulo/Soggetto/TipoSoggetto"))
        return {"Modulo": [{"Soggetto": soggetti[i:i + 3]} for i in range(0, len(soggetti), 3)]}

    # ---------------------------------------------------------------- beni
    def quota_possesso(self, b: dict, elemento: str):
        self.usa(b, "quota_defunto")
        q = b.get("quota_defunto")
        perc = f"beni[{b['id']}].quota_defunto"
        if q is None or V.e_stato(q):
            self.err("DATO_MANCANTE", perc, "quota di possesso del defunto obbligatoria", FO.fonte_xsd(elemento))
            return None, None
        try:
            n, d = F.quota_grezza(q)
            if len(str(d)) > 6:
                raise F.ValoreXml(f"denominatore {d}: massimo 6 cifre (PossessoDenominatore)")
            return {"PossessoNumeratore": F.numeratore_possesso(n), "PossessoDenominatore": str(d)}, Fraction(n, d)
        except (F.ValoreXml, V.ValoreNonValido) as e:
            self.err("VALORE_NON_VALIDO", perc, str(e), FO.fonte_xsd(elemento))
            return None, None

    # ---------------------------------------------------------------- beni esteri
    def imposta_estera_bene(self, b: dict, elemento: str) -> str | None:
        """ImpostaVersataEstero del bene (euro interi, DatoNP_Type) oppure ``None``. L'importo e' quello dell'INTERO cespite: la
        quota del beneficiario si ricava con la quota di devoluzione (guida al calcolo p. 8: IE = imposta x quota)."""
        v = SUP.attr(self.d, "beni", b, "imposta_estera")
        self.usa(b, "imposta_estera")
        if v in (None, ""):
            return None
        try:
            s = F.euro_intero(v)
        except (F.ValoreXml, V.ValoreNonValido) as e:
            self.err("VALORE_NON_VALIDO", f"beni[{b['id']}].imposta_estera", str(e), FO.fonte_xsd(elemento))
            return None
        self.imposta_estera[b["id"]] = int(s)
        return s

    def beni_esteri(self, b: dict, quadro: str) -> dict | None:
        """``BeniEsteri`` dei quadri EN, EO, EP, EQ, ER (BeneSitoEstero + ImpostaVersataEstero), ``None`` per un bene italiano."""
        from .quadri_efgh import _flag
        el = f"Quadro{quadro}/Modulo/{_RIGA[quadro]}/BeniEsteri"
        self.usa(b, "bene_estero")
        estero = _flag(SUP.attr(self.d, "beni", b, "bene_estero"))
        imposta = self.imposta_estera_bene(b, el + "/ImpostaVersataEstero")
        if not estero:
            if imposta is not None:
                self.err("DATI_INCOERENTI", f"beni[{b['id']}].imposta_estera", "imposta versata all'estero indicata per un bene "
                         "non sito all'estero (casella «bene estero»)", FO.fonte_xsd(el))
            return None
        self.estero_bene[b["id"]] = True
        out = {"BeneSitoEstero": "1"}
        if imposta is not None:
            out["ImpostaVersataEstero"] = imposta
        return out

    def _provincia_ee(self, b: dict) -> bool:
        v = SUP.attr(self.d, "beni", b, "provincia")
        return isinstance(v, str) and v.strip().upper() == "EE"

    def luogo_estero(self, b: dict, quadro: str) -> dict | None:
        """Luogo di un immobile estero (provincia EE): sezione ``Estero`` (reg:Luogo_Type, Residenza_Estera_Type + StatoEstero).
        Fonti: typesReg_v2.xsd Luogo_Type; datiFiscali_v4.xsd Residenza_Estera_Type; Fascicolo I pp. PDF 22 e 29."""
        c = "beni"
        el = f"Quadro{quadro}/Modulo/{'Terreni' if quadro == 'EB' else 'Fabbricati'}/Luogo/Estero"
        fonte = FO.fonte_xsd(el) + "; " + FO.fonte_fasc1(22 if quadro == "EB" else 29, "Codice dello Stato estero/Stato estero/...")

        def codice(v):
            s = str(v).strip().upper()
            if not re.fullmatch(r"[0-9A-Z]{3}", s):
                raise F.ValoreXml(f"{v!r}: codice dello Stato estero di 3 caratteri (Appendice del Modello Unico, es. 029)")
            return s
        out = {
            "CodiceStatoEstero": self.val(c, b, "codice_stato_estero", codice, elemento=el + "/CodiceStatoEstero", fonte=fonte),
            "StatoFederato": self.val(c, b, "stato_federato", lambda v: F.an(v, 24), elemento=el + "/StatoFederato", obbl=False),
            "LocalitaEstero": self.val(c, b, "localita_estero", lambda v: F.an(v, 50), elemento=el + "/LocalitaEstero",
                                       obbl=False),
            "IndirizzoEstero": self.val(c, b, "indirizzo", lambda v: F.an(v, 80), elemento=el + "/IndirizzoEstero", fonte=fonte),
            "StatoEstero": self.val(c, b, "stato_estero", lambda v: F.an(v, 34), elemento=el + "/StatoEstero", fonte=fonte),
        }
        if any(out[k] is None for k in ("CodiceStatoEstero", "IndirizzoEstero", "StatoEstero")):
            return None
        for facoltativo in ("StatoFederato", "LocalitaEstero"):
            if out[facoltativo] is None:
                del out[facoltativo]
        self.usa(b, "provincia")
        if b.get("comune") not in (None, ""):      # nome del comune: non previsto per gli immobili esteri
            self.usa(b, "comune")
            self.interno(b, "comune")
        return {"Provincia": "EE", "Estero": out}

    def _niente_estero_in_italia(self, b: dict) -> None:
        """Gli immobili italiani non hanno dati dello Stato estero ne' imposta estera (si usa la provincia EE)."""
        for campo in ("imposta_estera", "codice_stato_estero", "stato_estero", "stato_federato", "localita_estero", "bene_estero"):
            self.usa(b, campo)
            if SUP.attr(self.d, "beni", b, campo) not in (None, "", False):
                self.err("DATI_INCOERENTI", f"beni[{b['id']}].{campo}", "dato estero su un immobile con provincia italiana: "
                         "per un immobile estero indicare la provincia EE", FO.fonte_fasc1(22, "provincia EE"))

    def _riga_immobile_estero(self, b: dict, quadro: str, luogo: dict) -> dict | None:
        """Rigo EB/EC di un immobile estero: niente dati catastali (DatiTerreni/DatiFabbricati «non valorizzare» se EE),
        ma possesso, diritto, valore e imposta versata all'estero (Fascicolo I pp. PDF 22 e 29)."""
        c = "beni"
        el = f"Quadro{quadro}/Modulo/{'Terreni' if quadro == 'EB' else 'Fabbricati'}"
        # Il controllo ufficiale SUC13 2.3.1 (diagnostico 3072, prova locale 2026-11-05) respinge anche la tipologia del terreno su un
        # immobile estero («non devono essere inseriti i dati identificativi italiani»), che l'XSD lascerebbe facoltativa.
        for campo in ("sezione", "foglio", "particella", "subalterno", "natura", "categoria", "classe", "zona_censuaria",
                      "consistenza", "rendita", "reddito_dominicale", "superficie", "tipologia_terreno",
                      "discordanza_intestatario", "passaggi_senza_atti_legali"):
            v = SUP.attr(self.d, c, b, campo)
            if v not in (None, "", False):
                self.usa(b, campo)
                self.ns.append(f"beni[{b['id']}].{campo}: campo non previsto per un immobile estero (provincia EE): "
                               "i dati catastali non vanno valorizzati")
        poss, _ = self.quota_possesso(b, el + "/Possesso")
        dir_p = self.diritto_defunto(b, "CodiciDirittoImmobili_Type", el + "/CodiceDiritto_P")
        valore = self.valore_bene(b, el + "/Valore")
        imposta = self.imposta_estera_bene(b, el + "/ImpostaVersataEstero")
        if None in (luogo, poss, dir_p, valore):
            return None
        self.estero_bene[b["id"]] = True
        self.diritto_bene[b["id"]] = dir_p
        self.valore_beni[b["id"]] = int(valore)
        riga = {"Luogo": luogo, "Possesso": poss, "CodiceDiritto_P": dir_p}
        if imposta is not None:
            riga["ImpostaVersataEstero"] = imposta
        riga["Valore"] = valore
        return riga

    def luogo(self, b: dict, quadro: str, *, indirizzo_obbl: bool, tavolare: bool = False) -> dict | None:
        c, el = "beni", f"Quadro{quadro}/Modulo/{'Terreni' if quadro == 'EB' else 'Fabbricati'}/Luogo"
        if tavolare:
            return self.luogo_tavolare(b, quadro, indirizzo_obbl)
        prov = self.val(c, b, "provincia", lambda v: str(v).strip().upper(), elemento=el + "/Provincia")
        if prov is None:
            return None
        if prov == "EE":
            return self.luogo_estero(b, quadro)
        if prov not in X.enumerazioni("PENonTavolare_Type"):
            if prov in X.enumerazioni("PN_Type"):
                self.ns.append(f"beni[{b['id']}]: provincia {prov} del sistema tavolare (quadri EL/EM) non supportata")
            else:
                self.err("VALORE_NON_VALIDO", f"beni[{b['id']}].provincia", f"sigla provincia {prov!r} non ammessa",
                         FO.fonte_xsd(el + "/Provincia (reg:PENonTavolare_Type)"))
            return None
        it = {
            "ComuneAmministrativo": self.val(c, b, "comune_amministrativo", lambda v: F.an(v, 50),
                                             elemento=el + "/Italia/ComuneAmministrativo", obbl=False)
            or self.val(c, b, "comune", lambda v: F.an(v, 50), elemento=el + "/Italia/ComuneAmministrativo"),
            "CodiceComune": self.val(c, b, "codice_comune", lambda v: F.an(v, 4 if quadro == "EB" else 5),
                                     elemento=el + "/Italia/CodiceComune",
                                     fonte=FO.fonte_xsd(el + "/Italia/CodiceComune") + "; " +
                                     FO.fonte_fasc1(28, "Codice Comune: codice catastale")),
        }
        ind = self.val(c, b, "indirizzo", lambda v: F.an(v, 80), elemento=el + "/Italia/Indirizzo", obbl=indirizzo_obbl,
                       fonte=FO.fonte_annotazione(f"Quadro{quadro}/Modulo/Fabbricati/Luogo") if indirizzo_obbl else None)
        if ind:
            it["Indirizzo"] = ind
        it["CodiceComuneAmministrativo"] = self.val(c, b, "codice_comune_amministrativo", lambda v: F.an(v, 5),
                                                    elemento=el + "/Italia/CodiceComuneAmministrativo")
        self.usa(b, "comune")  # letto come ComuneAmministrativo se comune_amministrativo manca
        if any(v is None for v in it.values()):
            return None
        return {"Provincia": prov, "Italia": it}

    def luogo_tavolare(self, b: dict, quadro: str, indirizzo_obbl: bool) -> dict | None:
        """LuogoTavolareType (quadri EL/EM): luogo piatto con provincia tavolare e, per TN e BZ, comune catastale."""
        c = "beni"
        el = f"Quadro{quadro}/Modulo/{'TerreniTavolare' if quadro == 'EL' else 'FabbricatiTavolare'}/LuogoTavolare"
        prov = self.val(c, b, "provincia", lambda v: str(v).strip().upper(), elemento=el + "/Provincia")
        if prov is None:
            return None
        if prov not in X.enumerazioni("PRTavolare_Type"):
            self.err("VALORE_NON_VALIDO", f"beni[{b['id']}].provincia", f"{prov!r}: provincia non del catasto tavolare "
                     "(ammesse BZ, TN, BL, GO, UD, TS, BS, VI)", FO.fonte_xsd(el + "/Provincia (reg:PRTavolare_Type)"))
            return None
        out = {
            "ComuneAmministrativo": self.val(c, b, "comune_amministrativo", lambda v: F.an(v, 50),
                                             elemento=el + "/ComuneAmministrativo", obbl=False)
            or self.val(c, b, "comune", lambda v: F.an(v, 50), elemento=el + "/ComuneAmministrativo"),
            "CodiceComune": self.val(c, b, "codice_comune", lambda v: F.an(v, 5), elemento=el + "/CodiceComune",
                                     fonte=FO.fonte_xsd(el + "/CodiceComune")),
        }
        ind = self.val(c, b, "indirizzo", lambda v: F.an(v, 80), elemento=el + "/Indirizzo", obbl=indirizzo_obbl,
                       fonte=FO.fonte_annotazione(el) if indirizzo_obbl else None)
        if ind:
            out["Indirizzo"] = ind
        out["CodiceComuneAmministrativo"] = self.val(c, b, "codice_comune_amministrativo", lambda v: F.an(v, 5),
                                                     elemento=el + "/CodiceComuneAmministrativo")
        out["Provincia"] = prov
        self.usa(b, "comune")
        cc = self.val(c, b, "comune_catastale", lambda v: F.an(v, 50), elemento=el + "/ComuneCatastale", obbl=False)
        ccc = self.val(c, b, "codice_comune_catastale", lambda v: codice_enum(str(v), "ComuniCatastaliTNBZ_Type"),
                       elemento=el + "/CodiceComuneCatastale", obbl=False)
        if prov in ("TN", "BZ"):
            if cc:
                out["ComuneCatastale"] = cc
            if ccc:
                out["CodiceComuneCatastale"] = ccc
        elif cc or ccc:
            self.err("DATI_INCOERENTI", f"beni[{b['id']}].comune_catastale", "comune catastale e codice solo per le "
                     "province TN e BZ", FO.fonte_annotazione(el + "/ComuneCatastale"))
        if any(v is None for v in out.values()):
            return None
        return out

    def catastali(self, b: dict, quadro: str) -> dict | None:
        c = "beni"
        el = f"Quadro{quadro}/Modulo/{'Terreni/DatiTerreni' if quadro == 'EB' else 'Fabbricati/DatiFabbricati'}/DatiCatastali"
        r = {"Foglio": self.val(c, b, "foglio", lambda v: F.an(str(v), 4), elemento=el + "/Foglio"),
             "Particella": self.val(c, b, "particella", lambda v: F.an(str(v), 5, tipo="PART"), elemento=el + "/Particella")}
        sub = self.val(c, b, "subalterno", lambda v: F.an(str(v), 4), elemento=el + "/Subalterno", obbl=False)
        if sub:
            r["Subalterno"] = sub
        return r if all(v is not None for v in r.values()) else None

    def diritto_defunto(self, b: dict, tipo: str, elemento: str):
        return self.val("beni", b, "diritto", lambda v: codice_enum(v, tipo, alias_descrizione=True), elemento=elemento,
                        fonte=FO.fonte_xsd(elemento + f" ({tipo})"))

    def valore_bene(self, b: dict, elemento: str):
        def conv(v):
            s = F.euro_intero(v)
            if len(s) > 13:
                raise F.ValoreXml(f"{s}: massimo 13 cifre (Valore)")
            return s
        return self.val("beni", b, "valore", conv, elemento=elemento,
                        fonte=FO.fonte_xsd(elemento) + "; " + FO.fonte_fasc1(22, "Valore: base imponibile della quota del "
                                                                              "defunto, arrotondata all'unita' di euro"))

    def _flag_ei(self, b: dict, quadro: str, luogo: dict, cat: dict, sezione, tavolare: bool) -> dict:
        """Caselle «Discordanza dati intestatario» e «Passaggi senza atti legali» di EB/EC e registrazione per il quadro EI."""
        self.usa(b, "discordanza_intestatario")
        self.usa(b, "passaggi_senza_atti_legali")
        disc = SUP.attr(self.d, "beni", b, "discordanza_intestatario")
        pas = SUP.attr(self.d, "beni", b, "passaggi_senza_atti_legali")
        from .quadri_efgh import _flag
        disc, pas = _flag(disc), _flag(pas)
        if not (disc or pas):
            return {}
        if tavolare:
            self.ns.append(f"beni[{b['id']}]: discordanza e passaggi senza atti legali non sono previsti dai quadri EL/EM")
            return {}
        self.ei_beni.append({"id": b["id"], "bene": b, "quadro": quadro, "luogo": luogo, "cat": cat, "sezione": sezione,
                             "discordanza": disc, "passaggi": pas})
        out = {}
        if disc:
            out["DiscordanzaDatiIntestatario"] = "1"
        if pas:
            out["PassaggiSenzaAttiLegali"] = "1"
        return out

    def riga_eb(self, b: dict, tavolare: bool = False) -> dict | None:
        c, el = "beni", "QuadroEB/Modulo/Terreni"
        for campo in ("sezione", "categoria"):
            if b.get(campo) not in (None, ""):
                self.usa(b, campo)
                self.ns.append(f"beni[{b['id']}].{campo}: campo non previsto dal tracciato dei terreni "
                               "(reg:DatiCatastali_Type / reg:DatiCatastaliTerreni_Type)")
        luogo = self.luogo(b, "EB", indirizzo_obbl=False, tavolare=tavolare)
        if not tavolare and self._provincia_ee(b):
            return self._riga_immobile_estero(b, "EB", luogo)
        cat = self.catastali(b, "EB")
        natura = self.val(c, b, "natura", lambda v: codice_enum(str(v).upper(), "CodiciNatura_Type"),
                          elemento=el + "/DatiTerreni/DatiTerreni/Natura")
        if natura and natura != "T":
            self.ns.append(f"beni[{b['id']}].natura={natura}: solo natura 'T' supportata in questa versione")
        dt: dict = {}
        sup = SUP.attr(self.d, c, b, "superficie")
        self.usa(b, "superficie")
        if sup:
            try:
                if not isinstance(sup, dict) or set(sup) - SUP.CHIAVI_SUPERFICIE:
                    raise F.ValoreXml("attesa {'ettari','are','centiare'}")
                s = {k2: F.euro_intero(str(sup[k1])) for k1, k2 in (("ettari", "SuperficieEttari"), ("are", "SuperficieAre"),
                                                                    ("centiare", "SuperficieCentiare"))
                     if sup.get(k1) not in (None, 0, "0")}
                if s:
                    dt["Superficie"] = s
            except (F.ValoreXml, V.ValoreNonValido) as e:
                self.err("VALORE_NON_VALIDO", f"beni[{b['id']}].superficie", str(e),
                         FO.fonte_xsd(el + "/DatiTerreni/DatiTerreni/Superficie"))
        dt["Natura"] = natura
        rd = self.val(c, b, "reddito_dominicale", F.euro_centesimi, elemento=el + "/DatiTerreni/DatiTerreni/RedditoDominicale",
                      obbl=False)
        if rd is None and b.get("rendita") not in (None, ""):
            rd = self.val(c, b, "rendita", F.euro_centesimi, elemento=el + "/DatiTerreni/DatiTerreni/RedditoDominicale")
            if rd:
                self.avv("INTERPRETAZIONE_RENDITA_TERRENO", f"beni[{b['id']}].rendita",
                         "per un terreno il campo 'rendita' e' esportato come Reddito dominicale (unico reddito previsto "
                         "dal tracciato EB)", FO.fonte_xsd(el + "/DatiTerreni/DatiTerreni/RedditoDominicale"))
        else:
            self.usa(b, "rendita")
        if rd:
            dt["RedditoDominicale"] = rd
        poss, fposs = self.quota_possesso(b, el + "/Possesso")
        dir_p = self.diritto_defunto(b, "CodiciDirittoImmobili_Type", el + "/CodiceDiritto_P")
        tip = self.val(c, b, "tipologia_terreno", lambda v: codice_enum(v, "TerrenoEdificabile_Type"),
                       elemento=el + "/TipologiaTerreno", fonte=FO.fonte_annotazione(el + "/TipologiaTerreno"))
        valore = self.valore_bene(b, el + "/Valore")
        if None in (luogo, cat, natura, poss, dir_p, tip, valore):
            return None
        self.comune_bene[b["id"]] = luogo.get("Italia", luogo)["CodiceComune"]
        self.diritto_bene[b["id"]] = dir_p
        self.valore_beni[b["id"]] = int(valore)
        self.terreni_vf[b["id"]] = {"rd": Decimal(rd.replace(",", ".")) if rd else None, "quota": fposs, "tip": tip}
        riga = {"Luogo": luogo, "DatiTerreni": {"DatiCatastali": cat, "DatiTerreni": dt}, "Possesso": poss,
                "CodiceDiritto_P": dir_p, "TipologiaTerreno": tip, "Valore": valore}
        self._niente_estero_in_italia(b)
        riga.update(self._flag_ei(b, "EB", luogo, cat, None, tavolare))
        return riga

    def riga_ec(self, b: dict, tavolare: bool = False) -> dict | None:
        c, el = "beni", "QuadroEC/Modulo/Fabbricati"
        eld = el + "/DatiFabbricati/DatiFabbricati"
        luogo = self.luogo(b, "EC", indirizzo_obbl=True, tavolare=tavolare)
        if not tavolare and self._provincia_ee(b):
            return self._riga_immobile_estero(b, "EC", luogo)
        cat = self.catastali(b, "EC")
        df: dict = {}
        sez = self.val(c, b, "sezione", lambda v: F.an(str(v), 3), elemento=eld + "/SezioneUrbana", obbl=False)
        if sez:
            df["SezioneUrbana"] = sez
        zona = self.val(c, b, "zona_censuaria", lambda v: F.an(str(v), 3), elemento=eld + "/ZonaCensuaria", obbl=False)
        if zona:
            df["ZonaCensuaria"] = zona
        categ = self.val(c, b, "categoria", lambda v: codice_enum(str(v).upper().replace("/", ""),
                                                                  "CodiciCategoriaCatastale_Type"),
                         elemento=eld + "/CategoriaCatastale", fonte=FO.fonte_annotazione(eld + "/CategoriaCatastale"))
        df["CategoriaCatastale"] = categ
        classe = self.val(c, b, "classe", lambda v: F.an(str(v), 2), elemento=eld + "/Classe", obbl=False)
        if classe:
            df["Classe"] = classe
        richiede_consistenza = bool(categ) and categ[0] in "ABC"
        cons = self.val(c, b, "consistenza", F.euro_centesimi, elemento=eld + "/Consistenza", obbl=richiede_consistenza,
                        fonte=FO.fonte_annotazione(eld + "/Consistenza"))
        if cons and not richiede_consistenza and categ:
            self.err("REGOLA_CONSISTENZA", f"beni[{b['id']}].consistenza", f"la consistenza non va indicata per la "
                     f"categoria {categ}", FO.fonte_annotazione(eld + "/Consistenza"))
        elif cons:
            df["Consistenza"] = cons
        categoria_f = bool(categ) and categ.startswith("F")
        rend = self.val(c, b, "rendita", F.euro_centesimi, elemento=eld + "/RenditaCatastale", obbl=not categoria_f,
                        fonte=FO.fonte_annotazione(eld + "/RenditaCatastale") + " (rendita proposta/DeterminazioneRendita "
                        "non supportata)")
        if rend and categoria_f:
            self.err("REGOLA_RENDITA", f"beni[{b['id']}].rendita", f"la rendita non va indicata per la categoria {categ}",
                     FO.fonte_annotazione(eld + "/RenditaCatastale"))
        elif rend:
            df["RenditaCatastale"] = rend
        poss, fposs = self.quota_possesso(b, el + "/Possesso")
        dir_p = self.diritto_defunto(b, "CodiciDirittoImmobili_Type", el + "/CodiceDiritto_P")
        valore = self.valore_bene(b, el + "/Valore")
        if None in (luogo, cat, categ, poss, dir_p, valore):
            return None
        self.comune_bene[b["id"]] = luogo.get("Italia", luogo)["CodiceComune"]
        self.diritto_bene[b["id"]] = dir_p
        self.valore_beni[b["id"]] = int(valore)
        if not tavolare:
            self.info_ec[b["id"]] = {"luogo": luogo, "cat": cat, "sezione": df.get("SezioneUrbana"), "categoria": categ}
        riga = {"Luogo": luogo, "DatiFabbricati": {"DatiCatastali": cat, "DatiFabbricati": df}, "Possesso": poss,
                "CodiceDiritto_P": dir_p, "Valore": valore}
        self._niente_estero_in_italia(b)
        riga.update(self._flag_ei(b, "EC", luogo, cat, df.get("SezioneUrbana"), tavolare))
        return riga

    def riga_er(self, b: dict) -> dict | None:
        c, el = "beni", "QuadroER/Modulo/Rendite"
        for campo in ("comune", "sezione", "foglio", "particella", "subalterno", "categoria", "rendita"):
            if b.get(campo) not in (None, ""):
                self.usa(b, campo)
                self.ns.append(f"beni[{b['id']}].{campo}: campo catastale non previsto per i beni del quadro ER")
        tc = self.val(c, b, "tipo_cespite", lambda v: codice_enum(str(v).upper(), "TipoCespite_Type"),
                      elemento=el + "/TipoCespite", fonte=FO.fonte_xsd(el + "/TipoCespite") + "; " +
                      FO.fonte_fasc1(33, "Tipo cespite; CR comprende le somme depositate in conto corrente"))
        if tc == "GD":
            self.ns.append(f"beni[{b['id']}].tipo_cespite=GD: legato di cosa genericamente determinata non supportato")
        descr = self.val(c, b, "descrizione", lambda v: F.an(v, 250), elemento=el + "/Descrizione")
        poss, fposs = self.quota_possesso(b, el + "/Possesso")
        dir_p = self.diritto_defunto(b, "CodiciDirittoNonImmobili", el + "/CodiceDiritto_P")
        valore = self.valore_bene(b, el + "/Valore")
        if None in (tc, descr, poss, dir_p, valore):
            return None
        self.diritto_bene[b["id"]] = dir_p
        self.valore_beni[b["id"]] = int(valore)
        self.tipo_cespite[b["id"]] = tc
        riga = {"TipoCespite": tc, "Descrizione": descr, "Possesso": poss, "CodiceDiritto_P": dir_p, "Valore": valore}
        be = self.beni_esteri(b, "ER")
        if be:
            riga["BeniEsteri"] = be
        return riga

    def _anno_xml(self, b: dict, campo: str, elemento: str):
        """DatoDA_Type: anno aaaa tra 1800 e 2099, non futuro."""
        v = SUP.attr(self.d, "beni", b, campo)
        self.usa(b, campo)
        fonte = FO.fonte_xsd(elemento)
        if v in (None, "") or V.e_stato(v):
            self.err("DATO_MANCANTE", f"beni[{b['id']}].{campo}", "anno obbligatorio (aaaa)", fonte)
            return None
        if not re.fullmatch(r"(18|19|20)[0-9]{2}", str(v)) or int(v) > self.oggi.year:
            self.err("VALORE_NON_VALIDO", f"beni[{b['id']}].{campo}", f"{v!r}: anno aaaa tra 1800 e l'anno corrente (DatoDA_Type)", fonte)
            return None
        return str(v)

    def _testo_xml(self, b: dict, campo: str, elemento: str, massimo: int, *, numerico: bool = False):
        v = SUP.attr(self.d, "beni", b, campo)
        self.usa(b, campo)
        fonte = FO.fonte_xsd(elemento)
        if v in (None, "") or V.e_stato(v):
            self.err("DATO_MANCANTE", f"beni[{b['id']}].{campo}", "dato obbligatorio", fonte)
            return None
        try:
            if numerico:
                if not str(v).isdigit() or len(str(v)) > massimo:
                    raise F.ValoreXml(f"{v!r}: solo cifre, massimo {massimo}")
                return str(v)
            return F.an(str(v), massimo)
        except F.ValoreXml as e:
            self.err("VALORE_NON_VALIDO", f"beni[{b['id']}].{campo}", str(e), fonte)
            return None

    def _rigo_mezzo(self, b: dict, quadro: str, tipo_xml: dict | None) -> dict | None:
        el = f"Quadro{quadro}/Modulo/{_RIGA[quadro]}"
        for campo in ("comune", "sezione", "foglio", "particella", "subalterno", "categoria", "rendita"):
            if b.get(campo) not in (None, ""):
                self.usa(b, campo)
                self.ns.append(f"beni[{b['id']}].{campo}: campo catastale non previsto per il quadro {quadro}")
        poss, _ = self.quota_possesso(b, el + "/Possesso")
        dir_p = self.diritto_defunto(b, "CodiciDirittoNonImmobili", el + "/CodiceDiritto_P")
        valore = self.valore_bene(b, el + "/Valore")
        be = self.beni_esteri(b, quadro)
        if tipo_xml is None or None in (poss, dir_p, valore):
            return None
        self.diritto_bene[b["id"]] = dir_p
        self.valore_beni[b["id"]] = int(valore)
        riga = {"Tipo": tipo_xml, "Possesso": poss, "CodiceDiritto_P": dir_p, "Valore": valore}
        if be:
            riga["BeniEsteri"] = be
        return riga

    def riga_ep(self, b: dict) -> dict | None:
        """Quadro EP, rigo Aeromobili (Tipo: marca/modello, anno costruzione, nazionalita', anno e numero di immatricolazione)."""
        el = "QuadroEP/Modulo/Aeromobili/Tipo"
        t = {"MarcaModello": self._testo_xml(b, "marca_modello", el + "/MarcaModello", 45),
             "AnnoCostruzione": self._anno_xml(b, "anno_costruzione", el + "/AnnoCostruzione"),
             "Nazionalita": self._testo_xml(b, "nazionalita", el + "/Nazionalita", 20),
             "AnnoImmatricolazione": self._anno_xml(b, "anno_immatricolazione", el + "/AnnoImmatricolazione"),
             "NumeroImmatricolazione": self._testo_xml(b, "numero_immatricolazione", el + "/NumeroImmatricolazione", 10,
                                                       numerico=True)}
        r = self._rigo_mezzo(b, "EP", None if None in t.values() else t)
        if r is not None:   # EH rigo EH12: gli stessi dati dell'aeromobile
            self.eh_aeromobili.append({k: t[k] for k in ("Nazionalita", "AnnoImmatricolazione", "NumeroImmatricolazione")})
        return r

    def riga_eq(self, b: dict) -> dict | None:
        """Quadro EQ, rigo Navi (Tipo: vela/motore, nazionalita', ufficio e numero di iscrizione, dimensione lunghezza o stazza)."""
        el = "QuadroEQ/Modulo/Navi/Tipo"
        tu = self.val("beni", b, "tipo_unita", lambda v: codice_enum(str(v), "TipoUnita_Type"), elemento=el + "/TipoUnita")
        lun, staz = SUP.attr(self.d, "beni", b, "lunghezza"), SUP.attr(self.d, "beni", b, "stazza")
        self.usa(b, "lunghezza")
        self.usa(b, "stazza")
        dim = None
        if (lun in (None, "")) == (staz in (None, "")):
            self.err("DATI_INCOERENTI", f"beni[{b['id']}].lunghezza", "indicare la lunghezza oppure la stazza (scelta esclusiva)",
                     FO.fonte_xsd(el + "/Dimensione"))
        else:
            campo, nome = ("lunghezza", "Lunghezza") if lun not in (None, "") else ("stazza", "Stazza")
            v = self._testo_xml(b, campo, el + "/Dimensione/" + nome, 6, numerico=True)
            dim = {nome: v} if v is not None else None
        t = {"TipoUnita": tu,
             "Nazionalita": self._testo_xml(b, "nazionalita", el + "/Nazionalita", 20),
             "SiglaUfficioIscrizione": self._testo_xml(b, "sigla_ufficio_iscrizione", el + "/SiglaUfficioIscrizione", 6),
             "AnnoIscrizione": self._anno_xml(b, "anno_iscrizione", el + "/AnnoIscrizione"),
             "NumeroIscrizione": self._testo_xml(b, "numero_iscrizione", el + "/NumeroIscrizione", 10, numerico=True),
             "AnnoCostruzione": self._anno_xml(b, "anno_costruzione", el + "/AnnoCostruzione"),
             "Dimensione": dim}
        r = self._rigo_mezzo(b, "EQ", None if None in t.values() else t)
        if r is not None:   # EH rigo EH11: gli stessi dati della nave
            self.eh_navi.append({k: t[k] for k in ("SiglaUfficioIscrizione", "AnnoIscrizione", "NumeroIscrizione")})
        return r

    def riga_el(self, b: dict) -> dict | None:
        """Quadro EL, rigo TerreniTavolare: come EB con luogo tavolare e dati tavolari (partita tavolare obbligatoria)."""
        r = self.riga_eb(b, tavolare=True)
        pt = self.val("beni", b, "partita_tavolare", lambda v: F.an(str(v), 7),
                      elemento="QuadroEL/Modulo/TerreniTavolare/DatiTerreniTavolare/DatiTerreni/PartitaTavolare")
        ct = self.val("beni", b, "corpo_tavolare", lambda v: F.an(str(v), 3),
                      elemento="QuadroEL/Modulo/TerreniTavolare/DatiTerreniTavolare/DatiTerreni/CorpoTavolare", obbl=False)
        if r is None or pt is None:
            return None
        dt = dict(r["DatiTerreni"]["DatiTerreni"])
        dt["PartitaTavolare"] = pt
        if ct:
            dt["CorpoTavolare"] = ct
        self.usa(b, "porzione_materiale")
        return {"LuogoTavolare": r["Luogo"], "DatiTerreniTavolare": {"DatiCatastali": r["DatiTerreni"]["DatiCatastali"], "DatiTerreni": dt},
                "Possesso": r["Possesso"], "CodiceDiritto_P": r["CodiceDiritto_P"], "TipologiaTerreno": r["TipologiaTerreno"],
                "Valore": r["Valore"]}

    def riga_em(self, b: dict) -> dict | None:
        """Quadro EM, rigo FabbricatiTavolare: come EC con luogo tavolare e partita/corpo tavolare (facoltativi)."""
        r = self.riga_ec(b, tavolare=True)
        el = "QuadroEM/Modulo/FabbricatiTavolare/DatiFabbricatiTavolare/DatiFabbricati"
        pt = self.val("beni", b, "partita_tavolare", lambda v: F.an(str(v), 7), elemento=el + "/PartitaTavolare", obbl=False)
        ct = self.val("beni", b, "corpo_tavolare", lambda v: F.an(str(v), 3), elemento=el + "/CorpoTavolare", obbl=False)
        pm = self.val("beni", b, "porzione_materiale", lambda v: F.an(str(v), 12), elemento=el + "/PorzioneMateriale", obbl=False)
        if r is None:
            return None
        df = dict(r["DatiFabbricati"]["DatiFabbricati"])
        for k, v in (("PartitaTavolare", pt), ("CorpoTavolare", ct), ("PorzioneMateriale", pm)):
            if v:
                df[k] = v
        out = {"LuogoTavolare": r["Luogo"], "DatiFabbricatiTavolare": {"DatiCatastali": r["DatiFabbricati"]["DatiCatastali"],
                                                                         "DatiFabbricati": df},
               "Possesso": r["Possesso"], "CodiceDiritto_P": r["CodiceDiritto_P"]}
        for k in ("Valore",):
            if k in r:
                out[k] = r[k]
        return out

    def riga_en(self, b: dict) -> dict | None:
        """Quadro EN, rigo Aziende (denominazione e CF, inventario facoltativo, diritto 1/2, valore netto). Immobili aziendali,
        beni esteri, riduzioni art. 25 e agevolazioni: non supportati."""
        c, el = "beni", "QuadroEN/Modulo/Aziende"
        for campo in ("comune", "sezione", "foglio", "particella", "subalterno", "categoria", "rendita"):
            if b.get(campo) not in (None, ""):
                self.usa(b, campo)
                self.ns.append(f"beni[{b['id']}].{campo}: campo catastale non previsto per le aziende del quadro EN")
        den = self.val(c, b, "descrizione", lambda v: F.an(v, 250), elemento=el + "/Descrizione/Denominazione")
        cf_az = SUP.attr(self.d, c, b, "codice_fiscale_emittente")
        self.usa(b, "codice_fiscale_emittente")
        fonte_cf = FO.fonte_annotazione(el + "/Descrizione/CodiceFiscale")
        cf = None
        be_en = self.beni_esteri(b, "EN")
        if cf_az in (None, "") and be_en:
            cf = None       # azienda sita all'estero: il codice fiscale non e' richiesto (annotazione CodiceFiscale)
        elif cf_az in (None, ""):
            self.err("DATO_MANCANTE", f"beni[{b['id']}].codice_fiscale_emittente",
                     "codice fiscale dell'azienda obbligatorio per i beni non esteri", fonte_cf)
        else:
            try:
                cf = cf_persona(cf_az)
            except F.ValoreXml as e:
                self.err("VALORE_NON_VALIDO", f"beni[{b['id']}].codice_fiscale_emittente", str(e), fonte_cf)
        inv = SUP.attr(self.d, c, b, "inventario")
        dinv = SUP.attr(self.d, c, b, "data_redazione_inventario")
        self.usa(b, "inventario")
        self.usa(b, "data_redazione_inventario")
        inventario = None
        if inv is True or str(inv).lower() in ("1", "true", "si"):
            if dinv in (None, ""):
                self.err("DATO_MANCANTE", f"beni[{b['id']}].data_redazione_inventario",
                         "data di redazione obbligatoria se e' indicato l'inventario", FO.fonte_xsd(el + "/Inventario"))
            else:
                try:
                    inventario = {"Inventario": "1", "DataRedazioneInventario": F.data(dinv, non_oltre=self.oggi)}
                except F.ValoreXml as e:
                    self.err("VALORE_NON_VALIDO", f"beni[{b['id']}].data_redazione_inventario", str(e),
                             FO.fonte_xsd(el + "/Inventario"))
            self.ns.append(f"beni[{b['id']}].inventario: con l'inventario dell'azienda il quadro EH (EH10) e il rigo EG "
                           "Inventario richiedono ulteriori dati: non supportato")
        elif dinv not in (None, ""):
            self.err("DATI_INCOERENTI", f"beni[{b['id']}].data_redazione_inventario",
                     "data di redazione senza inventario", FO.fonte_xsd(el + "/Inventario"))
        poss, _ = self.quota_possesso(b, el + "/Possesso")
        dir_p = self.diritto_defunto(b, "CodiciDirittoNonImmobili", el + "/CodiceDiritto_P")
        if dir_p not in (None, "1", "2"):
            self.err("REGOLA_DIRITTO_AZIENDA", f"beni[{b['id']}].diritto", "per il quadro EN sono ammessi solo i codici "
                     "diritto 1 e 2", FO.fonte_annotazione(el + "/CodiceDiritto_P"))
            dir_p = None
        valore = self.valore_bene(b, el + "/Valore")
        if None in (den, dir_p, valore) or (cf is None and not be_en) or inventario is not None:
            return None
        self.diritto_bene[b["id"]] = dir_p
        self.valore_beni[b["id"]] = int(valore)
        riga = {"Descrizione": {"Denominazione": den, **({"CodiceFiscale": cf} if cf else {})}}
        if be_en:
            riga["BeniEsteri"] = be_en
        if inventario:
            riga["Inventario"] = inventario
        riga["CodiceDiritto_P"] = dir_p
        riga["Valore"] = valore
        return riga

    def riga_eo(self, b: dict) -> dict | None:
        """Quadro EO, rigo Titoli: quotati (1), non quotati (2), esenti (3, ValoreEsente), fondi comuni (4). Beni esteri: non supportati."""
        c, el = "beni", "QuadroEO/Modulo/Titoli"
        for campo in ("comune", "sezione", "foglio", "particella", "subalterno", "categoria", "rendita"):
            if b.get(campo) not in (None, ""):
                self.usa(b, campo)
                self.ns.append(f"beni[{b['id']}].{campo}: campo catastale non previsto per i titoli del quadro EO")
        tt = self.val(c, b, "tipo_titolo", lambda v: codice_enum(str(v), "Titoli_Type"), elemento=el + "/TipoTitolo")
        cf_em = SUP.attr(self.d, c, b, "codice_fiscale_emittente")
        self.usa(b, "codice_fiscale_emittente")
        out: dict = {"TipoTitolo": tt}
        fonte_cf = FO.fonte_annotazione(el + "/CodiceFiscale")
        if tt == "1" and cf_em in (None, ""):   # annotazione CodiceFiscale: obbligatorio se TipoTitolo = 1
            self.err("DATO_MANCANTE", f"beni[{b['id']}].codice_fiscale_emittente",
                     "codice fiscale dell'emittente obbligatorio per i titoli quotati (TipoTitolo 1)", fonte_cf)
        elif cf_em not in (None, ""):
            try:
                out["CodiceFiscale"] = cf_persona(cf_em)
            except F.ValoreXml as e:
                self.err("VALORE_NON_VALIDO", f"beni[{b['id']}].codice_fiscale_emittente", str(e), fonte_cf)
        if out.get("CodiceFiscale"):   # annotazione: diverso dal CF del defunto e da quello dei soggetti del quadro EA
            propri = {str(p.get("codice_fiscale") or "").strip().upper() for p in self.d.get("persone", [])
                      if p.get("ruolo") == "defunto" or p in self.ea}
            if out["CodiceFiscale"] in propri:
                self.err("REGOLA_CF_EMITTENTE", f"beni[{b['id']}].codice_fiscale_emittente",
                         "il codice fiscale dell'emittente deve essere diverso da quello del defunto e dei soggetti del quadro EA",
                         fonte_cf)
        qta = SUP.attr(self.d, c, b, "quantita")
        self.usa(b, "quantita")
        if qta not in (None, ""):
            if not str(qta).isdigit() or len(str(qta)) > 10:
                self.err("VALORE_NON_VALIDO", f"beni[{b['id']}].quantita", f"{qta!r}: quantita' intera, massimo 10 cifre",
                         FO.fonte_xsd(el + "/Quantita"))
            else:
                out["Quantita"] = str(qta)
        ct = SUP.attr(self.d, c, b, "codice_titolo")
        self.usa(b, "codice_titolo")
        if ct not in (None, ""):
            if tt != "1":
                self.err("DATI_INCOERENTI", f"beni[{b['id']}].codice_titolo", "il codice titolo va indicato solo per i titoli "
                         "quotati in borsa italiana", FO.fonte_annotazione(el + "/CodiceTitolo"))
            else:
                try:
                    out["CodiceTitolo"] = F.an(ct, 12)
                except F.ValoreXml as e:
                    self.err("VALORE_NON_VALIDO", f"beni[{b['id']}].codice_titolo", str(e), FO.fonte_xsd(el + "/CodiceTitolo"))
        descr = self.val(c, b, "descrizione", lambda v: F.an(v, 250), elemento=el + "/Descrizione")
        td = self.val(c, b, "tipo_documento", lambda v: codice_enum(str(v), "TipoDocumento_Type"),
                      elemento=el + "/TipoDocumento")
        dd = SUP.attr(self.d, c, b, "data_documento")
        self.usa(b, "data_documento")
        data_doc = None
        fonte_dd = FO.fonte_annotazione(el + "/DataDocumento")
        if dd in (None, ""):
            if td in ("1", "2"):
                self.err("DATO_MANCANTE", f"beni[{b['id']}].data_documento", "data del documento obbligatoria se il tipo "
                         "documento e' 1 (bilancio) o 2 (inventario)", fonte_dd)
        else:
            try:
                data_doc = F.data(dd, non_oltre=self.oggi)
            except F.ValoreXml as e:
                self.err("VALORE_NON_VALIDO", f"beni[{b['id']}].data_documento", str(e), fonte_dd)
        poss, _ = self.quota_possesso(b, el + "/Possesso")
        dir_c = self.diritto_defunto(b, "CodiciDirittoNonImmobili", el + "/CodiceDiritto_C")
        # Titolo esente (TipoTitolo 3): il valore va in Possesso/ValoreEsente e NON in Possesso/Valore (annotazioni XSD
        # PossessoEO_Type/Valore e /ValoreEsente: l'uno esclude l'altro; Valore «non puo' essere presente se titolo = 3»,
        # ValoreEsente «obbligatorio se titolo = 3» e «non puo' essere presente se titolo = 1, 2»).
        esente = tt == "3"
        el_valore = el + ("/Possesso/ValoreEsente" if esente else "/Possesso/Valore")
        valore = self.valore_bene(b, el_valore)
        if None in (tt, descr, td, poss, dir_c, valore):
            return None
        self.diritto_bene[b["id"]] = dir_c
        self.valore_beni[b["id"]] = int(valore)
        if esente:
            self.valore_esente_beni[b["id"]] = int(valore)
        riga = {"TipoTitolo": tt}
        for k in ("CodiceFiscale", "Quantita", "CodiceTitolo"):
            if k in out:
                riga[k] = out[k]
        riga["Descrizione"], riga["TipoDocumento"] = descr, td
        if data_doc:
            riga["DataDocumento"] = data_doc
        riga["Possesso"] = {**poss, ("ValoreEsente" if esente else "Valore"): valore}
        riga["CodiceDiritto_C"] = dir_c
        be = self.beni_esteri(b, "EO")
        if be:
            riga["BeniEsteri"] = be
            if "CodiceFiscale" in riga:     # annotazione CodiceFiscale: non presente se e' barrata «Bene sito all'estero»
                self.err("DATI_INCOERENTI", f"beni[{b['id']}].codice_fiscale_emittente", "titolo estero: il codice fiscale "
                         "dell'emittente non va indicato", fonte_cf)
        return riga

    def devoluzioni_bene(self, b: dict, quadro: str) -> list[dict]:
        """Righe della sezione devoluzione del bene, ordinate per posizione EA (annotazione IdentificazioneSoggetto:
        'in ordine progressivo')."""
        tipo_rip = "CodiciDirittoNonImmobiliDevoluzione" if quadro in ("ER", "EN", "EO", "EP", "EQ") else "CodiciDiritto_Type"
        el = f"Quadro{quadro}/Modulo/{_RIGA[quadro]}/Devoluzione{quadro}/Devoluzione"
        devs = [d for d in self.d.get("devoluzioni", []) if d.get("bene_id") == b["id"]]
        righe, somma, persone_viste = [], Fraction(0), set()
        dir_def = self.diritto_bene.get(b["id"])
        valore = self.valore_beni.get(b["id"])
        if not devs:
            self.err("DEVOLUZIONE_MANCANTE", f"beni[{b['id']}]", "in presenza del quadro EA la sezione devoluzione "
                     "deve essere compilata", FO.fonte_annotazione(f"Quadro{quadro}/Modulo/{_RIGA[quadro]}/Devoluzione{quadro}"))
            return []
        for d in devs:
            self.usa(d, "bene_id", "persona_id", "quota", "diritto")
            perc = f"devoluzioni[{d['id']}]"
            pid = d.get("persona_id")
            if pid not in self.pos_ea:
                self.err("DEVOLUZIONE_SOGGETTO", perc + ".persona_id", "il beneficiario deve essere un soggetto del "
                         "quadro EA (erede o chiamato)", FO.fonte_annotazione(el + "/IdentificazioneSoggetto"))
                continue
            if pid in self.rinunce:
                self.err("DEVOLUZIONE_RINUNCIATARIO", perc + ".persona_id", "un soggetto rinunciatario non puo' essere "
                         "beneficiario di una devoluzione (annotazione XSD di IdentificazioneSoggetto)",
                         FO.fonte_annotazione(el + "/IdentificazioneSoggetto"))
                continue
            if pid in persone_viste:
                self.err("DEVOLUZIONE_DUPLICATA", perc, "lo stesso beneficiario compare piu' volte sullo stesso bene con "
                         "lo stesso diritto", FO.fonte_annotazione(el + "/IdentificazioneSoggetto"))
            persone_viste.add(pid)
            try:
                n, den = F.quota_grezza(d.get("quota"))
            except (F.ValoreXml, V.ValoreNonValido, AttributeError) as e:
                self.err("VALORE_NON_VALIDO", perc + ".quota", f"quota di devoluzione: {e}", FO.fonte_xsd(el + "/Quota"))
                continue
            try:
                dir_r = codice_enum(d.get("diritto"), tipo_rip, alias_descrizione=True)
            except F.ValoreXml as e:
                self.err("VALORE_NON_VALIDO", perc + ".diritto", str(e), FO.fonte_xsd(el + "/CodiceDiritto_Rip"))
                continue
            if dir_def is not None and dir_r != dir_def:
                self.ns.append(f"{perc}: diritto devoluto {dir_r} diverso dal diritto del defunto {dir_def} (il valore "
                               "quota richiede le regole di valutazione dei diritti, Fascicolo I p. PDF 24): non supportato")
                continue
            if self.estero_bene.get(b["id"]) and quadro in ("EB", "EC"):
                # immobile estero: le agevolazioni (P, X, Y, Z: «Provincia diverso da EE») e le riduzioni non sono ammesse
                for campo in ("agevolazioni", "riduzioni"):
                    if SUP.attr(self.d, "devoluzioni", d, campo) not in (None, ""):
                        self.usa(d, campo)
                        self.err("REGOLA_AGEVOLAZIONE_ESTERO", f"{perc}.{campo}", "immobile estero: agevolazioni e riduzioni "
                                 "non ammesse (annotazione XSD di Agevolazioni)", FO.fonte_annotazione(el + "/Agevolazioni"))
                agev = None
            else:
                agev = PC.leggi_riga(self, d, b, quadro, perc)
                if agev:
                    PC.registra(self, d["id"], b["id"], pid, agev, quadro)
                RA.leggi_riga(self, d, b, quadro, perc, pid)
                AG.leggi_riga(self, d, b, quadro, perc, pid)
            somma += Fraction(n, den)
            self.persona_dev[d["id"]] = pid
            righe.append((self.pos_ea[pid], dir_r, d["id"], n, den))
        if righe and somma != 1:
            self.err("QUOTE_DEVOLUZIONE", f"beni[{b['id']}]", f"la somma delle quote di devoluzione e' "
                     f"{somma.numerator}/{somma.denominator}, deve essere 1/1",
                     FO.fonte_annotazione(el + "/Quota/QuotaElementi"))
        elif righe and self.quote_legge is not None:
            dich = {self.persona_dev[did]: Fraction(n, den) for _, _, did, n, den in righe}
            if dich != self.quote_legge:
                self.err("QUOTA_DI_LEGGE", f"beni[{b['id']}]", "devoluzione per legge: le quote devono seguire "
                         f"l'allegato 5 ({DL.descrivi(self.quote_legge)}); dichiarate: {DL.descrivi(dich)}",
                         FO.fonte_annotazione(el + "/Quota") + "; " + DL.FONTE)
        righe.sort()
        out = []
        for (m, r), dir_r, did, n, den in righe:
            qv = None
            if valore is not None:
                cent, esatto = F.frazione_a_centesimi(Fraction(valore) * Fraction(n, den))
                qv = F.euro_centesimi(cent)
                self.quota_valore[did] = cent
                self.righe_dev[did] = {"quadro": quadro, "bene_id": b["id"], "persona_id": self.persona_dev[did],
                                       "diritto": dir_r, "quota_valore": cent,
                                       "codice_comune": self.comune_bene.get(b["id"]),
                                       "estero": bool(self.estero_bene.get(b["id"]))}
                if not esatto:
                    self.avv("ARROTONDAMENTO_VALORE_QUOTA", f"devoluzioni[{did}]",
                             f"valore quota {valore} x {n}/{den} non esatto al centesimo: arrotondato a {qv} "
                             "(ROUND_HALF_UP, scelta implementativa entro la tolleranza dell'annotazione QuotaValore)",
                             FO.fonte_annotazione(el + "/Quota/QuotaValore") + "; " + FO.fonte_fasc1(24, "Valore quota"))
            quota = {"QuotaElementi": {"QuotaNumeratore": str(n), "QuotaDenominatore": str(den)}}
            if qv is not None:
                quota["QuotaValore"] = qv
            riga_dev = {"_id": did, "IdentificazioneSoggetto": {"Rigo": str(r), "Modulo": str(m)}, "Quota": quota,
                        "CodiceDiritto_Rip": dir_r}
            if did in self.agev_dev:
                riga_dev["Agevolazioni"] = self.agev_dev[did]
            if did in self.rid_dev:
                riga_dev["Riduzioni"] = self.rid_dev[did]
            if did in self.righe_dev:
                self.righe_dev[did]["agevolazione"] = self.agev_dev.get(did)
                self.righe_dev[did]["riduzione"] = self.rid_dev.get(did)
            out.append(riga_dev)
        return out

    # ---------------------------------------------------------------- quadri beni
    def quadro_beni(self, quadro: str, beni: list[dict], costruttore) -> dict | None:
        """Righe del quadro con continuazioni (max 3 devoluzioni per rigo) e impaginazione in moduli."""
        if not beni:
            return None
        righe: list[tuple[str, dict, list]] = []  # (id bene, dati rigo, devoluzioni del rigo)
        for b in beni:
            r = costruttore(b)
            if r is None:  # errori gia' registrati sul bene: le sue devoluzioni non si valutano
                for d in self.d.get("devoluzioni", []):
                    if d.get("bene_id") == b["id"]:
                        self.scartati.add(d["id"])
                continue
            RA.valore_prec_succ(self, b, r, quadro)
            devs = self.devoluzioni_bene(b, quadro) if self.ea else []
            blocchi = [devs[i:i + 3] for i in range(0, len(devs), 3)] or [[]]
            for k, blocco in enumerate(blocchi):
                righe.append((b["id"], r if k == 0 else {}, blocco, k < len(blocchi) - 1))
        per_mod = _PER_MODULO[quadro]
        moduli = []
        for i, (bid, dati_rigo, blocco, cont) in enumerate(righe):
            m, rr = i // per_mod + 1, i % per_mod + 1
            if i % per_mod == 0:
                moduli.append({_RIGA[quadro]: []})
            riga = dict(dati_rigo)
            if blocco or cont:
                sez = {"Devoluzione": [{k: v for k, v in dv.items() if k != "_id"} for dv in blocco]}
                if cont:
                    sez["Continuazione"] = "1"
                riga[f"Devoluzione{quadro}"] = sez
            moduli[-1][_RIGA[quadro]].append(riga)
            xp = f"{_XP_DICH}/suc:Quadro{quadro}/suc:Modulo[{m}]/suc:{_RIGA[quadro]}[{rr}]"
            if dati_rigo:
                self.mappa[bid] = {"coll": "beni", "quadro": quadro, "modulo": m, "rigo": rr, "xpath": xp,
                                   "righi_continuazione": []}
            else:
                self.mappa[bid]["righi_continuazione"].append({"modulo": m, "rigo": rr, "xpath": xp})
            for pos, dv in enumerate(blocco, 1):
                self.mappa[dv["_id"]] = {"coll": "devoluzioni", "quadro": quadro, "modulo": m, "rigo": rr,
                                         "posizione": pos,
                                         "xpath": f"{xp}/suc:Devoluzione{quadro}/suc:Devoluzione[{pos}]"}
        return {"Modulo": moduli} if moduli else None

    # ---------------------------------------------------------------- passivita'
    def quadro_ed(self) -> dict | None:
        pas = self.d.get("passivita", [])
        if not pas:
            return None
        el = "QuadroED/Modulo/Passivita"

        def chiave(p):
            s = SUP.sup(self.d).get("passivita", {}).get(p["id"], {})
            return (str(s.get("tipo") or ""), str(s.get("data_documento") or ""), str(p.get("descrizione") or ""), p["id"])
        righe = []
        for p in sorted(pas, key=chiave):
            c, base = "passivita", f"passivita[{p['id']}]"
            tipo = self.val(c, p, "tipo", lambda v: codice_enum(str(v), "CodiciPassivita_Type"), elemento=el + "/Tipo")
            descr = self.val(c, p, "descrizione", lambda v: F.an(v, 250), elemento=el + "/Descrizione",
                             fonte=FO.fonte_annotazione(el + "/Descrizione"))
            estr = self.val(c, p, "estremi_documento", lambda v: F.an(v, 50), elemento=el + "/EstremiDocumento",
                            fonte=FO.fonte_annotazione(el + "/EstremiDocumento"))
            dd = self.val(c, p, "data_documento", lambda v: F.data(v, non_oltre=self.oggi), elemento=el + "/DataDocumento",
                          fonte=FO.fonte_annotazione(el + "/DataDocumento"))
            valore = self.val(c, p, "importo", F.euro_intero, elemento=el + "/Possesso/Valore",
                              fonte=FO.fonte_xsd(el + "/Possesso/Valore") + "; " + FO.fonte_fasc1(38, "Valore: quota del "
                                                                                                   "defunto, all'unita' di euro"))
            poss: dict = {}
            q = SUP.attr(self.d, c, p, "possesso")
            self.usa(p, "possesso")
            if tipo == "11":
                # tipo 11 (legato o altro onere): Valore = valore del legato (Fascicolo I p. 38); il possesso non va valorizzato
                if q is not None:
                    self.err("REGOLA_POSSESSO_TIPO_11", base + ".possesso", "con tipo passivita' 11 il possesso non va "
                             "valorizzato (il valore e' quello del legato o dell'onere)",
                             FO.fonte_annotazione(el + "/Possesso/PossessoNumeratore"))
            elif q is None:
                self.err("DATO_MANCANTE", base + ".possesso", "quota del defunto nella passivita' obbligatoria (es. 1/1)",
                         FO.fonte_annotazione(el + "/Possesso") + "; " + FO.fonte_fasc1(38, "Quota del defunto"))
            else:
                try:
                    n, d = F.quota_grezza(q)
                    if len(str(d)) > 6:
                        raise F.ValoreXml("denominatore oltre 6 cifre")
                    poss = {"PossessoNumeratore": str(n), "PossessoDenominatore": str(d)}
                except (F.ValoreXml, V.ValoreNonValido, AttributeError) as e:
                    self.err("VALORE_NON_VALIDO", base + ".possesso", str(e), FO.fonte_xsd(el + "/Possesso"))
            if valore is not None:
                poss["Valore"] = valore
                if tipo == "2" and int(valore) > 1033:
                    self.err("REGOLA_SPESE_FUNERARIE", base + ".importo", "spese funerarie: importo massimo 1033",
                             FO.fonte_annotazione(el + "/Possesso/Valore"))
            prog = None
            bid = SUP.attr(self.d, c, p, "bene_id")
            self.usa(p, "bene_id")
            if tipo in ("3", "4", "5", "7"):
                if bid is None:
                    self.err("DATO_MANCANTE", base + ".bene_id", f"per il tipo {tipo} va indicato il cespite di "
                             "riferimento (quadro/rigo/modulo)", FO.fonte_annotazione(el + "/ProgressivoCespite"))
                else:
                    prog = {"_bene": bid, "_pas": p["id"]}
            elif bid is not None:
                self.err("REGOLA_PROGRESSIVO_CESPITE", base + ".bene_id", f"per il tipo {tipo} il cespite di riferimento "
                         "non va indicato", FO.fonte_annotazione(el + "/ProgressivoCespite"))
            # ripartizione (obbligatoria in presenza di EA): persona_id (tutta a un soggetto) oppure
            # opzioni.telematico.passivita[id].ripartizione = [{persona_id, quota}] (proposta P5)
            rip = self.ripartizione_ed(p, tipo, valore, base, el) if self.ea else None
            riga = {"Tipo": tipo, "Descrizione": descr, "EstremiDocumento": estr, "DataDocumento": dd, "Possesso": poss}
            if None in (tipo, descr, estr, dd, valore) or (tipo != "11" and not poss.get("PossessoDenominatore")):
                continue
            if prog:
                riga["ProgressivoCespite"] = prog
            righe.append((p["id"], riga, rip["Ripartizione"] if rip else []))
            self.valore_passivita[p["id"]] = int(valore)
        # Continuazione (annotazioni XSD di RipartizioneED e di Ripartizione_Type; Fascicolo I p. PDF 38): al massimo tre soggetti
        # per rigo; se sono di piu' si barra «Continuazione» e gli altri vanno nella sezione ripartizione del rigo che segue,
        # senza compilare i dati identificativi della passivita'.
        piatte: list[tuple[str, dict, bool]] = []     # (id passivita', rigo, e' un rigo di continuazione)
        for pid, riga, rip in righe:
            blocchi = [rip[i:i + 3] for i in range(0, len(rip), 3)] or [[]]
            for k, blocco in enumerate(blocchi):
                r_ = dict(riga) if k == 0 else {}
                if blocco:
                    sez = {"Ripartizione": blocco}
                    if k < len(blocchi) - 1:
                        sez["Continuazione"] = "1"
                    r_["RipartizioneED"] = sez
                piatte.append((pid, r_, k > 0))
        moduli = []
        for i, (pid, riga, cont) in enumerate(piatte):
            m, r = i // 3 + 1, i % 3 + 1
            if i % 3 == 0:
                moduli.append({"Passivita": []})
            moduli[-1]["Passivita"].append(riga)
            xp = f"{_XP_DICH}/suc:QuadroED/suc:Modulo[{m}]/suc:Passivita[{r}]"
            if not cont:
                self.mappa[pid] = {"coll": "passivita", "quadro": "ED", "modulo": m, "rigo": r, "xpath": xp,
                                   "righi_continuazione": []}
            else:
                self.mappa[pid]["righi_continuazione"].append({"modulo": m, "rigo": r, "xpath": xp})
        return {"Modulo": moduli} if moduli else None

    def devoluzione_fr(self) -> dict:
        """Frontespizio/TipoDichiarazione/Devoluzione nell'ordine dello schema: Legge, Testamento, sezione Testamento."""
        out = {}
        if SUP.dich(self.d, "devoluzione_per_legge") is True or SUP.dich(self.d, "devoluzione_per_testamento") is not True:
            out["DevoluzionePerLegge"] = "1"
        if SUP.dich(self.d, "devoluzione_per_testamento") is True:
            out["DevoluzionePerTestamento"] = "1"
            if self.testamento_x:
                out["Testamento"] = self.testamento_x
        return out

    def valida_testamento(self, el: str, ddec) -> None:
        """Controlla i dati della sezione Testamento (frontespizio). La devoluzione per testamento NON e' ancora
        esportabile (legatari EA, EG Testamento, EH, quote libere): se indicata, la bozza resta bloccata."""
        perc = "opzioni.telematico.dichiarazione"
        fonte = FO.fonte_annotazione(el + "/Devoluzione/Testamento")
        flag = SUP.dich(self.d, "devoluzione_per_testamento")
        sez = SUP.dich(self.d, "testamento")
        if flag is not True:
            if sez:
                self.err("DATI_INCOERENTI", perc + ".testamento", "la sezione Testamento non va compilata se la devoluzione "
                         "per testamento non e' selezionata", fonte)
            return
        if not isinstance(sez, dict) or not sez:
            self.err("DATO_MANCANTE", perc + ".testamento", "la sezione Testamento e' obbligatoria con la devoluzione per "
                     "testamento", fonte)
            return
        if sez.get("estero") is True:
            self.testamento_x = {"TestamentoEstero": "1"}
            return
        date_ = {}
        for k in ("data_pubblicazione", "data_registrazione"):
            try:
                date_[k] = F.data_iso(sez.get(k))
            except F.ValoreXml as e:
                self.err("VALORE_NON_VALIDO", f"{perc}.testamento.{k}", str(e), fonte)
        for k, lim in (("pubblico_ufficiale", 50), ("ufficio_registrazione", None), ("serie", 2), ("numero_registrazione", 6)):
            v = sez.get(k)
            if v in (None, ""):
                self.err("DATO_MANCANTE", f"{perc}.testamento.{k}", "obbligatorio se il testamento non e' estero", fonte)
            elif lim and len(str(v)) > lim:
                self.err("VALORE_NON_VALIDO", f"{perc}.testamento.{k}", f"al massimo {lim} caratteri", fonte)
        uff = sez.get("ufficio_registrazione")
        if uff not in (None, ""):
            try:
                uff = codice_enum(uff, "UfficioDiRegistrazione_Type")
            except F.ValoreXml as e:
                self.err("VALORE_NON_VALIDO", perc + ".testamento.ufficio_registrazione", str(e), fonte)
                uff = None
        if sez.get("serie") not in (None, "") and not re.fullmatch(r"[1-4][A-Z]?", str(sez["serie"])):
            self.err("VALORE_NON_VALIDO", perc + ".testamento.serie", "serie: una cifra da 1 a 4, con lettera maiuscola "
                     "facoltativa (reg:Serie_Type)", fonte)
        if sez.get("numero_registrazione") not in (None, "") and not re.fullmatch(r"\d{1,6}", str(sez["numero_registrazione"])):
            self.err("VALORE_NON_VALIDO", perc + ".testamento.numero_registrazione", "solo cifre, al massimo 6", fonte)
        sn = sez.get("sottonumero_registrazione")
        if sn not in (None, "") and len(str(sn)) > 3:
            self.err("VALORE_NON_VALIDO", perc + ".testamento.sottonumero_registrazione", "al massimo 3 caratteri", fonte)
        dp, dr = date_.get("data_pubblicazione"), date_.get("data_registrazione")
        if len(date_) == 2 and uff and not any(
                x.codice == "VALORE_NON_VALIDO" and "testamento" in x.percorso for x in self.errori) and all(
                sez.get(k) not in (None, "") for k in ("pubblico_ufficiale", "serie", "numero_registrazione")):
            reg = {"UfficioDiRegistrazione": uff, "Serie": str(sez["serie"]), "NumeroRegistrazione": str(sez["numero_registrazione"])}
            if sn not in (None, ""):
                reg["SottonumeroRegistrazione"] = str(sn)
            reg["DataRegistrazione"] = F.data(sez["data_registrazione"])
            self.test_reg = reg
            self.testamento_x = {"Pubblicazione": {"PubblicoUfficiale": F.an(sez["pubblico_ufficiale"], 50),
                                                   "DataPubblicazioneTestamento": F.data(sez["data_pubblicazione"])},
                                 "Registrazione": reg}
        if dp and ddec and dp < ddec:
            self.err("REGOLA_DATA_PUBBLICAZIONE", perc + ".testamento.data_pubblicazione",
                     "la data di pubblicazione deve essere maggiore o uguale alla data del decesso", fonte)
        if dr and dp and dr < dp:
            self.err("REGOLA_DATA_REGISTRAZIONE", perc + ".testamento.data_registrazione",
                     "la data di registrazione deve essere maggiore o uguale alla data di pubblicazione", fonte)
        if dr and ddec and dr < ddec:
            self.err("REGOLA_DATA_REGISTRAZIONE", perc + ".testamento.data_registrazione",
                     "la data di registrazione deve essere maggiore o uguale alla data del decesso", fonte)

    def ripartizione_ed(self, p: dict, tipo, valore, base: str, el: str) -> dict | None:
        fonte = FO.fonte_annotazione(el + "/RipartizioneED/Ripartizione") + "; " + FO.fonte_fasc1(38, "Ripartizione")
        self.usa(p, "persona_id", "ripartizione")
        pid = p.get("persona_id")
        rip_sup = SUP.attr(self.d, "passivita", p, "ripartizione")
        voci: list[tuple[str, int, int]] = []
        if rip_sup is not None:
            if pid not in (None, ""):
                self.err("DATI_INCOERENTI", base, "indicare persona_id oppure la ripartizione, non entrambi", fonte)
                return None
            if not isinstance(rip_sup, list) or not rip_sup:
                self.err("VALORE_NON_VALIDO", base + ".ripartizione", "attesa lista di {persona_id, quota}", fonte)
                return None
            for i, v in enumerate(rip_sup):
                try:
                    if not isinstance(v, dict) or set(v) - {"persona_id", "quota"}:
                        raise F.ValoreXml("attesi solo persona_id e quota")
                    n, d = F.quota_grezza(v.get("quota"))
                    voci.append((v.get("persona_id"), n, d))
                except (F.ValoreXml, V.ValoreNonValido, AttributeError) as e:
                    self.err("VALORE_NON_VALIDO", f"{base}.ripartizione[{i}]", str(e), fonte)
                    return None
        elif pid not in (None, ""):
            voci = [(pid, 1, 1)]
        for vp, _, _ in voci or [(pid, 1, 1)]:
            if vp not in self.pos_ea:
                self.err("RIPARTIZIONE_SOGGETTO", base + (".ripartizione" if rip_sup is not None else ".persona_id"),
                         "la passivita' va attribuita a soggetti del quadro EA", fonte)
                return None
        if len({v[0] for v in voci}) != len(voci):
            self.err("RIPARTIZIONE_DUPLICATA", base + ".ripartizione", "soggetto ripetuto nella ripartizione", fonte)
            return None
        somma = sum((Fraction(n, d) for _, n, d in voci), Fraction(0))
        if somma != 1:
            self.err("QUOTE_RIPARTIZIONE", base + ".ripartizione", f"somma delle quote {somma}: deve essere 1/1", fonte)
            return None
        if tipo not in DL.TIPI_PASSIVITA_LIBERE and tipo is not None:
            dich = {vp: Fraction(n, d) for vp, n, d in voci}
            if self.quote_legge is not None and dich != self.quote_legge:
                self.err("QUOTA_DI_LEGGE", base + (".ripartizione" if rip_sup is not None else ".persona_id"),
                         f"devoluzione per legge: la passivita' di tipo {tipo} va ripartita secondo l'allegato 5 "
                         f"({DL.descrivi(self.quote_legge)}); dichiarata: {DL.descrivi(dich)}",
                         FO.fonte_annotazione(el + "/RipartizioneED/Ripartizione/Quota") + "; " + DL.FONTE)
                return None
        if valore is None:
            return None
        righe = []
        for vp, n, d in sorted(voci, key=lambda v: self.pos_ea[v[0]]):
            qv = Fraction(int(valore)) * Fraction(n, d)
            if qv.denominator != 1:
                self.ns.append(f"{base}: valore quota della passivita' {valore} x {n}/{d} non intero: l'arrotondamento "
                               "all'unita' di euro (Fascicolo I p. 38) non ha un criterio indicato")
                return None
            m, r = self.pos_ea[vp]
            righe.append({"IdentificazioneSoggetto": {"Rigo": str(r), "Modulo": str(m)},
                          "Quota": {"QuotaElementi": {"QuotaNumeratore": str(n), "QuotaDenominatore": str(d)},
                                    "QuotaValore": F.euro_centesimi(int(qv))}})
            self.quota_passivo.setdefault(vp, []).append((p["id"], int(qv)))
        return {"Ripartizione": righe}

    def risolvi_progressivi(self, qed: dict | None):
        if not qed:
            return
        for modulo in qed["Modulo"]:
            for riga in modulo["Passivita"]:
                prog = riga.get("ProgressivoCespite")
                if not prog:
                    continue
                bid, pas = prog.pop("_bene"), prog.pop("_pas")
                ref = self.mappa.get(bid)
                tipo = riga.get("Tipo")
                if not ref or ref.get("coll") != "beni":
                    self.err("RIFERIMENTO_INESISTENTE", f"passivita[{pas}].bene_id", f"il cespite {bid} non e' "
                             "esportato in questa dichiarazione",
                             FO.fonte_annotazione("QuadroED/Modulo/Passivita/ProgressivoCespite"))
                    continue
                if bid in self.valore_esente_beni:
                    # Le fonti non dicono se una passivita' collegata a un titolo esente sia deducibile
                    # (Fascicolo I p. PDF 36: deducibili i debiti per beni «compresi nell'attivo ereditario»; il titolo
                    # esente e' «compreso nell'attivo» per l'XSD Titoli_Type 3 ma «esente dall'imposta», Fasc. I p. PDF 3).
                    self.ns.append(f"passivita[{pas}].bene_id: passivita' collegata al titolo esente {bid}: deducibilita' "
                                   "non determinabile dalle fonti, non supportato")
                    continue
                if tipo == "3" and ref["quadro"] not in ("EB", "EC", "EL", "EM"):
                    self.err("REGOLA_PROGRESSIVO_CESPITE", f"passivita[{pas}].bene_id", "per il tipo 3 (mutui) il "
                             "cespite deve essere un immobile (EB, EC)",
                             FO.fonte_annotazione("QuadroED/Modulo/Passivita/ProgressivoCespite/Quadro"))
                prog.update({"Quadro": ref["quadro"], "Rigo": str(ref["rigo"]), "Mod": str(ref["modulo"])})

    # ---------------------------------------------------------------- EE
    def quadro_ee(self) -> dict | None:
        """Totali dalle annotazioni XSD di QuadroEE (nessun bene aziendale o agevolazione A nel perimetro)."""
        con_a = {r["bene_id"] for r in getattr(self, "ag_righe", []) if r["codice"] == "A"}   # annotazioni di QuadroEE: al netto di A
        imm = sum(v for k, v in self.valore_beni.items() if self.quadro_bene.get(k) in ("EB", "EC", "EL", "EM") and k not in con_a)
        altri = sum(v for k, v in self.valore_beni.items() if self.quadro_bene.get(k) == "ER")
        titoli = sum(v for k, v in self.valore_beni.items() if self.quadro_bene.get(k) == "EO")
        aziende = sum(v for k, v in self.valore_beni.items() if self.quadro_bene.get(k) == "EN")
        mezzi = sum(v for k, v in self.valore_beni.items() if self.quadro_bene.get(k) in ("EP", "EQ"))
        passivo = sum(self.valore_passivita.values())
        attivo = imm + aziende + titoli + mezzi + altri
        if not (imm or aziende or titoli or mezzi or altri or passivo):
            return None
        ee: dict = {}
        if imm:
            ee["TotaleValoreImmobili"] = str(imm)
        if aziende:
            ee["TotaleValoreAziende"] = str(aziende)
        if titoli:
            ee["TotaleValoreTitoli"] = str(titoli)
        if mezzi:
            ee["TotaleValoreAereiNavi"] = str(mezzi)
        if altri:
            ee["TotaleValoreAltriBeni"] = str(altri)
        if attivo:
            ee["TotaleAttivo"] = str(attivo)
        if passivo:
            ee["TotalePassivo"] = str(passivo)
        netto = attivo - passivo
        if netto:
            ee["TotaleValoreAsseEreditarioNetto"] = F.intero_con_segno(netto)
        else:
            self.avv("EE_NETTO_ZERO", "quadro[EE]", "asse netto pari a zero: DatoNU_Type non ammette 0, elemento omesso",
                     FO.fonte_xsd("QuadroEE/TotaleValoreAsseEreditarioNetto"))
        self.mappa["quadro:EE"] = {"coll": None, "quadro": "EE", "xpath": f"{_XP_DICH}/suc:QuadroEE",
                                   "totali": dict(ee)}
        return ee

    # ---------------------------------------------------------------- frontespizio
    def frontespizio(self, quadri_presenti: list[str]) -> dict | None:
        el = "Frontespizio"
        dft = self.defunto
        if dft is None:
            return None
        cfd = self.val("persone", dft, "codice_fiscale", cf_persona, elemento=el + "/CodiceFiscaleDefunto")
        ddec = self.val("persone", dft, "data_decesso", lambda v: F.data_iso(v), elemento=el + "/DatiDefunto/UlterioriDati/DataDecesso")
        if ddec:
            dnasc = F.data_iso(dft["data_nascita"]) if isinstance(dft.get("data_nascita"), str) and \
                re.match(r"^\d{4}-\d{2}-\d{2}$", dft["data_nascita"]) else None
            if ddec <= date(2006, 10, 2) or (dnasc and ddec < dnasc) or ddec > self.oggi:
                self.err("REGOLA_DATA_DECESSO", f"persone[{dft['id']}].data_decesso", "la data del decesso deve essere "
                         "successiva al 2 ottobre 2006, non anteriore alla nascita e non futura",
                         FO.fonte_annotazione(el + "/DatiDefunto/UlterioriDati/DataDecesso"))
        self.data_decesso = ddec
        if dft.get("relazione_con_defunto") not in (None, ""):
            self.usa(dft, "relazione_con_defunto")
            self.ns.append(f"persone[{dft['id']}].relazione_con_defunto: campo non applicabile al defunto")
        ana_d = self.anagrafica(dft, el + "/DatiDefunto/DatiAnagrafici")
        stato_civ = SUP.dich(self.d, "stato_civile")
        try:
            stato_civ = codice_enum(stato_civ, "StatoCivile_Type") if stato_civ is not None else None
        except F.ValoreXml as e:
            self.err("VALORE_NON_VALIDO", "opzioni.telematico.dichiarazione.stato_civile", str(e),
                     FO.fonte_xsd(el + "/DatiDefunto/UlterioriDati/StatoCivile"))
            stato_civ = None
        if SUP.dich(self.d, "stato_civile") is None:
            self.err("DATO_MANCANTE", "opzioni.telematico.dichiarazione.stato_civile", "stato civile del defunto "
                     "obbligatorio", FO.fonte_xsd(el + "/DatiDefunto/UlterioriDati/StatoCivile"))
        # devoluzione: solo per legge
        legge = SUP.dich(self.d, "devoluzione_per_legge")
        if legge is not True and SUP.dich(self.d, "devoluzione_per_testamento") is not True:
            self.ns.append("opzioni.telematico.dichiarazione.devoluzione_per_legge: indicare la devoluzione per legge "
                           "o per testamento (la legge estera non e' ancora mappata)")
        self.valida_testamento(el, ddec)
        # presentatore
        pres = self.presentatore
        pres_x = None
        psup = SUP.presentatore_sup(self.d)
        carica = psup.get("codice_carica")
        try:
            carica = codice_enum(carica, "CodiciCarica_Type") if carica is not None else None
        except F.ValoreXml as e:
            self.err("VALORE_NON_VALIDO", "opzioni.telematico.dichiarazione.presentatore.codice_carica", str(e),
                     FO.fonte_xsd(el + "/Presentatore/CodiceCarica"))
            carica = None
        if carica is None:
            self.err("DATO_MANCANTE", "opzioni.telematico.dichiarazione.presentatore.codice_carica",
                     "codice carica del dichiarante obbligatorio", FO.fonte_xsd(el + "/Presentatore/CodiceCarica"))
        elif carica not in FR.CARICHE_SUPPORTATE:
            self.ns.append(f"opzioni.telematico.dichiarazione.presentatore.codice_carica={carica}: {FR.MOTIVO_CARICA.get(carica, 'non supportato')} "
                           f"(supportati: {', '.join(FR.CARICHE_SUPPORTATE)})")
        self.codice_carica = carica
        if pres is not None:
            cfp = self.val("persone", pres, "codice_fiscale", cf_persona, elemento=el + "/Presentatore/CodiceFiscale")
            if cfp and cfd and cfp == cfd:
                self.err("REGOLA_PRESENTATORE", f"persone[{pres['id']}].codice_fiscale", "il dichiarante deve essere "
                         "diverso dal defunto", FO.fonte_annotazione(el + "/Presentatore/CodiceFiscale"))
            in_ea = [p for p in self.ea if isinstance(p.get("codice_fiscale"), str)
                     and p["codice_fiscale"].strip().upper() == cfp]
            if carica == "1" and not in_ea and not self.integrativa:
                self.err("REGOLA_PRESENTATORE", f"persone[{pres['id']}]", "con codice carica 1 il dichiarante deve essere "
                         "presente nel quadro EA come erede o chiamato", FO.fonte_annotazione(el + "/Presentatore/CodiceCarica"))
            FR.regole_carica(self, carica, pres, cfp, cfd, in_ea)
            if pres.get("ruolo") == "presentatore" and in_ea:
                gemello = in_ea[0]
                for campo in ("cognome", "nome", "data_nascita", "luogo_nascita"):
                    if (pres.get(campo) or "") != (gemello.get(campo) or ""):
                        self.err("PRESENTATORE_INCOERENTE", f"persone[{pres['id']}].{campo}", f"diverso dal soggetto EA "
                                 f"persone[{gemello['id']}] con lo stesso codice fiscale", "controllo interno")
                self.avv("PERSONA_DUPLICATA", f"persone[{pres['id']}]", f"il dichiarante e' registrato anche come "
                         f"persone[{gemello['id']}]: preferire il riferimento opzioni.telematico.dichiarazione.presentatore"
                         ".persona_id (proposta in docs/PROPOSTE_telematico.md)", "docs/PROPOSTE_telematico.md")
            if pres.get("ruolo") == "presentatore":
                for campo in ("relazione_con_defunto", "data_decesso"):
                    if pres.get(campo) not in (None, ""):
                        self.usa(pres, campo)
                        self.interno(pres, campo)
            ana_p = self.anagrafica(pres, el + "/Presentatore/DatiAnagrafici")
            tel = psup.get("telefono")
            mail = psup.get("email")
            pres_x = {"CodiceFiscale": cfp, "CodiceCarica": carica, "DatiAnagrafici": ana_p}
            dec_term = FR.decorrenza(self, ddec, psup)
            if dec_term:
                pres_x["DecorrenzaTerminePresentazione"] = dec_term
            estero_p = FR.residente_estero(self, psup)
            if estero_p:
                pres_x["ResidenteEstero"] = estero_p
            rapp_cf = FR.rappresentato(self, carica, psup, cfp, cfd)
            if rapp_cf:
                pres_x["CodiceFiscaleRappresentato"] = rapp_cf
            try:
                if tel:
                    pres_x["Telefono"] = F.telefono(tel)
                if mail:
                    pres_x["Email"] = F.email(mail)
            except F.ValoreXml as e:
                self.err("VALORE_NON_VALIDO", "opzioni.telematico.dichiarazione.presentatore", str(e),
                         FO.fonte_xsd(el + "/Presentatore/Telefono|Email"))
            if not tel and not mail:
                self.err("DATO_MANCANTE", "opzioni.telematico.dichiarazione.presentatore", "indicare almeno telefono "
                         "o email del dichiarante", FO.fonte_annotazione(el + "/Presentatore/Telefono"))
            self.mappa["presentatore"] = {"coll": "persone", "id": pres["id"], "quadro": "Frontespizio",
                                          "xpath": f"{_XP_DICH}/suc:Frontespizio/suc:Presentatore"}
        if SUP.dich(self.d, "firma_dichiarante") is not True:
            self.err("FIRMA_MANCANTE", "opzioni.telematico.dichiarazione.firma_dichiarante", "la casella firma del "
                     "dichiarante deve essere confermata esplicitamente (true)", FO.fonte_xsd(el + "/FirmaModello/FirmaDichiarante"))
        self.mappa[dft["id"]] = {"coll": "persone", "quadro": "Frontespizio",
                                 "xpath": f"{_XP_DICH}/suc:Frontespizio/suc:DatiDefunto"}
        n1 = sum(1 for t in self.tipo_ea.values() if t == "1")
        n3 = sum(1 for t in self.tipo_ea.values() if t == "3")
        n2 = sum(1 for t in self.tipo_ea.values() if t == "2")
        ben = {k: str(v) for k, v in (("NumeroEredi", n1), ("NumeroChiamati", n3), ("NumeroLegatari", n2)) if v}
        firma = {f"Casella{q}": "1" for q in quadri_presenti}
        firma["FirmaDichiarante"] = "1"
        self.sost, errori_sost = SO.leggi(self.d, ddec)
        for cod, perc, msg, fonte in errori_sost:
            self.err(cod, perc, msg, fonte)
        tipo_dich = SO.tipo_dichiarazione_xml(self.sost)
        tipo_dich["Devoluzione"] = self.devoluzione_fr()
        cas = FR.leggi(self, ddec)           # caselle del frontespizio: legge estera, eventi eccezionali, opzione, inventario...
        if cas["legge_estera"]:
            tipo_dich["Devoluzione"]["LeggeEstera"] = "1"
        if cas["eventi"]:
            tipo_dich["EventiEccezionali"] = cas["eventi"]
        if cas["data_opzione"]:
            tipo_dich["DataOpzione"] = cas["data_opzione"]
        if cas["beneficio"]:
            ben["AccettazioneConBeneficioInventario"] = "1"
        self.casi_particolari = cas["casi"]
        fr = {"CodiceFiscaleDefunto": cfd, "TipoDichiarazione": tipo_dich}
        if ben:
            fr["Beneficiari"] = ben
        ulteriori = {"DataDecesso": F.data(dft["data_decesso"]) if ddec else None, "StatoCivile": stato_civ}
        if cas["res_defunto"]:
            ulteriori["ResidenzaEstera"] = cas["res_defunto"]
        fr["DatiDefunto"] = {"DatiAnagrafici": ana_d, "UlterioriDati": ulteriori}
        fr["Presentatore"] = pres_x
        fr["FirmaModello"] = firma
        imp = self.impegno(pres_x["CodiceFiscale"] if pres_x else None)
        if imp:
            fr["ImpegnoATrasmettere"] = imp
        return fr

    def impegno(self, cf_presentatore: str | None) -> dict | None:
        """ImpegnoATrasmettere: obbligatorio se TipoFornitore=10 e CF fornitore diverso dal richiedente; altrimenti
        non puo' essere presente (annotazione Frontespizio/ImpegnoATrasmettere)."""
        ctx = self.ctx
        fonte = FO.fonte_annotazione("Frontespizio/ImpegnoATrasmettere")
        try:
            cff = F.cf(ctx.cf_fornitore)
        except F.ValoreXml as e:
            self.err("VALORE_NON_VALIDO", "contesto.cf_fornitore", str(e), FO.fonte_spec(13, "§3.2.1"))
            return None
        if len(cff) == 16 and not ID.cf_persona_fisica_valido(cff):
            msg = (f"codice fiscale del fornitore {cff}: carattere di controllo errato (atteso "
                   f"{ID.carattere_controllo(cff[:15])})")
            if ctx.scopo == "completo":
                self.err("VALORE_NON_VALIDO", "contesto.cf_fornitore", msg, ID.FONTE_CF)
            else:
                self.avv("CF_FORNITORE_NON_VALIDO", "contesto.cf_fornitore", msg + ": ammesso solo nella bozza tecnica",
                         ID.FONTE_CF)
        self.fornitore_diverso_da_dichiarante = bool(cf_presentatore) and cff != cf_presentatore
        if ctx.tipo_fornitore == "10" and cf_presentatore and cff != cf_presentatore:
            if ctx.impegno_codice not in ("1", "2") or not ctx.data_impegno:
                self.err("DATO_MANCANTE", "contesto.impegno", "con TipoFornitore 10 e fornitore diverso dal dichiarante "
                         "servono codice impegno (1|2) e data impegno", fonte)
                return None
            try:
                di = F.data(ctx.data_impegno, non_oltre=self.oggi)
            except F.ValoreXml as e:
                self.err("VALORE_NON_VALIDO", "contesto.data_impegno", str(e), fonte)
                return None
            return {"CFintermediario": cff, "ImpegnoATrasmettere": ctx.impegno_codice, "DataImpegno": di,
                    "FirmaIntermediario": "1"}
        if ctx.tipo_fornitore == "1" and cf_presentatore and cff != cf_presentatore:
            self.avv("FORNITORE_DIVERSO_DAL_DICHIARANTE", "contesto.cf_fornitore", "TipoFornitore 1 indica il soggetto "
                     "che invia la propria dichiarazione, ma il codice fiscale del fornitore e' diverso da quello del "
                     "dichiarante: verificare (per un intermediario usare TipoFornitore 10)",
                     FO.fonte_annotazione("Intestazione/TipoFornitore") + "; " + FO.fonte_spec(15, "§3.3.1"))
        if ctx.impegno_codice or ctx.data_impegno:
            self.err("REGOLA_IMPEGNO", "contesto.impegno", "l'impegno alla trasmissione si indica solo con TipoFornitore "
                     "10 e fornitore diverso dal dichiarante", fonte)
        return None

    # ---------------------------------------------------------------- controlli finali
    def campi_non_esportati(self):
        """Nessuna perdita silenziosa: ogni campo valorizzato e non usato finisce in non_supportato."""
        for coll in ("persone", "beni", "devoluzioni", "passivita", "documenti_ref"):
            for e in self.d.get(coll, []):
                if e["id"] in self.scartati:
                    continue
                usati = self.usati.get(e["id"], set())
                for k, v in e.items():
                    if k in ("id", "_origine") or v in (None, "") or k in usati:
                        continue
                    if V.e_stato(v) and v["stato"] in ("assente", "non_applicabile"):
                        continue
                    self.ns.append(f"{coll}[{e['id']}].{k}: dato presente ma non serializzato da questa versione")
        for eid, campi in sorted(self.interni.items()):
            coll = next((c for c in ("persone", "beni") if any(x["id"] == eid for x in self.d.get(c, []))), "?")
            for k in sorted(campi):
                self.avv("DATO_INTERNO_NON_ESPORTATO", f"{coll}[{eid}].{k}", "campo di lavoro interno senza elemento "
                         "corrispondente nel tracciato: non esportato (classificazione in docs/regole/mappa_xsd.md)",
                         "docs/regole/mappa_xsd.md")
        if self.d.get("note"):
            self.avv("DATO_INTERNO_NON_ESPORTATO", "note", "note interne della pratica: non fanno parte del dichiarato",
                     "src/successioni/schema.py (SEZIONI)")
        self.ns.extend(f"{p}: chiave non gestita" for p in SUP.chiavi_non_gestite(self.d))

    def quadri_attivi(self):
        att = Q.attivi(self.d)
        for q in sorted(att):
            if q in Q.SEMPRE_ATTIVI or q in QUADRI_ESPORTABILI:
                continue
            self.ns.append(f"quadro[{q}]: selezionato nella pratica ma non serializzato da questa versione")
        for coll in ("persone", "beni", "passivita", "documenti_ref"):
            for e in self.d.get(coll, []):
                q = Q.quadro_di(coll, e)
                if q and q not in att and q not in Q.SEMPRE_ATTIVI:
                    self.err("DATI_IN_QUADRO_NON_ATTIVO", f"{coll}[{e['id']}]", f"dati nel quadro {q} non selezionato: "
                             "attivare il quadro o rimuovere i dati", "src/successioni/quadri.py (registro dei quadri)")

    def quadri_obbligatori(self, presenti: list[str]):
        """Quadri resi obbligatori dalle annotazioni XSD ma non generati (motivo gia' registrato o dati mancanti)."""
        gia = {e.percorso for e in self.mancanti}
        if self.integrativa:     # codice 3: il quadro EG e' obbligatorio, EA/EF/EH non devono essere presenti
            if "EG" not in presenti and not any(p.startswith("quadro[EG]") for p in gia):
                self.mancanti.append(Errore("QUADRO_OBBLIGATORIO_NON_SUPPORTATO", "quadro[EG]", "dichiarazione integrativa (codice 3): "
                                            "il quadro EG con la documentazione e' obbligatorio ma non e' stato generato (nessun "
                                            "allegato)", FO.fonte_annotazione("QuadroEG")))
            return
        immobili = any(q in presenti for q in ("EB", "EC"))
        dal_2025 = self.data_decesso is not None and self.data_decesso >= date(2025, 1, 1)
        if (dal_2025 or ("EA" in presenti and immobili)) and "EF" not in presenti and "quadro[EF]" not in gia:
            self.mancanti.append(Errore("QUADRO_OBBLIGATORIO_NON_SUPPORTATO", "quadro[EF]",
                                        "il quadro EF (liquidazione imposte; dal 2025 anche sezione V-bis imposta di "
                                        "successione) e' obbligatorio per questa pratica ma non e' stato generato",
                                        FO.fonte_annotazione("QuadroEF") + "; " +
                                        FO.fonte_annotazione("QuadroEF/SezioneVBis_ImpostaSuccessione")))
        if "EA" in presenti and "EG" not in presenti and not any(p.startswith("quadro[EG]") for p in gia):
            self.mancanti.append(Errore("QUADRO_OBBLIGATORIO_NON_SUPPORTATO", "quadro[EG]", "il quadro EG e' obbligatorio "
                                        "in presenza del quadro EA ma non e' stato generato (nessun allegato)",
                                        FO.fonte_annotazione("QuadroEG")))
        if self.codice_carica not in ("5", "6", "7") and "EH" not in presenti:
            self.mancanti.append(Errore("QUADRO_OBBLIGATORIO_NON_SUPPORTATO", "quadro[EH]", "il quadro EH e' obbligatorio "
                                        "(dichiarazione non integrativa, codice carica diverso da 5, 6, 7) ma non e' "
                                        "stato generato", FO.fonte_annotazione("QuadroEH")))

    # ---------------------------------------------------------------- orchestrazione
    def esegui(self) -> EsitoExport:
        ctx = self.ctx
        if ctx.scopo not in SCOPI:
            self.err("CONTESTO_NON_VALIDO", "contesto.scopo", f"valori ammessi: {SCOPI}", "docs/CONTRATTI_MODULI.md")
        if ctx.tipo_fornitore not in ("1", "10"):
            self.err("VALORE_NON_VALIDO", "contesto.tipo_fornitore", "TipoFornitore ammette 1 o 10",
                     FO.fonte_spec(15, "§3.3.1"))
        if not isinstance(ctx.identificativo, str) or not _ID_DICH.fullmatch(ctx.identificativo):
            self.err("VALORE_NON_VALIDO", "contesto.identificativo", "5 cifre, non tutte zero (Identificativo_Type)",
                     "fornitura_v2.xsd Identificativo_Type")
        self.diritto_bene: dict[str, str] = {}
        self.valore_beni: dict[str, int] = {}
        #: titoli EO tipo 3: compresi in valore_beni (EE3 = Valore + ValoreEsente) ma fuori dall'imponibile
        self.valore_esente_beni: dict[str, int] = {}
        self.quadro_bene: dict[str, str] = {}
        self.tipo_cespite: dict[str, str] = {}
        self.quota_valore: dict = {}
        self.quota_passivo: dict = {}
        self.valore_passivita: dict[str, int] = {}
        self.scartati: set[str] = set()
        self.tipo_ea, self.codice_carica, self.data_decesso = {}, None, None
        self.comune_bene: dict[str, str] = {}
        self.righe_dev: dict[str, dict] = {}
        self.persona_dev: dict[str, str] = {}
        self.soggetti_ea: dict[str, dict] = {}
        self.handicap_ea: dict[str, bool] = {}
        self.fornitore_diverso_da_dichiarante = False
        self.totale_da_versare = 0
        self.sost = None   # dichiarazione sostitutiva (telematico/sostitutiva.py)
        self.estero_bene: dict[str, bool] = {}   # beni sedenti all'estero (immobili con provincia EE o casella «bene sito all'estero»)
        self.imposta_estera: dict[str, int] = {}  # imposta versata all'estero per bene (euro interi): richiede EG4
        self.rinunce: dict[str, dict | None] = {}   # rinunciatari EA -> estremi di registrazione (EH rigo 8)
        self.terreni_vf: dict[str, dict] = {}   # reddito dominicale, quota del defunto e tipologia dei terreni EB (valori fiscali, EF1/EF9)
        self.defunto = self.presentatore = None
        self.testamento_x, self.test_reg = None, None
        self.eh_navi, self.eh_aeromobili, self.ei_beni = [], [], []
        PC.inizializza(self)
        RA.inizializza(self)
        AG.inizializza(self)

        self.integrativa = SO.e_integrativa(self.d)
        if self.integrativa:
            self.d = FR.riduci_per_integrativa(self)    # codice 3: solo frontespizio ed EG
        self.classifica_persone()
        if self.integrativa:
            self.ea = []     # il presentatore resta nel frontespizio ma non compare nel quadro EA (assente con il codice 3)
        self.ordina_ea()
        qea = self.quadro_ea()
        self.quote_legge = None
        if SUP.dich(self.d, "devoluzione_per_testamento") is True:
            pass  # con testamento le quote non sono quelle di legge (annotazioni Quota/CodiceDiritto_Rip): nessun controllo
        elif SUP.dich(self.d, "legge_estera") is True:
            pass  # legge straniera: le quote non sono quelle dell'allegato 5 (annotazioni Quota: «se legge estera = 0»)
        elif self.ea and all(self.grado_ea.get(p["id"]) for p in self.ea):
            # i rinunciatari non sono beneficiari di quote: restano fuori dal calcolo (e dalle devoluzioni)
            attivi = [p for p in self.ea if p["id"] not in self.rinunce]
            self.quote_legge = DL.quote_di_legge({p["id"]: self.grado_ea[p["id"]] for p in attivi},
                                                 {p["id"]: self.tipo_ea.get(p["id"]) for p in attivi}, dict(self.rapp_ea))                 if attivi else None
            if self.quote_legge is None:
                self.avv("QUOTE_DI_LEGGE_NON_VERIFICATE", "quadro[EA]", "configurazione di eredi non coperta dal "
                         "controllo delle quote di legge (coperti: figli, coniuge, genitori e fratelli nelle combinazioni delle tabelle di p. 69-70 dell'Allegato 5): le quote "
                         "di devoluzione non sono verificate dall'export", DL.FONTE)
                self.mancanti.append(Errore("QUOTE_DI_LEGGE_NON_VERIFICATE", "quadro[EA]",
                    "configurazione di eredi non coperta dalla verifica delle quote di legge: "
                    "conservabile come bozza tecnica, non finalizzabile", DL.FONTE))
        beni = self.d.get("beni", [])
        per_q: dict[str, list] = {"EB": [], "EC": [], "EL": [], "EM": [], "EN": [], "EO": [], "EP": [], "EQ": [], "ER": []}
        for b in beni:
            self.usa(b, "tipo")
            q = Q.quadro_di("beni", b)
            per_q[q].append(b)
            self.quadro_bene[b["id"]] = q
            for campo in ("provenienza", "data_visura"):   # dati interni: non esportati
                if b.get(campo) not in (None, ""):
                    self.usa(b, campo)
                    self.interno(b, campo)
            if q in ("EB", "EC") and b.get("descrizione") not in (None, ""):
                self.usa(b, "descrizione")
                self.interno(b, "descrizione")
        qeb = self.quadro_beni("EB", sorted(per_q["EB"], key=_chiave_immobile), self.riga_eb)
        qec = self.quadro_beni("EC", sorted(per_q["EC"], key=_chiave_immobile), self.riga_ec)
        qel = self.quadro_beni("EL", sorted(per_q["EL"], key=_chiave_immobile), self.riga_el)
        qem = self.quadro_beni("EM", sorted(per_q["EM"], key=_chiave_immobile), self.riga_em)
        qen = self.quadro_beni("EN", sorted(per_q["EN"], key=lambda b: (str(b.get("descrizione") or ""), b["id"])), self.riga_en)
        qeo = self.quadro_beni("EO", sorted(per_q["EO"], key=lambda b: (
            str(SUP.attr(self.d, "beni", b, "tipo_titolo") or ""), str(b.get("descrizione") or ""), b["id"])), self.riga_eo)
        qep = self.quadro_beni("EP", sorted(per_q["EP"], key=lambda b: (
            str(b.get("marca_modello") or ""), b["id"])), self.riga_ep)
        qeq = self.quadro_beni("EQ", sorted(per_q["EQ"], key=lambda b: (
            str(b.get("numero_iscrizione") or ""), b["id"])), self.riga_eq)
        qer = self.quadro_beni("ER", sorted(per_q["ER"], key=lambda b: (
            str(SUP.attr(self.d, "beni", b, "tipo_cespite") or ""), str(b.get("descrizione") or ""), b["id"])), self.riga_er)
        PC.valida(self)
        RA.valida(self)
        AG.valida(self)
        if self.ea:
            assegnati = {d.get("persona_id") for d in self.d.get("devoluzioni", [])}
            for p in self.ea:
                if p["id"] not in assegnati and p["id"] not in self.rinunce:     # i rinunciatari non hanno devoluzioni
                    self.err("SOGGETTO_SENZA_DEVOLUZIONE", f"persone[{p['id']}]", "ogni soggetto del quadro EA deve "
                             "comparire nella devoluzione di almeno un bene", FO.fonte_annotazione("QuadroEA/Modulo/Soggetto"))
        elif self.d.get("devoluzioni"):
            self.err("DEVOLUZIONE_SENZA_EA", "devoluzioni", "la sezione devoluzione non puo' essere presente senza "
                     "quadro EA", FO.fonte_annotazione("QuadroEB/Modulo/Terreni/DevoluzioneEB/Devoluzione"))
        qed = self.quadro_ed()
        self.risolvi_progressivi(qed)
        qee = self.quadro_ee()
        corpo = {"QuadroEA": qea, "QuadroEB": qeb, "QuadroEC": qec, "QuadroED": qed, "QuadroEE": qee, "QuadroEL": qel, "QuadroEM": qem, "QuadroEN": qen, "QuadroEO": qeo, "QuadroEP": qep, "QuadroEQ": qeq, "QuadroER": qer}
        presenti = [k[6:] for k, v in corpo.items() if v]
        fr = self.frontespizio(presenti)
        if fr is not None and (("EL" in presenti or "EM" in presenti) and not ("EB" in presenti or "EC" in presenti)
                               or getattr(self, "casi_particolari", None)):
            # annotazione CasiParticolari: obbligatorio in assenza dei quadri EB, EC ed in presenza di EL o EM (volture non richieste);
            # facoltativo negli altri casi su richiesta del dichiarante (Fascicolo I p. PDF 15, «non voler dar corso alle volture»)
            fr["CasiParticolari"] = {"CasiParticolari": "1", "FirmaDichiarante": "1"}
        intest = {"TipoFornitore": ctx.tipo_fornitore}
        if ctx.spazio_utente:
            try:
                intest["SpazioUtente"] = F.an(ctx.spazio_utente)
            except F.ValoreXml as e:
                self.err("VALORE_NON_VALIDO", "contesto.spazio_utente", str(e), FO.fonte_spec(15))
        # quadri EG, EH, EF (EF dopo una prima serializzazione: il calcolo V-bis legge il file dichiarato)
        liq = fr is not None and ctx.quadri_liquidazione
        qeg = EFGH.quadro_eg(self) if liq else None
        qeh = EFGH.quadro_eh(self, fr, qeg) if liq and not self.integrativa else None
        corpo["QuadroEI_new"] = EFGH.quadro_ei(self, fr) if fr is not None and not self.integrativa else None
        xml_pre = None
        if liq and not self.errori and not self.ns and not self.integrativa:   # codice 3: nessun quadro EF da calcolare
            dich_pre = {"@identificativo": ctx.identificativo, "Frontespizio": fr}
            dich_pre.update({k: v for k, v in corpo.items() if v})
            try:
                xml_pre = serializza(F.cf(ctx.cf_fornitore), intest, dich_pre)
            except (M.ErroreModello, F.ValoreXml) as e:
                self.err("ERRORE_SERIALIZZAZIONE", "/", str(e), FO.fonte_xsd())
        qef = EFGH.quadro_ef(self, xml_pre) if fr is not None and xml_pre is not None else None
        corpo.update({"QuadroEF": qef, "QuadroEG": qeg, "QuadroEH": qeh})
        presenti = [("EI" if k == "QuadroEI_new" else k[6:]) for k, v in corpo.items() if v]
        if fr is not None:
            fr["FirmaModello"] = {**{f"Casella{q}": "1" for q in presenti}, "FirmaDichiarante": "1"}
        if fr is not None and qef is not None:
            ver = EFGH.versamento(self, (fr.get("Presentatore") or {}).get("CodiceFiscale"))
            if ver:
                fr["Versamento"] = ver
            if self.totale_da_versare:
                # annotazione Frontespizio/ImportoDaVersare; il componente ufficiale lo confronta con EF19 + EF24 col. 1
                # e 2 (QuadroEF.calcolaTotaleDaVersareF24, ispezione javap; messaggio 3376 se diverso)
                fr["ImportoDaVersare"] = F.euro_centesimi(self.totale_da_versare)
        self.campi_non_esportati()
        self.quadri_attivi()
        if ctx.quadri_liquidazione:
            self.quadri_obbligatori(presenti)
        else:
            self.mancanti.append(Errore("QUADRI_LIQUIDAZIONE_ESCLUSI", "quadro[EF,EG,EH]", "esportazione per uso "
                                        "interno (calcolo): quadri EF, EG, EH non generati", "contesto.quadri_liquidazione"))
        ns = sorted(set(self.ns))
        esito = EsitoExport(xml=None, errori=self.errori, non_supportato=ns, mappa=self.mappa, avvisi=self.avvisi,
                            quadri_mancanti=self.mancanti, completo=False)
        if self.errori or ns:
            return esito
        dich = {"@identificativo": ctx.identificativo, "Frontespizio": fr}
        dich.update({k: v for k, v in corpo.items() if v})
        try:
            xml = serializza(F.cf(ctx.cf_fornitore), intest, dich)
        except M.ErroreModello as e:  # errore di programma: struttura non prevista dallo schema
            self.err("ERRORE_SERIALIZZAZIONE", "/", str(e), FO.fonte_xsd())
            return esito
        err_xsd = X.valida_xsd(xml)
        if err_xsd:
            esito.errori = self.errori + _riferisci(err_xsd, self.mappa)
            return esito
        from ..documenti.dimensioni import verifica_fornitura
        dimensioni = verifica_fornitura({"xml": xml}, richiedi_xml=True)
        if dimensioni:
            esito.errori.extend(dimensioni)
            return esito
        self.avv("MISURA_FORNITURA_ASSUNTA", "fornitura", "limite di 40 MB misurato sull'XML effettivo "
                 "compresso DEFLATE, byte decimali: algoritmo/contenitore del canale reale da collaudare",
                 FO.fonte_spec(3, "limite 40 MB compressi"))
        esito.completo = not self.mancanti
        esito.impronta_xml = hashlib.sha256(xml).hexdigest()
        if esito.completo or ctx.scopo == "bozza_tecnica":
            esito.xml = xml
        return esito


_RIGA = {"EB": "Terreni", "EC": "Fabbricati", "EL": "TerreniTavolare", "EM": "FabbricatiTavolare", "EN": "Aziende", "EO": "Titoli", "EP": "Aeromobili", "EQ": "Navi", "ER": "Rendite"}
_PER_MODULO = {"EB": 2, "EC": 2, "EL": 2, "EM": 1, "EN": 2, "EO": 3, "EP": 1, "EQ": 2, "ER": 4}
_XP_DICH = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"


def _naturale(s) -> str:
    s = str(s or "").strip().upper()
    return s.zfill(12) if s.isdigit() else s


def _chiave_immobile(b: dict):
    return (str((b.get("comune") or "")).upper(), _naturale(b.get("sezione")), _naturale(b.get("foglio")),
            _naturale(b.get("particella")), _naturale(b.get("subalterno")), b["id"])


def serializza(cf_fornitore: str, intestazione: dict, dichiarazione: dict) -> bytes:
    """Busta tm:Messaggio + suc:Fornitura; ordine e namespace dei figli ricavati dagli XSD (modello_xsd)."""
    tm, suc = FO.NS_TM, FO.NS_SUC
    root = etree.Element(f"{{{tm}}}Messaggio", nsmap=FO.NSMAP)
    ti = etree.SubElement(root, f"{{{tm}}}Intestazione")
    etree.SubElement(ti, f"{{{tm}}}CodiceFiscaleFornitore").text = cf_fornitore
    cont = etree.SubElement(root, f"{{{tm}}}Contenuto")
    cont.set("CodiceFornitura", "SUC13")  # Specifiche p. 4 e p. 14
    forn = etree.SubElement(cont, f"{{{suc}}}Fornitura")
    el_forn, ctx_forn = M.modello().el[(suc, "Fornitura")]
    M.costruisci(etree.SubElement(forn, f"{{{suc}}}Intestazione"), _ct_locale(el_forn, ctx_forn, "Intestazione"),
                 intestazione, "/Fornitura/Intestazione")
    M.costruisci(etree.SubElement(forn, f"{{{suc}}}Dichiarazione"), M.radice_suc(), dichiarazione,
                 "/Fornitura/Dichiarazione")
    corpo = etree.tostring(root, encoding="UTF-8", xml_declaration=False, pretty_print=True)
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + corpo


def _ct_locale(el, ctx: "M.CT", nome: str) -> "M.CT":
    """complexType anonimo dell'elemento locale ``nome`` dentro un elemento globale (qui suc:Fornitura)."""
    xs = "{http://www.w3.org/2001/XMLSchema}"
    for e in el.iter(f"{xs}element"):
        if e.get("name") == nome:
            return M.CT(e.find(f"{xs}complexType"), ctx.tns, ctx.nsmap)
    raise M.ErroreModello(f"elemento {nome} non trovato")


def _norm_xpath(p: str) -> list[str]:
    out = []
    for seg in p.strip("/").split("/"):
        out.append(seg if seg.endswith("]") else seg + "[1]")
    return out


def _riferisci(errori: list[Errore], mappa: dict) -> list[Errore]:
    """Associa gli errori XSD (XPath) all'elemento interno della mappa con il prefisso piu' lungo."""
    voci = [(k, _norm_xpath(v["xpath"]), v) for k, v in mappa.items() if v.get("xpath")]
    out = []
    for e in errori:
        segs = _norm_xpath(e.percorso) if e.percorso.startswith("/") else []
        best = None
        for k, xp, v in voci:
            if len(xp) <= len(segs) and segs[:len(xp)] == xp and (best is None or len(xp) > len(best[1])):
                best = (k, xp, v)
        if best and best[2].get("coll"):
            ident = best[2].get("id", best[0])
            e = Errore(e.codice, f"{best[2]['coll']}[{ident}] @ {e.percorso}", e.messaggio, e.fonte)
        out.append(e)
    return out


def esporta_xml(dati: dict, contesto: ContestoExport) -> EsitoExport:
    """Esporta la pratica nel tracciato SUC13. Vedi la documentazione del modulo per perimetro e limiti."""
    return _Export(dati, contesto).esegui()
