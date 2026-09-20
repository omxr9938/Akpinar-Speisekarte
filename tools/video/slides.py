#!/usr/bin/env python3
"""
Baut die einzelnen Bildschirmseiten ("Slides") für die Fernseher-Videos als
HTML. Jede Seite wird später zu einem Standbild gerendert und in ffmpeg mit
Überblendungen zu einem Video zusammengesetzt.

Gestaltung folgt Karte und Website: dunkler Grund, Gold, Playfair Display für
Überschriften, Inter für alles andere. Schriftgrößen sind bewusst groß — ein
Fernseher im Laden wird aus zwei bis vier Metern gelesen, nicht aus 50 cm.
"""

import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATEN = json.loads((ROOT / "assets/data/menu.json").read_text(encoding="utf-8"))

BREITE, HOEHE = 1920, 1080

KOPF = """<!doctype html>
<meta charset="utf-8">
<style>
  @font-face { font-family:"Inter"; font-style:normal; font-weight:400;
    src:url("@@FONTS@@/inter-latin-400-normal.woff2") format("woff2"); }
  @font-face { font-family:"Inter"; font-style:normal; font-weight:600;
    src:url("@@FONTS@@/inter-latin-600-normal.woff2") format("woff2"); }
  @font-face { font-family:"Inter"; font-style:normal; font-weight:700;
    src:url("@@FONTS@@/inter-latin-700-normal.woff2") format("woff2"); }
  @font-face { font-family:"Inter"; font-style:italic; font-weight:400;
    src:url("@@FONTS@@/inter-latin-400-italic.woff2") format("woff2"); }
  @font-face { font-family:"Playfair Display"; font-style:italic; font-weight:800;
    src:url("@@FONTS@@/playfair-display-latin-800-italic.woff2") format("woff2"); }
  @font-face { font-family:"Playfair Display"; font-style:normal; font-weight:800;
    src:url("@@FONTS@@/playfair-display-latin-800-normal.woff2") format("woff2"); }

  :root {
    --bg:#0c0a09; --bg2:#14100e; --panel:#1a1513;
    --gold:#e2b35f; --gold2:#c8912f; --gold3:#a8791f;
    --rot:#c1201f;
    --text:#f5f0e8; --text2:#c9bfb2; --text3:#8b8178;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  html,body { width:1920px; height:1080px; overflow:hidden; }
  body {
    background:var(--bg); color:var(--text);
    font-family:"Inter",system-ui,sans-serif;
    -webkit-font-smoothing:antialiased;
    display:flex; flex-direction:column;
  }
  .flaeche {
    position:absolute; inset:0;
    background:
      radial-gradient(120% 80% at 50% -10%, rgba(193,32,31,.20), transparent 60%),
      linear-gradient(180deg,#171210,var(--bg) 60%);
  }
  .inhalt { position:relative; display:flex; flex-direction:column;
            width:100%; height:100%; padding:54px 76px; }

  /* Kopfzeile */
  .kopf { display:flex; align-items:center; justify-content:space-between;
          margin-bottom:18px; }
  .kopf img { height:66px; mix-blend-mode:screen; }
  .kopf .kat { font-family:"Playfair Display",serif; font-style:italic;
               font-weight:800; font-size:54px; color:var(--gold);
               letter-spacing:.01em; }

  /* Gerichte */
  .liste { flex:1; display:flex; flex-direction:column; justify-content:center;
           gap:var(--luecke,26px); }
  .zeile { display:grid; grid-template-columns:96px 1fr auto; align-items:baseline;
           gap:0 30px; padding-bottom:var(--pad,20px);
           border-bottom:1px solid rgba(226,179,95,.16); }
  .zeile:last-child { border-bottom:0; }
  .nr { font-size:44px; font-weight:700; color:var(--gold3);
        font-variant-numeric:tabular-nums; }
  .name { font-size:var(--gross,52px); font-weight:700; line-height:1.1; }
  .besch { display:block; margin-top:8px; font-size:var(--klein,30px);
           color:var(--text2); line-height:1.25; font-weight:400; }
  .preise { display:flex; gap:44px; }
  .preis { min-width:170px; text-align:right; }
  .preis .zahl { font-size:var(--pgross,50px); font-weight:700; color:var(--gold);
                 font-variant-numeric:tabular-nums; white-space:nowrap; }
  .preis .etikett { display:block; font-size:24px; color:var(--text3);
                    margin-bottom:4px; letter-spacing:.06em; }

  /* Fußzeile */
  .fuss { display:flex; align-items:center; justify-content:space-between;
          margin-top:18px; padding-top:16px;
          border-top:1px solid rgba(226,179,95,.22);
          font-size:30px; color:var(--text2); }
  .fuss b { color:var(--gold); font-size:36px; }

  /* Titelseite */
  .titel { flex:1; display:flex; flex-direction:column; align-items:center;
           justify-content:center; gap:34px; text-align:center; }
  .titel img.logo { width:820px; mix-blend-mode:screen; }
  .titel h1 { font-family:"Playfair Display",serif; font-style:italic;
              font-weight:800; font-size:104px; color:var(--gold); }
  .titel p { font-size:38px; color:var(--text2); }
  .linie { width:280px; height:3px; background:
           linear-gradient(90deg,transparent,var(--gold2),transparent); }

  /* Akzentseite mit Bild */
  .akzent { flex:1; display:flex; align-items:center; justify-content:center;
            gap:86px; }
  .akzent .bildrahmen { flex:none; border-radius:50%; overflow:hidden;
            border:5px solid var(--gold2);
            box-shadow:0 0 0 14px rgba(226,179,95,.10), 0 30px 70px rgba(0,0,0,.6); }
  .akzent .bildrahmen img { display:block; }
  .akzent .spruch { max-width:880px; }
  .akzent .spruch h2 { font-family:"Playfair Display",serif; font-style:italic;
            font-weight:800; font-size:86px; color:var(--gold); line-height:1.08; }
  .akzent .spruch p { margin-top:26px; font-size:40px; color:var(--text2);
            line-height:1.35; }

  /* Angebotskarten */
  .gruppe { flex:1; display:flex; flex-direction:column; justify-content:center; }
  .gruppe > h2 { font-family:"Playfair Display",serif; font-weight:800;
      font-size:72px; color:var(--gold); text-align:center; letter-spacing:.02em; }
  .gruppe > .hinweis { text-align:center; font-size:32px; color:var(--text2);
      margin-top:14px; }
  .karten { display:flex; flex-wrap:wrap; justify-content:center; gap:30px;
            margin-top:48px; }
  .karte { background:linear-gradient(180deg,#e9c987,#c8912f);
           color:#241a08; border-radius:22px; padding:34px 46px; min-width:380px;
           text-align:center; box-shadow:0 18px 44px rgba(0,0,0,.45); }
  .karte.breit { min-width:700px; }
  .karte .kt { font-family:"Playfair Display",serif; font-style:italic;
               font-weight:800; font-size:46px; }
  .karte .ks { font-size:28px; margin-top:8px; opacity:.78; }
  .karte .kp { font-family:"Playfair Display",serif; font-style:italic;
               font-weight:800; font-size:62px; margin-top:16px; }

  /* Abspann */
  .ende { flex:1; display:flex; flex-direction:column; align-items:center;
          justify-content:center; text-align:center; gap:26px; }
  .ende .tel { font-family:"Playfair Display",serif; font-style:italic;
               font-weight:800; font-size:128px; color:var(--gold); }
  .ende .adr { font-size:42px; color:var(--text2); }
  .ende .netz { margin-top:18px; font-size:34px; color:var(--text3); }
  .ende img.qr { width:330px; border-radius:16px; margin-top:12px;
                 background:#fff; padding:14px; }
</style>
"""


