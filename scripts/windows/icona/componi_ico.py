"""Unisce i PNG generati da genera_icona.js in scripts/windows/successioni.ico (una immagine per misura, non ridimensionata)."""
from pathlib import Path

from PIL import Image

QUI = Path(__file__).resolve().parent
MISURE = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
immagini = [Image.open(QUI / "png" / f"{s}.png").convert("RGBA") for s in MISURE]
dest = QUI.parent / "successioni.ico"
immagini[-1].save(dest, format="ICO", sizes=[(s, s) for s in MISURE], append_images=immagini[:-1])
print(dest)
