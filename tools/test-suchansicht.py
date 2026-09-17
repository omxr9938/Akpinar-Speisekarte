from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    pg=b.new_page(viewport={'width':390,'height':844})
    pg.goto('http://localhost:8765/', wait_until='networkidle'); pg.wait_for_timeout(700)
    fehler=[]

    def zustand():
        return pg.evaluate("""() => {
          const sicht = s => { const e=document.querySelector(s);
            return !!e && e.offsetParent !== null; };
          const ersterTreffer = [...document.querySelectorAll('.item')]
            .find(e => e.offsetParent !== null);
          const tb = document.querySelector('.toolbar')?.getBoundingClientRect().bottom ?? 0;
          return {angebote:sicht('#angebote'), service:sicht('#service'),
                  allergene:sicht('#allergene'),
                  trefferY: ersterTreffer ? Math.round(ersterTreffer.getBoundingClientRect().top) : null,
                  toolbarUnten: Math.round(tb)};
        }""")

    print('ohne Suche :', zustand())
    pg.click('#search'); pg.keyboard.type('thunfi', delay=25); pg.wait_for_timeout(400)
    z = zustand()
    print('bei Suche  :', z)
    if z['angebote']: fehler.append('Angebote bleiben waehrend der Suche sichtbar')
    if z['service']: fehler.append('Service-Block bleibt sichtbar')
    if z['allergene']: fehler.append('Allergen-Block bleibt sichtbar')
    if z['trefferY'] is None: fehler.append('kein Treffer sichtbar')
    elif z['trefferY'] > 400: fehler.append(f"erster Treffer erst bei y={z['trefferY']} — zu weit unten")

    pg.click('#search-clear'); pg.wait_for_timeout(400)
    z2 = zustand()
    print('nach X     :', z2)
    for k in ('angebote','service','allergene'):
        if not z2[k]: fehler.append(f'{k} kommt nach dem Zuruecksetzen nicht zurueck')

    # Leersuche: no-results muss sichtbar sein, Bloecke weiterhin aus
    pg.click('#search'); pg.keyboard.type('zzzz', delay=20); pg.wait_for_timeout(350)
    leer = pg.evaluate("() => { const e=document.querySelector('#no-results'); return !!e && e.offsetParent!==null; }")
    print('Leermeldung bei "zzzz":', leer)
    if not leer: fehler.append('Leermeldung fehlt')

    b.close()
    print()
    print('FEHLER:' if fehler else 'alles in Ordnung')
    for f in fehler: print('  -', f)
