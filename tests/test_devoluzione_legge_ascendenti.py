"""Quote di legge per gli ascendenti oltre i genitori (nonni 5A/5B, bisavi 7A/7B, trisavi 9A/9B).
Fonte: Succ_FASCICOLO_I_Nov_23.pdf p. 55 (Allegato 1, codici) e p. 69 (Allegato 5, esempi e tabelle), trascritti alla lettera:
i valori attesi vengono dalla fonte, non dall'implementazione."""
from fractions import Fraction as Fr

import pytest

from successioni.telematico.devoluzione_legge import ASCENDENTI, quote_di_legge


def q(*gradi):
    ids = {f"p{i}": g for i, g in enumerate(gradi)}
    return quote_di_legge(ids, {k: "1" for k in ids}), list(ids)


def per_persona(quote, ids):
    return [quote[i] for i in ids]


C, G, GER, UNI = "01", "03", "10", "11"


# Allegato 5, p. 69, esempi (defunto senza discendenti, genitori, fratelli):
#   Padre (defunto) - 1/4 Nonno e 1/4 Nonna;  Madre (defunta) - 1/4 Nonno e 1/4 Nonna
def test_esempio_1_quattro_nonni_un_quarto_ciascuno():
    quote, ids = q("5A", "5A", "5B", "5B")
    assert per_persona(quote, ids) == [Fr(1, 4)] * 4


#   Padre (defunto) - 1/4 Nonno e 1/4 Nonna;  Madre (defunta) - 1/2 Nonno/a
def test_esempio_2_un_solo_nonno_materno_ha_meta():
    quote, ids = q("5A", "5A", "5B")
    assert per_persona(quote, ids) == [Fr(1, 4), Fr(1, 4), Fr(1, 2)]


#   Padre (defunto) - 1/2 Nonno e 1/2 Nonna;  Madre (defunta) - Nonno (defunto) e Nonna (defunta) - Bisnonno/a
# Il bisnonno non eredita (ascendenti di grado diverso: al piu' vicino senza distinzione di linea): in EA compaiono solo i due nonni
# paterni. Se un ascendente piu' lontano e' elencato in EA la configurazione non e' coperta (l'XSD vieta soggetti senza devoluzione).
def test_esempio_3_ascendenti_di_grado_diverso_al_piu_vicino_senza_distinzione_di_linea():
    quote, ids = q("5A", "5A")
    assert per_persona(quote, ids) == [Fr(1, 2), Fr(1, 2)]
    assert q("5A", "5A", "7B")[0] is None


def test_somma_sempre_uno_per_ascendenti_dello_stesso_grado():
    for gradi in (("5A",), ("5A", "5B"), ("7A", "7B"), ("9A", "9B", "9B"), ("5A", "5A", "5A", "5B")):
        quote, ids = q(*gradi)
        assert sum(quote.values()) == 1, gradi
        assert set(quote) == set(ids), gradi

def test_una_sola_linea_stesso_grado_parti_uguali():
    quote, ids = q("5A", "5A")                 # solo nonni paterni: nessuna meta' di linea da rispettare
    assert per_persona(quote, ids) == [Fr(1, 2), Fr(1, 2)]


def test_bisavi_di_linee_diverse_meta_ciascuno():
    quote, ids = q("7A", "7B")
    assert per_persona(quote, ids) == [Fr(1, 2), Fr(1, 2)]


# Allegato 5, p. 69: «Coniuge + genitore (o entrambi o altri Ascendenti): 2/3 al coniuge, 1/3 agli ascendenti»
def test_coniuge_e_nonni():
    quote, ids = q(C, "5A", "5B")
    assert per_persona(quote, ids) == [Fr(2, 3), Fr(1, 6), Fr(1, 6)]
    quote, ids = q(C, "5A", "5A", "5B")        # la meta' di linea vale dentro il terzo degli ascendenti
    assert per_persona(quote, ids) == [Fr(2, 3), Fr(1, 12), Fr(1, 12), Fr(1, 6)]


# p. 70, «Concorso del genitore/i (o altri ascendenti) con fratelli/sorelle»: righe «Ascendente/i»
@pytest.mark.parametrize("gradi,ascendenti,fratelli", [
    (["5A", GER], Fr(1, 2), Fr(1, 2)),                 # Ascendente/i + 1 fratello germano
    (["5A", UNI], Fr(2, 3), Fr(1, 3)),                 # Ascendente/i + 1 fratello unilaterale
    (["5A", GER, GER], Fr(1, 2), Fr(1, 2)),            # Ascendente/i + 2 o piu' fratelli
    (["5A", UNI, UNI], Fr(1, 2), Fr(1, 2)),
    (["5A", GER, UNI], Fr(1, 2), Fr(1, 2)),
    (["5A", "5B", GER], Fr(1, 2), Fr(1, 2)),           # il gruppo degli ascendenti vale come un solo genitore
    (["5A", "5A", "5B", UNI], Fr(2, 3), Fr(1, 3)),
])
def test_ascendenti_e_fratelli_tabella_p70(gradi, ascendenti, fratelli):
    quote, ids = q(*gradi)
    assert sum(quote.values()) == 1
    asc = sum((quote[i] for i, g in zip(ids, gradi) if g in ASCENDENTI), Fr(0))
    fr = sum((quote[i] for i, g in zip(ids, gradi) if g in (GER, UNI)), Fr(0))
    assert (asc, fr) == (ascendenti, fratelli)


# p. 69: «Coniuge + 1 genitore (o entrambi o altro ascendente) + 1 o piu' fratelli: 8/12, 3/12, 1/12»
def test_coniuge_ascendente_e_fratelli_8_12_3_12_1_12():
    quote, ids = q(C, "5A", GER)
    assert per_persona(quote, ids) == [Fr(8, 12), Fr(3, 12), Fr(1, 12)]
    quote, ids = q(C, "5A", "5B", GER, UNI)
    assert quote[ids[0]] == Fr(8, 12)
    assert quote[ids[1]] + quote[ids[2]] == Fr(3, 12)
    assert quote[ids[3]] + quote[ids[4]] == Fr(1, 12) and quote[ids[3]] == 2 * quote[ids[4]]


@pytest.mark.parametrize("gradi", [
    [G, "5A"],               # i genitori escludono gli altri ascendenti
    ["02", "5A"],            # i figli escludono gli ascendenti
    ["02", C, "5B"],
    ["5C"],                  # codice inesistente
    ["16"],                  # zio/a: l'Allegato 5 non da' le quote dei collaterali oltre i fratelli
    ["21"],                  # cugino/a
    ["5A", "16"],
])
def test_configurazioni_non_coperte(gradi):
    assert q(*gradi)[0] is None


def test_codici_minuscoli_accettati():
    quote, ids = q("5a", "5b")
    assert per_persona(quote, ids) == [Fr(1, 2), Fr(1, 2)]


def test_rappresentazione_di_ascendenti_non_coperta():
    ids = {"a": "5A", "b": "04"}
    assert quote_di_legge(ids, {"a": "1", "b": "1"}, {"b": ("CF", "02")}) is None      # nonno + nipote di figlio: figli escludono
