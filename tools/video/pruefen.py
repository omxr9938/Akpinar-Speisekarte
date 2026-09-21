#!/usr/bin/env python3
"""
Prueft die Fernseher-Seiten, bevor sie zu Videos werden.

    python3 tools/video/pruefen.py

Rendert jede Seite jedes Bildschirms in Chromium und prueft:

  1. Passt alles in 1920x1080, ohne Ueberlauf in irgendeiner Richtung?
  2. Wird irgendwo Text abgeschnitten?
  3. Steht die Karte still, wenn der Streifen unten wechselt?
     (Schriftgroesse, Listenanfang und Streifenhoehe muessen auf allen
     Seiten eines Bildschirms identisch sein - sonst springt das Bild.)
  4. Steht jedes Gericht der Karte genau einmal auf genau einem Bildschirm,
     mit genau den Preisen aus menu.json?
  5. Ist die Schrift auf einem Fernseher aus der Entfernung noch lesbar?

Beendet sich mit Code 1, sobald etwas nicht stimmt.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import slides                                            # noqa: E402
import build                                             # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
TMP = ROOT / ".video-pruefung"

# Breite eines 55-Zoll-Fernsehers in Millimetern. 1920 Bildpunkte verteilen
# sich darauf, ein Punkt ist also rund 0,63 mm hoch. Faustregel fuer bequemes
# Lesen: Schrifthoehe mindestens Betrachtungsabstand geteilt durch 200.
TV_BREITE_MM = 1210.0
MM_JE_PUNKT = TV_BREITE_MM / slides.BREITE

fehler = []
warnungen = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)
    return bedingung


MESSUNG = """() => {
  const norm = t => (t || '').replace(/\\s+/g, ' ').trim();
  const voll = document.getElementById('voll');
  const band = document.querySelector('.band');
  const wurzel = document.querySelector('.inhalt');

  // Abgeschnittener Text: Ein Element, dessen Inhalt breiter oder hoeher ist
  // als es selbst, zeigt nicht alles an. Mehrspaltige Container und die
  // Listen-Box selbst sind ausgenommen, die duerfen scrollen-wirken.
  const ausnahme = new Set([voll, document.body, document.documentElement]);
  const beschnitten = [];
  for (const el of document.querySelectorAll('.inhalt *')) {
    if (ausnahme.has(el)) continue;
    const st = getComputedStyle(el);
    if (st.columnCount !== 'auto' && st.columnCount !== '1') continue;
    if (el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0) {
      beschnitten.push(['breit', el.className || el.tagName, norm(el.textContent).slice(0, 60)]);
    }
  }

  // Gerichte so auslesen, wie sie wirklich auf dem Schirm stehen.
  // Den Namen ohne die hochgestellten Zusatzstoff-Zahlen lesen: "Salami1)2)3)"
  // ist derselbe Artikel wie "Salami" in menu.json, die Marker kommen erst
  // beim Rendern dazu.
  const ohneMarker = el => {
    if (!el) return '';
    const k = el.cloneNode(true);
    k.querySelectorAll('sup').forEach(s => s.remove());
    return norm(k.textContent);
  };
  const zeilen = [...document.querySelectorAll('.vz')].map(z => ({
    nr: norm(z.querySelector('.vnr')?.textContent),
    name: ohneMarker(z.querySelector('.vname')),
    marker: norm(z.querySelector('.vname sup')?.textContent),
    besch: norm(z.querySelector('.vbesch')?.textContent),
    preise: [...z.querySelectorAll('.vpreise > span')].map(s => norm(s.textContent)),
  }));

  const kat = [...document.querySelectorAll('.vkat .vkname')].map(e => norm(e.textContent));

  // Die tiefste und aeusserste Kante im Bild. document.scrollHeight taugt
  // dafuer nicht: html und body sind auf overflow:hidden gestellt, dort wird
  // ein Ueberlauf abgeschnitten statt gemeldet. Genau deshalb blieb
  // unbemerkt, dass der Angebotsstreifen einen Pixel unter dem Bildrand
  // endete und die Unterlaengen von g, ss und p abgeschnitten wurden.
  let tiefste = 0, weiteste = 0;
  for (const el of document.querySelectorAll('.inhalt, .inhalt *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    if (r.bottom > tiefste) tiefste = r.bottom;
    if (r.right > weiteste) weiteste = r.right;
  }

  return {
    tiefsteKante: Math.round(tiefste),
    weitesteKante: Math.round(weiteste),
    seiteBreit: document.documentElement.scrollWidth,
    seiteHoch: document.documentElement.scrollHeight,
    skala: parseFloat(getComputedStyle(wurzel).getPropertyValue('--s')) || 1,
    vollOben: Math.round(voll ? voll.getBoundingClientRect().top * 100 : 0) / 100,
    vollUnten: Math.round(voll ? voll.getBoundingClientRect().bottom * 100 : 0) / 100,
    vollPasst: voll ? voll.scrollHeight <= voll.clientHeight + 1 : true,
    bandOben: Math.round(band ? band.getBoundingClientRect().top * 100 : 0) / 100,
    bandHoehe: Math.round(band ? band.getBoundingClientRect().height * 100 : 0) / 100,
    bandPasst: band ? (band.scrollHeight <= band.clientHeight + 1
                       && band.scrollWidth <= band.clientWidth + 1) : true,
    namePx: (() => { const e = document.querySelector('.vz .vname');
                     return e ? parseFloat(getComputedStyle(e).fontSize) : 0; })(),
    beschPx: (() => { const e = document.querySelector('.vz .vbesch');
                      return e ? parseFloat(getComputedStyle(e).fontSize) : 0; })(),
    preisPx: (() => { const e = document.querySelector('.vz .vpreise span');
                      return e ? parseFloat(getComputedStyle(e).fontSize) : 0; })(),
    bilderFehlen: [...document.images].filter(i => !i.complete || !i.naturalWidth)
                                      .map(i => i.src),
    beschnitten, zeilen, kat,
  };
}"""


def erwartete_gerichte(kat_ids):
    """Was laut menu.json auf dem Bildschirm stehen muss."""
    raus = []
    for kid in kat_ids:
        k = build.kategorie(kid)
        for g in k["items"]:
            if g.get("groessen"):
                preise = [" · ".join(f'{x["label"]} {x["preis"]}'
                                     for x in g["groessen"])]
            else:
                preise = [p if p not in (None, "", "-") else "–"
                          for p in g.get("preise", [])]
            raus.append({"nr": str(g.get("nr") or ""), "name": g["name"],
                         "preise": preise})
    return raus


# Welche Kategorien auf welchem Bildschirm stehen - dieselbe Zuordnung wie
# in build.VIDEOS, hier aber unabhaengig noch einmal hingeschrieben. Waere sie
# aus build.py abgeleitet, wuerde der Test einen Tippfehler dort mitmachen.
SCHIRME = {
    "angebote": [],                  # zeigt das Mittagsangebot, keine Kategorie
    "pizza": ["pizza"],
    "tuerkisch": ["tuerkisch"],
    "nudeln": ["nudeln", "verschiedenes", "burger"],
}


def main():
    from playwright.sync_api import sync_playwright
    TMP.mkdir(parents=True, exist_ok=True)
    gesehen = {}
    laengen = {}

    with sync_playwright() as p:
        b = p.chromium.launch(
            executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = b.new_page(viewport={"width": slides.BREITE, "height": slides.HOEHE})

        for schluessel in SCHIRME:
            name, macher = build.VIDEOS[schluessel]
            seiten = macher()
            laengen[name] = (sum(d for _, d in seiten)
                             - build.UEBERBLENDUNG * (len(seiten) - 1))
            print(f"\n{name}  ({len(seiten)} Seiten)")
            messungen = []

            for i, (html_text, dauer) in enumerate(seiten):
                datei = TMP / f"{schluessel}-{i:02d}.html"
                datei.write_text(build.pfade_einsetzen(html_text), encoding="utf-8")
                pg.goto(datei.as_uri(), wait_until="load")
                pg.evaluate("() => document.fonts.ready")
                build.anpassen(pg, i)
                pg.wait_for_timeout(60)
                m = pg.evaluate(MESSUNG)
                messungen.append(m)

                v = f"{name} Seite {i}"
                pruefe(m["seiteBreit"] <= slides.BREITE,
                       f"{v}: Seite ist {m['seiteBreit']} px breit statt {slides.BREITE}")
                pruefe(m["seiteHoch"] <= slides.HOEHE,
                       f"{v}: Seite ist {m['seiteHoch']} px hoch statt {slides.HOEHE}")
                pruefe(m["tiefsteKante"] <= slides.HOEHE,
                       f"{v}: etwas reicht bis y={m['tiefsteKante']}, das Bild ist "
                       f"nur {slides.HOEHE} hoch - unten wird abgeschnitten")
                pruefe(m["weitesteKante"] <= slides.BREITE,
                       f"{v}: etwas reicht bis x={m['weitesteKante']}, das Bild ist "
                       f"nur {slides.BREITE} breit - rechts wird abgeschnitten")
                pruefe(m["vollPasst"], f"{v}: Gerichteliste passt nicht in ihren Bereich")
                pruefe(m["bandPasst"], f"{v}: Streifen unten laeuft ueber")
                pruefe(not m["bilderFehlen"],
                       f"{v}: Bild laedt nicht: {m['bilderFehlen']}")
                for art, klasse, text in m["beschnitten"]:
                    fehler.append(f"{v}: Text abgeschnitten ({art}, .{klasse}): {text}")

            # Steht die Karte still, wenn der Streifen wechselt?
            for feld, beschreibung in (("skala", "Schriftgroesse"),
                                       ("vollOben", "Listenanfang"),
                                       ("vollUnten", "Listenende"),
                                       ("bandOben", "Streifenoberkante"),
                                       ("bandHoehe", "Streifenhoehe")):
                werte = {m[feld] for m in messungen}
                pruefe(len(werte) == 1,
                       f"{name}: {beschreibung} springt zwischen den Seiten: "
                       f"{sorted(werte)}")

            m0 = messungen[0]
            print(f"  Schriftgroesse {m0['skala']:.0%}  "
                  f"Name {m0['namePx']:.0f} px  "
                  f"Beschreibung {m0['beschPx']:.0f} px  "
                  f"Preis {m0['preisPx']:.0f} px")

            # Lesbarkeit: ab welchem Abstand wird es eng?
            for feld, was in (("namePx", "Gerichtname"),
                              ("beschPx", "Beschreibung")):
                px = m0[feld]
                if not px:
                    continue
                mm = px * MM_JE_PUNKT
                max_m = mm * 200 / 1000
                print(f"    {was}: {mm:.1f} mm hoch -> bequem bis {max_m:.1f} m")
                if max_m < 2.0:
                    warnungen.append(
                        f"{name}: {was} nur {mm:.1f} mm - bequem nur bis "
                        f"{max_m:.1f} m Abstand lesbar")

            # Gerichte gegen menu.json
            erwartet = erwartete_gerichte(SCHIRME[schluessel])
            ist = m0["zeilen"]
            if not SCHIRME[schluessel]:
                # Angebotsbildschirm: keine Gerichteliste, nur die Angebote.
                pruefe(not ist, f"{name}: zeigt unerwartet Gerichte")
                gesehen[name] = 0
                continue
            pruefe(len(ist) == len(erwartet),
                   f"{name}: {len(ist)} Gerichte auf dem Schirm, "
                   f"{len(erwartet)} in der Karte")
            for e, i_ in zip(erwartet, ist):
                if e["name"] != i_["name"]:
                    fehler.append(f"{name}: Name weicht ab - Karte "
                                  f"{e['name']!r}, Schirm {i_['name']!r}")
                if e["nr"] != i_["nr"]:
                    fehler.append(f"{name}: Nummer weicht ab bei {e['name']!r} - "
                                  f"Karte {e['nr']!r}, Schirm {i_['nr']!r}")
                if e["preise"] != i_["preise"]:
                    fehler.append(f"{name}: Preis weicht ab bei {e['name']!r} - "
                                  f"Karte {e['preise']}, Schirm {i_['preise']}")
            gesehen[name] = len(ist)

        b.close()

    # Keine Kategorie doppelt, keine vergessen. Bewusst ueber die Kategorien
    # und nicht ueber die Gerichtnamen: "Tonno" gibt es zweimal, als Pizza
    # Nr. 11 und als Nudelgericht Nr. 77. Das sind zwei Gerichte, kein Fehler.
    alle_kat = [k["id"] for k in slides.DATEN["kategorien"]]
    zugeteilt = [kid for kats in SCHIRME.values() for kid in kats]
    for kid in alle_kat:
        n = zugeteilt.count(kid)
        pruefe(n <= 1, f"Kategorie {kid!r} steht auf {n} Bildschirmen doppelt")
    fremd = set(zugeteilt) - set(alle_kat)
    pruefe(not fremd, f"Bildschirm zeigt Kategorien, die es nicht gibt: {fremd}")

    # Kategorien ohne Bildschirm sind kein Fehler, aber niemand soll sie
    # uebersehen: Wer sie nicht zeigt, hat sie im Laden nirgends haengen.
    fehlend = [k for k in alle_kat if k not in zugeteilt]
    for kid in fehlend:
        k = next(x for x in slides.DATEN["kategorien"] if x["id"] == kid)
        warnungen.append(f"Kategorie {k['name']!r} ({len(k['items'])} Gerichte) "
                         f"steht auf keinem Bildschirm")

    gezeigt = sum(len(next(x for x in slides.DATEN["kategorien"] if x["id"] == kid)["items"])
                  for kid in zugeteilt)
    anzahl_karte = sum(len(k["items"]) for k in slides.DATEN["kategorien"])
    pruefe(sum(gesehen.values()) == gezeigt,
           f"{sum(gesehen.values())} Gerichte auf den Bildschirmen, "
           f"{gezeigt} laut Zuordnung")

    # Gleiche Laenge, sonst laufen die vier Geraete auseinander
    pruefe(len(set(laengen.values())) == 1,
           f"Videolaengen weichen ab: {laengen}")

    print("\n" + "=" * 62)
    print(f"Gerichte in der Karte:         {anzahl_karte}")
    print(f"Gerichte auf den Bildschirmen: {sum(gesehen.values())}  "
          + "  ".join(f"{k.split('-')[0]}:{v}" for k, v in gesehen.items()))
    print(f"Videolaenge je Bildschirm: {list(laengen.values())[0]:.1f} s")
    for w in warnungen:
        print(f"HINWEIS  {w}")
    if fehler:
        print(f"\n{len(fehler)} FEHLER:")
        for f in fehler:
            print(f"  - {f}")
        return 1
    print("\nAlles in Ordnung.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
