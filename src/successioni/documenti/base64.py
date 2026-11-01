"""Contenuto Base64 e dati dell'allegato EG secondo ``reg:FileAttachment_Type``.

Fonte: ``fonti/Specifiche tecniche/SUC13_20250702/registro/xsd/typesReg_v2.xsd`` righe 419-431 (riprodotto in
Specifiche_SUC13_20250702.pdf p.794-796) e ``FileType_Type`` riga 3177 (p.795 e p.902)::

    <xs:complexType name="FileAttachment_Type">
      <xs:sequence>
        <xs:element name="FileType" type="reg:FileType_Type"/>          application/pdf | image/tif | image/tiff
        <xs:element name="FileName">  restriction base="cm:DatoAN_Type", maxLength 100
        <xs:element name="FileDescription" type="cm:DatoAN_Type" minOccurs="0"/>
        <xs:element name="ImageData" type="xs:base64Binary" xmime:expectedContentTypes="application/octet-stream"/>

Usato in ``Dichiarazione_SUC_Type/QuadroEG/<Sezione>/<Sezione>All`` (fornituraSUC13_v1.xsd righe 1173-1308; p.263-281
del PDF): DichSostAll, TestamentoAll, InventarioAll, CertificazioneImpostaVersataEsteroAll, DocumentiPassivitaAll,
AlberoGenealogicoAll, DocumentiIdentitaAll, AltroAll, PrimaCasaAll, AgevolazioniImposteIpocatastaliAll,
RiduzioniImposteSuccessioneAll (tutti ``maxOccurs="unbounded"``).

* ``ImageData``: ``xs:base64Binary`` SENZA faccette: nessuna lunghezza massima e nessun pattern nello schema. Il limite
  pratico viene da Specifiche p.7 (5 MB per file allegato) e p.3 (40 MB compressi per fornitura). Si produce la forma
  canonica XSD (alfabeto RFC 2045, padding '=', nessun a capo): 4*ceil(n/3) caratteri per n byte.
* ``FileName`` e ``FileDescription``: ``cm:DatoAN_Type`` di ``common/xsd/typesDati_v2.xsd`` riga 13-20 (incluso da
  fornitura_v2.xsd, importato da typesReg_v2.xsd): SOLO maiuscole, cifre e alcuni segni; niente minuscole ne'
  trattino basso. ``FileName`` ha in piu' ``maxLength 100``.
"""
from __future__ import annotations

import binascii
import re
from pathlib import Path

from ..schema import Errore
from . import limiti as L

ELEMENTI_EG_ALLEGATO = (
    "DichSostAll", "TestamentoAll", "InventarioAll", "CertificazioneImpostaVersataEsteroAll",
    "DocumentiPassivitaAll", "AlberoGenealogicoAll", "DocumentiIdentitaAll", "AltroAll", "PrimaCasaAll",
    "AgevolazioniImposteIpocatastaliAll", "RiduzioniImposteSuccessioneAll",
)
FONTE_IMAGEDATA = "typesReg_v2.xsd FileAttachment_Type/ImageData xs:base64Binary (Specifiche_SUC13_20250702.pdf p.796)"
FONTE_FILENAME = ("typesReg_v2.xsd FileAttachment_Type/FileName: cm:DatoAN_Type (typesDati_v2.xsd) maxLength 100 "
                  "(Specifiche_SUC13_20250702.pdf p.794-795)")
FONTE_FILETYPE = "typesReg_v2.xsd FileType_Type (Specifiche_SUC13_20250702.pdf p.795, p.902)"

# Pattern XSD di cm:DatoAN_Type (typesDati_v2.xsd riga 18), valore dopo lo scioglimento delle entita' XML:
PATTERN_DATO_AN_XSD = ("([0-9A-Z\\-]|\"){1}([0-9A-Z&]|'|\\-|\\.|,|\\s|/|°|\\^|\\(|\\)|À|È|É|Ì|Ò|Ù|Ü|\"|\\\\|\\||\\+)*")
# Traduzione Python: in XSD '\s' vale [#x20\t\n\r] e il pattern e' implicitamente ancorato (fullmatch).
_RE_DATO_AN = re.compile(PATTERN_DATO_AN_XSD.replace("\\s", "[ \\t\\n\\r]"))
_CARATTERE_AMMESSO = re.compile("[0-9A-Z&'\\-., \t\n\r/°^()ÀÈÉÌÒÙÜ\"\\\\|+]")
_PRIMO_AMMESSO = re.compile('[0-9A-Z\\-"]')
_SPAZI_XML = re.compile(r"[ \t\n\r]+")


# ------------------------------------------------------------------------------------------------ Base64

