"""Prospetto stampabile dei byte esportati, distinto dal modello ministeriale."""
from html import escape
import re
from lxml import etree


def prospetto(xml: bytes, *, titolo: str, revisione: int, sha256: str, completo: bool) -> str:
    root = etree.fromstring(xml, etree.XMLParser(resolve_entities=False, no_network=True))
    sezioni = []
    ns = {'s': 'urn:www.agenziaentrate.gov.it:specificheTecniche:sco:suc:v1'}
    for sezione in root.xpath('//s:Dichiarazione/*', namespaces=ns):
        righe = []
        for e in sezione.iter():
            if len(e) or not (e.text or '').strip():
                continue
            nome = etree.QName(e).localname
            if nome == 'ImageData':
                valore = 'Contenuto incorporato nel file XML (Base64); vedere il documento originale.'
            else:
                valore = e.text
            path = e.getroottree().getpath(e).split('/suc:Dichiarazione/', 1)[-1]
            # Rimuove solo i prefissi XML, preservando indici, gruppi e codici ufficiali.
            path = re.sub(r'\b\w+:', '', path)
            righe.append(f'<tr><th>{escape(path)}</th><td>{escape(valore)}</td></tr>')
        sezioni.append(f'<section><h2>{escape(etree.QName(sezione).localname)}</h2><table>{"".join(righe)}</table></section>')
    stato = 'Completo nel perimetro implementato' if completo else 'BOZZA TECNICA INCOMPLETA - NON TRASMISSIBILE'
    return f'''<!doctype html><html lang="it"><meta charset="utf-8"><title>Prospetto di controllo</title>
<style>body{{font:12px Arial,sans-serif;margin:28px;color:#172330}}h1{{font-size:22px}}h2{{font-size:17px}}
table{{border-collapse:collapse;width:100%;table-layout:fixed}}th,td{{text-align:left;vertical-align:top;border:1px solid #ccd3da;padding:6px;overflow-wrap:anywhere}}th{{width:60%;font-weight:normal;background:#f5f7f9}}
section{{margin-top:22px}}tr{{break-inside:avoid}}h2{{break-after:avoid}}.sha{{overflow-wrap:anywhere}}@media print{{button{{display:none}}body{{margin:0}}@page{{size:A4;margin:15mm}}thead{{display:table-header-group}}}}</style>
<h1>{escape(titolo)}</h1><p>Prospetto di controllo - non è il modello ministeriale da presentare o sottoscrivere.</p>
<p>Revisione {revisione} dell'esportazione. {stato}.</p><p class="sha">SHA-256 XML: {escape(sha256)}</p>
<p>Stampa ricavata dagli stessi byte del file XML. Non attesta il controllo ufficiale, l'invio o la conformità fiscale.</p>
<button onclick="window.print()">Stampa / salva in PDF</button>{''.join(sezioni)}</html>'''
