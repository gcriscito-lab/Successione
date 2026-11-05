"""Pagamenti: crediti d'imposta (EF7, EF13, EF18bis col. 4 e sezione III del quadro EH) e sanzioni/interessi indicati dal
professionista (EF, Sezione VI). Scheda: docs/regole/pagamenti_crediti.md.

Fonti: XSD ``fornituraSUC13_v1.xsd`` (annotazioni di ``QuadroEF`` ``CreditoImposta`` x3, ``ImpostaCalcolata`` e
``SezioneVI_SanzioniInteressi``; ``QuadroEH/PrimoModulo/SezioneIII_CreditoImposta``; ``TipoImposta_Type``); Fascicolo I pp. PDF 41-44
(EF7, EF8, EF13, EF14), p. 47 (EF18bis colonne 3 e 4), p. 49 (Sezione VI: sanzioni e interessi).

I crediti sono quelli della Legge 448/1998 art. 7 c. 2 e del DL 73/2021 art. 64 c. 7 («prima casa under 36»): dati ``credito_*``
indicati dal professionista in ``opzioni.telematico.dichiarazione``. Sanzioni e interessi sono DATI DICHIARATI dal professionista, mai
calcolati: il tasso legale per anno non e' nelle fonti.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .. import valori as V
from . import fonti as FO
from . import formati as F
from . import supplemento as SUP

_PERC = "opzioni.telematico.dichiarazione."
CHIAVI_CREDITI = ("credito_ipotecaria", "credito_catastale", "credito_successione", "credito_tipologia", "credito_imposta",
                  "credito_acquisto", "credito_vendita", "credito_tipologia_2", "credito_imposta_2", "credito_acquisto_2", "credito_vendita_2")
#: tributo -> (elemento di SezioneVI_SanzioniInteressi, rigo)
TRIBUTI = {"ipotecaria": ("ImpostaIpotecaria", "EF20"), "catastale": ("ImpostaCatastale", "EF21"),
           "tassa_ipotecaria": ("TassaIpotecaria", "EF22"), "bollo": ("ImpostaBollo", "EF23"),
           "successione": ("ImpostaSuccessione", "EF23bis")}
CHIAVI_SANZIONI = tuple(f"{tipo}_{t}" for t in TRIBUTI for tipo in ("sanzione", "interessi"))
FONTE_CREDITI = ("fornituraSUC13_v1.xsd (CreditoImposta di EF7/EF13/EF18bis; QuadroEH/PrimoModulo/SezioneIII_CreditoImposta); "
                 "Fascicolo I pp. PDF 41-42, 44 e 47")
FONTE_SANZIONI = "fornituraSUC13_v1.xsd (SezioneVI_SanzioniInteressi); Fascicolo I p. PDF 49 (Sezione VI)"


@dataclass(frozen=True)
class Crediti:
    ipotecaria: int            # EF7
    catastale: int             # EF13
    successione: int           # EF18bis colonna 4
    righe: tuple               # righi di acquisto/vendita della sezione III del quadro EH (1 o 2): dict con tipologia, imposta, acquisto, vendita

    @property
    def totale(self) -> int:
        return self.ipotecaria + self.catastale + self.successione


def _intero(x, chiave: str) -> int:
    v = SUP.dich(x.d, chiave)
    if v in (None, "", False):
        return 0
    try:
        d = V.parse_importo(v)
    except V.ValoreNonValido as e:
        x.err("VALORE_NON_VALIDO", _PERC + chiave, str(e), FONTE_CREDITI)
        return 0
    if d < 0 or d != d.to_integral_value():
        x.err("VALORE_NON_VALIDO", _PERC + chiave, f"{d}: euro interi non negativi (tracciato DatoNP_Type)", FONTE_CREDITI)
        return 0
    return int(d)


def _data_ord(reg: dict) -> str:
    d = reg["DataRegistrazione"]          # GGMMAAAA
    return d[4:] + d[2:4] + d[:2]


def _riga(x, suff: str, usati: int, fonte: str) -> dict | None:
    """Un rigo della sezione III: tipologia, imposta, registrazione dell'acquisto e (facoltativa) della vendita."""
    tip = SUP.dich(x.d, "credito_tipologia" + suff)
    if tip in (None, ""):
        x.err("DATO_MANCANTE", _PERC + "credito_tipologia" + suff, "con il credito d'imposta indicare la tipologia di ogni rigo: "
              "1 registro, 2 IVA, 3 IVA «credito Decreto Sostegni-bis»", fonte)
        return None
    if str(tip) not in ("1", "2", "3"):
        x.err("VALORE_NON_VALIDO", _PERC + "credito_tipologia" + suff, f"{tip!r}: ammessi 1, 2, 3 (TipoImposta_Type)", fonte)
        return None
    imposta = _intero(x, "credito_imposta" + suff) or (usati if not suff else 0)
    if not imposta:
        x.err("DATO_MANCANTE", _PERC + "credito_imposta" + suff, "indicare l'imposta (registro o IVA) di questo rigo (annotazione XSD "
              "«campo obbligatorio»)", fonte)
        return None
    acq = x.estremi_registrazione(SUP.dich(x.d, "credito_acquisto" + suff), _PERC + "credito_acquisto" + suff, fonte)
    ven = None
    if SUP.dich(x.d, "credito_vendita" + suff) not in (None, ""):
        ven = x.estremi_registrazione(SUP.dich(x.d, "credito_vendita" + suff), _PERC + "credito_vendita" + suff, fonte)
        if ven is not None and acq is not None and _data_ord(ven) < _data_ord(acq):
            x.err("DATI_INCOERENTI", _PERC + "credito_vendita" + suff + ".data_registrazione", "la data di vendita non puo' essere "
                  "anteriore a quella di acquisto (annotazione XSD di RegistrazioneVendita)", fonte)
            ven = None
    if acq is None:
        return None
    return {"tipologia": str(tip), "imposta": imposta, "acquisto": acq, "vendita": ven}


