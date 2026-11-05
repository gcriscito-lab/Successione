"""Compila src/successioni/collegamenti/java/StampaModello.java (Java 8) contro il componente di controllo SUC13.

Uso: python scripts/compila_stampa.py [--jdk <cartella JDK>] [--componente <cartella controlli SUC13>]
Servono un JDK (javac) e la cartella del componente (SUCCESSIONI_CONTROLLI_SUC13). Il risultato, StampaModello.class, e' versionato:
a runtime basta un JRE 8 (lo stesso del controllo)."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1] / "src/successioni/collegamenti/java"
ap = argparse.ArgumentParser()
ap.add_argument("--jdk", default=os.environ.get("JAVA_HOME") or r"C:\Program Files\Java\jdk-23")
ap.add_argument("--componente", default=os.environ.get("SUCCESSIONI_CONTROLLI_SUC13"))
a = ap.parse_args()
if not a.componente:
    sys.exit("indicare --componente o SUCCESSIONI_CONTROLLI_SUC13")
javac = Path(a.jdk) / "bin" / ("javac.exe" if os.name == "nt" else "javac")
subprocess.run([str(javac), "--release", "8", "-nowarn", "-cp", str(Path(a.componente) / "*"), "-d", str(R), str(R / "StampaModello.java")], check=True)
print("compilato:", R / "StampaModello.class")
