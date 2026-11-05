"""Quote di legge: ogni riga delle tabelle di Succ_FASCICOLO_I_Nov_23.pdf pp. 69-70 (Allegato 5), trascritte alla lettera.
I valori attesi vengono dalla fonte, non dall'implementazione."""
from fractions import Fraction as Fr

import pytest

from successioni.telematico.devoluzione_legge import quote_di_legge


def q(*gradi):
    ids = {f"p{i}": g for i, g in enumerate(gradi)}
    return quote_di_legge(ids, {k: "1" for k in ids}), list(ids)


C, F, G, GER, UNI = "01", "02", "03", "10", "11"

# (gradi degli eredi, quota totale per categoria nell'ordine coniuge, figli, genitori, fratelli)  - p. 69
P69 = [
    ([C, F], (Fr(1, 2), Fr(1, 2), 0, 0)),
    ([C, F, F], (Fr(1, 3), Fr(2, 3), 0, 0)),
    ([C, F, F, F], (Fr(1, 3), Fr(2, 3), 0, 0)),
    ([C, G], (Fr(2, 3), 0, Fr(1, 3), 0)),
    ([C, G, G], (Fr(2, 3), 0, Fr(1, 3), 0)),
    ([C, GER], (Fr(2, 3), 0, 0, Fr(1, 3))),
    ([C, GER, UNI], (Fr(2, 3), 0, 0, Fr(1, 3))),
    ([C, G, GER], (Fr(8, 12), 0, Fr(3, 12), Fr(1, 12))),
    ([C, G, G, GER, UNI], (Fr(8, 12), 0, Fr(3, 12), Fr(1, 12))),
    ([C], (Fr(1), 0, 0, 0)),
    ([F, F], (0, Fr(1), 0, 0)),
]
# (gradi, quota genitori, quota fratelli) - p. 70, "Concorso del genitore/i con fratelli/sorelle"
P70 = [
    ([G, GER], Fr(1, 2), Fr(1, 2)),
    ([G, UNI], Fr(2, 3), Fr(1, 3)),
    ([G, GER, GER], Fr(1, 2), Fr(1, 2)),
    ([G, UNI, UNI], Fr(1, 2), Fr(1, 2)),
    ([G, G, GER], Fr(2, 3), Fr(1, 3)),
    ([G, G, UNI], Fr(4, 5), Fr(1, 5)),
    ([G, G, GER, GER], Fr(1, 2), Fr(1, 2)),
    ([G, G, UNI, UNI], Fr(2, 3), Fr(1, 3)),
    ([G, G, GER, UNI], Fr(4, 7), Fr(3, 7)),
    ([G, G, UNI, UNI, UNI], Fr(4, 7), Fr(3, 7)),
    ([G, G, GER, UNI, UNI], Fr(1, 2), Fr(1, 2)),     # 3 fratelli di cui almeno 1 germano
    ([G, G, GER, GER, GER], Fr(1, 2), Fr(1, 2)),
    ([G, G, UNI, UNI, UNI, UNI], Fr(1, 2), Fr(1, 2)),  # 4 o piu' fratelli
    ([G, G, GER, GER, GER, GER, GER], Fr(1, 2), Fr(1, 2)),
]


def somma(quote, ids, gradi, gruppo):
    return sum((quote[i] for i, g in zip(ids, gradi) if g in gruppo), Fr(0))


@pytest.mark.parametrize("gradi,attese", P69)
def test_tabella_p69(gradi, attese):
    quote, ids = q(*gradi)
    assert quote is not None and sum(quote.values()) == 1
    got = tuple(somma(quote, ids, gradi, gr) for gr in ({C}, {F}, {G}, {GER, UNI}))
    assert got == tuple(Fr(a) for a in attese)


@pytest.mark.parametrize("gradi,genitori,fratelli", P70)
def test_tabella_p70(gradi, genitori, fratelli):
    quote, ids = q(*gradi)
    assert quote is not None and sum(quote.values()) == 1
    assert somma(quote, ids, gradi, {G}) == genitori
    assert somma(quote, ids, gradi, {GER, UNI}) == fratelli


def test_ripartizione_interna_fra_fratelli_e_genitori():
    quote, ids = q(G, G, GER, UNI)          # 4/7 ai genitori (2/7 ciascuno), 3/7 ai fratelli: germano il doppio dell'unilaterale
    assert [quote[i] for i in ids] == [Fr(2, 7), Fr(2, 7), Fr(2, 7), Fr(1, 7)]