def crediti(x) -> Crediti | None:
    """Crediti d'imposta dichiarati (memorizzati sull'esportazione: gli errori si registrano una sola volta)."""
    if hasattr(x, "_crediti"):
        return x._crediti
    x._crediti = None
    ip, cat, succ = (_intero(x, k) for k in ("credito_ipotecaria", "credito_catastale", "credito_successione"))
    altri = [k for k in CHIAVI_CREDITI[3:] if SUP.dich(x.d, k) not in (None, "")]
    if not (ip or cat or succ):
        if altri:
            x.err("DATO_MANCANTE", _PERC + "credito_ipotecaria", "indicati dati del credito d'imposta senza l'importo da utilizzare "
                  "(EF7, EF13 o EF18bis colonna 4)", FONTE_CREDITI)
        return None
    fonte = FO.fonte_annotazione("QuadroEH/Modulo/SezioneIII_CreditoImposta") + "; " + FONTE_CREDITI
    usati = ip + cat + succ
    r1 = _riga(x, "", usati, fonte)
    if r1 is None:
        return None
    righe = [r1]
    if r1["tipologia"] in ("1", "2"):
        # annotazione XSD di Modulo/SezioneIII_CreditoImposta: «in presenza di tipologia di imposta = 1 o 2 devono essere presenti
        # almeno 2 righi di acquisti con tipologia 1 o 2» (Legge 448/1998: acquisto agevolato, vendita, nuovo acquisto; controllo
        # ufficiale 2.3.1, messaggio 3386)
        r2 = _riga(x, "_2", usati, fonte)
        if r2 is None:
            return None
        if r2["tipologia"] not in ("1", "2"):
            x.err("VALORE_NON_VALIDO", _PERC + "credito_tipologia_2", "con il primo rigo di tipologia 1 o 2 anche il secondo deve essere "
                  "di tipologia 1 o 2", fonte)
            return None
        righe.append(r2)
        if usati > min(r["imposta"] for r in righe):
            x.err("VALORE_NON_VALIDO", _PERC + "credito_imposta", f"il credito utilizzato ({usati}) non puo' superare la minore fra le "
                  f"imposte dei due acquisti ({min(r['imposta'] for r in righe)}): Fascicolo I pp. PDF 41-42", fonte)
            return None
    else:
        if any(SUP.dich(x.d, k + "_2") not in (None, "") for k in CHIAVI_CREDITI[3:]):
            x.err("DATI_INCOERENTI", _PERC + "credito_tipologia_2", "il credito di tipologia 3 (IVA Sostegni-bis) ha un solo rigo",
                  fonte)
            return None
        if usati > r1["imposta"]:
            x.err("VALORE_NON_VALIDO", _PERC + "credito_imposta", f"il credito utilizzato ({usati}) non puo' superare l'imposta "
                  f"indicata ({r1['imposta']})", fonte)
            return None
    x._crediti = Crediti(ip, cat, succ, tuple(righe))
    return x._crediti


