#!/usr/bin/env python3
"""
Prueft die Auswahlfragen im Bestellfenster.

    python3 tools/test-wahlen.py

Die Karte legt sich bei manchen Gerichten nicht fest: "mit Pommes, Reis oder
Salat", "Alle Pizzen mit Tomaten- oder Sahnesosse", "Rigatoni / Spaghetti /
Tortellini". Der Gast muss sich entscheiden koennen, und bei den Beilagen darf
ohne Antwort nichts im Warenkorb landen - per WhatsApp faellt eine fehlende
Beilage sonst erst beim Kochen auf.

Startet einen eigenen Webserver, beendet sich mit Code 1 bei Fehlern.
"""

import sys, pathlib, http.server, socketserver, threading, functools, json
ROOT = pathlib.Path(__file__).resolve().parent.parent
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("127.0.0.1", 8931), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()

from playwright.sync_api import sync_playwright
fehler = []

def pruefe(ok, text):
    print(("  OK   " if ok else "  FEHL ") + text)
    if not ok: fehler.append(text)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    pg = b.new_page(viewport={"width": 390, "height": 780})
    konsole = []
    pg.on("console", lambda m: konsole.append(m.type + ": " + m.text))
    pg.on("pageerror", lambda e: konsole.append("pageerror: " + str(e)))
    pg.goto("http://127.0.0.1:8931/index.html", wait_until="networkidle")
    pg.wait_for_timeout(800)

    def oeffnen(name, kategorie=None):
        # Name allein reicht nicht: "Vegetarisch" ist Pizza Nr. 13 UND
        # Nudelgericht Nr. 74, "Tonno" ebenso.
        pg.evaluate("""([n, k]) => {
            localStorage.removeItem('akpinar-korb');
            const li = [...document.querySelectorAll('.item')].find(e =>
              e._gericht && e._gericht.name === n &&
              (!k || (e._kategorie && e._kategorie.id === k)));
            if (!li) throw new Error('Gericht nicht gefunden: ' + n + ' / ' + k);
            li.querySelector('.item__bestellen').click();
        }""", [name, kategorie])
        pg.wait_for_selector(".bf", timeout=3000)

    def fragen():
        return pg.evaluate("""() => [...document.querySelectorAll('.bf__titel')]
            .map(e => e.textContent.trim())""")

    def chips(frage):
        # Ab dem Titel weitergehen bis zur naechsten Chipreihe: Bei "Zutaten
        # weglassen" steht dazwischen noch ein Erklaersatz.
        return pg.evaluate("""(f) => {
            const t = [...document.querySelectorAll('.bf__titel')]
              .find(e => e.textContent.trim().startsWith(f));
            if (!t) return null;
            let n = t.nextElementSibling;
            while (n && !n.classList.contains('bf__chips')) {
              if (n.classList.contains('bf__titel')) return [];
              n = n.nextElementSibling;
            }
            if (!n) return [];
            return [...n.querySelectorAll('.bf__chip')]
              .map(c => ({text: c.textContent.trim(), an: c.classList.contains('ist-an')}));
        }""", frage)

    # --- 1. Döner-Box: Pflichtwahl Pommes/Reis/Salat
    print("\nDöner-Box")
    oeffnen("Döner-Box")
    pruefe(any(f.startswith("Beilage") for f in fragen()), "Frage 'Beilage' erscheint")
    c = chips("Beilage")
    pruefe([x["text"] for x in c] == ["Pommes", "Reis", "Salat"],
           f"Optionen Pommes/Reis/Salat  (ist: {[x['text'] for x in c]})")
    pruefe(not any(x["an"] for x in c), "nichts vorausgewählt (Pflichtfrage)")
    zut = chips("Zutaten weglassen") or []
    pruefe(not any("Reis" in x["text"] or x["text"] == "Pommes" for x in zut),
           f"Beilagen stehen nicht mehr bei 'Zutaten weglassen'  (ist: {[x['text'] for x in zut]})")
    # ohne Antwort in den Korb -> muss blockieren
    pg.click(".bf__rein"); pg.wait_for_timeout(400)
    pruefe(pg.locator(".bf").count() == 1, "ohne Beilage: Fenster bleibt offen")
    pruefe(pg.locator(".bf__chips.ist-fehlend").count() == 1, "offene Frage wird markiert")
    pruefe(pg.evaluate("() => JSON.parse(localStorage.getItem('akpinar-korb')||'[]').length") == 0,
           "nichts im Warenkorb gelandet")
    # jetzt antworten
    pg.click(".bf__chip--wahl:has-text('Reis')"); pg.wait_for_timeout(150)
    pg.click(".bf__rein"); pg.wait_for_timeout(500)
    pruefe(pg.locator(".bf").count() == 0, "mit Beilage: Fenster schließt")
    korb = pg.evaluate("() => JSON.parse(localStorage.getItem('akpinar-korb')||'[]')")
    pruefe(len(korb) == 1 and korb[0]["wahl"] == ["Beilage: Reis"],
           f"Antwort im Warenkorb  (ist: {korb[0].get('wahl') if korb else None})")

    # --- 2. Döner-Teller
    print("\nDöner-Teller")
    oeffnen("Döner-Teller")
    c = chips("Beilage")
    pruefe(c and [x["text"] for x in c] == ["Pommes", "gemischter Salat"],
           f"Optionen Pommes/gemischter Salat  (ist: {[x['text'] for x in c] if c else None})")
    zut = chips("Zutaten weglassen") or []
    pruefe(not any("oder" in x["text"] for x in zut),
           f"kein 'Pommes oder gem. Salat' mehr zum Abwählen  (ist: {[x['text'] for x in zut]})")
    pruefe(any(x["text"] == "Fleisch" for x in zut), "Fleisch bleibt abwählbar")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(200)

    # --- 3. Pizza: Soße vorausgewählt, keine Pflicht
    print("\nPizza Margherita")
    oeffnen("Margherita", "pizza")
    c = chips("Soße")
    pruefe(c and [x["text"] for x in c] == ["Tomatensoße", "Sahnesoße"],
           f"Soßenwahl da  (ist: {[x['text'] for x in c] if c else None})")
    pruefe(c and c[0]["an"] and not c[1]["an"], "Tomatensoße vorausgewählt")
    pg.click(".bf__rein"); pg.wait_for_timeout(500)
    pruefe(pg.locator(".bf").count() == 0, "ohne Klick direkt in den Korb (keine Pflicht)")
    korb = pg.evaluate("() => JSON.parse(localStorage.getItem('akpinar-korb')||'[]')")
    pruefe(korb and korb[-1]["wahl"] == ["Soße: Tomatensoße"],
           f"Soße im Warenkorb  (ist: {korb[-1].get('wahl') if korb else None})")

    # --- 4. Pizzabrot: keine Soßenwahl
    print("\nPizzabrot")
    oeffnen("Pizzabrot", "pizza")
    pruefe(not any(f.startswith("Soße") for f in fragen()),
           f"keine Soßenwahl beim Pizzabrot  (Fragen: {fragen()})")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(200)

    # --- 5. Nudeln: Sorte vorausgewählt
    print("\nNudeln Napoli")
    oeffnen("Napoli", "nudeln")
    c = chips("Nudelsorte")
    pruefe(c and [x["text"] for x in c] == ["Rigatoni", "Spaghetti", "Tortellini"],
           f"Nudelsorte da  (ist: {[x['text'] for x in c] if c else None})")
    pruefe(c and c[0]["an"], "Rigatoni vorausgewählt")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(200)

    # --- 6. Nudeln Vegetarisch: zwei Fragen
    print("\nNudeln Vegetarisch")
    oeffnen("Vegetarisch", "nudeln")
    f = fragen()
    pruefe(any(x.startswith("Nudelsorte") for x in f) and any(x.startswith("Soße") for x in f),
           f"Nudelsorte UND Soße  (Fragen: {f})")
    zut = chips("Zutaten weglassen") or []
    pruefe(not any("/" in x["text"] for x in zut),
           f"'Tomaten-/Sahnesoße' nicht mehr zum Abwählen  (ist: {[x['text'] for x in zut]})")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(200)

    # --- 7. Döner Classic: keine Wahl, unverändert
    print("\nDöner im Fladenbrot (Classic)")
    oeffnen("Döner im Fladenbrot (Classic)")
    f = fragen()
    pruefe(not any(x.startswith("Beilage") or x.startswith("Nudelsorte") for x in f),
           f"keine fremde Frage  (Fragen: {f})")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(200)

    # --- 8. WhatsApp-Text
    print("\nBestelltext")
    pg.evaluate("""() => localStorage.setItem('akpinar-korb', JSON.stringify([
      {name:'Döner-Box', nr:'', kategorie:'Türkisch', groesse:'', wahl:['Beilage: Reis'],
       ohne:['Zwiebeln'], extras:[], sossen:['Knoblauchsoße'], menue:null, notiz:'',
       preis:7, anzahl:1}]))""")
    pg.reload(wait_until="networkidle"); pg.wait_for_timeout(700)
    pg.evaluate("() => { window.__auf = null; window.open = u => { window.__auf = u; }; }")
    pg.click("#korb-knopf"); pg.wait_for_timeout(600)
    # Kasse ausfuellen: Abholung, Barzahlung, Name und Telefon.
    pg.evaluate("""() => {
      const klick = t => {
        const b = [...document.querySelectorAll('button')]
          .find(x => x.textContent.trim().toLowerCase().indexOf(t) === 0);
        if (b) b.click();
      };
      klick('abholung');
      klick('bar bei abholung');
      document.querySelectorAll('input[required], input').forEach(i => {
        if (i.type === 'tel') i.value = '0170 1234567';
        else if (i.type === 'text' && !i.value) i.value = 'Testbestellung';
        i.dispatchEvent(new Event('input', {bubbles: true}));
      });
    }""")
    pg.wait_for_timeout(400)
    pg.evaluate("() => { const b = document.querySelector('#kasse-senden'); if (b) b.click(); }")
    pg.wait_for_timeout(300)
    txt = pg.evaluate("() => window.__auf ? decodeURIComponent(window.__auf) : '(nicht abgeschickt)'")
    # Kleinschreibung ist Absicht: toUpperCase() machte im Deutschen aus
    # "Sosse" ein "SOSSE". Siehe Abschnitt 13.
    pruefe("*Beilage:* Reis" in (txt or ""), "Beilage steht im WhatsApp-Text")
    if "Beilage" not in (txt or ""):
        print("      Text:", (txt or "")[:400])

    # --- 9. Keine erfundenen Zutaten
    print("\nZutaten gegen die Karte")
    def wegliste(name, kat):
        oeffnen(name, kat)
        r = pg.evaluate("""() => {
            const t = [...document.querySelectorAll('.bf__titel')]
              .find(e => e.textContent.trim().startsWith('Zutaten weglassen'));
            if (!t) return [];
            let x = t.nextElementSibling;
            while (x && !x.classList.contains('bf__chips')) x = x.nextElementSibling;
            return x ? [...x.querySelectorAll('.bf__chip')].map(c => c.textContent.trim()) : [];
        }""")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
        return r

    # Die Basiszutaten des Standard-Doeners duerfen nur dort auftauchen, wo die
    # Beschreibung auf ein anderes Gericht verweist und die Fuellung deshalb
    # nicht selbst nennt.
    # Die Box hat gar nichts zum Abwaehlen: Die Karte nennt nur die Beilage,
    # und die ist eine Auswahl, keine Zutat. Eine Sosse stand hier zeitweise
    # zusaetzlich drin - vom Laden wieder gestrichen, weil man sie dann
    # gleichzeitig waehlen und abwaehlen konnte.
    w = wegliste("Döner-Box", "tuerkisch")
    pruefe(w == [], f"Döner-Box: nichts zum Abwählen  (ist: {w})")
    w = wegliste("Chip Cheese Bolognese", "tuerkisch")
    pruefe("Soße" not in w, f"Chip Cheese Bolognese ohne Soße  (ist: {w})")
    w = wegliste("Gyros-Pizza", "pizza")
    pruefe("Blaukraut" in w and "Kraut" not in w,
           f"Gyros-Pizza sagt Blaukraut  (ist: {w})")
    w = wegliste("Döner-Teller", "tuerkisch")
    pruefe(w == ["Fleisch", "Soße"], f"Döner-Teller: Fleisch und Soße  (ist: {w})")
    w = wegliste("Pide Weichkäse", "tuerkisch")
    pruefe("Fleisch" not in w, f"Pide Weichkäse hat kein Fleisch  (ist: {w})")
    w = wegliste("Sucuk Pide mit Ei", "tuerkisch")
    pruefe("Fleisch" not in w, f"Sucuk Pide hat kein Fleisch  (ist: {w})")
    w = wegliste("Käse Lahmacun", "tuerkisch")
    pruefe(not any(x in w for x in ("Tomaten", "Zwiebeln", "Blaukraut")),
           f"Käse Lahmacun ohne erfundene Zutaten  (ist: {w})")
    # Gegenprobe: Wo die Karte verweist, muss die Fuellung weiter dastehen.
    w = wegliste("Döner Saray", "tuerkisch")
    pruefe(all(x in w for x in ("Sucuk", "Weichkäse", "Fleisch", "Salat", "Blaukraut")),
           f"Döner Saray behält die Döner-Füllung  (ist: {w})")

    # --- 10. Keine Abkuerzungen auf den Knoepfen
    print("\nAbkürzungen")
    for name, kat in (("Vegetarischer Döner", "tuerkisch"), ("Pide Döner", "tuerkisch"),
                      ("Spinat Pide mit Ei", "tuerkisch"), ("Vegetarisch", "nudeln"),
                      ("Käse Lahmacun", "tuerkisch"), ("Mexikanischer Salat", "salate")):
        w = wegliste(name, kat)
        kurz = [z for z in w if z.endswith(".")]
        pruefe(not kurz, f"{name}: ausgeschrieben  (abgekürzt: {kurz})")

    # --- 11. Menue-Getraenke: erreichbar OHNE jedes Scrollen
    # Dreimal gemeldet, zweimal falsch repariert. Die Getraenke standen als
    # Block rund 630 Pixel tief im Bestellfenster, also unter dem Bildrand
    # jedes Telefons, und wurden nur durch Scrollen sichtbar. Jetzt ist es ein
    # eigenes, mittiges Fenster. Der Test legt deshalb JEDE Art von Scrollen
    # stumm - scrollIntoView, window.scrollTo und scrollTop: Was danach noch
    # antippbar ist, haengt von keinem Rollen mehr ab.
    print("\nMenü-Getränke ohne jedes Scrollen")
    for tag, bw, bh in (("Telefon klein", 375, 629), ("Telefon sehr klein", 320, 480)):
        ctx = b.new_context(viewport={"width": bw, "height": bh})
        s2 = ctx.new_page()
        s2.add_init_script("""
            Element.prototype.scrollIntoView = function(){};
            window.scrollTo = function(){};
            Object.defineProperty(Element.prototype, 'scrollTop',
              { get(){ return 0; }, set(v){}, configurable: true });
        """)
        s2.goto("http://127.0.0.1:8931/index.html", wait_until="networkidle")
        s2.wait_for_timeout(700)
        gerichte = s2.evaluate("""() => [...document.querySelectorAll('.item')]
            .map(e => [e._kategorie.id, e._gericht.name])""")
        schlecht = []
        geprueft = 0
        for kid, gn in gerichte:
            s2.evaluate("""([k,n]) => {
                document.querySelectorAll('.bf').forEach(x => x.remove());
                document.body.classList.remove('bf-offen');
                const li = [...document.querySelectorAll('.item')].find(e =>
                  e._gericht && e._gericht.name === n && e._kategorie.id === k);
                li.querySelector('.item__bestellen').click();
            }""", [kid, gn])
            s2.wait_for_selector(".bf", timeout=3000)
            art = s2.evaluate("""() => {
                if (document.querySelector('.bf__menue')) return 'schalter';
                const o = [...document.querySelectorAll('.bf__opt')]
                  .find(x => /men/i.test(x.textContent));
                return o ? 'groesse' : null;
            }""")
            if not art:
                continue
            geprueft += 1
            if art == "schalter":
                s2.evaluate("() => document.querySelector('.bf__menue').click()")
            else:
                s2.evaluate("""() => [...document.querySelectorAll('.bf__opt')]
                    .find(o => /men/i.test(o.textContent)).click()""")
            s2.wait_for_timeout(250)
            r = s2.evaluate("""() => {
                const f = document.querySelector('.bf--klein');
                if (!f) return {ok: 0, gesamt: 0, fehler: 'Getränkefenster fehlt'};
                const chips = [...f.querySelectorAll('.bf__chip')];
                const ok = chips.filter(c => {
                  const r = c.getBoundingClientRect();
                  const o = document.elementFromPoint(r.left+r.width/2, r.top+r.height/2);
                  return o && (o === c || c.contains(o));
                });
                return {ok: ok.length, gesamt: chips.length};
            }""")
            if r["gesamt"] == 0 or r["ok"] != r["gesamt"]:
                schlecht.append((gn, r.get("fehler") or f"{r['ok']}/{r['gesamt']}"))
            s2.keyboard.press("Escape")
            s2.wait_for_timeout(80)
        pruefe(geprueft >= 15,
               f"{tag}: {geprueft} Gerichte mit Menü gefunden (erwartet 15)")
        pruefe(not schlecht, f"{tag}: alle Getränke antippbar  (Problem: {schlecht[:4]})")
        s2.close(); ctx.close()

    # --- 12. Menue kommt nie ohne Getraenk in den Korb
    print("\nMenü ohne Getränk")
    oeffnen("Döner im Fladenbrot (Classic)", "tuerkisch")
    pg.evaluate("() => localStorage.removeItem('akpinar-korb')")
    pg.evaluate("() => document.querySelector('.bf__menue').click()")
    pg.wait_for_timeout(300)
    pruefe(pg.locator(".bf--klein").count() == 1,
           "Menü-Schalter öffnet sofort die Getränkewahl")
    # Abbrechen -> Menue bleibt aus
    pg.keyboard.press("Escape"); pg.wait_for_timeout(250)
    aus = pg.evaluate("""() => !document.querySelector('.bf__menue').classList.contains('ist-an')""")
    pruefe(aus, "Abbruch: Menü bleibt aus")
    # Getraenk waehlen -> Menue an, Getraenk am Knopf sichtbar
    pg.evaluate("() => document.querySelector('.bf__menue').click()")
    pg.wait_for_timeout(250)
    pg.evaluate("""() => [...document.querySelectorAll('.bf--klein .bf__chip')]
        .find(c => c.textContent.trim() === 'Cola Zero').click()""")
    pg.wait_for_timeout(300)
    r = pg.evaluate("""() => ({
        zu: !document.querySelector('.bf--klein'),
        an: document.querySelector('.bf__menue').classList.contains('ist-an'),
        text: document.querySelector('.bf__menuebesch').textContent
    })""")
    pruefe(r["zu"], "ein Tipp genügt: Fenster schließt sofort")
    pruefe(r["an"], "Menü ist an")
    pruefe("Cola Zero" in r["text"], f"Getränk steht am Menü-Knopf ({r['text']!r})")
    pg.click(".bf__rein"); pg.wait_for_timeout(500)
    korb = pg.evaluate("() => JSON.parse(localStorage.getItem('akpinar-korb')||'[]')")
    pruefe(korb and korb[-1].get("menue") == "Cola Zero",
           f"Getränk steht im Warenkorb ({korb[-1].get('menue') if korb else None})")

    # --- 13. Deutsche Sonderzeichen im Bestelltext
    # toUpperCase() machte im Deutschen aus "Sosse" ein "SOSSE" und aus der
    # Auswahl des Gastes, "Tomatensosse", ein "TOMATENSOSSE". Auch "Groesse"
    # war betroffen. Die Bezeichnungen sind jetzt fest und richtig
    # geschrieben, hervorgehoben wird mit den Sternchen von WhatsApp.
    print("\nSonderzeichen im Bestelltext")
    pg.evaluate("""() => localStorage.setItem('akpinar-korb', JSON.stringify([
      {name:'Döner-Box', nr:'', kategorie:'Türkisch', groesse:'Ø 32',
       wahl:['Beilage: Reis','Soße: Tomatensoße'], ohne:['Käse'],
       extras:['Gemüse'], sossen:['Knoblauchsoße'], menue:'Cola Zero',
       notiz:'süß-sauer', preis:7, anzahl:1}]))""")
    pg.reload(wait_until="networkidle"); pg.wait_for_timeout(800)
    pg.evaluate("() => { window.__auf=null; window.open = u => { window.__auf = u; }; }")
    pg.click("#korb-knopf"); pg.wait_for_timeout(600)
    pg.evaluate("""() => {
      const klick = t => { const b=[...document.querySelectorAll('button')]
        .find(x=>x.textContent.trim().toLowerCase().indexOf(t)===0); if(b) b.click(); };
      klick('abholung'); klick('bar bei abholung');
      document.querySelectorAll('input').forEach(i => {
        if (i.type==='tel') i.value='0170 1234567';
        else if (i.type==='text' && !i.value) i.value='Test';
        i.dispatchEvent(new Event('input',{bubbles:true}));
      });
    }""")
    pg.wait_for_timeout(400)
    pg.evaluate("() => document.querySelector('#kasse-senden').click()")
    pg.wait_for_timeout(300)
    url = pg.evaluate("() => window.__auf") or ""
    import urllib.parse
    bt = urllib.parse.unquote(url.split("text=", 1)[1]) if "text=" in url else ""
    pruefe(bool(bt), "Bestelltext wurde erzeugt")
    for falsch in ("MENUE", "SOSSE", "GROESSE", "TOMATENSOSSE", "Menue", "Groesse", "Sosse"):
        pruefe(falsch not in bt, f"'{falsch}' steht nicht im Bestelltext")
    for richtig in ("*Menü:*", "*Soße:*", "Tomatensoße", "Knoblauchsoße",
                    "Käse", "Gemüse", "süß-sauer", "Ø 32"):
        pruefe(richtig in bt, f"'{richtig}' steht richtig im Bestelltext")

    echt = [k for k in konsole if "pageerror" in k or k.startswith("error")]
    pruefe(not echt, f"keine JavaScript-Fehler  ({echt[:3]})")
    b.close()
srv.shutdown()
print("\n" + "="*60)
print("ALLES BESTANDEN" if not fehler else f"{len(fehler)} FEHLER")
sys.exit(1 if fehler else 0)
