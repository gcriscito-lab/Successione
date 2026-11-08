"""Regole del design system (design-system/successioni/MASTER.md) verificate su app.css:
bordo dei controlli >= 3:1 (WCAG 1.4.11) in ogni tema e con contrasto alto, spazi solo sulla scala --s-*."""
import re
from pathlib import Path

import pytest

from test_gui_layout import STATIC, _blocchi, colore, rapporto, sopra, temi

RADICE = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def css():
    return (STATIC / "app.css").read_text(encoding="utf-8")


@pytest.mark.parametrize("tema", ["chiaro", "scuro", "seppia"])
def test_bordo_dei_controlli_almeno_3_a_1(css, tema):
    t = temi(css)[tema]
    bordo = colore(t["--sep-f"], t)
    for nome in ("--campo", "--solido", "--fondo", "--pann"):
        sf = colore(t[nome], t)
        r = rapporto(sopra(bordo, sf), sf)
        assert r >= 3.0, f"{tema}: --sep-f su {nome} = {r:.2f}"


def test_spazi_solo_dalla_scala(css):
    """padding, margin e gap usano i token --s-*; restano ammessi 0, 1px, auto, percentuali e calc()."""
    fuori = []
    for sel, corpo in _blocchi(css):
        for prop, val in re.findall(r"(?<![-\w])((?:padding|margin|gap|row-gap|column-gap)[\w-]*):([^;]+)", corpo):
            if "(" in val and "var(--s-" not in val and "calc(" in val:
                continue
            for parte in val.split():
                m = re.fullmatch(r"-?(\d+(?:\.\d+)?)px", parte)
                if m and float(m.group(1)) > 1:
                    fuori.append(f"{sel.strip()} {{ {prop}:{val.strip()} }}")
    assert not fuori, "spazi fuori scala:\n" + "\n".join(fuori[:20])


def test_token_della_scala_presenti(css):
    t = temi(css)["chiaro"]
    for nome in ("--s-05", "--s-1", "--s-15", "--s-2", "--s-3", "--s-4", "--s-5", "--s-6", "--s-8", "--s-10",
                 "--r0", "--r1", "--r2", "--r-pill", "--r-tondo", "--fs-s", "--fs-m", "--fs-base", "--fs-l", "--fs-xl", "--e1", "--e2"):
        assert nome in t, nome


def test_documento_del_design_system_presente():
    master = RADICE / "design-system" / "successioni" / "MASTER.md"
    assert master.is_file() and "WCAG 1.4.11" in master.read_text(encoding="utf-8")
