#!/usr/bin/env python3
"""
Baut die Bildschirmseiten für die Fernseher im Laden als HTML. Jede Seite
wird später mit Chromium zu einem Standbild gerendert und als PNG und JPG in
bilder/ abgelegt — das ist die Datei, die auf den USB-Stick kommt.

Gestaltung folgt Karte und Website: dunkler Grund, Gold, Playfair Display für
Überschriften, Inter für alles andere. Schriftgrößen sind bewusst groß — ein
Fernseher im Laden wird aus zwei bis vier Metern gelesen, nicht aus 50 cm.
"""

import html
import json
import pathlib
import re

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
  .gruppe > h2 { font-family:"Playfair Display",serif; font-style:italic;
      font-weight:800; font-size:72px; color:var(--gold); text-align:center;
      letter-spacing:.02em; }
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






# --------------------------------------------------------------- Seitentypen --


# ------------------------------------------------- vollständige Kartenseite --

VOLLSTIL = """
  /* Zwei Spalten per CSS-Mehrspaltensatz: Der Browser verteilt die Eintraege
     selbst so, dass beide Spalten gleich hoch werden. Nach Anzahl geteilt
     waeren sie unterschiedlich lang, weil manche Beschreibungen umbrechen. */
  /* min-height:0 ist hier nicht kosmetisch: Ohne die Angabe bekommt ein
     Flex-Element als Mindesthoehe seinen eigenen Inhalt (min-height:auto).
     Bei einer mehrspaltigen Liste ist das mehr, als die Seite hoch ist - die
     Liste draengt sich auf, schiebt den Streifen darunter ueber den unteren
     Bildrand hinaus, und die Unterlaengen von g, ss und p werden abgeschnitten.
     Der Suchlauf nach der Schriftgroesse merkt davon nichts, weil er
     voll.scrollHeight gegen voll.clientHeight prueft und clientHeight durch
     genau diesen Ueberlauf schon zu gross ist. */
  .voll { flex:1; min-height:0; column-count:2; column-gap:58px;
          column-fill:balance; }
  .vz { display:grid; grid-template-columns:auto 1fr auto; gap:0 16px;
        align-items:baseline; padding:calc(9px * var(--s)) 0;
        border-bottom:1px solid rgba(226,179,95,.12);
        break-inside:avoid; -webkit-column-break-inside:avoid; }
  /* Feste Breite, nicht min-width: Jede Zeile ist ein eigenes Raster, also
     richtet sich die Spalte nach der Nummer IN DIESER Zeile. "14A" ist breiter
     als "14" und schob seinen Gerichtnamen um vier Pixel nach rechts, waehrend
     alle anderen buendig standen. */
  .vz .vnr { font-size:calc(27px * var(--s)); font-weight:700; color:var(--gold3);
             font-variant-numeric:tabular-nums;
             width:calc(58px * var(--s)); flex:none; }
  .vz .vname { font-size:calc(33px * var(--s)); font-weight:700; line-height:1.15; }
  .vz .vbesch { display:block; font-size:calc(22px * var(--s)); color:var(--text2);
                line-height:1.2; margin-top:2px; }
  .vz .vpreise { display:flex; }
  .vz .vpreise span { width:calc(var(--pbreite,132px) * var(--s)); text-align:right;
      font-size:calc(32px * var(--s)); font-weight:700; color:var(--gold);
      font-variant-numeric:tabular-nums; white-space:nowrap; }
  .vz sup { font-size:.46em; color:var(--gold3); margin-left:.18em; }
  /* Kein Seitenkopf und kein Streifen mehr: Die Bildschirme haengen im
     Laden, ueber der Theke. Wer davorsteht, weiss, wo er ist - Logo und
     Ueberschrift haben ihm nichts gesagt, was er nicht schon wusste, und
     kosteten zusammen mit dem Streifen unten rund 300 der 1080 Zeilen.
     Die gehoeren den Gerichten. */
  .groessen { text-align:center; font-size:calc(30px * var(--s));
              color:var(--gold3); letter-spacing:.08em;
              margin:0 0 calc(10px * var(--s)); }
  /* Einzeiliger Fuss. Auf den Gerichten stehen hochgestellte Ziffern; ohne
     einen Hinweis, wo sie erklaert sind, waeren sie Rauschen - und § 9 ZZulV
     verlangt die Kenntlichmachung. Eine Zeile, die kleinste auf dem Schirm. */
  .fuss { text-align:center; font-size:calc(19px * var(--s)); color:var(--text3);
          margin-top:calc(8px * var(--s)); }

  /* Zwischenueberschrift, wenn mehrere Kategorien auf einem Bildschirm stehen.
     break-after verhindert, dass eine Ueberschrift allein am Spaltenende
     haengen bleibt und ihre Gerichte erst in der naechsten Spalte folgen. */
  .vkat { margin:calc(26px * var(--s)) 0 calc(6px * var(--s));
          padding-bottom:calc(9px * var(--s));
          border-bottom:3px solid var(--gold2);
          break-inside:avoid; -webkit-column-break-inside:avoid;
          break-after:avoid-column; }
  .vkat:first-child { margin-top:0; }
  .vkat .vkkopf { display:flex; align-items:baseline;
          justify-content:space-between; gap:20px; }
  .vkat .vkname { font-family:"Playfair Display",serif; font-style:italic;
                  /* Auf dem Nudelbildschirm trennen diese drei Ueberschriften
                     drei Kategorien. Sie muessen aus der Liste herausstechen,
                     sonst liest sich die Seite als ein einziger Block. */
          font-weight:800; font-size:calc(58px * var(--s)); color:var(--gold);
          white-space:nowrap; }
  .vkat .vkleg { font-size:calc(21px * var(--s)); color:var(--text3);
          letter-spacing:.07em; white-space:nowrap; }
  /* Kategoriehinweis in eigener Zeile statt neben dem Namen: "Menue = inkl.
     Pommes + 0,33 l Getraenk" neben "Burger" und der Groessenlegende waere in
     einer Spalte zu breit - und ein waagrechter Ueberlauf faellt bei der
     Hoehenmessung nicht auf. In eigener Zeile darf er umbrechen. */
  .vkat .vkhinweis { font-size:calc(21px * var(--s)); color:var(--text2);
          line-height:1.25; margin-top:calc(4px * var(--s)); }

  /* Gerichte mit eigenen Groessen (Portion Pommes: klein 3,00 / gross 4,00).
     Sie brauchen keine feste Spaltenbreite - es gibt in ihrer Kategorie nur
     eine Preisspalte, an der sie sich ausrichten muessten. */
  .vz .vgr { width:auto !important; font-size:calc(22px * var(--s));
             font-weight:400; color:var(--text2); }
  .vz .vgr b { color:var(--gold); font-weight:700;
               font-size:calc(30px * var(--s)); margin-left:calc(5px * var(--s)); }

  /* Hinweisleiste unter der Kopfzeile — Menue-Aufpreis, Extra-Zutaten. */
  /* Die Hinweisleiste schrumpft nur begrenzt mit. Sie steht einmal oben und
     kostet kaum Platz; ohne Untergrenze landete die Marke auf dem
     Pizzabildschirm bei 17 Pixeln - halb so gross wie dieselbe goldene Marke
     im Streifen unten, und auf einem Fernseher nicht mehr zu lesen. */
  .vnotiz { display:flex; flex-wrap:wrap; align-items:baseline;
            justify-content:center;
            gap:max(4px, calc(8px * var(--s))) max(14px, calc(26px * var(--s)));
            margin:2px 0 8px;
            padding:max(5px, calc(10px * var(--s))) max(14px, calc(20px * var(--s)));
            border:1px solid rgba(226,179,95,.30); border-radius:14px;
            background:rgba(226,179,95,.06);
            font-size:max(19px, calc(26px * var(--s))); color:var(--text2); }
  /* Dieselbe goldene Pille wie die Marke "Mittagsangebot" im Streifen
     unten: Als blosser goldener Text ging der Menue-Aufpreis zwischen
     Unterzeile und Preislegende unter und wirkte wie Kleingedrucktes. */
  .vnotiz .nt { background:linear-gradient(180deg,#e9c987,#c8912f);
                color:#241a08; border-radius:999px;
                padding:max(3px, calc(5px * var(--s))) max(13px, calc(20px * var(--s)));
                font-family:"Playfair Display",serif; font-style:italic;
                font-weight:800; font-size:max(24px, calc(32px * var(--s))); }
  .vnotiz b { color:var(--gold); font-weight:700; }
"""



