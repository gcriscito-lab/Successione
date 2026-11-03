"""Layout, accessibilita' e asset statici della GUI: contrasto dei token colore (calcolato leggendo app.css), favicon,
larghezza memorizzata della barra laterale, struttura di index.html e dei file statici.
Le parti che richiedono un browser (trascinamento, responsive, tastiera) sono nelle prove Playwright di tests/e2e."""
import json
import re
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from successioni import impostazioni as IM
from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.web import crea_app

STATIC = Path(__file__).resolve().parents[1] / "src" / "successioni" / "static"
T = "tok123"
SOGLIA = 4.5   # WCAG AA, testo normale


# ---------------------------------------------------------------- lettura dei token da app.css
def _senza_at_regole(css: str) -> str:
    """Toglie i blocchi @media/@container (con parentesi graffe annidate): restano solo le regole di primo livello."""
    out, i = [], 0
    while i < len(css):
        if css[i] == "@":
            j = css.index("{", i)
            livello, k = 1, j + 1
            while livello:
                livello += {"{": 1, "}": -1}.get(css[k], 0)
                k += 1
            i = k
        else:
            out.append(css[i])
            i += 1
    return "".join(out)


def _blocchi(css: str):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", _senza_at_regole(css)):
        yield m.group(1).strip(), m.group(2)


def _dichiarazioni(corpo: str) -> dict:
    return {k.strip(): v.strip() for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);?", corpo)}


def temi(css: str) -> dict:
    """Valori effettivi dei token (cascata di primo livello) per tema: chiaro, scuro, seppia."""
    base, extra = {}, {"scuro": {}, "seppia": {}}
    for sel, corpo in _blocchi(css):
        d = _dichiarazioni(corpo)
        if sel in (":root", ':root[data-tema="chiaro"]'):
            base.update(d)
        elif sel == ':root[data-tema="scuro"]':
            extra["scuro"].update(d)
        elif sel == ':root[data-tema="seppia"]':
            extra["seppia"].update(d)
    return {"chiaro": base, "scuro": {**base, **extra["scuro"]}, "seppia": {**base, **extra["seppia"]}}


def colore(valore: str, tokens: dict, _prof: int = 0):
    """'#rgb', '#rrggbb', 'rgb(a)(...)' o 'var(--x)' -> (r, g, b, a)."""
    assert _prof < 10, "riferimenti var() ciclici"
    v = valore.strip()
    m = re.fullmatch(r"var\((--[\w-]+)\)", v)
    if m:
        return colore(tokens[m.group(1)], tokens, _prof + 1)
    m = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", v)
    if m:
        h = m.group(1)
        h = "".join(c * 2 for c in h) if len(h) == 3 else h
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)", v)
    if m:
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return (float(m.group(1)), float(m.group(2)), float(m.group(3)), a)
    raise AssertionError(f"colore non riconosciuto: {valore!r}")


def sopra(fg, bg):
    """Composizione alfa di fg sopra bg (bg opaco)."""
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3)) + (1.0,)


def luminanza(c) -> float:
    def lin(x):
        x = x / 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])


