#!/usr/bin/env python3
"""
Hängt an CSS, JavaScript und Speisekarten-Daten eine Versionskennung an, die
sich aus dem Dateiinhalt ergibt:

    assets/css/styles.css  ->  assets/css/styles.css?v=a1b2c3d4

    python3 tools/stamp-assets.py

Warum: Die Dateinamen ändern sich nie. Ohne Kennung liefert jeder
Zwischenspeicher — Browser wie CDN — nach einer Änderung weiter die alte
Fassung aus, und Korrekturen kommen bei Gästen erst Stunden später an. Mit
Kennung ändert sich bei jeder Änderung die Adresse, die alte Fassung wird
nie wieder angefragt, und die Dateien dürfen trotzdem lange gespeichert
bleiben.

Nach jeder Änderung an CSS, JS oder menu.json ausführen, vor dem Commit.
"""

import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def kennung(pfad: pathlib.Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()[:8]


def stempeln(datei: pathlib.Path, muster: str, ziel: pathlib.Path) -> int:
    """Ersetzt den Verweis auf `ziel` in `datei` durch einen mit Kennung."""
    if not ziel.exists():
        print(f"  fehlt: {ziel.relative_to(ROOT)}")
        return 0
    v = kennung(ziel)
    text = datei.read_text(encoding="utf-8")
    neu, n = re.subn(muster, lambda m: f"{m.group(1)}?v={v}", text)
    if n and neu != text:
        datei.write_text(neu, encoding="utf-8")
    return n, v


def main() -> int:
    index = ROOT / "index.html"
    appjs = ROOT / "assets/js/app.js"

    aufgaben = [
        # Nur Verweise in Anfuehrungszeichen stempeln - sonst landet die Kennung
        # auch in Kommentaren, die denselben Pfad nennen.
        (index, r'("assets/css/styles\.css)(?:\?v=[0-9a-f]+)?(?=")', ROOT / "assets/css/styles.css"),
        (index, r'("assets/js/app\.js)(?:\?v=[0-9a-f]+)?(?=")',      appjs),
        (appjs, r"('assets/data/menu\.json)(?:\?v=[0-9a-f]+)?(?=')", ROOT / "assets/data/menu.json"),
    ]

    # app.js zuletzt hashen, denn sein Inhalt ändert sich durch den ersten Stempel
    reihenfolge = [aufgaben[0], aufgaben[2], aufgaben[1]]

    for datei, muster, ziel in reihenfolge:
        n, v = stempeln(datei, muster, ziel)
        print(f"  {ziel.relative_to(ROOT)} -> v={v}  ({n}x in {datei.name})")

    print("\nFertig. Die Adressen ändern sich nur, wenn sich der Inhalt ändert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
