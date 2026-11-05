"""Quote di devoluzione per legge (successione legittima) - sottoinsieme coperto.

Fonte: ``Succ_FASCICOLO_I_Nov_23.pdf`` p. 69, "ALLEGATO 5 - DEVOLUZIONE" (artt. 565-585 cod. civ. come riportati
nell'allegato): "Al padre e alla madre succedono i figli ... in parti uguali"; "In mancanza di figli ..., di
ascendenti, di fratelli o sorelle, al coniuge si devolve l'intera eredita'"; tabella "Successioni legittime -
devoluzione": Coniuge + 1 figlio = 1/2 e 1/2; Coniuge + 2 o piu' figli = 1/3 al coniuge e 2/3 ai figli.

L'obbligo di applicarle viene dalle annotazioni XSD (fornituraSUC13_v1.xsd) degli elementi ``Devoluzione/Quota``
dei quadri EB/EC/ER e ``RipartizioneED/Ripartizione/Quota`` del quadro ED: "In presenza di devoluzione per legge ... se
nel Quadro EA i tipi soggetto sono tutti '1' (erede) o tutti '3' (chiamati) ... il campo quota deve essere compilato
in base al grado di parentela, come riportato nell'allegato 5 al modello" (per ED solo se il tipo passivita' e'
diverso da 1, 2, 11 e 12). Il controllo ufficiale 2.3.1 lo verifica (messaggi 3118 'Numero di soggetti presenti nella
sezione devoluzione diverso da quello degli Eredi aventi diritto' e 'Dati di devoluzione non coerenti con quelli
relativi agli Eredi', osservati eseguendo il componente in locale).

COPERTI (tabelle di p. 69-70 dell'Allegato 5; codici GradoParentela dell'XSD: 01 coniuge, 02 figlio/a, 03 genitore,
10 fratello/sorella germano, 11 unilaterale):
- solo figli (parti uguali); solo coniuge (intera eredita'); coniuge + figli (1/2 e 1/2 con un figlio, 1/3 e 2/3 con piu');
- senza figli: solo genitori (parti uguali); solo fratelli e sorelle (parti uguali, gli unilaterali la meta' dei germani);
- coniuge + genitori: 2/3 e 1/3; coniuge + fratelli: 2/3 e 1/3; coniuge + genitori + fratelli: 8/12, 3/12, 1/12;
- genitori + fratelli senza coniuge: tabella «Concorso del genitore/i con fratelli» (p. 70). Tutte le righe di quella tabella
  sono riprodotte dalla regola: genitore = 2 quote, germano = 2, unilaterale = 1, e ai genitori spetta almeno la meta'.
Tutto il resto (altri ascendenti, rappresentazione, parenti oltre i fratelli, gradi diversi, concorso di categorie che in
presenza di figli si escludono) -> ``None``: le quote NON vengono verificate e l'export lo segnala.
"""
from __future__ import annotations

from fractions import Fraction

FONTE = ("Succ_FASCICOLO_I_Nov_23.pdf p. 69 (Allegato 5 - Devoluzione); fornituraSUC13_v1.xsd, annotazione "
         "Devoluzione/Quota e RipartizioneED/Ripartizione/Quota (quote in base all'allegato 5)")
TIPI_PASSIVITA_LIBERE = {"1", "2", "11", "12"}  # annotazione RipartizioneED/Ripartizione/Quota


GRADI_RAPPRESENTANTE_RETTA = ("04", "06", "08")      # nipote, pronipote, figlio/a di pronipote (discendenti dei figli)
GRADI_RAPPRESENTANTE_COLLATERALE = ("15", "20", "27")  # nipote di zio, figlio/a di nipote, nipote di nipote (discendenti di fratelli)
GRADI_RAPPRESENTANTE = GRADI_RAPPRESENTANTE_RETTA + GRADI_RAPPRESENTANTE_COLLATERALE
FONTE_RAPPRESENTAZIONE = ("Succ_FASCICOLO_I_Nov_23.pdf pp. PDF 18-19 (successione per rappresentazione: si divide per stirpi e poi "
                          "fra i rappresentanti di ciascuna stirpe); fornituraSUC13_v1.xsd, annotazioni di "
                          "SuccessionePerRappresentazione")


def _stirpi(ids: list[str], pesi: list[int], totale: Fraction) -> dict[str, Fraction]:
    """Ripartisce ``totale`` fra stirpi (liste di persone) secondo i pesi; dentro ogni stirpe in parti uguali."""
    # ``ids``: una stirpe per elemento, come stringa 'a|b|c'
    somma = sum(pesi)
    out: dict[str, Fraction] = {}
    for gruppo, peso in zip(ids, pesi):
        membri = gruppo.split("|")
        for m in membri:
            out[m] = totale * peso / somma / len(membri)
    return out