def rapporto(a, b) -> float:
    la, lb = luminanza(a), luminanza(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def sfondi_pagina(css: str, t: dict, tema: str = "chiaro"):
    """Colori possibili dello sfondo della pagina: --fondo e ciascun alone radiale del body composto su --fondo.
    Una regola `:root[data-tema="<tema>"] body` con `background` sostituisce quella generale (es. tema scuro senza aloni)."""
    fondo = colore(t["--fondo"], t)
    body = next(c for s, c in _blocchi(css) if s == "body")
    for sel, corpo in _blocchi(css):
        if sel == f':root[data-tema="{tema}"] body' and "background" in corpo:
            body = corpo
    aloni = re.findall(r"radial-gradient\([^)]*?(rgba?\([^)]*\))", body)
    return [fondo] + [sopra(colore(a, t), fondo) for a in aloni]


def superfici(css: str, t: dict, tema: str = "chiaro"):
    """(nome, colore opaco) di ogni superficie su cui compare testo, nel caso peggiore su tutti gli sfondi possibili."""
    out = []
    for i, pag in enumerate(sfondi_pagina(css, t, tema)):
        lat = sopra(colore(t["--lat"], t), pag)
        out += [(f"lat/{i}", lat), (f"pann/{i}", sopra(colore(t["--pann"], t), pag)),
                (f"grigio su lat/{i}", sopra(colore(t["--grigio"], t), lat))]
    solido = colore(t["--solido"], t)
    out += [("solido", solido), ("campo", colore(t["--campo"], t)), ("grigio su solido", sopra(colore(t["--grigio"], t), solido))]
    return out


@pytest.fixture(scope="module")
def css():
    return (STATIC / "app.css").read_text(encoding="utf-8")


# ---------------------------------------------------------------- il calcolo del contrasto e' corretto
def test_formula_contrasto_valori_noti():
    assert rapporto((0, 0, 0), (255, 255, 255)) == pytest.approx(21.0)
    assert rapporto((255, 255, 255), (255, 255, 255)) == pytest.approx(1.0)
    assert rapporto((119, 119, 119), (255, 255, 255)) == pytest.approx(4.48, abs=0.01)   # #777 su bianco: valore di riferimento WCAG
    assert rapporto((255, 255, 255), (0, 0, 0)) == rapporto((0, 0, 0), (255, 255, 255))
    # canali primari: i coefficienti 0,2126 / 0,7152 / 0,0722 devono stare sul canale giusto
    assert rapporto((255, 0, 0), (255, 255, 255)) == pytest.approx(4.00, abs=0.01)
    assert rapporto((0, 255, 0), (255, 255, 255)) == pytest.approx(1.37, abs=0.01)
    assert rapporto((0, 0, 255), (255, 255, 255)) == pytest.approx(8.59, abs=0.01)


def test_composizione_alfa_e_lettura_colori():
    assert sopra((0, 0, 0, 0.5), (200, 100, 50, 1.0)) == (100.0, 50.0, 25.0, 1.0)
    assert colore("#fff", {}) == (255, 255, 255, 1.0)
    assert colore("rgba(10, 20, 30, .5)", {}) == (10.0, 20.0, 30.0, 0.5)
    assert colore("var(--x)", {"--x": "#0a0b0c"}) == (10, 11, 12, 1.0)


def test_cascata_dei_token_ultimo_valore_vince(css):
    t = temi(css)
    assert t["chiaro"]["--blu"] == "#176a67" and t["scuro"]["--blu"] == "#7bd3c7"   # le ridefinizioni in coda a app.css prevalgono
    assert t["seppia"]["--t2"] != t["chiaro"]["--t2"]
    assert "--t2" in t["scuro"]


# ---------------------------------------------------------------- problema 11: contrasto
@pytest.mark.parametrize("tema", ["chiaro", "scuro", "seppia"])
def test_testo_secondario_e_principale_sopra_la_soglia(css, tema):
    t = temi(css)[tema]
    sec, pri = colore(t["--t2"], t), colore(t["--t"], t)
    for nome, sf in superfici(css, t, tema):
        assert rapporto(sec, sf) >= SOGLIA, f"{tema}: --t2 su {nome} = {rapporto(sec, sf):.2f}"
        assert rapporto(pri, sf) >= SOGLIA, f"{tema}: --t su {nome} = {rapporto(pri, sf):.2f}"


@pytest.mark.parametrize("tema", ["chiaro", "scuro", "seppia"])
def test_sigle_dei_quadri_leggibili(css, tema):
    """Le sigle (EA, EC...) hanno testo --sg-t su sfondo per stato; l'inattivo e' trasparente con testo secondario."""
    t = temi(css)[tema]
    testo = colore(t["--sg-t"], t)
    for nome in ("--sg-n", "--sg-ok", "--sg-er", "--sg-am", "--blu"):
        assert rapporto(testo, colore(t[nome], t)) >= SOGLIA, f"{tema}: {nome}"
    lat = sopra(colore(t["--lat"], t), sfondi_pagina(css, t, tema)[0])
    assert rapporto(colore(t["--t2"], t), lat) >= SOGLIA


def test_sigle_usano_i_token_e_non_colori_fissi(css):
    """Regressione: sfondi fissi (#8e8e93, #a8a8ae con opacita') non devono tornare nelle regole delle sigle."""
    regole = [c for s, c in _blocchi(css) if ".sigla" in s]
    assert len(regole) >= 6
    for corpo in regole:
        assert "opacity" not in corpo
        assert not re.search(r"background\s*:\s*#", corpo), corpo
    assert "color:var(--sg-t)" in next(c for s, c in _blocchi(css) if s.strip() == ".sigla").replace(" ", "")


# ---------------------------------------------------------------- problema 4: barra laterale ridimensionabile
def test_griglia_con_larghezza_variabile_e_separatore(css):
    regole = dict((s.strip(), c) for s, c in _blocchi(css))
    assert "var(--larghezza-nav,240px) 10px minmax(0,1fr)" in regole[".app"].replace(" ,", ",")
    assert regole[".app.conIns"].count("10px") == 2 and "var(--larghezza-ins,360px)" in regole[".app.conIns"]
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<div id="ridimensionaNav"[^>]*>', html)
    assert m and 'role="separator"' in m.group(0) and 'tabindex="0"' in m.group(0)
    assert 'aria-valuemin="180"' in m.group(0) and 'aria-valuemax="480"' in m.group(0)
    assert html.index('id="ridimensionaNav"') > html.index('id="lat"') and html.index('id="ridimensionaNav"') < html.index('id="vista"')


def test_preferenza_larghezza_nav_predefinita_e_intervallo(tmp_path, monkeypatch):
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "configurazione.json"))
    assert IM.INTERFACCIA_DEFAULT["larghezza_nav"] == 240
    assert IM.stato()["interfaccia"]["larghezza_nav"] == 240
    for ok in (180, 300, 480):
        IM.salva({}, {"larghezza_nav": ok})
        assert IM.stato()["interfaccia"]["larghezza_nav"] == ok
    for no in (179, 481, True, "300", 300.5, None):
        prima = (tmp_path / "configurazione.json").read_text()
        with pytest.raises(IM.DatiNonValidi):
            IM.salva({}, {"larghezza_nav": no})
        assert (tmp_path / "configurazione.json").read_text() == prima