def _marken(g):
    if not g.get("zusatz"):
        return ""
    return ('<sup>' + _e("".join(z if z == "*" else z + ")" for z in g["zusatz"]))
            + '</sup>')


def _vzeile(g, pbreite):
    # Gerichte mit eigenen Groessen tragen sie in "groessen"; "preise" haelt nur
    # den kleinsten Preis, damit die Liste auf der Website sortierbar bleibt.
    # Auf dem Fernseher muessen beide Groessen stehen, sonst wirkt die grosse
    # Portion an der Kasse wie ein Aufschlag.
    if g.get("groessen"):
        preise = ('<span class="vgr">'
                  + "  \u00b7  ".join(f'{_e(x["label"])} <b>{_e(x["preis"])}</b>'
                                   for x in g["groessen"])
                  + '</span>')
    else:
        preise = "".join(
            f'<span>{_e(p)}</span>' if p not in (None, "", "-") else '<span>\u2013</span>'
            for p in g.get("preise", []))
    besch = (f'<span class="vbesch">{_e(g["beschreibung"])}</span>'
             if g.get("beschreibung") else '')
    return (f'<div class="vz" style="--pbreite:{pbreite}px">'
            f'<span class="vnr">{_e(g.get("nr") or "")}</span>'
            f'<span><span class="vname">{_e(g["name"])}{_marken(g)}</span>{besch}</span>'
            f'<span class="vpreise">{preise}</span></div>')


