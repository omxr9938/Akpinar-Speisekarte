#!/usr/bin/env python3
"""
Erzeugt die vier Fernseher-Bilder für die USB-Sticks.

    python3 tools/bildschirme/build.py            # alle vier
    python3 tools/bildschirme/build.py pizza      # nur eines

Ergebnis in bilder/ , je Bildschirm eine PNG und eine JPG:
    1-Angebote  2-Pizza  3-Tuerkisch  4-Nudeln-Verschiedenes-Burger

Ablauf: Jede Bildschirmseite wird als HTML gebaut und mit Chromium zu einem
Standbild gerendert. Auf jedem Schirm steht ein stehendes Bild - Text auf
einem Fernseher soll ruhig stehen und lesbar sein, nicht wandern.

Format: 1920x1080. PNG ist verlustfrei und die erste Wahl; die JPG liegt
daneben, weil aeltere Geraete oft nur JPEG anzeigen.
"""

import json
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import slides                                            # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
BILDER = ROOT / "bilder"       # hier liegen die vier Schirme als Bilddatei
TMP = ROOT / ".bildschirm-tmp"
D = slides.DATEN


# ------------------------------------------------------------ Seitenfolgen --

def kategorie(kat_id):
    return next(k for k in D["kategorien"] if k["id"] == kat_id)



BESTELL = json.loads((ROOT / "assets/data/bestellung.json").read_text(encoding="utf-8"))


# Telefonnummer und Adresse stehen bewusst nicht drauf: Die Bildschirme haengen
# im Laden. Wer davorsteht, ruft nicht an und sucht nicht die Adresse. Auf den
# Kartenbildschirmen steht auch das Mittagsangebot nicht noch einmal - es hat
# mit Bildschirm 1 einen eigenen Fernseher, gross und vollstaendig. Der Platz
# gehoert hier ganz den Gerichten.
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
# Dass nichts wechselt, ist der Grund, warum eine Bilddatei genuegt: Ein Video
# muesste genau dasselbe Bild minutenlang wiederholen.
#
# Einzige Ausnahme ist die Ueberschrift "Mittagsangebot" auf Bildschirm 1.
# Die sagt etwas, was man dem Bild sonst nicht ansieht - dass diese Preise
# nur mittags gelten.
BILDSCHIRME = {
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
    #     python3 tools/bildschirme/build.py salate
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
    Pruefskript (tools/bildschirme/pruefen.py) misst die Seiten nach genau
    diesem Schritt. Waere die Logik dort noch einmal hingeschrieben, wuerde der
    Test seine eigene Kopie pruefen statt das, was spaeter auf dem Stick landet.

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


def bilder_ablegen(bild, name):
    """Den gerenderten Schirm als PNG und als JPG in bilder/ ablegen.

    Auf diesen Schirmen bewegt sich nichts, deshalb ist eine Bilddatei alles,
    was der Fernseher braucht - ein paar hundert Kilobyte statt eines Videos,
    kein Decoder, und kein kurzes Schwarz, wenn das Geraet die Datei am Ende
    neu aufzieht.

    PNG ist verlustfrei, die Schrift steht damit exakt so da wie gerendert.
    Aeltere Geraete koennen aber nur JPEG, deshalb liegt beides bereit.
    JPEG bewusst ohne Farbunterabtastung (subsampling=0, also 4:4:4): Bei
    4:2:0 franst goldene Schrift auf dunklem Grund sichtbar aus, und hier ist
    fast alles Schrift. Qualitaet 95 aus demselben Grund - darunter setzen
    sich sichtbare Rasterkanten an die Buchstabenraender.
    """
    from PIL import Image
    BILDER.mkdir(parents=True, exist_ok=True)
    png = BILDER / f"{name}.png"
    shutil.copy2(bild, png)
    jpg = BILDER / f"{name}.jpg"
    with Image.open(bild) as im:
        im.convert("RGB").save(jpg, "JPEG", quality=95, subsampling=0,
                               optimize=True)
    return png, jpg


def bauen(schluessel):
    name, macher = BILDSCHIRME[schluessel]
    print(f"\n{name}")
    ordner = TMP / schluessel
    if ordner.exists():
        shutil.rmtree(ordner)
    bild = rendern(macher(), ordner)
    png, jpg = bilder_ablegen(bild, name)
    kb = lambda f: f.stat().st_size / 1024
    print(f"  -> bilder/{png.name}  {kb(png):.0f} kB   "
          f"bilder/{jpg.name}  {kb(jpg):.0f} kB   <- auf den USB-Stick")
    return png


if __name__ == "__main__":
    wunsch = sys.argv[1:] or ["angebote", "pizza", "tuerkisch", "nudeln"]
    for w in wunsch:
        if w not in BILDSCHIRME:
            raise SystemExit(f"Unbekannt: {w}. Möglich: {', '.join(BILDSCHIRME)}")
        bauen(w)
    if TMP.exists():
        shutil.rmtree(TMP)
    print("\nFertig. Auf den USB-Stick kommt je eine Datei aus bilder/ - "
          "die PNG,\nund wenn der Fernseher die nicht anzeigt, die JPG "
          "daneben.")
