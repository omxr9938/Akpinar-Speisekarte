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
TMP = ROOT / ".video-tmp"
D = slides.DATEN

FPS = 30
UEBERBLENDUNG = 1.0          # Sekunden

# Der Fernseher blendet kurz schwarz, wenn er die Datei am Ende neu aufzieht -
# er baut dabei seinen Decoder neu auf, das laesst sich in der Datei nicht
# abschalten. Zwei Dinge nehmen es dem Gast trotzdem aus dem Blick:
#
# SCHLUSSBLENDE haengt die erste Seite hinten noch einmal an. Die Datei endet
# damit auf genau dem Bild, auf dem sie anfaengt - nach dem Schwarz steht
# dasselbe da wie davor, der Sprung faellt nicht mehr auf.
#
# WIEDERHOLUNGEN legt den fertigen Durchlauf mehrfach in dieselbe Datei. Aus
# "alle 72 Sekunden" wird "alle zwoelf Minuten" - und weil der Kreis
# geschlossen ist, sind die Uebergaenge innerhalb der Datei nahtlos.
SCHLUSSBLENDE = 1.2          # Sekunden Rueckblende auf die erste Seite
WIEDERHOLUNGEN = 10          # Durchlaeufe je Datei

import imageio_ffmpeg
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


# ------------------------------------------------------------ Seitenfolgen --

def teile(liste, n):
    return [liste[i:i + n] for i in range(0, len(liste), n)]


def kategorie(kat_id):
    return next(k for k in D["kategorien"] if k["id"] == kat_id)


# Alle vier Videos sind exakt gleich lang, damit sie bei gleichzeitigem Start
# zusammenbleiben. Wichtiger noch: Die Karte steht durchgehend, nur der Streifen
# unten wechselt - dadurch ist auf jedem Bildschirm jederzeit alles lesbar und
# es spielt keine Rolle, ob die Geraete auseinanderlaufen.
#
# Die Standzeiten sind bewusst ungleich: Das Mittagsangebot hat Vorrang, das
# Logo ist nur eine Erinnerung an den Namen und braucht keine 15 Sekunden.
# 20 + 5 + 12 + 20 + 10 + 10 = 77,0 s, minus 5 x 1,0 s Ueberblendung = 72,0 s.
# Das Angebot steht damit 40 von 77 Sekunden auf dem Schirm, das Logo 5.
STAND_ANGEBOT = 20.0
STAND_LOGO = 5.0
STAND_STEMPEL = 12.0
STAND_LIEFERUNG = 10.0
STAND_SCHLUSS = 10.0
STANDZEIT = 15.0          # nur noch fuer die Angebotsseite (siehe unten)

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
def baender(akzent):
    """Liefert (Streifen, Standzeit) in der Reihenfolge, in der sie laufen."""
    return [
        (slides.band_stempel(), STAND_ANGEBOT),
        (slides.band_logo(), STAND_LOGO),
        (slides.band_zeiten(), STAND_STEMPEL),
        (slides.band_lieferung(), STAND_ANGEBOT),
        (slides.band_spruch(*akzent), STAND_LIEFERUNG),
        (slides.band_zusatzstoffe(), STAND_SCHLUSS),
    ]


def folge_angebote(akzente):
    """Der Angebotsbildschirm.

    Unten laufen hier keine Angebotsstreifen - das Angebot steht ja gross auf
    dem Schirm. Die beiden langen Plaetze bekommen stattdessen Gerichtebilder:
    oben die Preise, unten der Appetit. Die Standzeiten sind dieselben wie auf
    den Kartenbildschirmen, sonst laufen die vier Geraete auseinander.
    """
    b = [
        (slides.band_spruch(*akzente[0]), STAND_ANGEBOT),
        (slides.band_logo(), STAND_LOGO),
        (slides.band_stempel(), STAND_STEMPEL),
        (slides.band_spruch(*akzente[1]), STAND_ANGEBOT),
        (slides.band_lieferung(), STAND_LIEFERUNG),
        (slides.band_zeiten(), STAND_SCHLUSS),
    ]
    return [(slides.alleangeboteseite(band), dauer) for band, dauer in b]


def block(kat_id, titel=None, pbreite=132):
    """Ein Kartenblock fuer volllisteseite: (Ueberschrift, Gerichte, Legende,
    Preisspaltenbreite, Kategoriehinweis). titel=None heisst: einzelne
    Kategorie, keine Zwischenueberschrift - deren Hinweis steht dann als
    Unterzeile oben und wird hier nicht noch einmal ausgegeben."""
    k = kategorie(kat_id)
    hinweis = k.get("hinweis", "") if titel else ""
    return (titel, k["items"], k.get("spaltenKurz"), pbreite, hinweis)