def _e(s):
    return html.escape(str(s or ""))


def seite(inhalt_html: str) -> str:
    return KOPF + f'<div class="flaeche"></div><div class="inhalt">{inhalt_html}</div>'


def kopf(kategorie: str) -> str:
    return (f'<div class="kopf"><img src="@@LOGO@@" alt="">'
            f'<span class="kat">{_e(kategorie)}</span></div>')


def fuss() -> str:
    b = DATEN["betrieb"]
    return (f'<div class="fuss"><span>{_e(b["strasse"])} · {_e(b["plz"])} {_e(b["ort"])}</span>'
            f'<span>Bestellung: <b>{_e(b["telefon"])}</b></span></div>')


# --------------------------------------------------------------- Seitentypen --

def titelseite(kategorie: str, unterzeile: str) -> str:
    return seite(
        '<div class="titel">'
        '<img class="logo" src="@@LOGO@@" alt="">'
        '<div class="linie"></div>'
        f'<h1>{_e(kategorie)}</h1>'
        f'<p>{_e(unterzeile)}</p>'
        '</div>'
    )


def gerichteseite(kategorie, gerichte, spalten, spalten_kurz, dicht=False):
    """Eine Seite mit mehreren Gerichten. `dicht` für Kategorien ohne Preisspalten."""
    mehrspaltig = len([s for s in spalten if s]) > 1
    stil = ('--gross:46px;--klein:27px;--pgross:44px;--luecke:18px;--pad:14px'
            if dicht else '')

    zeilen = []
    for g in gerichte:
        nr = f'<span class="nr">{_e(g["nr"])}</span>' if g.get("nr") else '<span class="nr"></span>'
        besch = (f'<span class="besch">{_e(g["beschreibung"])}</span>'
                 if g.get("beschreibung") else '')
        zusatz = ''
        if g.get("zusatz"):
            # Ziffern bekommen eine schliessende Klammer, das Sternchen nicht -
            # genauso wie auf der Website und in der gedruckten Karte.
            marken = "".join(z if z == "*" else z + ")" for z in g["zusatz"])
            zusatz = ('<sup style="font-size:.42em;color:var(--gold3);margin-left:.25em">'
                      + _e(marken) + '</sup>')

        felder = []
        for i, p in enumerate(g.get("preise", [])):
            if p in (None, "", "-"):
                continue
            etikett = ''
            if mehrspaltig and spalten_kurz and i < len(spalten_kurz):
                etikett = f'<span class="etikett">{_e(spalten_kurz[i])}</span>'
            felder.append(f'<span class="preis">{etikett}'
                          f'<span class="zahl">{_e(p)} €</span></span>')

        zeilen.append(
            f'<div class="zeile"><span class="nr">{_e(g.get("nr") or "")}</span>'
            f'<span><span class="name">{_e(g["name"])}{zusatz}</span>{besch}</span>'
            f'<span class="preise">{"".join(felder)}</span></div>'
        )

    return seite(
        kopf(kategorie)
        + f'<div class="liste" style="{stil}">' + "".join(zeilen) + '</div>'
        + fuss()
    )


