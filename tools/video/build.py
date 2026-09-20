#!/usr/bin/env python3
"""
Erzeugt die vier Fernseher-Videos für die USB-Sticks.

    python3 tools/video/build.py            # alle vier
    python3 tools/video/build.py pizza      # nur eines

Ergebnis in video/ :
    1-Angebote.mp4  2-Pizza.mp4  3-Doener.mp4  4-Nudeln.mp4

Ablauf: Jede Bildschirmseite wird als HTML gebaut, mit Chromium zu einem
Standbild gerendert und anschließend in ffmpeg mit weichen Überblendungen
aneinandergereiht. Bewusst Standbilder statt Einzelbild-Animation — Text auf
einem Fernseher soll ruhig stehen und lesbar sein, nicht wandern.

Format: 1920x1080, 30 Bilder/s, H.264 (yuv420p) plus stille Tonspur. Diese
Kombination spielen praktisch alle Fernseher vom USB-Stick ab; manche Geräte
verweigern Dateien komplett ohne Tonspur, deshalb die stille Spur.
"""

import json
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import slides                                            # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
AUS = ROOT / "video"
TMP = ROOT / ".video-tmp"
D = slides.DATEN

FPS = 30
UEBERBLENDUNG = 0.8          # Sekunden
import imageio_ffmpeg
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


# ------------------------------------------------------------ Seitenfolgen --

def teile(liste, n):
    return [liste[i:i + n] for i in range(0, len(liste), n)]


def kategorie(kat_id):
    return next(k for k in D["kategorien"] if k["id"] == kat_id)


def folge_angebote():
    a = D["angebote"]
    s = []
    for g in a["gruppen"]:
        s.append((slides.angebotsseite(g, a["zusatz"]), 11))
        s.append((slides.logoseite(), 3))
    s.append((slides.stempelseite(D["stempelkarte"]), 10))
    s.append((slides.endseite(), 8))
    return s


def folge_karte(kat_id, titel, unterzeile, pbreite=132, akzent=None, standzeit=20):
    """Die ganze Kategorie steht auf einer Seite und bleibt lange stehen.
    Dazwischen nur kurze Einblendungen — Gaeste sollen ihr Gericht sofort
    finden und nicht darauf warten, dass die naechste Seite umblaettert."""
    k = kategorie(kat_id)
    karte = slides.volllisteseite(titel, unterzeile, k["items"],
                                  k.get("spaltenKurz"), pbreite)
    einschuebe = [(slides.logoseite(), 3)]
    if akzent:
        einschuebe.append((slides.spruchseite(*akzent), 4))
    einschuebe.append((slides.telefonseite(), 4))

    s = []
    for i, einschub in enumerate(einschuebe):
        s.append((karte, standzeit))
        s.append(einschub)
    s.append((slides.endseite(), 7))
    return s


VIDEOS = {
    "angebote": ("1-Angebote", folge_angebote),
    "pizza": ("2-Pizza", lambda: folge_karte(
        "pizza", "Pizza", "Alle Pizzen mit Tomaten- oder Sahnesoße und Käse",
        pbreite=124,
        akzent=("@@IMG@@/pizza-hero.jpg", 285, 285, "Frisch aus dem Ofen",
                "Jede Pizza wird bei uns frisch belegt und gebacken."))),
    "doener": ("3-Doener", lambda: folge_karte(
        "tuerkisch", "Türkische Spezialitäten", "Döner · Dürüm · Boxen · Teller",
        pbreite=150,
        akzent=("@@IMG@@/doener-hero.jpg", 341, 264, "Täglich frisch gedreht",
                "Dönerfleisch vom Spieß und frisches Fladenbrot."))),
    "nudeln": ("4-Nudeln", lambda: folge_karte(
        "nudeln", "Nudeln", "Rigatoni · Spaghetti · Tortellini — Überbacken: +1,50",
        pbreite=150, standzeit=18)),
}


# ----------------------------------------------------------------- Rendern --

def pfade_einsetzen(html_text):
    """Platzhalter durch echte Dateiadressen ersetzen."""
    # Platzhalter bewusst in doppelten geschweiften Klammern: ein blosses "QR"
    # hatte zuvor auch die Buchstaben im Wort "QR-Code" im Fliesstext ersetzt.
    ersetzungen = {
        "@@FONTS@@": (ROOT / "assets/fonts").as_uri(),
        "@@LOGO@@": (ROOT / "assets/img/logo.webp").as_uri(),
        "@@IMG@@": (ROOT / "assets/img").as_uri(),
        "@@QR@@": (ROOT / "qr/speisekarte-qr.png").as_uri(),
    }
    for k, v in ersetzungen.items():
        html_text = html_text.replace(k, v)
    return html_text


