"""Limiti dimensionali e formati dell'allegato, con la fonte esatta.

Fonte: ``fonti/Specifiche tecniche/Specifiche_SUC13_20250702.pdf`` (versione 2 luglio 2025).

* p.7, par. 2.3 "Gli allegati": "Sono accettati documenti con formato file: TIF e/o TIFF e PDF/A (PDF/A-1a o
  PDF/A-1b)." ... "Ogni file allegato non deve superare la dimensione massima di 5 MB. Nel caso in cui il file superi
  la dimensione massima e' necessario suddividerlo in piu' file."
* p.7, par. 2.3, formato TIFF: "E' necessario utilizzare una risoluzione non superiore a 300 DPI, selezionare il
  colore B/N e specificare la Compressione CCITT Group IV (modalita' Fax)."
* p.3, par. 1: "la dimensione complessiva delle dichiarazioni di successione da trasmettere non puo' eccedere il
  limite previsto di 40 MB compressi." e "La fornitura deve contenere i dati relativi ad una sola dichiarazione."
* p.794-795 (typesReg_v2.xsd, FileAttachment_Type): FileType in {application/pdf, image/tif, image/tiff},
  FileName max 100 caratteri e pattern DatoAN_Type, ImageData di tipo xs:base64Binary senza altre faccette.
* ``fonti/Istruzioni/Succ_FASCICOLO_I_Nov_23.pdf`` p.49 (quadro EG): "La documentazione da allegare deve avere una
  bassa risoluzione (200x200dpi, colore Bianco e Nero), purche' leggibile" - indicazione di prassi, piu' severa
  dei 300 DPI delle specifiche tecniche.

INCOGNITE (non risolte dalle fonti locali, da accertare con CIVIS / software di controllo):
  1. unita' di "MB": decimale (10^6) o binaria (2^20)? Il codice usa il valore DECIMALE (piu' severo) come predefinito;
  2. a quale oggetto si riferisce il limite di 5 MB: al file prima della codifica Base64 (ipotesi adottata) o ai
     caratteri Base64 nell'XML (+33%)?
  3. "40 MB compressi": formato di compressione, e se si misura l'XML con gli allegati Base64 compressi o il solo
     insieme degli allegati binari. Le specifiche non lo dicono.
"""
from __future__ import annotations

# Unita' alternative (l'unita' effettiva e' un'incognita, vedi sopra).
MB_DECIMALE = 1000 * 1000
MB_BINARIO = 1024 * 1024
UNITA = {"decimale": MB_DECIMALE, "binaria": MB_BINARIO}

LIMITE_ALLEGATO_MB = 5      # Specifiche_SUC13_20250702.pdf p.7 par. 2.3
LIMITE_FORNITURA_MB = 40    # Specifiche_SUC13_20250702.pdf p.3 par. 1 ("compressi")

LIMITE_ALLEGATO_DECIMALE = LIMITE_ALLEGATO_MB * MB_DECIMALE
LIMITE_ALLEGATO_BINARIO = LIMITE_ALLEGATO_MB * MB_BINARIO
LIMITE_FORNITURA_DECIMALE = LIMITE_FORNITURA_MB * MB_DECIMALE
LIMITE_FORNITURA_BINARIO = LIMITE_FORNITURA_MB * MB_BINARIO

# XSD typesReg_v2.xsd, FileAttachment_Type (righe 419-431) e FileType_Type (riga 3177).
TIPI_FILE_EG = ("application/pdf", "image/tif", "image/tiff")
NOME_FILE_EG_MAX = 100

# TIFF (specifiche p.7).
TIFF_DPI_MAX = 300
TIFF_COMPRESSIONE = "CCITT Group IV"

# Indicazione di prassi (Fascicolo 1 p.49).
DPI_PRASSI = 200

FONTE_ALLEGATO = "Specifiche_SUC13_20250702.pdf p.7 par. 2.3 (max 5 MB per file allegato)"
FONTE_FORNITURA = "Specifiche_SUC13_20250702.pdf p.3 par. 1 (max 40 MB compressi, una sola dichiarazione)"
FONTE_FORMATI = "Specifiche_SUC13_20250702.pdf p.7 par. 2.3 (TIF/TIFF e PDF/A-1a/1b)"
FONTE_TIFF = "Specifiche_SUC13_20250702.pdf p.7 par. 2.3 (TIFF: max 300 DPI, B/N, CCITT Group IV)"
FONTE_FILEATTACHMENT = "typesReg_v2.xsd FileAttachment_Type (Specifiche_SUC13_20250702.pdf p.794-795)"