def lunghezza_base64(n_byte: int) -> int:
    """Caratteri della forma canonica per ``n_byte`` byte (nessun a capo)."""
    return 4 * ((n_byte + 2) // 3)


def codifica_base64(dati: bytes) -> str:
    """Forma canonica xs:base64Binary: alfabeto RFC 2045 con '=' di riempimento, senza a capo."""
    return binascii.b2a_base64(dati, newline=False).decode("ascii")


def incorpora_base64(percorso: Path | str) -> str:
    """Legge il file cosi' com'e' (nessuna conversione) e restituisce il testo per ``ImageData``."""
    return codifica_base64(Path(percorso).read_bytes())


def decodifica_base64(testo: str) -> bytes:
    """Decodifica rigorosa: ammette solo gli spazi XML (#x20, TAB, CR, LF) che il tipo XSD tollera.

    Solleva ``ValueError`` su caratteri fuori alfabeto o riempimento errato."""
    pulito = _SPAZI_XML.sub("", testo)
    try:
        return binascii.a2b_base64(pulito.encode("ascii"), strict_mode=True)
    except (binascii.Error, UnicodeEncodeError) as e:
        raise ValueError(f"Base64 non valido: {e}") from None


# ---------------------------------------------------------------------------------------- nomi e tipi

def valida_nome_file_eg(nome: str, percorso: str = "FileName", *, lunghezza_max: int | None = L.NOME_FILE_EG_MAX
                        ) -> list[Errore]:
    """Controlla ``FileName`` (o ``FileDescription`` con ``lunghezza_max=None``) rispetto all'XSD."""
    err: list[Errore] = []
    if not isinstance(nome, str) or not nome:
        return [Errore("ALLEGATO_NOME_NON_VALIDO", percorso, "nome mancante", FONTE_FILENAME)]
    if lunghezza_max is not None and len(nome) > lunghezza_max:
        err.append(Errore("ALLEGATO_NOME_NON_VALIDO", percorso,
                          f"{len(nome)} caratteri: massimo {lunghezza_max}", FONTE_FILENAME))
    if not _RE_DATO_AN.fullmatch(nome):
        cattivi = sorted({c for c in nome if not _CARATTERE_AMMESSO.fullmatch(c)})
        dett = f"caratteri non ammessi: {''.join(cattivi)!r}" if cattivi else "primo carattere non ammesso"
        err.append(Errore("ALLEGATO_NOME_NON_VALIDO", percorso,
                          f"non rispetta cm:DatoAN_Type (solo maiuscole, cifre e alcuni segni): {dett}",
                          FONTE_FILENAME))
    return err


def _normalizza_dato_an(testo: str, lunghezza_max: int | None, conserva_estensione: bool) -> str:
    out = "".join(c if c == " " or (_CARATTERE_AMMESSO.fullmatch(c) and c not in "\t\n\r") else "-"
                  for c in testo.upper())
    out = re.sub(r"-{2,}", "-", out).strip(" ")
    if not out or not _PRIMO_AMMESSO.fullmatch(out[0]):
        out = "ALLEGATO-" + out.lstrip("-. ")
    if lunghezza_max is not None and len(out) > lunghezza_max:
        stem, punto, est = out.rpartition(".")
        if conserva_estensione and punto and 0 < len(est) <= 5:
            out = stem[: lunghezza_max - len(est) - 1].rstrip() + "." + est
        else:
            out = out[:lunghezza_max].rstrip()
    return out


def normalizza_nome_file_eg(nome: str, *, lunghezza_max: int = L.NOME_FILE_EG_MAX) -> str:
    """Rende ``nome`` conforme a cm:DatoAN_Type: maiuscolo, caratteri non ammessi -> '-', estensione conservata."""
    return _normalizza_dato_an(Path(nome).name, lunghezza_max, True)


def normalizza_descrizione_eg(testo: str) -> str:
    """``FileDescription``: stesso tipo cm:DatoAN_Type, senza limite di lunghezza nell'XSD."""
    return _normalizza_dato_an(testo, None, False)


def tipo_file_eg(dati_o_percorso: bytes | Path | str) -> str | None:
    """FileType dal contenuto (non dall'estensione): 'application/pdf', 'image/tiff' oppure None se non ammesso."""
    dati = dati_o_percorso if isinstance(dati_o_percorso, bytes) else Path(dati_o_percorso).read_bytes()[:8]
    if dati.startswith(b"%PDF-"):
        return "application/pdf"
    if dati[:4] in (b"II*\x00", b"MM\x00*"):
        return "image/tiff"
    return None


def dati_file_attachment(percorso: Path | str, *, nome: str | None = None, descrizione: str | None = None,
                         file_type: str | None = None) -> dict:
    """Valori per un elemento ``reg:FileAttachment_Type`` (la serializzazione XML spetta al modulo telematico).

    Il nome e la descrizione sono normalizzati per cm:DatoAN_Type; il tipo e' ricavato dal contenuto se non indicato.
    Solleva ``ValueError`` se il contenuto non e' PDF o TIFF o se il tipo indicato non e' tra quelli dell'XSD."""
    p = Path(percorso)
    contenuto = p.read_bytes()
    rilevato = tipo_file_eg(contenuto)
    if rilevato is None:
        raise ValueError("contenuto non PDF ne' TIFF: non allegabile (" + L.FONTE_FORMATI + ")")
    if file_type is not None:
        if file_type not in L.TIPI_FILE_EG:
            raise ValueError(f"FileType {file_type!r} non ammesso: {L.TIPI_FILE_EG} ({FONTE_FILETYPE})")
        if (file_type == "application/pdf") != (rilevato == "application/pdf"):
            raise ValueError(f"FileType {file_type!r} non coerente con il contenuto ({rilevato})")
    out = {"FileType": file_type or rilevato, "FileName": normalizza_nome_file_eg(nome or p.name)}
    if descrizione:
        out["FileDescription"] = normalizza_descrizione_eg(descrizione)
    out["ImageData"] = codifica_base64(contenuto)
    return out
