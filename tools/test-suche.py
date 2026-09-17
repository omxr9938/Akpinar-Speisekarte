from playwright.sync_api import sync_playwright

def sichtbar(pg, sel):
    """Zaehlt wirklich sichtbare Elemente - offsetParent statt hidden-Attribut."""
    return pg.evaluate("""s => [...document.querySelectorAll(s)]
        .filter(e => e.offsetParent !== null && e.getBoundingClientRect().height > 0).length""", sel)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    pg = b.new_page(viewport={'width': 420, 'height': 900})
    fehler = []
    pg.on('console', lambda m: fehler.append('Konsole: ' + m.text) if m.type == 'error' else None)
    pg.goto('http://localhost:8765/', wait_until='networkidle')
    pg.wait_for_timeout(700)

    gesamt = sichtbar(pg, '.item')
    print('ohne Suche sichtbar: %d Gerichte' % gesamt)

    for begriff, treffer_erwartet in [('doener', None), ('pizza', True), ('cola', True),
                                      ('salat', True), ('zzzz', False)]:
        pg.fill('#search', '')
        pg.click('#search')
        pg.keyboard.type(begriff, delay=25)
        pg.wait_for_timeout(350)
        n  = sichtbar(pg, '.item')
        ns = sichtbar(pg, '#kategorien .section')
        leer = pg.evaluate("() => { const e=document.querySelector('#no-results'); return !!e && getComputedStyle(e).display !== 'none'; }")
        passend = pg.evaluate("""q => [...document.querySelectorAll('.item')]
            .filter(e => e.offsetParent !== null)
            .every(e => (e.dataset.search || '').includes(q))""", begriff)
        print('  "%s": %d Gerichte in %d Abschnitten, Leermeldung %s, alle passend: %s'
              % (begriff, n, ns, leer, passend))
        if treffer_erwartet is True:
            if n == 0: fehler.append('"%s" liefert keine Treffer' % begriff)
            if n == gesamt: fehler.append('"%s" filtert nicht - alle %d bleiben sichtbar' % (begriff, gesamt))
            if not passend: fehler.append('"%s" zeigt auch unpassende Gerichte' % begriff)
            if leer: fehler.append('"%s" zeigt faelschlich die Leermeldung' % begriff)
        elif treffer_erwartet is False:
            if n != 0: fehler.append('"%s" sollte 0 Treffer haben, hat %d' % (begriff, n))
            if not leer: fehler.append('"%s" zeigt keine Leermeldung' % begriff)

    pg.click('#search-clear'); pg.wait_for_timeout(300)
    z = sichtbar(pg, '.item')
    print('nach Klick auf X: %d Gerichte' % z)
    if z != gesamt: fehler.append('X stellt nicht alle her: %d statt %d' % (z, gesamt))

    pg.click('#search'); pg.keyboard.type('pizza', delay=20); pg.wait_for_timeout(250)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    e = sichtbar(pg, '.item')
    print('nach Escape: %d Gerichte' % e)
    if e != gesamt: fehler.append('Escape stellt nicht alle her: %d statt %d' % (e, gesamt))

    b.close()
    print()
    if fehler:
        print('FEHLER:')
        for f in fehler: print('  -', f)
    else:
        print('alle Suchpruefungen bestanden')