def test_larghezze_pannello_e_dimensione_conservano_i_limiti(tmp_path, monkeypatch):
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "configurazione.json"))
    for chiave, ok, no in (("larghezza_pannello", (280, 760), (279, 761)), ("dimensione", (12, 22), (11, 23))):
        for v in ok:
            IM.salva({}, {chiave: v})
        for v in no:
            with pytest.raises(IM.DatiNonValidi):
                IM.salva({}, {chiave: v})


def test_larghezza_nav_salvata_via_api_e_riletta(tmp_path, monkeypatch):
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "configurazione.json"))
    c = TestClient(crea_app(Servizio(Archivio(tmp_path / "d")), token=T, ammetti_host_di_prova=True), base_url="http://testserver")
    c.get("/", params={"t": T})
    r = c.post("/api/impostazioni", json={"interfaccia": {"larghezza_nav": 333}})
    assert r.status_code == 200 and r.json()["interfaccia"]["larghezza_nav"] == 333
    assert c.get("/api/impostazioni").json()["interfaccia"]["larghezza_nav"] == 333
    assert json.loads((tmp_path / "configurazione.json").read_text())["interfaccia"]["larghezza_nav"] == 333
    assert c.post("/api/impostazioni", json={"interfaccia": {"larghezza_nav": 9999}}).status_code == 422