def quote_di_legge(gradi: dict[str, str], tipi: dict[str, str],
                   rappresentati: dict[str, tuple[str, str]] | None = None) -> dict[str, Fraction] | None:
    """Quote di legge per persona (id -> frazione) oppure ``None`` se la configurazione non e' coperta.

    ``gradi``: id -> codice GradoParentela del quadro EA; ``tipi``: id -> TipoSoggetto; ``rappresentati``: per chi succede per
    rappresentazione, id -> (codice fiscale del rappresentato, grado del rappresentato). Le annotazioni chiedono le quote di legge
    solo se i tipi soggetto sono tutti '1' o tutti '3'. I figli/fratelli premorti non compaiono: si riconoscono dai loro
    discendenti, che formano una stirpe (conta come un figlio/fratello) e dividono in parti uguali la quota della stirpe."""
    rapp = rappresentati or {}
    if not gradi or set(gradi) != set(tipi):
        return None
    if not (set(tipi.values()) == {"1"} or set(tipi.values()) == {"3"}):
        return None
    if set(rapp) - set(gradi):
        return None
    per = {g: [p for p, x in sorted(gradi.items()) if x == g and p not in rapp] for g in ("01", "02", "03", "10", "11")}
    n_normali = sum(len(v) for v in per.values())
    gruppi: dict[tuple[str, str], list[str]] = {}
    for p, (cf, gr) in sorted(rapp.items()):
        if gradi[p] not in GRADI_RAPPRESENTANTE or gr not in ("02", "10", "11") or not cf:
            return None
        if (gradi[p] in GRADI_RAPPRESENTANTE_RETTA) != (gr == "02"):
            return None                      # i discendenti dei figli rappresentano un figlio; quelli dei fratelli un fratello
        gruppi.setdefault((cf, gr), []).append(p)
    if n_normali + len(rapp) != len(gradi):
        return None                          # gradi non coperti (nonni, altri parenti, estranei...)
    coniuge, genitori = per["01"], per["03"]
    if len(coniuge) > 1 or len(genitori) > 2:
        return None
    # stirpi: ogni figlio/fratello presente e' una stirpe; i rappresentanti dello stesso rappresentato formano una stirpe
    figli = per["02"] + ["|".join(v) for (cf, gr), v in gruppi.items() if gr == "02"]
    fr_germ = per["10"] + ["|".join(v) for (cf, gr), v in gruppi.items() if gr == "10"]
    fr_unil = per["11"] + ["|".join(v) for (cf, gr), v in gruppi.items() if gr == "11"]
    fratelli = fr_germ + fr_unil
    pesi_fr = [2] * len(fr_germ) + [1] * len(fr_unil)
    if figli:                            # i figli (e le loro stirpi) escludono ascendenti e collaterali
        if genitori or fratelli:
            return None
        if not coniuge:
            return _stirpi(figli, [1] * len(figli), Fraction(1))
        if len(figli) == 1:
            return {coniuge[0]: Fraction(1, 2), **_stirpi(figli, [1], Fraction(1, 2))}
        return {coniuge[0]: Fraction(1, 3), **_stirpi(figli, [1] * len(figli), Fraction(2, 3))}
    if coniuge and not genitori and not fratelli:
        return {coniuge[0]: Fraction(1)}
    if genitori and fratelli:
        if coniuge:                      # tabella p. 69: coniuge 8/12, genitori 3/12, fratelli 1/12
            return {coniuge[0]: Fraction(8, 12), **_stirpi(genitori, [1] * len(genitori), Fraction(3, 12)),
                    **_stirpi(fratelli, pesi_fr, Fraction(1, 12))}
        g_unita, f_unita = 2 * len(genitori), sum(pesi_fr)
        quota_genitori = max(Fraction(1, 2), Fraction(g_unita, g_unita + f_unita))
        return {**_stirpi(genitori, [1] * len(genitori), quota_genitori), **_stirpi(fratelli, pesi_fr, 1 - quota_genitori)}
    resto = Fraction(1, 3) if coniuge else Fraction(1)
    if not genitori and not fratelli:
        return None
    out: dict[str, Fraction] = {coniuge[0]: Fraction(2, 3)} if coniuge else {}
    if genitori:
        out.update(_stirpi(genitori, [1] * len(genitori), resto))
    else:
        out.update(_stirpi(fratelli, pesi_fr, resto))
    return out


def descrivi(quote: dict[str, Fraction]) -> str:
    return ", ".join(f"{p} {q.numerator}/{q.denominator}" for p, q in sorted(quote.items()))
