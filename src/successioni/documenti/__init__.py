"""Area 2 - documenti e PDF/A: verifica strutturale indicativa, dimensioni, Base64, TIFF, anteprima, corpus sintetico.

Le funzioni pubbliche si importano dai singoli moduli (importazione pigra: nessun ciclo con ``successioni.pdfa``):

- ``limiti``              costanti dimensionali con riferimento alla specifica (p.3 e p.7), ``limite_byte``
- ``pdfa_strutturale``    ``verifica_strutturale_pdfa`` (esito INDICATIVO, mai "conforme")
- ``dimensioni``          ``riduci_o_suddividi``, ``verifica_fornitura``, ``misura_fornitura``
- ``base64``              ``incorpora_base64``, ``decodifica_base64``, ``valida_nome_file_eg``,
                          ``normalizza_nome_file_eg``, ``dati_file_attachment``
- ``tiff``                ``verifica_tiff``, ``converti_in_tiff_g4``
- ``anteprima``           ``confronta_visivo``, ``rendi_pagine`` (indicatore di fedelta', non una prova)
- ``corpus_sintetico``    generatore del corpus di prova (file SINTETICI) e ``collaudo_a11``

Documentazione: ``docs/PDFA.md``.
"""
from __future__ import annotations

import importlib

_ESPORTA = {
    "riduci_o_suddividi": "dimensioni",
    "verifica_fornitura": "dimensioni",
    "misura_fornitura": "dimensioni",
    "incorpora_base64": "base64",
    "decodifica_base64": "base64",
    "valida_nome_file_eg": "base64",
    "normalizza_nome_file_eg": "base64",
    "dati_file_attachment": "base64",
    "verifica_strutturale_pdfa": "pdfa_strutturale",
    "verifica_tiff": "tiff",
    "converti_in_tiff_g4": "tiff",
    "confronta_visivo": "anteprima",
    "rendi_pagine": "anteprima",
    "genera_corpus": "corpus_sintetico",
    "collaudo_a11": "corpus_sintetico",
}


def __getattr__(nome: str):
    if nome in _ESPORTA:
        return getattr(importlib.import_module(f".{_ESPORTA[nome]}", __name__), nome)
    raise AttributeError(nome)


__all__ = sorted(_ESPORTA)