def akzentseite(bild, breite, hoehe, ueberschrift, text):
    """Bild als runder Akzent neben einem Spruch. Bild bewusst in Originalgröße,
    hochskaliert würde es auf einem Fernseher matschig aussehen."""
    seite_ = (
        '<div class="akzent">'
        f'<div class="bildrahmen" style="width:{breite}px;height:{hoehe}px">'
        f'<img src="{bild}" width="{breite}" height="{hoehe}" alt=""></div>'
        f'<div class="spruch"><h2>{_e(ueberschrift)}</h2><p>{_e(text)}</p></div>'
        '</div>'
    )
    return seite(kopf("") + seite_ + fuss())


def angebotsseite(gruppe, gueltigkeit):
    karten = []
    for k in gruppe.get("karten", []):
        breit = ' breit' if k.get("breit") else ''
        sub = f'<div class="ks">{_e(k["sub"])}</div>' if k.get("sub") else ''
        preis = f'<div class="kp">{_e(k["preis"])}</div>' if k.get("preis") else ''
        karten.append(f'<div class="karte{breit}"><div class="kt">{_e(k["titel"])}</div>'
                      f'{sub}{preis}</div>')
    hinweis = (f'<p class="hinweis">{_e(gruppe["hinweis"])}</p>'
               if gruppe.get("hinweis") else '')
    return seite(
        kopf("Special-Angebote")
        + f'<div class="gruppe"><h2>{_e(gruppe["titel"])}</h2>{hinweis}'
        + f'<div class="karten">{"".join(karten)}</div></div>'
        + f'<div class="fuss"><span>{_e(gueltigkeit)}</span></div>'
    )


def stempelseite(s):
    return seite(
        kopf("Special-Angebote")
        + '<div class="gruppe">'
        + f'<h2>{_e(s["titel"])}</h2>'
        + f'<p class="hinweis" style="max-width:1200px;margin:26px auto 0;font-size:40px;'
          f'line-height:1.4">{_e(s["text"])}</p>'
        + f'<p class="hinweis" style="margin-top:22px;font-size:30px;color:var(--text3)">'
          f'{_e(s["hinweis"])}</p>'
        + '</div>' + fuss()
    )


def endseite():
    b = DATEN["betrieb"]
    return seite(
        '<div class="ende">'
        '<img src="@@LOGO@@" alt="" style="width:620px;mix-blend-mode:screen">'
        f'<div class="tel">{_e(b["telefon"])}</div>'
        f'<div class="adr">{_e(b["strasse"])} · {_e(b["plz"])} {_e(b["ort"])}</div>'
        '<img class="qr" src="@@QR@@" alt="">'
        '<div class="netz">Ganze Speisekarte online — QR-Code scannen</div>'
        '</div>'
    )


# ------------------------------------------------- vollständige Kartenseite --

