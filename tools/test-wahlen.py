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
    pruefe("BEILAGE: REIS" in (txt or ""), f"Beilage steht im WhatsApp-Text")
    if "BEILAGE" not in (txt or ""):
        print("      Text:", (txt or "")[:400])

    echt = [k for k in konsole if "pageerror" in k or k.startswith("error")]
    pruefe(not echt, f"keine JavaScript-Fehler  ({echt[:3]})")
    b.close()
srv.shutdown()
print("\n" + "="*60)
print("ALLES BESTANDEN" if not fehler else f"{len(fehler)} FEHLER")
sys.exit(1 if fehler else 0)
