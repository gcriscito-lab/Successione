#!/usr/bin/env python3
"""Ripristina le skill di sviluppo in .claude/skills/ dai commit registrati (docs/SKILLS_SETUP.md).

Uso: python scripts/installa_skills.py [--verifica]
Scarica in una cartella temporanea (dati non fidati, solo copia di file di testo), non esegue nulla
di scaricato. La skill `pdf` NON viene copiata: licenza proprietaria, si usa quella dell'account claude.ai.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
DEST = RADICE / ".claude" / "skills"
FONTI = {
    "anthropics": ("https://github.com/anthropics/skills", "ca45fc496a3436251f191354091d557da31c15b5", "Apache-2.0"),
    "superpowers": ("https://github.com/obra/superpowers", "2ce8aa15d05bd57213e6f746f953aafb7ded7a8b", "MIT"),
}
# (fonte, nome, file da copiare oppure None = intera cartella)
SKILL = [
    ("anthropics", "mcp-builder", None),
    ("anthropics", "webapp-testing", None),
    ("superpowers", "dispatching-parallel-agents", ["SKILL.md"]),
    ("superpowers", "verification-before-completion", ["SKILL.md"]),
    ("superpowers", "systematic-debugging",
     ["SKILL.md", "condition-based-waiting.md", "defense-in-depth.md", "root-cause-tracing.md"]),
]


def verifica() -> int:
    ko = 0
    for _, nome, _ in SKILL:
        s = DEST / nome / "SKILL.md"
        ok = s.is_file() and s.read_text(encoding="utf-8").startswith("---")
        print(("OK  " if ok else "MANCA"), nome)
        ko += not ok
    return 1 if ko else 0


def installa() -> int:
    with tempfile.TemporaryDirectory() as t:
        clone = {}
        for k, (url, commit, _) in FONTI.items():
            d = Path(t) / k
            subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", url, str(d)], check=True)
            subprocess.run(["git", "-C", str(d), "checkout", "-q", commit], check=True)
            clone[k] = d
        for k, nome, files in SKILL:
            src = clone[k] / "skills" / nome
            dst = DEST / nome
            if dst.exists():
                shutil.rmtree(dst)
            if files is None:
                shutil.copytree(src, dst)
            else:
                dst.mkdir(parents=True)
                for f in files:
                    shutil.copy2(src / f, dst / f)
            lic = clone[k] / "LICENSE"
            if k == "superpowers":
                shutil.copy2(lic, dst / "LICENSE")
            url, commit, licenza = FONTI[k]
            (dst / "SOURCE.txt").write_text(
                f"Fonte: {url} (skills/{nome})\nCommit: {commit}\nLicenza: {licenza}. Copia non modificata.\n",
                encoding="utf-8")
    print("Skill ripristinate in", DEST, "- eseguire /reload-skills nella sessione Claude Code.")
    return verifica()


if __name__ == "__main__":
    sys.exit(verifica() if "--verifica" in sys.argv else installa())
