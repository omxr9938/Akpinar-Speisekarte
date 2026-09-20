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


# --------------------------------------------------------------- Seitentypen --


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


def volllisteseite(kategorie, unterzeile, gerichte, spalten_kurz=None, pbreite=132,
                   band=None):
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

    return (KOPF + f'<style>{VOLLSTIL}{BANNERSTIL}</style>'
            + '<div class="flaeche"></div>'
            + f'<div class="inhalt" style="--s:1;--pbreite:{pbreite}px;padding:30px 58px">'
            + kopf(kategorie) + unter + groessen
            + f'<div class="voll" id="voll">{"".join(zeilen)}</div>'
            + (band if band is not None else band_logo()) + '</div>')


# ------------------------------------------------------- wechselnder Streifen --

BANNERSTIL = """
  /* Feste Hoehe, nicht min-height: Die vier Streifen sind unterschiedlich hoch
     (Logo, Foto, Text). Bei variabler Hoehe verschoebe sich die Gerichteliste
     darueber um ein paar Pixel und die Karte wuerde beim Wechsel springen. */
  .band { display:flex; align-items:center; justify-content:space-between;
          gap:40px; height:112px; flex:none; box-sizing:border-box;
          margin-top:16px; padding-top:16px; overflow:hidden;
          border-top:1px solid rgba(226,179,95,.24); }
  .band--mitte { justify-content:center; }
  .band .adr { font-size:30px; color:var(--text2); }
  .band .tel { font-size:36px; color:var(--text2); }
  .band .tel b { color:var(--gold); font-size:42px; }
  .band .gross { font-family:"Playfair Display",serif; font-style:italic;
                 font-weight:800; font-size:62px; color:var(--gold);
                 white-space:nowrap; }
  .band .vor { font-size:32px; color:var(--text2); margin-right:22px; }
  .band img.blogo { height:78px; mix-blend-mode:screen; }
  .band .claim { font-size:28px; letter-spacing:.16em; color:var(--gold2);
                 margin-left:28px; }
  .band img.bfoto { height:84px; width:84px; object-fit:cover; border-radius:50%;
                    border:3px solid var(--gold2); }
  .band .spruchtext { font-family:"Playfair Display",serif; font-style:italic;
                      font-weight:800; font-size:46px; color:var(--gold);
                      margin-left:26px; }
  .band .btitel { font-family:"Playfair Display",serif; font-style:italic;
                  font-weight:800; font-size:44px; color:var(--gold);
                  white-space:nowrap; margin-right:26px; }
  .band .btext { font-size:32px; color:var(--text2); white-space:nowrap; }
  .band .bklein { font-size:24px; color:var(--text3); margin-left:22px;
                  white-space:nowrap; }
"""


def band_logo():
    return ('<div class="band band--mitte">'
            '<img class="blogo" src="@@LOGO@@" alt="">'
            '<span class="claim">QUALITÄT · FRISCH · LECKER</span>'
            '</div>')


def band_stempel():
    """Stempelkarte — für jemanden im Laden die nützlichste Information:
    Sie bringt ihn beim nächsten Mal wieder."""
    st = DATEN["stempelkarte"]
    return ('<div class="band band--mitte">'
            f'<span class="btitel">{_e(st["titel"])}</span>'
            '<span class="btext">Ab 25 € ein Stempel · 10 Stempel = '
            'Familien-Pizza gratis</span>'
            f'<span class="bklein">{_e(st["hinweis"])}</span>'
            '</div>')


def band_lieferung():
    """Viele Laufkunden wissen nicht, dass es einen Lieferdienst gibt."""
    orte = []
    for z in DATEN["lieferung"]["zonen"]:
        orte += [o.strip() for o in z["orte"].replace("…", "").split(",") if o.strip()]
    return ('<div class="band band--mitte">'
            '<span class="btitel">Wir liefern</span>'
            f'<span class="btext">{_e(" · ".join(orte[:8]))} u. a.</span>'
            '</div>')


