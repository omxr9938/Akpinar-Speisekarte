#!/usr/bin/env python3
"""
Erzeugt die QR-Codes für die Online-Speisekarte von Akpinar Döner & Pizza.

    python3 qr/generate_qr.py
    python3 qr/generate_qr.py --url https://www.meine-domain.de/

Ausgabe (im Ordner qr/):
    speisekarte-qr.svg        Vektor, mit Logo-Feld — für den Druck
    speisekarte-qr.png        1200 px, mit Logo-Feld — für Web/WhatsApp
    speisekarte-qr-plain.svg  Vektor, ohne Logo — maximale Lesbarkeit
    speisekarte-qr-plain.png  1200 px, ohne Logo
    url.txt                   die hinterlegte Adresse

Alle Codes nutzen Fehlerkorrektur-Stufe H (30 %), damit das Logo in der Mitte
die Lesbarkeit nicht beeinträchtigt.
"""

import argparse
import pathlib
import sys

try:
    import segno
except ImportError:
    sys.exit("Bitte zuerst installieren:  pip install segno pillow")

HERE = pathlib.Path(__file__).resolve().parent

# Adresse der veröffentlichten Speisekarte. Bei eigener Domain hier ändern
# (oder --url benutzen) und das Skript erneut ausführen.
DEFAULT_URL = "https://akpinardonerpizza.pages.dev/"

DARK = "#0c0a09"   # Modulfarbe — dunkel, wie die Speisekarte
LIGHT = "#ffffff"  # Hintergrund — für den Scan immer hell lassen
GOLD = "#c8912f"


def build(url: str) -> None:
    qr = segno.make(url, error="h", micro=False)
    print(f"QR-Version {qr.version}, Fehlerkorrektur {qr.error.upper()}")

    # --- schlichte Varianten (höchste Scan-Sicherheit) --------------------
    qr.save(HERE / "speisekarte-qr-plain.svg", scale=10, border=4,
            dark=DARK, light=LIGHT)
    qr.save(HERE / "speisekarte-qr-plain.png", scale=40, border=4,
            dark=DARK, light=LIGHT)

    # --- Varianten mit freigestelltem Logo-Feld in der Mitte --------------
    _with_logo_svg(qr, HERE / "speisekarte-qr.svg", url)
    _with_logo_png(qr, HERE / "speisekarte-qr.png")

    (HERE / "url.txt").write_text(url + "\n", encoding="utf-8")

    for f in sorted(HERE.glob("speisekarte-qr*")):
        print(f"  {f.name:28} {f.stat().st_size // 1024:4} KB")


def _logo_box(qr):
    """Größe und Position des Logo-Feldes in Modulen (ca. 20 % der Fläche)."""
    size = qr.symbol_size(scale=1, border=0)[0]
    box = max(5, round(size * 0.22))
    if (size - box) % 2:          # mittig auf dem Modulraster halten
        box += 1
    start = (size - box) // 2
    return size, box, start


def _with_logo_svg(qr, path, url):
    """QR als SVG, mit ausgespartem Feld und goldenem »A« in der Mitte."""
    size, box, start = _logo_box(qr)
    border = 4
    total = size + 2 * border

    rows = []
    for y, row in enumerate(qr.matrix):
        for x, bit in enumerate(row):
            if not bit:
                continue
            # Module unter dem Logo weglassen
            if start <= x < start + box and start <= y < start + box:
                continue
            rows.append(f'<rect x="{x + border}" y="{y + border}" width="1" height="1"/>')

    cx = border + size / 2
    r = box / 2

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}"
     width="{total * 10}" height="{total * 10}" shape-rendering="crispEdges">
  <title>Speisekarte Akpinar Döner &amp; Pizza</title>
  <desc>{url}</desc>
  <rect width="{total}" height="{total}" fill="{LIGHT}"/>
  <g fill="{DARK}">
    {chr(10).join("    " + r_ for r_ in rows)}
  </g>
  <circle cx="{cx}" cy="{cx}" r="{r:.3f}" fill="{LIGHT}"/>
  <circle cx="{cx}" cy="{cx}" r="{r - 0.45:.3f}" fill="{DARK}"/>
  <text x="{cx}" y="{cx}" fill="{GOLD}" font-family="Georgia, 'Times New Roman', serif"
        font-size="{box * 0.62:.3f}" font-weight="bold" text-anchor="middle"
        dominant-baseline="central">A</text>
</svg>
'''
    path.write_text(svg, encoding="utf-8")


def _with_logo_png(qr, path):
    """QR als PNG, mit demselben ausgesparten Logo-Feld."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  (Pillow fehlt — PNG mit Logo wird übersprungen)")
        return

    scale, border = 40, 4
    size, box, start = _logo_box(qr)
    total = (size + 2 * border) * scale

    img = Image.new("RGB", (total, total), LIGHT)
    d = ImageDraw.Draw(img)

    for y, row in enumerate(qr.matrix):
        for x, bit in enumerate(row):
            if not bit:
                continue
            if start <= x < start + box and start <= y < start + box:
                continue
            x0 = (x + border) * scale
            y0 = (y + border) * scale
            d.rectangle([x0, y0, x0 + scale - 1, y0 + scale - 1], fill=DARK)

    cx = (border + size / 2) * scale
    r = (box / 2) * scale
    d.ellipse([cx - r, cx - r, cx + r, cx + r], fill=LIGHT)
    d.ellipse([cx - r + 6, cx - r + 6, cx + r - 6, cx + r - 6], fill=DARK)

    fs = int(box * scale * 0.6)
    font = None
    for cand in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"):
        if pathlib.Path(cand).exists():
            font = ImageFont.truetype(cand, fs)
            break
    if font is None:
        font = ImageFont.load_default()

    d.text((cx, cx), "A", fill=GOLD, font=font, anchor="mm")
    img.save(path, optimize=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=DEFAULT_URL,
                    help=f"Adresse hinter dem QR-Code (Standard: {DEFAULT_URL})")
    args = ap.parse_args()
    print(f"Ziel: {args.url}")
    build(args.url)
