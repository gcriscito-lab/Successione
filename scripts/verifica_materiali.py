#!/usr/bin/env python3
"""Verifica locale delle fonti incluse; non scarica né esegue programmi."""
from pathlib import Path
import argparse
import hashlib
import json
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-xsd',action='store_true',help='Compila lo schema SUC13 con lxml, se installato')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    manifest_path=root/'fonti/manifest.json'
    if not manifest_path.is_file():
        print('ERRORE: manifest non trovato: fonti/manifest.json',file=sys.stderr)
        return 1
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    errors=[]
    entries=manifest['files']
    paths=set()
    for item in entries:
        relative=item['path']
        p=(root/relative).resolve()
        if not p.is_relative_to(root/'fonti') or relative in paths:
            errors.append('Percorso non valido o duplicato: '+relative)
            continue
        paths.add(relative)
        if not p.is_file():
            errors.append('Mancante: '+relative)
            continue
        data=p.read_bytes()
        if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
            errors.append('Dimensione/impronta diversa: '+relative)
    if len(entries)!=manifest['file_count']:
        errors.append('Conteggio del manifest incoerente')
    for name in ['CLAUDE.md','docs/01_PROMPT_CLAUDE_CODE.md','docs/02_SPECIFICA_E_COLLAUDO.md','docs/COLLAUDO_CLOUD_WINDOWS.md']:
        if not (root/name).is_file():errors.append('Documento mancante: '+name)
    if errors:
        print('\n'.join(errors),file=sys.stderr)
        return 1
    counts={ext:sum(Path(x).suffix.lower()==ext for x in paths) for ext in ['.pdf','.xsd','.jnlp']}
    print(f"OK: {len(entries)} fonti verificate ({counts['.pdf']} PDF, {counts['.xsd']} XSD, {counts['.jnlp']} JNLP).")
    print('OK: documenti di progetto presenti; nessun percorso Windows richiesto per leggere le fonti.')
    if args.check_xsd:
        try:
            from lxml import etree
        except ImportError:
            print('XSD non verificato: per --check-xsd serve il pacchetto lxml.',file=sys.stderr)
            return 2
        schema_path=root/'fonti/Specifiche tecniche/SUC13_20250702/SUC/xsd/fornituraSUC13_v1.xsd'
        try:
            xml_parser=etree.XMLParser(resolve_entities=False,no_network=True)
            etree.XMLSchema(etree.parse(str(schema_path),parser=xml_parser))
        except Exception as exc:
            print('ERRORE compilazione XSD: '+str(exc),file=sys.stderr)
            return 1
        print('OK: schema principale e dipendenze XSD compilati. Non equivale al controllo ufficiale dei dati.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