def _legende(spalten_kurz):
    """Nur sinnvoll, wenn es mehr als eine Preisspalte gibt \u2014 sonst ist
    klar, wozu der Preis geh\u00f6rt."""
    echte = [t for t in (spalten_kurz or []) if t]
    return "  \u00b7  ".join(echte) if len(echte) > 1 else ""


def volllisteseite(bloecke, notiz=None):
    """Eine oder mehrere Kategorien vollständig auf einer Seite, zweispaltig.

    Auf der Seite steht nur die Karte: keine Überschrift, kein Logo, kein
    Streifen. Der Bildschirm hängt über der Theke — wer davorsteht, weiß, in
    welchem Laden er ist und dass das eine Speisekarte ist. Die Zeilen, die
    ihm das noch einmal gesagt haben, sind jetzt Schriftgröße.

    Gäste sollen ihr Gericht sofort finden und nicht warten, bis die nächste
    Seite umblättert. Die Schriftgröße wird beim Rendern automatisch so weit
    gesucht, dass alles gerade noch auf den Bildschirm passt (--s).

    bloecke: Liste von (titel|None, gerichte, spalten_kurz, pbreite, hinweis).
    Steht nur ein Block ohne Titel drin, steht die Größenlegende einmal oben.
    Bei mehreren Kategorien bekommt jede eine Zwischenüberschrift mit ihrer
    eigenen Legende — Nudeln haben einen Preis, Burger zwei, das lässt sich
    nicht gemeinsam oben abhandeln.
    """
    einzeln = len(bloecke) == 1 and not bloecke[0][0]

    teile = []
    for titel, gerichte, spalten_kurz, pbreite, hinweis in bloecke:
        if titel:
            leg = _legende(spalten_kurz)
            teile.append(
                '<div class="vkat"><div class="vkkopf">'
                f'<span class="vkname">{_e(titel)}</span>'
                + (f'<span class="vkleg">{_e(leg)}</span>' if leg else '')
                + '</div>'
                + (f'<div class="vkhinweis">{_e(hinweis)}</div>' if hinweis else '')
                + '</div>')
        teile += [_vzeile(g, pbreite) for g in gerichte]

    # Die Größenlegende bleibt, auch wenn sonst alles über der Liste weg ist:
    # Ohne sie stehen auf dem Pizzabildschirm drei Preise nebeneinander und
    # niemand weiß, welcher zu welchem Durchmesser gehört. Bei einer einzigen
    # Preisspalte ist sie überflüssig und fällt weg.
    leg = _legende(bloecke[0][2]) if einzeln else ""
    groessen = f'<div class="groessen">Preise in Euro: {_e(leg)}</div>' if leg else ""

    return (KOPF + f'<style>{VOLLSTIL}</style>'
            + '<div class="flaeche"></div>'
            + '<div class="inhalt inhalt--liste" style="--s:1;padding:26px 48px">'
            + groessen + (notiz or "")
            + f'<div class="voll" id="voll">{"".join(teile)}</div>'
            + _fuss(bloecke) + '</div>')