def rendern(seiten, ordner):
    """Jede Seite als HTML-Datei ablegen und aufrufen. Bewusst nicht über
    set_content: Chromium laedt aus einer so gesetzten Seite keine lokalen
    Bilder und Schriften, die Seiten blieben dann leer."""
    from playwright.sync_api import sync_playwright
    ordner.mkdir(parents=True, exist_ok=True)
    bilder = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = b.new_page(viewport={"width": slides.BREITE, "height": slides.HOEHE})
        for i, (html_text, _dauer) in enumerate(seiten):
            htm = ordner / f"seite-{i:02d}.html"
            htm.write_text(pfade_einsetzen(html_text), encoding="utf-8")
            pg.goto(htm.as_uri(), wait_until="load")
            pg.evaluate("() => document.fonts.ready")
            # Vollständige Karten automatisch so weit verkleinern, bis sie auf
            # den Bildschirm passen. Ohne das wuerde bei langen Beschreibungen
            # unten etwas abgeschnitten, ohne dass es jemand merkt.
            passt = pg.evaluate("""() => {
                const voll = document.getElementById('voll');
                if (!voll) return null;
                const wurzel = document.querySelector('.inhalt');
                const passtBei = s => {
                    wurzel.style.setProperty('--s', s.toFixed(3));
                    return voll.scrollHeight <= voll.clientHeight + 1
                        && document.body.scrollHeight <= window.innerHeight + 1;
                };
                // Groesste Schrift suchen, die noch passt. Nach oben gedeckelt,
                // damit kurze Kategorien wie Nudeln nicht ins Alberne wachsen.
                let unten = 0.40, oben = 1.60;
                if (!passtBei(unten)) return unten;
                for (let i = 0; i < 22; i++) {
                    const mitte = (unten + oben) / 2;
                    if (passtBei(mitte)) unten = mitte; else oben = mitte;
                }
                passtBei(unten);
                return unten;
            }""")
            if passt is not None:
                print(f"    Seite {i}: Schriftgroesse {passt:.0%}")
            fehlend = pg.evaluate(
                "() => [...document.images].filter(i => !i.complete || !i.naturalWidth)"
                ".map(i => i.src)")
            if fehlend:
                raise SystemExit(f"Bild laedt nicht auf Seite {i}: {fehlend}")
            pg.wait_for_timeout(150)
            datei = ordner / f"seite-{i:02d}.png"
            pg.screenshot(path=str(datei))
            bilder.append(datei)
        b.close()
    return bilder


def montieren(bilder, dauern, ziel):
    """Standbilder mit Überblendungen zu einem Video verketten."""
    eingaben, filter_teile = [], []
    for bild, dauer in zip(bilder, dauern):
        eingaben += ["-loop", "1", "-t", str(dauer), "-i", str(bild)]

    n = len(bilder)
    for i in range(n):
        filter_teile.append(
            f"[{i}:v]scale=1920:1080:flags=lanczos,format=yuv420p,fps={FPS},"
            f"setsar=1[v{i}]")

    # nacheinander überblenden; Versatz = bisherige Länge minus Überblendzeit
    kette, versatz = "[v0]", 0.0
    for i in range(1, n):
        versatz += dauern[i - 1] - UEBERBLENDUNG
        ziel_label = f"[x{i}]"
        filter_teile.append(
            f"{kette}[v{i}]xfade=transition=fade:duration={UEBERBLENDUNG}:"
            f"offset={versatz:.3f}{ziel_label}")
        kette = ziel_label

    filtergraph = ";".join(filter_teile)
    gesamt = sum(dauern) - UEBERBLENDUNG * (n - 1)

    befehl = [FFMPEG, "-y", *eingaben,
              "-f", "lavfi", "-t", f"{gesamt:.3f}", "-i",
              "anullsrc=channel_layout=stereo:sample_rate=48000",
              "-filter_complex", filtergraph,
              "-map", kette, "-map", f"{n}:a",
              "-c:v", "libx264", "-preset", "medium", "-crf", "20",
              "-profile:v", "high", "-level", "4.0", "-pix_fmt", "yuv420p",
              "-movflags", "+faststart", "-g", str(FPS * 2),
              "-c:a", "aac", "-b:a", "96k", "-shortest",
              str(ziel)]
    r = subprocess.run(befehl, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2500:])
        raise SystemExit(f"ffmpeg fehlgeschlagen für {ziel.name}")
    return gesamt


def bauen(schluessel):
    name, macher = VIDEOS[schluessel]
    seiten = macher()
    print(f"\n{name}: {len(seiten)} Seiten")
    ordner = TMP / schluessel
    if ordner.exists():
        shutil.rmtree(ordner)
    bilder = rendern(seiten, ordner)
    AUS.mkdir(exist_ok=True)
    ziel = AUS / f"{name}.mp4"
    laenge = montieren(bilder, [d for _, d in seiten], ziel)
    mb = ziel.stat().st_size / 1024 / 1024
    print(f"  -> {ziel.name}  {laenge:.0f} s  {mb:.1f} MB")
    return ziel


if __name__ == "__main__":
    wunsch = sys.argv[1:] or list(VIDEOS)
    for w in wunsch:
        if w not in VIDEOS:
            raise SystemExit(f"Unbekannt: {w}. Möglich: {', '.join(VIDEOS)}")
        bauen(w)
    if TMP.exists():
        shutil.rmtree(TMP)
    print("\nFertig. Dateien liegen in video/")