# ---------------------------------------------------------------- problema 12: favicon
@pytest.fixture
def client(tmp_path):
    c = TestClient(crea_app(Servizio(Archivio(tmp_path / "d")), token=T, ammetti_host_di_prova=True), base_url="http://testserver")
    c.get("/", params={"t": T})
    return c


def test_favicon_servita_e_coincide_con_il_logo(client):
    r = client.get("/favicon.ico")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert r.content == (STATIC / "logo.svg").read_bytes() and r.content.lstrip().startswith(b"<svg")


def test_index_dichiara_icona_e_script_serviti(client):
    html = client.get("/").text
    assert '<link rel="icon" type="image/svg+xml" href="/static/logo.svg">' in html
    for percorso in re.findall(r'(?:href|src)="(/static/[^"]+)"', html):
        r = client.get(percorso)
        assert r.status_code == 200, percorso
    assert '<script src="/static/layout.js"></script>' in html
    assert html.index("/static/app.js") < html.index("/static/layout.js")


# ---------------------------------------------------------------- problema 7 / 1: struttura di index.html
def test_index_id_unici_e_riferimenti_aria_validi():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    ids = re.findall(r'\sid="([^"]+)"', html)
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]
    for rif in re.findall(r'aria-controls="([^"]+)"', html):
        assert rif in ids, rif
    for per in re.findall(r'\sfor="([^"]+)"', html):
        assert per in ids, per


def test_barra_mobile_controlli_presenti():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for i in ("bNav", "bMenu", "velo", "lat", "azioni"):
        assert f'id="{i}"' in html
    assert 'aria-expanded="false"' in re.search(r'<button id="bNav"[^>]*>', html).group(0)


def test_css_mobile_un_solo_scroll_e_cassetto(css):
    mobile = re.search(r"@media \(max-width:960px\) \{\s*html, body \{ height:auto; \}.*?\n\}", css, re.S)
    assert mobile, "blocco responsive sotto 960 px mancante"
    corpo = mobile.group(0)
    assert re.search(r"main \{ overflow:visible", corpo)                      # niente scroll annidato nella vista
    assert ".tab { max-height:none; }" in corpo                               # la tabella non ha uno scroll verticale proprio
    assert re.search(r"\.lat \{ position:fixed", corpo) and "visibility:hidden" in corpo   # cassetto chiuso: fuori dal Tab
    assert "body.navAperta .lat" in corpo
    assert re.search(r"\.sb \{[^}]*flex-wrap:nowrap", corpo)                  # barra di stato su una riga


# ---------------------------------------------------------------- problema 9 e 7: comportamenti JS (controllo sul sorgente)
def test_js_tabella_roving_tabindex_e_tasti():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert 'tabindex: "0"' not in js.split("function renderTabella")[1].split("function aggiungiRiga")[0].replace('? "0" : "-1"', "")
    assert '? "0" : "-1"' in js
    corpo = js.split("function tastiTabella")[1].split("function rigaDaFocalizzare")[0]
    for tasto in ("ArrowDown", "ArrowUp", "Home", "End", "Enter"):
        assert tasto in corpo
    assert 'selezionaRiga(key, "pannello")' in corpo
    assert '#ins .rg input, #ins .rg select' in js.split("function selezionaRiga")[1].split("function tornaTabella")[0]


def test_layout_js_esc_e_collegamento_label():
    js = (STATIC / "layout.js").read_text(encoding="utf-8")
    assert '"Escape"' in js and "tr.focus()" in js
    assert "label:not([for])" in js and "l.htmlFor = idUnivoco(c)" in js
    assert "MutationObserver" in js


def test_voci_dei_quadri_con_tooltip_e_testo_su_piu_righe(css):
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    voce = js.split("function renderAlbero")[1].split("/* ---------- campi")[0]
    assert 'title: q.id + " — " + q.titolo' in voce
    nome = next(c for s, c in _blocchi(css) if s.strip() == ".voce .nome")
    assert "line-clamp:2" in nome and "white-space:nowrap" not in nome
