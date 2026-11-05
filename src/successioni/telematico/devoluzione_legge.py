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


def _parti_uguali(ids: list[str], totale: Fraction) -> dict[str, Fraction]:
    return {p: totale / len(ids) for p in ids}


def _fratelli(germani: list[str], unilaterali: list[str], totale: Fraction) -> dict[str, Fraction]:
    unita = 2 * len(germani) + len(unilaterali)
    out = {p: totale * 2 / unita for p in germani}
    out.update({p: totale / unita for p in unilaterali})
    return out


def quote_di_legge(gradi: dict[str, str], tipi: dict[str, str]) -> dict[str, Fraction] | None:
    """Quote di legge per persona (id -> frazione) oppure ``None`` se la configurazione non e' coperta.

    ``gradi``: id -> codice GradoParentela del quadro EA; ``tipi``: id -> TipoSoggetto. Le annotazioni chiedono le
    quote di legge solo se i tipi soggetto sono tutti '1' o tutti '3'."""
    if not gradi or set(gradi) != set(tipi):
        return None
    if not (set(tipi.values()) == {"1"} or set(tipi.values()) == {"3"}):
        return None
    per = {g: [p for p, x in sorted(gradi.items()) if x == g] for g in ("01", "02", "03", "10", "11")}
    if sum(len(v) for v in per.values()) != len(gradi):
        return None                      # gradi non coperti (nonni, nipoti, altri parenti, estranei...)
    coniuge, figli, genitori = per["01"], per["02"], per["03"]
    germani, unilaterali = per["10"], per["11"]
    fratelli = germani + unilaterali
    if len(coniuge) > 1 or len(genitori) > 2:
        return None
    if figli:                            # i figli escludono ascendenti e collaterali
        if genitori or fratelli:
            return None
        if not coniuge:
            return _parti_uguali(figli, Fraction(1))
        if len(figli) == 1:
            return {coniuge[0]: Fraction(1, 2), figli[0]: Fraction(1, 2)}
        return {coniuge[0]: Fraction(1, 3), **_parti_uguali(figli, Fraction(2, 3))}
    if coniuge and not genitori and not fratelli:
        return {coniuge[0]: Fraction(1)}
    if genitori and fratelli:
        if coniuge:                      # tabella p. 69: coniuge 8/12, genitori 3/12, fratelli 1/12
            return {coniuge[0]: Fraction(8, 12), **_parti_uguali(genitori, Fraction(3, 12)),
                    **_fratelli(germani, unilaterali, Fraction(1, 12))}
        g_unita, f_unita = 2 * len(genitori), 2 * len(germani) + len(unilaterali)
        quota_genitori = max(Fraction(1, 2), Fraction(g_unita, g_unita + f_unita))
        return {**_parti_uguali(genitori, quota_genitori),
                **_fratelli(germani, unilaterali, 1 - quota_genitori)}
    resto = Fraction(1, 3) if coniuge else Fraction(1)
    if not genitori and not fratelli:
        return None
    out: dict[str, Fraction] = {coniuge[0]: Fraction(2, 3)} if coniuge else {}
    if genitori:
        out.update(_parti_uguali(genitori, resto))
    else:
        out.update(_fratelli(germani, unilaterali, resto))
    return out


def descrivi(quote: dict[str, Fraction]) -> str:
    return ", ".join(f"{p} {q.numerator}/{q.denominator}" for p, q in sorted(quote.items()))
