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

COPERTI: solo figli (grado 02); solo coniuge (grado 01); coniuge + figli. Tutto il resto (ascendenti, fratelli,
unilaterali, rappresentazione, gradi diversi) -> ``None``: le quote NON vengono verificate e l'export lo segnala.
"""
from __future__ import annotations

from fractions import Fraction

FONTE = ("Succ_FASCICOLO_I_Nov_23.pdf p. 69 (Allegato 5 - Devoluzione); fornituraSUC13_v1.xsd, annotazione "
         "Devoluzione/Quota e RipartizioneED/Ripartizione/Quota (quote in base all'allegato 5)")
TIPI_PASSIVITA_LIBERE = {"1", "2", "11", "12"}  # annotazione RipartizioneED/Ripartizione/Quota


def quote_di_legge(gradi: dict[str, str], tipi: dict[str, str]) -> dict[str, Fraction] | None:
    """Quote di legge per persona (id -> frazione) oppure ``None`` se la configurazione non e' coperta.

    ``gradi``: id -> codice GradoParentela del quadro EA; ``tipi``: id -> TipoSoggetto. Le annotazioni chiedono le
    quote di legge solo se i tipi soggetto sono tutti '1' o tutti '3'."""
    if not gradi or set(gradi) != set(tipi):
        return None
    if not (set(tipi.values()) == {"1"} or set(tipi.values()) == {"3"}):
        return None
    coniugi = [p for p, g in gradi.items() if g == "01"]
    figli = [p for p, g in gradi.items() if g == "02"]
    if len(coniugi) + len(figli) != len(gradi) or len(coniugi) > 1:
        return None
    if not figli:
        return {coniugi[0]: Fraction(1)}
    if not coniugi:
        return {p: Fraction(1, len(figli)) for p in figli}
    if len(figli) == 1:
        return {coniugi[0]: Fraction(1, 2), figli[0]: Fraction(1, 2)}
    out = {coniugi[0]: Fraction(1, 3)}
    out.update({p: Fraction(2, 3 * len(figli)) for p in figli})
    return out


def descrivi(quote: dict[str, Fraction]) -> str:
    return ", ".join(f"{p} {q.numerator}/{q.denominator}" for p, q in sorted(quote.items()))