@pytest.mark.parametrize("gradi", [
    [F, G], [F, GER], [C, F, G],            # i figli escludono ascendenti e fratelli
    [C, C], [G, G, G],                      # piu' coniugi / piu' di due genitori
    ["04"], [F, "04"], [C, "35"],           # nipote in linea retta (rappresentazione), estraneo
    ["14"],                                 # grado non previsto dalle tabelle
])
def test_configurazioni_non_coperte(gradi):
    assert q(*gradi)[0] is None


def test_tipi_misti_non_coperti():
    assert quote_di_legge({"a": F, "b": F}, {"a": "1", "b": "3"}) is None


# ---- rappresentazione e premorti: Fascicolo I pp. 18-19 (esempio ministeriale) -------------------------------------------
from successioni.telematico.devoluzione_legge import quote_di_legge as _q  # noqa: E402


def qr(gradi, rapp):
    return _q(gradi, {k: "1" for k in gradi}, rapp)


def test_esempio_ministeriale_due_figli_rinunciatari_con_nipoti():
    # figlio 1 con tre figli, figlio 2 con un figlio, immobile da 60.000: 10.000 a ciascuno dei tre nipoti e 30.000 all'altro
    g = {"n1": "04", "n2": "04", "n3": "04", "m1": "04"}
    r = {"n1": ("CF_FIGLIO1", "02"), "n2": ("CF_FIGLIO1", "02"), "n3": ("CF_FIGLIO1", "02"), "m1": ("CF_FIGLIO2", "02")}
    assert qr(g, r) == {"n1": Fr(1, 6), "n2": Fr(1, 6), "n3": Fr(1, 6), "m1": Fr(1, 2)}
    assert [60000 * qr(g, r)[k] for k in ("n1", "m1")] == [10000, 30000]


def test_figlio_premorto_e_figlio_vivo():
    g = {"f": "02", "n1": "04", "n2": "04"}
    assert qr(g, {"n1": ("CF_P", "02"), "n2": ("CF_P", "02")}) == {"f": Fr(1, 2), "n1": Fr(1, 4), "n2": Fr(1, 4)}


def test_coniuge_con_stirpi_conta_ogni_stirpe_come_un_figlio():
    g = {"c": "01", "f": "02", "n1": "04", "n2": "04"}      # una stirpe di due nipoti + un figlio = due figli: 1/3 al coniuge
    assert qr(g, {"n1": ("CF_P", "02"), "n2": ("CF_P", "02")}) == {"c": Fr(1, 3), "f": Fr(1, 3), "n1": Fr(1, 6), "n2": Fr(1, 6)}
    g = {"c": "01", "n1": "04", "n2": "04"}                  # una sola stirpe: come un figlio unico (1/2 e 1/2)
    assert qr(g, {"n1": ("CF_P", "02"), "n2": ("CF_P", "02")}) == {"c": Fr(1, 2), "n1": Fr(1, 4), "n2": Fr(1, 4)}


def test_fratello_premorto_rappresentato_dai_nipoti():
    g = {"g": "10", "n1": "15", "n2": "15"}                  # germano vivo + due nipoti di un germano premorto: stirpi alla pari
    assert qr(g, {"n1": ("CF_P", "10"), "n2": ("CF_P", "10")}) == {"g": Fr(1, 2), "n1": Fr(1, 4), "n2": Fr(1, 4)}
    g = {"g": "10", "n1": "15"}                              # stirpe di un fratello unilaterale premorto: peso 1 contro 2
    assert qr(g, {"n1": ("CF_P", "11")}) == {"g": Fr(2, 3), "n1": Fr(1, 3)}


@pytest.mark.parametrize("gradi,rapp", [
    ({"n": "04"}, {"n": ("CF_P", "10")}),                    # nipote di figlio che rappresenta un fratello
    ({"n": "15"}, {"n": ("CF_P", "02")}),                    # nipote di fratello che rappresenta un figlio
    ({"n": "02"}, {"n": ("CF_P", "02")}),                    # grado non ammesso per la rappresentazione
    ({"n": "04"}, {"n": ("", "02")}),                        # rappresentato senza codice fiscale
    ({"n": "04", "f": "02", "g": "03"}, {"n": ("CF_P", "02")}),   # i figli escludono i genitori
    ({"n": "04"}, {"x": ("CF_P", "02")}),                    # rappresentante assente dal quadro
])
def test_rappresentazione_non_coperta(gradi, rapp):
    assert qr(gradi, rapp) is None