def folge_karte(titel, unterzeile, bloecke, akzent, notiz=None):
    """Die ganze Kategorie steht fest auf dem Bildschirm; nur der Streifen
    unten wechselt. Kein Gast muss warten, bis sein Gericht wieder erscheint."""
    return [(slides.volllisteseite(titel, unterzeile, bloecke, band, notiz), dauer)
            for band, dauer in baender(akzent)]


VIDEOS = {
    "angebote": ("1-Angebote", lambda: folge_angebote([
        ("@@IMG@@/pizza-hero.jpg", "Frisch aus dem Ofen"),
        ("@@IMG@@/doener-hero.jpg", "Täglich frisch gedreht"),
    ])),

    "pizza": ("2-Pizza", lambda: folge_karte(
        "Pizza", kategorie("pizza")["hinweis"],
        [block("pizza", pbreite=124)],
        ("@@IMG@@/pizza-hero.jpg", "Frisch aus dem Ofen"),
        notiz=slides.notiz_extras(kategorie("pizza")["extras"]))),

    # Die Unterzeile kommt aus der Karte, nicht aus dem Programm: Dort stehen
    # die Soßen. "Döner · Dürüm · Boxen · Pide · Teller" stand hier vorher und
    # war verschenkter Platz - die Kategorien sieht der Gast in der Liste
    # darunter ohnehin. Welche Soßen es gibt, sieht er sonst nirgends.
    "tuerkisch": ("3-Tuerkisch", lambda: folge_karte(
        "Türkische Gerichte", kategorie("tuerkisch")["hinweis"],
        [block("tuerkisch", pbreite=150)],
        ("@@IMG@@/doener-hero.jpg", "Täglich frisch gedreht"),
        notiz=slides.notiz_menue(BESTELL["zutaten"]["tuerkisch"],
                                 kategorie("tuerkisch")["items"]))),

    "nudeln": ("4-Nudeln-Verschiedenes-Burger", lambda: folge_karte(
        "Nudeln · Verschiedenes · Burger", None,
        [block("nudeln", "Nudeln", 150),
         block("verschiedenes", "Verschiedenes", 150),
         block("burger", "Burger", 132)],
        ("@@IMG@@/burger.jpg", "Frisch gemacht"))),

    # Salate und Getraenke haben in dieser Aufteilung keinen eigenen
    # Bildschirm. Baubar bleiben sie:  python3 tools/video/build.py salate
    "salate": ("Zusatz-Salate-Getraenke", lambda: folge_karte(
        "Salate · Getränke", None,
        [block("salate", "Salate", 132),
         block("getraenke", "Getränke", 118)],
        ("@@IMG@@/getraenke.jpg", "Frisch und kalt"))),
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
    """Schrift so weit verkleinern, bis Karte und Angebotsstreifen passen.

    Bewusst eine eigene Funktion und nicht in rendern() vergraben: Das
    Pruefskript (tools/video/pruefen.py) misst die Seiten nach genau diesem
    Schritt. Waere die Logik dort noch einmal hingeschrieben, wuerde der Test
    seine eigene Kopie pruefen statt das, was spaeter im Video landet.
    """
    # Vollstaendige Karten automatisch so weit verkleinern, bis sie auf
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

    # Der Angebotsstreifen darf nicht abgeschnitten werden. Er darf
    # zweizeilig umbrechen - die Familien-Pizza mit vier Preisen und
    # dem Hinweis "inkl. Salat oder Getraenk" passt in eine Zeile nicht,
    # und der Hinweis ist das halbe Angebot. Gemessen wird deshalb die
    # Hoehe; passt es auch dann nicht, wird die Schrift verkleinert.
    bandmass = pg.evaluate("""() => {
        const box = document.querySelector('[data-anpassen]');
        if (!box) return null;
        const band = box.closest('.band');
        // Gemessen wird die tatsaechliche Unterkante des tiefsten Elements,
        // nicht scrollHeight: Letzteres laesst die Unterlaengen von g, ss und p
        // aus und meldet "passt", waehrend sie schon angeschnitten sind.
        // Vier Pixel Luft, weil Schriften auf anderen Geraeten minimal anders
        // rendern.
        const luft = 4;
        const passtBei = s => {
            box.style.setProperty('--bs', s.toFixed(3));
            const br = band.getBoundingClientRect();
            let tief = 0, weit = 0;
            for (const e of box.querySelectorAll('*')) {
                const r = e.getBoundingClientRect();
                if (!r.width && !r.height) continue;
                if (r.bottom > tief) tief = r.bottom;
                if (r.right > weit) weit = r.right;
            }
            return tief <= br.bottom - luft && weit <= br.right;
        };
        if (passtBei(1)) return 1;
        let unten = 0.55, oben = 1.0;
        if (!passtBei(unten)) return unten;
        for (let i = 0; i < 20; i++) {
            const mitte = (unten + oben) / 2;
            if (passtBei(mitte)) unten = mitte; else oben = mitte;
        }
        passtBei(unten);
        return unten;
    }""")
    if bandmass is not None and bandmass < 1:
        print(f"    Seite {i}: Angebotsstreifen {bandmass:.0%}")
    if bandmass is not None and bandmass <= 0.55:
        raise SystemExit(
            f"Angebotsstreifen passt auf Seite {i} selbst bei 55 % nicht "
            "in den Streifen - Angebotsgruppe kuerzen.")

    return passt, bandmass


def kreis_schliessen(seiten):
    """Erste Seite hinten noch einmal anhaengen, damit das letzte Bild der
    Datei exakt das erste ist.

    Die Gesamtlaenge bleibt unveraendert: Was die Schlussblende hinten
    braucht, wird der ersten Seite vorne abgezogen. Die vier Bildschirme
    bleiben dadurch gleich lang.
    """
    seiten = list(seiten)
    erste_html, erste_dauer = seiten[0]
    zugabe = SCHLUSSBLENDE - UEBERBLENDUNG
    seiten[0] = (erste_html, erste_dauer - zugabe)
    seiten.append((erste_html, SCHLUSSBLENDE))
    return seiten


def verlaengern(ziel, mal):
    """Den fertigen Durchlauf mehrfach hintereinander in dieselbe Datei legen.

    Ohne Neucodierung: Die Bilder werden unveraendert kopiert, nur die
    Zeitstempel laufen weiter. Kein Qualitaetsverlust, und der Decoder im
    Fernseher laeuft durch, statt an jeder Naht neu anzulaufen.
    """
    if mal <= 1:
        return
    liste = ziel.with_suffix(".liste.txt")
    liste.write_text("".join(f"file '{ziel.name}'\n" for _ in range(mal)),
                     encoding="utf-8")
    lang = ziel.with_suffix(".lang.mp4")
    r = subprocess.run(
        [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(liste),
         "-c", "copy", "-movflags", "+faststart", str(lang)],
        capture_output=True, text=True, cwd=str(ziel.parent))
    if r.returncode != 0:
        print(r.stderr[-2500:])
        raise SystemExit(f"Verlaengern fehlgeschlagen fuer {ziel.name}")
    liste.unlink()
    lang.replace(ziel)


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
        fertig = {}
        for i, (html_text, _dauer) in enumerate(seiten):
            # Die angehaengte Schlussseite ist dieselbe wie die erste - einmal
            # rendern genuegt, und beide Bilder sind dann garantiert identisch.
            if html_text in fertig:
                bilder.append(fertig[html_text])
                continue
            htm = ordner / f"seite-{i:02d}.html"
            htm.write_text(pfade_einsetzen(html_text), encoding="utf-8")
            pg.goto(htm.as_uri(), wait_until="load")
            pg.evaluate("() => document.fonts.ready")
            anpassen(pg, i)
            fehlend = pg.evaluate(
                "() => [...document.images].filter(i => !i.complete || !i.naturalWidth)"
                ".map(i => i.src)")
            if fehlend:
                raise SystemExit(f"Bild laedt nicht auf Seite {i}: {fehlend}")
            pg.wait_for_timeout(150)
            datei = ordner / f"seite-{i:02d}.png"
            pg.screenshot(path=str(datei))
            fertig[html_text] = datei
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
    seiten = kreis_schliessen(macher())
    print(f"\n{name}: {len(seiten)} Seiten")
    ordner = TMP / schluessel
    if ordner.exists():
        shutil.rmtree(ordner)
    bilder = rendern(seiten, ordner)
    AUS.mkdir(exist_ok=True)
    ziel = AUS / f"{name}.mp4"
    laenge = montieren(bilder, [d for _, d in seiten], ziel)
    verlaengern(ziel, WIEDERHOLUNGEN)
    mb = ziel.stat().st_size / 1024 / 1024
    print(f"  -> {ziel.name}  {laenge:.1f} s x {WIEDERHOLUNGEN} = "
          f"{laenge * WIEDERHOLUNGEN / 60:.0f} min  {mb:.0f} MB")
    return ziel


if __name__ == "__main__":
    wunsch = sys.argv[1:] or ["angebote", "pizza", "tuerkisch", "nudeln"]
    for w in wunsch:
        if w not in VIDEOS:
            raise SystemExit(f"Unbekannt: {w}. Möglich: {', '.join(VIDEOS)}")
        bauen(w)
    if TMP.exists():
        shutil.rmtree(TMP)
    print("\nFertig. Dateien liegen in video/")