# ------------------------------------------------------------- Hinweisleisten --

def _fuss(bloecke):
    """Die einzige Zeile unter der Karte — und nur, wenn sie gebraucht wird.

    Auf manchen Gerichten stehen hochgestellte Ziffern. Ohne einen Hinweis,
    was sie bedeuten, sind sie für den Gast nur Rauschen — und § 9 ZZulV
    verlangt die Kenntlichmachung. Alle zwölf Zusatzstoffe auf den Bildschirm
    zu schreiben, ginge nicht; dafür gibt es den Aushang, den dieselbe
    Vorschrift ohnehin verlangt. Diese Zeile verbindet beides.

    Steht auf dem Bildschirm kein einziges gekennzeichnetes Gericht — wie auf
    dem türkischen —, entfällt die Zeile. Eine Erklärung für Zeichen, die
    nirgends stehen, kostet nur Schriftgröße.
    """
    markiert = any(g.get("zusatz") for _t, gerichte, *_r in bloecke
                   for g in gerichte)
    if not markiert:
        return ""
    return ('<div class="fuss">Hochgestellte Ziffern: Zusatzstoffe und '
            'Allergene — erklärt der Aushang im Laden</div>')


def _nummernbereiche(nummern):
    """[30,31,32,34,35,36,37] -> "30\u201332, 34\u201337". Eine Aufz\u00e4hlung von elf
    Einzelnummern liest auf einem Fernseher niemand."""
    zahlen = sorted({int(n) for n in nummern if str(n).isdigit()})
    if not zahlen:
        return ""
    bereiche, start, vorher = [], zahlen[0], zahlen[0]
    for z in zahlen[1:]:
        if z == vorher + 1:
            vorher = z
            continue
        bereiche.append((start, vorher))
        start = vorher = z
    bereiche.append((start, vorher))
    teile = [str(a) if a == b else f"{a}\u2013{b}" for a, b in bereiche]
    if len(teile) == 1:
        return teile[0]
    return ", ".join(teile[:-1]) + " und " + teile[-1]


def notiz_menue(zutaten_konf, gerichte):
    """\u201eAls Men\u00fc + 5,00 \u20ac\u201c. Preis, Text und vor allem die Frage, f\u00fcr welche
    Gerichte das gilt, kommen aus bestellung.json \u2014 mit genau demselben
    Ausdruck, den auch die Bestellseite auswertet. Sonst steht auf dem
    Fernseher irgendwann ein Men\u00fc, das sich online nicht bestellen l\u00e4sst.

    Bewusst die Nummern und nicht \u201ealle D\u00f6ner-Gerichte\u201c: D\u00f6ner Pomm, D\u00f6ner-
    Teller, D\u00f6ner-Box, D\u00f6ner Bowl und Pide D\u00f6ner hei\u00dfen auch D\u00f6ner, bekommen
    aber kein Men\u00fc \u2014 sie enthalten Pommes oder Reis bereits.
    """
    m = zutaten_konf["menue"]
    muster = re.compile(zutaten_konf["menue"]["gilt_fuer"], re.IGNORECASE)
    passend = [g.get("nr") for g in gerichte if muster.search(g["name"])]
    bereiche = _nummernbereiche(passend)
    wo = f"bei Nr. {bereiche}" if bereiche else ""
    return ('<div class="vnotiz">'
            f'<span class="nt">Als Men\u00fc + {_e(m["preis"])} \u20ac</span>'
            f'<span>{_e(m["beschreibung"])}</span>'
            + (f'<span><b>{_e(wo)}</b></span>' if wo else '')
            + '</div>')




# ------------------------------------------------------- wechselnder Streifen --















_PREISMUSTER = re.compile(r"(\+\s?)?(\d{1,3},\d{2}\s*€)")








