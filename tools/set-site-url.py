#!/usr/bin/env python3
"""
Setzt die Adresse der Speisekarte an allen Stellen im Projekt auf einmal.

    python3 tools/set-site-url.py https://akpinardonerpizza.pages.dev/

Danach die QR-Codes und Druckvorlagen neu erzeugen:

    python3 qr/generate_qr.py

Hintergrund: Die Adresse steckt an mehreren Stellen — im QR-Generator, in den
Druckvorlagen (als lesbarer Text unter dem Code), in der canonical-URL der
Seite und in der README. Wird eine davon vergessen, zeigen gedruckte Kärtchen
und Website auf verschiedene Ziele. Dieses Skript hält sie zusammen.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def stellen(url: str):
    """(Datei, Suchmuster, Ersatz) für jede Stelle, an der die Adresse steht."""
    schlicht = re.sub(r"^https?://", "", url).rstrip("/")
    return [
        ("qr/generate_qr.py",
         r'DEFAULT_URL = "[^"]*"',
         f'DEFAULT_URL = "{url}"'),
        ("qr/tischaufsteller.html",
         r'<p class="url">[^<]*</p>',
         f'<p class="url">{schlicht}</p>'),
        ("index.html",
         r'<link rel="canonical" href="[^"]*">',
         f'<link rel="canonical" href="{url}">'),
        ("index.html",
         r'<meta property="og:url" content="[^"]*">',
         f'<meta property="og:url" content="{url}">'),
        # og:image muss absolut sein, sonst zeigt WhatsApp beim Teilen kein Logo
        ("index.html",
         r'<meta property="og:image" content="[^"]*">',
         f'<meta property="og:image" content="{url}assets/img/logo.webp">'),
        ("README.md",
         r'\*\*Adresse der Seite:\*\* <[^>]*>',
         f'**Adresse der Seite:** <{url}>'),
    ]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip())
        return 2

    url = sys.argv[1]
    if not url.startswith(("http://", "https://")):
        print("Die Adresse muss mit http:// oder https:// beginnen.")
        return 2
    if not url.endswith("/"):
        url += "/"

    geaendert = 0
    for datei, muster, ersatz in stellen(url):
        p = ROOT / datei
        if not p.exists():
            print(f"  übersprungen (fehlt): {datei}")
            continue
        alt = p.read_text(encoding="utf-8")
        neu, n = re.subn(muster, ersatz, alt)
        if n:
            p.write_text(neu, encoding="utf-8")
            geaendert += n
            print(f"  {datei}: {n}x gesetzt")

    if not geaendert:
        print("Nichts geändert — stehen die Muster noch so im Projekt?")
        return 1

    print(f"\n{geaendert} Stellen auf {url} gesetzt.")
    print("Jetzt noch:  python3 qr/generate_qr.py")

    # Rest-Suche: meldet Adressen, die auf ein anderes Ziel zeigen. Treffer
    # unterhalb der neuen Adresse (etwa das og:image) sind in Ordnung, ebenso
    # das Beispiel in diesem Skript selbst.
    rest = []
    for p in ROOT.rglob("*"):
        if not (p.is_file() and p.suffix in {".html", ".md", ".py", ".json", ".yml"}):
            continue
        if ".git" in p.parts or p.name == pathlib.Path(__file__).name:
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        for treffer in re.findall(r"https?://[\w.-]*(?:github\.io|pages\.dev)[\w./-]*", t):
            if not treffer.startswith(url.rstrip("/")):
                rest.append(f"{p.relative_to(ROOT)}: {treffer}")
    if rest:
        print("\nHinweis — diese Adressen stehen noch im Projekt:")
        for r in sorted(set(rest)):
            print(f"  {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