def _sez(r: dict, firma: bool) -> dict:
    sez = {"TipologiaImposta": r["tipologia"], "Imposta": str(r["imposta"]), "RegistrazioneAcquisto": dict(r["acquisto"])}
    if r["vendita"]:
        sez["RegistrazioneVendita"] = dict(r["vendita"])
    if firma:
        sez["FirmaDichiarante"] = "1"
    return sez


def sezioni_eh(x) -> tuple[dict | None, dict | None]:
    """EH, sezione III «credito d'imposta»: (primo modulo, secondo rigo nel primo ``Modulo`` successivo). Il dichiarante che richiede
    l'utilizzo del credito la compila (Fascicolo I p. PDF 42); non puo' essere presente senza EF7 (annotazione XSD)."""
    c = crediti(x)
    if c is None:
        return None, None
    if c.ipotecaria == 0:
        x.err("DATI_INCOERENTI", _PERC + "credito_ipotecaria", "la sezione III del quadro EH richiede il rigo EF7 (credito per "
              "l'imposta ipotecaria): il credito si indica sempre prima sull'ipotecaria, l'eccedenza passa a EF13 e a EF18bis col. 4 "
              "(annotazione XSD «non deve essere presente in assenza del campo EF7»; Fascicolo I p. PDF 42)", FONTE_CREDITI)
        return None, None
    return _sez(c.righe[0], True), (_sez(c.righe[1], False) if len(c.righe) > 1 else None)


def importo_vp(x, chiave: str) -> Decimal | None:
    """Sanzione o interessi dichiarati: importo non negativo con al massimo due decimali (DatoVP_Type); ``None`` se non indicato."""
    v = SUP.dich(x.d, chiave)
    if v in (None, ""):
        return None
    try:
        d = v if isinstance(v, Decimal) else V.parse_importo(v)
        F.euro_centesimi(d)
    except (V.ValoreNonValido, F.ValoreXml) as e:
        x.err("VALORE_NON_VALIDO", _PERC + chiave, str(e), FONTE_SANZIONI)
        return None
    return d


def sanzioni(x) -> dict[str, tuple[Decimal | None, Decimal | None]]:
    """tributo -> (sanzione, interessi) dichiarati dal professionista; solo i tributi con almeno un importo indicato."""
    if hasattr(x, "_sanzioni"):
        return x._sanzioni
    out: dict = {}
    for t in TRIBUTI:
        s, i = importo_vp(x, f"sanzione_{t}"), importo_vp(x, f"interessi_{t}")
        if s is not None or i is not None:
            out[t] = (s, i)
    x._sanzioni = out
    return out


def sezione_vi(x, presenti: dict[str, bool]) -> tuple[dict | None, Decimal]:
    """SezioneVI_SanzioniInteressi e totale da aggiungere a EF19/ImportoDaVersare (EF24 col. 1 + col. 2). ``presenti``: tributo ->
    True se il rigo «da versare» corrispondente c'e' (vincolo XSD: «puo' essere presente solo se e' presente il campo ...»)."""
    dich = sanzioni(x)
    if not dich:
        return None, Decimal(0)
    sez: dict = {}
    tot_s = tot_i = Decimal(0)
    for t, (elem, rigo) in TRIBUTI.items():
        if t not in dich:
            continue
        if not presenti.get(t):
            x.err("DATI_INCOERENTI", _PERC + f"sanzione_{t}", f"sanzioni/interessi per {t.replace('_', ' ')} ({rigo}) senza il relativo "
                  "importo da versare: la sezione puo' essere presente solo con il rigo corrispondente (annotazioni XSD)",
                  FONTE_SANZIONI)
            continue
        s, i = dich[t]
        voce = {}
        if s is not None:
            voce[f"{elem}_Sanzioni"] = F.euro_centesimi(s)
            tot_s += s
        if i is not None:
            voce[f"{elem}_Interessi"] = F.euro_centesimi(i)
            tot_i += i
        sez[elem] = voce
    if not sez:
        return None, Decimal(0)
    tot = {}
    if tot_s or any(dich[t][0] is not None for t in dich):
        tot["TotaleDaVersare_Sanzioni"] = F.euro_centesimi(tot_s)
    if tot_i or any(dich[t][1] is not None for t in dich):
        tot["TotaleDaVersare_Interessi"] = F.euro_centesimi(tot_i)
    if tot:
        sez["TotaleDaVersare"] = tot
    return sez, tot_s + tot_i