ANGEBOTSTIL = """
  /* Die einzige Ueberschrift, die geblieben ist - und sie steht mittig,
     nicht mehr neben einem Logo am Rand. Sie sagt dem Gast etwas, was er
     sonst nicht sieht: dass diese Preise nur mittags gelten. */
  .atitel { text-align:center; font-family:"Playfair Display",serif;
      font-style:italic; font-weight:800; font-size:calc(86px * var(--s));
      color:var(--gold); line-height:1.05; }
  .zeitleiste { text-align:center; font-size:calc(40px * var(--s));
      font-weight:700; color:var(--gold2); letter-spacing:.03em;
      margin:calc(4px * var(--s)) 0 calc(16px * var(--s)); }
  /* min-height:0 wie bei der Gerichteliste: Ohne die Angabe draengt sich der
     Inhalt auf seine eigene Hoehe auf und schiebt den Streifen darunter unter
     den Bildrand - die Unterlaengen werden dann abgeschnitten. */
  /* align-items:start - sonst zieht jede Gruppe ihren Rahmen auf die Hoehe
     der hoechsten in derselben Zeile. Unter der Familien-Pizza stand dadurch
     ein handbreiter leerer Kasten, weil die Doener-Gruppe daneben sechs
     Karten hat. */
  /* Die groesste Gruppe steht links und reicht ueber beide Reihen, die
     kleineren stapeln sich rechts daneben. Ohne das blieb rechts unten ein
     leeres Viertel des Bildschirms stehen, seit die Familien-Pizza weg ist -
     und leere Flaeche ist auf einem Fernseher nur ungenutzte Schriftgroesse. */
  .alle { flex:1; min-height:0; display:grid; grid-template-columns:1fr 1fr;
          gap:calc(22px * var(--s)) 46px;
          align-content:start; align-items:start; }
  .agruppe--gross { grid-row:span 2; }
  .agruppe { border:1px solid rgba(226,179,95,.22); border-radius:18px;
             padding:calc(18px * var(--s)) calc(22px * var(--s));
             background:rgba(255,255,255,.02); }
  .agruppe h3 { font-family:"Playfair Display",serif; font-style:italic;
      font-weight:800; font-size:calc(44px * var(--s)); color:var(--gold);
      text-align:center; }
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


def alleangeboteseite(ohne=()):
    """Alle Angebotsgruppen auf einer Seite, ohne Kopf und ohne Streifen.

    "Mittagsangebot" steht groß und mittig oben — es ist die einzige
    Überschrift, die auf den vier Bildschirmen geblieben ist, und zwar weil
    sie hier etwas sagt, was der Gast nicht sieht: dass diese Preise nur
    mittags gelten. Direkt darunter steht, wann.

    ohne: Titel von Gruppen, die nicht auf den Bildschirm sollen.
    """
    a = DATEN["angebote"]
    gruppen = []
    for g in a["gruppen"]:
        if g["titel"] in ohne:
            continue
        karten = []
        for k in g.get("karten", []):
            titel = f'<div class="kt">{_e(k["titel"])}</div>' if k.get("titel") else ""
            sub = f'<div class="ks">{_e(k["sub"])}</div>' if k.get("sub") else ""
            preis = f'<div class="kp">{_e(k["preis"])}</div>' if k.get("preis") else ""
            karten.append(f'<div class="akarte">{titel}{sub}{preis}</div>')
        hinweis = (f'<p class="ghinweis">{_e(g["hinweis"])}</p>'
                   if g.get("hinweis") else "")
        gruppen.append((len(karten),
                        f'<h3>{_e(g["titel"])}</h3>{hinweis}'
                        f'<div class="akarten">{"".join(karten)}</div>'))

    # Die Gruppe mit den meisten Karten bekommt die hohe Spalte. Bewusst
    # ueber die Kartenzahl und nicht ueber die Position: Kommt eine Gruppe
    # dazu oder faellt eine weg, sitzt die grosse weiterhin richtig.
    groesste = max(range(len(gruppen)), key=lambda i: gruppen[i][0]) if gruppen else -1
    gruppen = [f'<div class="agruppe{" agruppe--gross" if i == groesste else ""}">'
               f'{inhalt}</div>' for i, (_n, inhalt) in enumerate(gruppen)]

    return (KOPF + f'<style>{ANGEBOTSTIL}</style>'
            + '<div class="flaeche"></div>'
            + '<div class="inhalt inhalt--angebot" style="--s:1;padding:26px 48px">'
            + f'<h1 class="atitel">{_e(a["titel"])}</h1>'
            + f'<p class="zeitleiste">{_e(a["gueltigkeit"])}</p>'
            + f'<div class="alle" id="voll">{"".join(gruppen)}</div>'
            + f'<p class="bedingung">{_e(a["zusatz"])}</p>' + '</div>')