def band_zeiten():
    """Bewusst beide Jahreszeiten nennen: Das Video ist eine feste Datei und
    wuerde im Winter sonst eine falsche Uhrzeit zeigen."""
    o = DATEN["oeffnungszeiten"]
    sommer = o["saisons"][0]["zeiten"][0]["zeit"]
    winter = o["saisons"][1]["zeiten"][0]["zeit"]
    return ('<div class="band band--mitte">'
            '<span class="btitel">Täglich geöffnet</span>'
            f'<span class="btext">{_e(sommer)} · im Winter {_e(winter)}</span>'
            '</div>')


def band_spruch(bild, text):
    return ('<div class="band band--mitte">'
            f'<img class="bfoto" src="{bild}" alt="">'
            f'<span class="spruchtext">{_e(text)}</span>'
            '</div>')


ANGEBOTSTIL = """
  .zeitleiste { text-align:center; font-size:calc(40px * var(--s));
      font-weight:700; color:var(--gold2); letter-spacing:.03em; margin:-6px 0 14px; }
  .alle { flex:1; display:grid; grid-template-columns:1fr 1fr; gap:calc(22px * var(--s)) 46px;
          align-content:start; }
  .agruppe { border:1px solid rgba(226,179,95,.22); border-radius:18px;
             padding:calc(18px * var(--s)) calc(22px * var(--s));
             background:rgba(255,255,255,.02); }
  .agruppe h3 { font-family:"Playfair Display",serif; font-weight:800;
      font-size:calc(44px * var(--s)); color:var(--gold); text-align:center; }
  .ghinweis { text-align:center; font-size:calc(24px * var(--s));
              color:var(--text2); margin-top:calc(6px * var(--s)); }
  .akarten { display:flex; flex-wrap:wrap; justify-content:center;
             gap:calc(14px * var(--s)); margin-top:calc(16px * var(--s)); }
  .akarte { background:linear-gradient(180deg,#e9c987,#c8912f); color:#241a08;
            border-radius:14px; padding:calc(14px * var(--s)) calc(22px * var(--s));
            text-align:center; min-width:calc(190px * var(--s)); }
  .akarte .kt { font-family:"Playfair Display",serif; font-style:italic;
                font-weight:800; font-size:calc(30px * var(--s)); }
  .akarte .ks { font-size:calc(20px * var(--s)); opacity:.78;
                margin-top:calc(3px * var(--s)); }
  .akarte .kp { font-family:"Playfair Display",serif; font-style:italic;
                font-weight:800; font-size:calc(38px * var(--s));
                margin-top:calc(8px * var(--s)); }
  .bedingung { text-align:center; font-size:calc(26px * var(--s));
               color:var(--text3); margin-top:calc(12px * var(--s)); }
"""


def alleangeboteseite(band=None):
    """Alle Angebotsgruppen auf einer Seite. Damit steht auch auf dem
    Angebots-Bildschirm durchgehend alles — kein Gast muss warten, bis seine
    Gruppe wieder drankommt."""
    a = DATEN["angebote"]
    gruppen = []
    for g in a["gruppen"]:
        karten = []
        for k in g.get("karten", []):
            titel = f'<div class="kt">{_e(k["titel"])}</div>' if k.get("titel") else ""
            sub = f'<div class="ks">{_e(k["sub"])}</div>' if k.get("sub") else ""
            preis = f'<div class="kp">{_e(k["preis"])}</div>' if k.get("preis") else ""
            karten.append(f'<div class="akarte">{titel}{sub}{preis}</div>')
        hinweis = (f'<p class="ghinweis">{_e(g["hinweis"])}</p>'
                   if g.get("hinweis") else "")
        gruppen.append(f'<div class="agruppe"><h3>{_e(g["titel"])}</h3>{hinweis}'
                       f'<div class="akarten">{"".join(karten)}</div></div>')

    return (KOPF + f'<style>{ANGEBOTSTIL}{BANNERSTIL}</style>'
            + '<div class="flaeche"></div>'
            + '<div class="inhalt" style="--s:1;padding:28px 56px">'
            + kopf(a["titel"])
            + f'<p class="zeitleiste">{_e(a["gueltigkeit"])}</p>'
            + f'<div class="alle" id="voll">{"".join(gruppen)}</div>'
            + f'<p class="bedingung">{_e(a["zusatz"])}</p>'
            + (band if band is not None else band_logo()) + '</div>')
