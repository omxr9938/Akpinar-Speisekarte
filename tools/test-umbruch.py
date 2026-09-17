from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    pg=b.new_page(viewport={'width':360,'height':800})
    pg.goto('http://localhost:8765/', wait_until='networkidle')
    print('Breite | htmlScroll/client | Ueberlauf | Verursacher')
    for w in (320, 360, 375, 390, 414, 768, 1024, 1440):
        pg.set_viewport_size({'width':w,'height':800}); pg.wait_for_timeout(300)
        d=pg.evaluate("""() => {
          const h=document.documentElement, cw=h.clientWidth;
          const inScroll = e => { for(let n=e;n&&n!==h;n=n.parentElement){const s=getComputedStyle(n);
            if(['auto','scroll','hidden'].includes(s.overflowX)) return true;} return false; };
          const schuld=[...document.querySelectorAll('*')]
            .filter(e=>e.getBoundingClientRect().right>cw+1 && !inScroll(e))
            .slice(0,2).map(e=>e.tagName+'.'+String(e.className).split(' ')[0]);
          return {s:h.scrollWidth, c:cw, ov:h.scrollWidth>cw, schuld};
        }""")
        print(f"  {w:5} | {d['s']:5}/{d['c']:5} | {str(d['ov']):5} | {d['schuld'] or '-'}")
    b.close()