VOLLSTIL = """
  /* Zwei Spalten per CSS-Mehrspaltensatz: Der Browser verteilt die Eintraege
     selbst so, dass beide Spalten gleich hoch werden. Nach Anzahl geteilt
     waeren sie unterschiedlich lang, weil manche Beschreibungen umbrechen. */
  .voll { flex:1; column-count:2; column-gap:58px; column-fill:balance; }
  .vz { display:grid; grid-template-columns:auto 1fr auto; gap:0 16px;
        align-items:baseline; padding:calc(9px * var(--s)) 0;
        border-bottom:1px solid rgba(226,179,95,.12);
        break-inside:avoid; -webkit-column-break-inside:avoid; }
  .vz .vnr { font-size:calc(27px * var(--s)); font-weight:700; color:var(--gold3);
             font-variant-numeric:tabular-nums; min-width:calc(48px * var(--s)); }
  .vz .vname { font-size:calc(33px * var(--s)); font-weight:700; line-height:1.15; }
  .vz .vbesch { display:block; font-size:calc(22px * var(--s)); color:var(--text2);
                line-height:1.2; margin-top:2px; }
  .vz .vpreise { display:flex; }
  .vz .vpreise span { width:calc(var(--pbreite,132px) * var(--s)); text-align:right;
      font-size:calc(32px * var(--s)); font-weight:700; color:var(--gold);
      font-variant-numeric:tabular-nums; white-space:nowrap; }
  .vz sup { font-size:.46em; color:var(--gold3); margin-left:.18em; }
  .groessen { text-align:center; font-size:27px; color:var(--gold3);
              letter-spacing:.08em; margin:-8px 0 16px; }
"""


def _marken(g):
    if not g.get("zusatz"):
        return ""
    return ('<sup>' + _e("".join(z if z == "*" else z + ")" for z in g["zusatz"]))
            + '</sup>')


def volllisteseite(kategorie, unterzeile, gerichte, spalten_kurz=None, pbreite=132):
    """Die ganze Kategorie auf einer Seite, zweispaltig.

    Gäste sollen ihr Gericht sofort finden und nicht warten, bis die nächste
    Seite umblättert. Die Schriftgröße wird beim Rendern automatisch so weit
    verkleinert, bis alles auf den Bildschirm passt (--s).
    """
    zeilen = []
    for g in gerichte:
        preise = "".join(
            f'<span>{_e(p)}</span>' if p not in (None, "", "-") else '<span>–</span>'
            for p in g.get("preise", []))
        besch = (f'<span class="vbesch">{_e(g["beschreibung"])}</span>'
                 if g.get("beschreibung") else '')
        zeilen.append(
            f'<div class="vz"><span class="vnr">{_e(g.get("nr") or "")}</span>'
            f'<span><span class="vname">{_e(g["name"])}{_marken(g)}</span>{besch}</span>'
            f'<span class="vpreise">{preise}</span></div>')

    # Groessenlegende einmal oben statt ueber jeder Spalte — spart Platz und
    # bleibt eindeutig, weil die Preise immer in derselben Reihenfolge stehen.
    groessen = ""
    echte = [s for s in (spalten_kurz or []) if s]
    if len(echte) > 1:
        groessen = ('<div class="groessen">Preise in Euro: '
                    + _e("  ·  ".join(echte)) + '</div>')

    unter = (f'<div style="text-align:center;font-size:28px;color:var(--text2);'
             f'margin:-6px 0 10px">{_e(unterzeile)}</div>' if unterzeile else '')

    return (KOPF + f'<style>{VOLLSTIL}</style>'
            + '<div class="flaeche"></div>'
            + f'<div class="inhalt" style="--s:1;--pbreite:{pbreite}px;padding:30px 58px">'
            + kopf(kategorie) + unter + groessen
            + f'<div class="voll" id="voll">{"".join(zeilen)}</div>'
            + fuss() + '</div>')


def logoseite():
    """Kurze Einblendung zwischen zwei Standzeiten der Karte."""
    return seite(
        '<div class="titel">'
        '<img class="logo" src="@@LOGO@@" alt="" style="width:980px">'
        '<div class="linie"></div>'
        '<p style="font-size:44px;letter-spacing:.14em;color:var(--gold2)">'
        'QUALITÄT · FRISCH · LECKER</p>'
        '</div>'
    )


def spruchseite(bild, breite, hoehe, ueberschrift, text):
    return akzentseite(bild, breite, hoehe, ueberschrift, text)


def telefonseite():
    b = DATEN["betrieb"]
    return seite(
        '<div class="ende">'
        f'<p style="font-size:44px;color:var(--text2)">Bestellen Sie jetzt</p>'
        f'<div class="tel" style="font-size:150px">{_e(b["telefon"])}</div>'
        f'<div class="adr">{_e(b["strasse"])} · {_e(b["plz"])} {_e(b["ort"])}</div>'
        '</div>'
    )
