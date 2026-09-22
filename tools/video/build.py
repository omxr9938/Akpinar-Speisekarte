#!/usr/bin/env python3
"""
Erzeugt die vier Fernseher-Videos für die USB-Sticks.

    python3 tools/video/build.py            # alle vier
    python3 tools/video/build.py pizza      # nur eines

Ergebnis in video/ :
    1-Angebote.mp4  2-Pizza.mp4  3-Tuerkisch.mp4
    4-Nudeln-Verschiedenes-Burger.mp4

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
STICK = AUS / "stick"          # die langen Dateien fuer die USB-Sticks
TMP = ROOT / ".video-tmp"
D = slides.DATEN

FPS = 30

# Jeder Bildschirm ist ein stehendes Bild. DAUER ist die Laenge eines
# Durchlaufs, WIEDERHOLUNGEN legt ihn mehrfach in dieselbe Datei.
#
# Der Fernseher blendet kurz schwarz, wenn er die Datei am Ende neu aufzieht -
# er baut dabei seinen Decoder neu auf, das laesst sich in der Datei nicht
# abschalten. Weil vor und nach dem Umbruch aber dasselbe Bild steht, faellt
# es kaum noch auf; die Wiederholungen machen aus "alle 72 Sekunden" zusaetzlich
# "alle zwoelf Minuten".
#
# GOP: Bei einem stehenden Bild kostet nur das Schluesselbild etwas, die Bilder
# dazwischen sind praktisch leer. Ein langer Abstand macht die Datei darum um
# ein Vielfaches kleiner, ohne dass man etwas sieht - gesprungen wird in diesen
# Dateien ohnehin nie.
DAUER = 72.0                 # Sekunden je Durchlauf
WIEDERHOLUNGEN = 10          # Durchlaeufe je Datei
GOP = FPS * 5                # Schluesselbild alle fuenf Sekunden

import imageio_ffmpeg
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


# ------------------------------------------------------------ Seitenfolgen --

def kategorie(kat_id):
    return next(k for k in D["kategorien"] if k["id"] == kat_id)



BESTELL = json.loads((ROOT / "assets/data/bestellung.json").read_text(encoding="utf-8"))


# Telefonnummer und Adresse stehen bewusst nicht mehr drauf: Die Bildschirme
# haengen im Laden. Wer davorsteht, ruft nicht an und sucht nicht die Adresse.
# Stattdessen Dinge, die er noch nicht weiss - Stempelkarte, Lieferdienst,
# Oeffnungszeiten.
#
# Auf den Kartenbildschirmen laeuft kein Angebotsstreifen mehr: Das
# Mittagsangebot hat mit Bildschirm 1 einen eigenen Fernseher, gross und
# vollstaendig. Es unten noch einmal durchlaufen zu lassen, waere dieselbe
# Information zweimal - und nimmt den Dingen Platz weg, die sonst nirgends
# stehen.
#
# Die langen Plaetze bekommen deshalb die beiden Angaben, die einen Gast
# wirklich wiederbringen: die Stempelkarte und der Lieferdienst.
def block(kat_id, titel=None, pbreite=132):
    """Ein Kartenblock fuer volllisteseite: (Ueberschrift, Gerichte, Legende,
    Preisspaltenbreite, Kategoriehinweis). titel=None heisst: einzelne
    Kategorie, keine Zwischenueberschrift."""
    k = kategorie(kat_id)
    hinweis = k.get("hinweis", "") if titel else ""
    return (titel, k["items"], k.get("spaltenKurz"), pbreite, hinweis)


# Jeder Bildschirm ist EIN stehendes Bild. Kein Logo, keine Ueberschrift, kein
# wechselnder Streifen unten - die haben zusammen rund 300 der 1080 Zeilen
# gekostet und dem Gast nichts gesagt, was er nicht schon wusste: Er steht im
# Laden, vor der Theke, unter dem Bildschirm.
#
# Dass nichts mehr wechselt, loest nebenbei das Schwarzblenden beim Neustart
# vollstaendig: Vor und nach dem Umbruch steht dasselbe Bild.
#
# Einzige Ausnahme ist die Ueberschrift "Mittagsangebot" auf Bildschirm 1.
# Die sagt etwas, was man dem Bild sonst nicht ansieht - dass diese Preise
# nur mittags gelten.
VIDEOS = {
    "angebote": ("1-Angebote",
                 lambda: slides.alleangeboteseite(ohne=("Familien-Pizza",))),

    "pizza": ("2-Pizza",
              lambda: slides.volllisteseite([block("pizza", pbreite=124)])),

    "tuerkisch": ("3-Tuerkisch",
                  lambda: slides.volllisteseite(
                      [block("tuerkisch", pbreite=150)],
                      notiz=slides.notiz_menue(BESTELL["zutaten"]["tuerkisch"],
                                               kategorie("tuerkisch")["items"]))),

    "nudeln": ("4-Nudeln-Verschiedenes-Burger",
               lambda: slides.volllisteseite(
                   [block("nudeln", "Nudeln", 150),
                    block("verschiedenes", "Verschiedenes", 150),
                    block("burger", "Burger", 132)])),

    # Salate und Getraenke haben keinen eigenen Bildschirm. Baubar bleiben sie:
    #     python3 tools/video/build.py salate
    "salate": ("Zusatz-Salate-Getraenke",
               lambda: slides.volllisteseite(
                   [block("salate", "Salate", 132),
                    block("getraenke", "Getränke", 118)])),
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


def anpassen(pg, i=0):
    """Die groesste Schrift suchen, bei der die Seite noch ganz drauf ist.

    Bewusst eine eigene Funktion und nicht in rendern() vergraben: Das
    Pruefskript (tools/video/pruefen.py) misst die Seiten nach genau diesem
    Schritt. Waere die Logik dort noch einmal hingeschrieben, wuerde der Test
    seine eigene Kopie pruefen statt das, was spaeter im Video landet.

    Gemessen wird die tatsaechliche Unterkante des tiefsten Elements, nicht
    scrollHeight. Letzteres laesst die Unterlaengen von g, ss und p aus und
    meldet "passt", waehrend sie schon angeschnitten sind - und seit Kopf und
    Streifen weg sind, faengt nichts mehr unter der Liste diesen Ueberlauf ab.
    """
    passt = pg.evaluate("""() => {
        const wurzel = document.querySelector('.inhalt');
        if (!wurzel) return null;
        const luft = 4;   // Schriften rendern auf anderen Geraeten minimal anders
        const passtBei = s => {
            wurzel.style.setProperty('--s', s.toFixed(3));
            let tief = 0, weit = 0;
            for (const e of wurzel.querySelectorAll('*')) {
                const r = e.getBoundingClientRect();
                if (!r.width && !r.height) continue;
                if (r.bottom > tief) tief = r.bottom;
                if (r.right > weit) weit = r.right;
            }
            // Zusaetzlich: Der Inhalt muss in SEINEN Kasten passen, nicht
            // nur irgendwo auf den Schirm. Ein Raster mit flex:1 laesst
            // seine Kacheln sonst ueber den eigenen Rand hinauswachsen -
            // sie stehen dann noch im Bild, aber ueber der Zeile darunter.
            const voll = document.getElementById('voll');
            let drin = true;
            if (voll) {
                const vb = voll.getBoundingClientRect();
                for (const e of voll.children) {
                    if (e.getBoundingClientRect().bottom > vb.bottom + 1) {
                        drin = false;
                        break;
                    }
                }
            }
            return drin
                && tief <= window.innerHeight - luft
                && weit <= window.innerWidth - luft
                && document.body.scrollHeight <= window.innerHeight + 1;
        };
        // Nach oben weit offen: Seit Kopf und Streifen weg sind, hat eine
        // kurze Kategorie wirklich Platz, gross zu werden.
        let unten = 0.40, oben = 3.00;
        if (!passtBei(unten)) return unten;
        for (let i = 0; i < 24; i++) {
            const mitte = (unten + oben) / 2;
            if (passtBei(mitte)) unten = mitte; else oben = mitte;
        }
        passtBei(unten);
        return unten;
    }""")
    if passt is not None:
        print(f"    Schriftgroesse {passt:.0%}")
    return passt



def verlaengern(ziel, mal):
    """Den Durchlauf mehrfach hintereinander nach video/stick/ legen.

    Ohne Neucodierung: Die Bilder werden unveraendert kopiert, nur die
    Zeitstempel laufen weiter. Kein Qualitaetsverlust, und der Decoder im
    Fernseher laeuft durch, statt an jeder Naht neu anzulaufen.

    Bewusst eine zweite Datei und nicht dieselbe: Der Durchlauf hat rund
    8 MB, zehn Durchlaeufe haben 80. Im Git liegt der Durchlauf, denn aus
    ihm entsteht die lange Datei in Sekunden wieder. Lagen die langen
    Dateien darin, waere das Lager nach ein paar Preisaenderungen im
    Gigabytebereich - und GitHub nimmt einzelne Dateien ueber 100 MB gar
    nicht erst an. Auf den USB-Stick kommt die Datei aus video/stick/.
    """
    lang = STICK / ziel.name
    STICK.mkdir(parents=True, exist_ok=True)
    if mal <= 1:
        shutil.copy2(ziel, lang)
        return lang
    liste = ziel.with_suffix(".liste.txt")
    liste.write_text("".join(f"file '{ziel.name}'\n" for _ in range(mal)),
                     encoding="utf-8")
    r = subprocess.run(
        [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(liste),
         "-c", "copy", "-movflags", "+faststart", str(lang)],
        capture_output=True, text=True, cwd=str(ziel.parent))
    liste.unlink()
    if r.returncode != 0:
        print(r.stderr[-2500:])
        raise SystemExit(f"Verlaengern fehlgeschlagen fuer {ziel.name}")
    return lang


def rendern(html_text, ordner):
    """Die Seite als HTML-Datei ablegen, aufrufen und abfotografieren.

    Bewusst nicht über set_content: Chromium laedt aus einer so gesetzten
    Seite keine lokalen Bilder und Schriften, die Seite bliebe leer."""
    from playwright.sync_api import sync_playwright
    ordner.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(
            executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = b.new_page(viewport={"width": slides.BREITE, "height": slides.HOEHE})
        htm = ordner / "seite.html"
        htm.write_text(pfade_einsetzen(html_text), encoding="utf-8")
        pg.goto(htm.as_uri(), wait_until="load")
        pg.evaluate("() => document.fonts.ready")
        anpassen(pg)
        fehlend = pg.evaluate(
            "() => [...document.images].filter(i => !i.complete || !i.naturalWidth)"
            ".map(i => i.src)")
        if fehlend:
            raise SystemExit(f"Bild laedt nicht: {fehlend}")
        pg.wait_for_timeout(150)
        datei = ordner / "seite.png"
        pg.screenshot(path=str(datei))
        b.close()
    return datei


def montieren(bild, ziel):
    """Aus dem Standbild ein Video von DAUER Sekunden machen.

    Die stille Tonspur ist Absicht: Manche Fernseher weigern sich, Dateien
    ganz ohne Ton abzuspielen."""
    befehl = [FFMPEG, "-y",
              "-loop", "1", "-t", f"{DAUER:.3f}", "-i", str(bild),
              "-f", "lavfi", "-t", f"{DAUER:.3f}", "-i",
              "anullsrc=channel_layout=stereo:sample_rate=48000",
              "-vf", f"scale=1920:1080:flags=lanczos,format=yuv420p,fps={FPS},setsar=1",
              "-c:v", "libx264", "-preset", "medium", "-crf", "20",
              "-profile:v", "high", "-level", "4.0", "-pix_fmt", "yuv420p",
              "-movflags", "+faststart", "-g", str(GOP),
              "-c:a", "aac", "-b:a", "96k", "-shortest",
              str(ziel)]
    r = subprocess.run(befehl, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2500:])
        raise SystemExit(f"ffmpeg fehlgeschlagen für {ziel.name}")
    return DAUER


def bauen(schluessel):
    name, macher = VIDEOS[schluessel]
    print(f"\n{name}")
    ordner = TMP / schluessel
    if ordner.exists():
        shutil.rmtree(ordner)
    bild = rendern(macher(), ordner)
    AUS.mkdir(exist_ok=True)
    ziel = AUS / f"{name}.mp4"
    laenge = montieren(bild, ziel)
    lang = verlaengern(ziel, WIEDERHOLUNGEN)
    print(f"  -> {ziel.name}  Durchlauf {laenge:.1f} s  "
          f"{ziel.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"     stick/{lang.name}  {laenge * WIEDERHOLUNGEN / 60:.0f} min  "
          f"{lang.stat().st_size / 1024 / 1024:.1f} MB  <- auf den USB-Stick")
    return ziel


if __name__ == "__main__":
    wunsch = sys.argv[1:] or ["angebote", "pizza", "tuerkisch", "nudeln"]
    for w in wunsch:
        if w not in VIDEOS:
            raise SystemExit(f"Unbekannt: {w}. Möglich: {', '.join(VIDEOS)}")
        bauen(w)
    if TMP.exists():
        shutil.rmtree(TMP)
    print("\nFertig. Auf den USB-Stick kommen die Dateien aus video/stick/.")