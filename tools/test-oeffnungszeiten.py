from playwright.sync_api import sync_playwright

# Offset je nach Sommer-/Winterzeit in Deutschland
faelle = [
    ('2026-07-15T10:59:00+02:00', 'Mi Sommer 10:59'),
    ('2026-07-15T11:00:00+02:00', 'Mi Sommer 11:00'),
    ('2026-07-15T21:59:00+02:00', 'Mi Sommer 21:59'),
    ('2026-07-15T22:00:00+02:00', 'Mi Sommer 22:00'),
    ('2026-01-14T10:59:00+01:00', 'Mi Winter 10:59'),
    ('2026-01-14T11:00:00+01:00', 'Mi Winter 11:00'),
    ('2026-01-14T20:59:00+01:00', 'Mi Winter 20:59'),
    ('2026-01-14T21:00:00+01:00', 'Mi Winter 21:00'),
    ('2026-01-14T21:30:00+01:00', 'Mi Winter 21:30'),
    ('2026-04-01T12:00:00+02:00', '1. April'),
    ('2026-03-31T12:00:00+02:00', '31. Maerz'),
    ('2026-10-31T12:00:00+01:00', '31. Oktober'),
    ('2026-11-01T12:00:00+01:00', '1. November'),
]

with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    for stamp, label in faelle:
        ctx=b.new_context(viewport={'width':390,'height':844}, timezone_id='Europe/Berlin')
        pg=ctx.new_page()
        pg.add_init_script(f"""
          const fest = new Date('{stamp}').getTime();
          const Echt = Date;
          Date = class extends Echt {{
            constructor(...a) {{ return a.length ? new Echt(...a) : new Echt(fest); }}
            static now() {{ return fest; }}
          }};
        """)
        pg.goto('http://localhost:8765/', wait_until='domcontentloaded'); pg.wait_for_timeout(500)
        r = pg.evaluate("""() => {
          const saisons=[...document.querySelectorAll('.season')].map(e=>({
            name:e.querySelector('.season__name')?.innerText, aktiv:e.getAttribute('data-active')}));
          return {status:(document.querySelector('#status-text')?.innerText||'').replace(/\\n/g,' '),
                  ortszeit:new Date().getHours()+':'+String(new Date().getMinutes()).padStart(2,'0'),
                  saisons};
        }""")
        akt = [s['name'] for s in r['saisons'] if s['aktiv']=='true']
        print(f"  {label:16} Uhr={r['ortszeit']:6} aktiv={akt}  | {r['status']}")
        ctx.close()
    b.close()
