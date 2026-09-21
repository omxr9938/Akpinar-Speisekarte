#!/usr/bin/env python3
"""
Prueft die Wunschzeit in der Kasse.

    python3 tools/test-lieferzeit.py

Der Laden will mindestens eine Stunde Vorlauf. Die angebotenen Zeiten muessen
also innerhalb der Oeffnungszeiten liegen, fruehestens eine Stunde ab jetzt,
und im Viertelstundentakt. Geprueft wird mit festgenagelter Uhr ueber Sommer-
und Winterzeiten und ueber die Raender: kurz vor Oeffnung, kurz vor Schluss,
mitten in der Nacht.

Startet einen eigenen Webserver, beendet sich mit Code 1 bei Fehlern.
"""

import sys, pathlib, http.server, socketserver, threading, functools
ROOT = pathlib.Path(__file__).resolve().parent.parent
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("127.0.0.1", 8942), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
from playwright.sync_api import sync_playwright

fehler = []
def pruefe(ok, t):
    print(("  OK   " if ok else "  FEHL ") + t)
    if not ok: fehler.append(t)

# (Beschreibung, feste Uhrzeit, erwartet-offen, erwartete erste Zeit, Tag)
FAELLE = [
    ("Sommer, mittags",        "2026-07-15T12:00:00", True,  "13:00", "Heute"),
    ("Sommer, kurz vor Oeffnung","2026-07-15T10:00:00", False, "11:00", "Heute"),
    ("Sommer, 11:10 (offen)",  "2026-07-15T11:10:00", True,  "12:15", "Heute"),
    ("Sommer, 20:00 (letzte 22:00)","2026-07-15T20:00:00", True, "21:00", "Heute"),
    # 21:10 + 1 h = 22:10, also nach Ladenschluss 22:00 -> heute nichts mehr
    ("Sommer, 21:10 -> morgen", "2026-07-15T21:10:00", True,  "11:00", "Morgen"),
    ("Sommer, 21:20 (nichts mehr heute)","2026-07-15T21:20:00", True, "11:00", "Morgen"),
    ("Sommer, 23:00 (zu)",     "2026-07-15T23:00:00", False, "11:00", "Morgen"),
    ("Winter, 19:00 (schliesst 21)","2026-01-15T19:00:00", True, "20:00", "Heute"),
    # 20:10 + 1 h = 21:10, nach Winterschluss 21:00 -> heute nichts mehr
    ("Winter, 20:10 -> morgen","2026-01-15T20:10:00", True,  "11:00", "Morgen"),
    ("Winter, 20:20 (nichts mehr)","2026-01-15T20:20:00", True, "11:00", "Morgen"),
    ("Sommer, 03:00 nachts",   "2026-07-15T03:00:00", False, "11:00", "Heute"),
]

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    for tag, zeit, off_erw, erste_erw, tag_erw in FAELLE:
        ctx = b.new_context(viewport={"width": 390, "height": 800})
        pg = ctx.new_page()
        # Uhr der Seite festnageln, bevor irgendein Skript laeuft
        pg.add_init_script(f"""
          (() => {{
            const fest = new Date('{zeit}').getTime();
            const Echt = Date;
            function Fake(...a) {{ return a.length ? new Echt(...a) : new Echt(fest); }}
            Fake.now = () => fest;
            Fake.parse = Echt.parse; Fake.UTC = Echt.UTC;
            Fake.prototype = Echt.prototype;
            window.Date = Fake;
          }})();
        """)
        pg.goto("http://127.0.0.1:8942/index.html", wait_until="networkidle")
        pg.wait_for_timeout(700)
        pg.evaluate("""() => localStorage.setItem('akpinar-korb', JSON.stringify([
          {name:'Margherita', nr:'1', kategorie:'Pizza', groesse:'Ø 32', wahl:[],
           ohne:[], extras:[], sossen:[], menue:null, notiz:'', preis:30, anzahl:1}]))""")
        pg.reload(wait_until="networkidle"); pg.wait_for_timeout(700)
        pg.click("#korb-knopf"); pg.wait_for_timeout(500)
        r = pg.evaluate("""() => {
            const box = document.querySelector('#kasse-zeit');
            const sofort = box.querySelector('.kasse__zopt--sofort');
            const tage = [...box.querySelectorAll('.kasse__ztag')].map(e=>e.textContent.trim());
            const zeiten = [...box.querySelectorAll('.kasse__zopt:not(.kasse__zopt--sofort)')]
              .map(e=>e.textContent.trim());
            const an = [...box.querySelectorAll('.ist-an')].map(e=>e.textContent.trim());
            return {sofort: !!sofort, tage, erste: zeiten[0]||null, letzte: zeiten[zeiten.length-1]||null,
                    anzahl: zeiten.length, an, hinweis: (document.querySelector('#kasse-zeit-hinweis')||{}).textContent};
        }""")
        ok = (r['sofort'] == off_erw and r['erste'] == erste_erw
              and (not r['tage'] or r['tage'][0] == tag_erw))
        pruefe(ok, f"{tag:34s} offen={r['sofort']!s:5s} erste={str(r['erste']):5s} "
                   f"letzte={str(r['letzte']):5s} ({r['anzahl']:2d}) {r['tage']} an={r['an']}")
        ctx.close()

    # --- Eine Stunde Vorlauf wirklich eingehalten?
    print("\nVorlauf")
    ctx = b.new_context(viewport={"width": 390, "height": 800})
    pg = ctx.new_page()
    pg.add_init_script("""
      (() => { const fest = new Date('2026-07-15T12:07:00').getTime();
        const E = Date; function F(...a){return a.length?new E(...a):new E(fest);}
        F.now=()=>fest; F.parse=E.parse; F.UTC=E.UTC; F.prototype=E.prototype; window.Date=F; })();
    """)
    pg.goto("http://127.0.0.1:8942/index.html", wait_until="networkidle"); pg.wait_for_timeout(700)
    pg.evaluate("""() => localStorage.setItem('akpinar-korb', JSON.stringify([
      {name:'Margherita', nr:'1', kategorie:'Pizza', groesse:'Ø 32', wahl:[],
       ohne:[], extras:[], sossen:[], menue:null, notiz:'', preis:30, anzahl:1}]))""")
    pg.reload(wait_until="networkidle"); pg.wait_for_timeout(700)
    pg.click("#korb-knopf"); pg.wait_for_timeout(500)
    z = pg.evaluate("""() => [...document.querySelectorAll('#kasse-zeit .kasse__zopt')]
        .filter(e=>!e.classList.contains('kasse__zopt--sofort')).map(e=>e.textContent.trim())""")
    pruefe(z[0] == "13:15", f"12:07 + 1 h -> naechste Viertelstunde 13:15 (ist {z[0]})")
    pruefe(all(int(t[:2])*60+int(t[3:]) >= 12*60+7+60 for t in z),
           "keine Zeit frueher als eine Stunde ab jetzt")
    pruefe(z[-1] == "22:00", f"letzte Zeit = Ladenschluss 22:00 (ist {z[-1]})")
    pruefe(all((int(t[:2])*60+int(t[3:])) % 15 == 0 for t in z), "alle Zeiten im Viertelstundentakt")

    # --- Bestelltext
    print("\nBestelltext")
    pg.evaluate("""() => {
      window.__auf = null; window.open = u => { window.__auf = u; };
      const klick = t => { const b=[...document.querySelectorAll('button')]
        .find(x=>x.textContent.trim().toLowerCase().indexOf(t)===0); if(b) b.click(); };
      klick('abholung'); klick('bar bei abholung');
      document.querySelectorAll('input').forEach(i => {
        if (i.type==='tel') i.value='0170 1234567';
        else if (i.type==='text' && !i.value) i.value='Test';
        i.dispatchEvent(new Event('input',{bubbles:true}));
      });
    }""")
    pg.wait_for_timeout(300)
    pg.evaluate("""() => [...document.querySelectorAll('#kasse-zeit .kasse__zopt')]
        .find(e=>e.textContent.trim()==='18:30').click()""")
    pg.wait_for_timeout(300)
    pg.evaluate("() => document.querySelector('#kasse-senden').click()")
    pg.wait_for_timeout(300)
    import urllib.parse
    url = pg.evaluate("() => window.__auf") or ""
    txt = urllib.parse.unquote(url.split("text=",1)[1]) if "text=" in url else ""
    pruefe("*Abholung:* um 18:30 Uhr" in txt, f"feste Zeit steht im Bestelltext")
    if "18:30" not in txt: print("      ", txt[:300])
    # jetzt "so schnell wie moeglich"
    pg.evaluate("""() => { window.__auf=null;
      document.querySelector('.kasse__zopt--sofort').click(); }""")
    pg.wait_for_timeout(300)
    pg.evaluate("() => document.querySelector('#kasse-senden').click()")
    pg.wait_for_timeout(300)
    url = pg.evaluate("() => window.__auf") or ""
    txt = urllib.parse.unquote(url.split("text=",1)[1]) if "text=" in url else ""
    pruefe("*Abholung:* so schnell wie möglich" in txt, "schnellstmöglich steht im Bestelltext")
    ctx.close()
    b.close()
srv.shutdown()
print("\n" + "="*62)
print("ALLES BESTANDEN" if not fehler else f"{len(fehler)} FEHLER")
sys.exit(1 if fehler else 0)
