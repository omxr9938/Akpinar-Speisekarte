from playwright.sync_api import sync_playwright

JS = """() => {
  const num = s => (s.match(/[-\\d.]+/g)||[]).map(Number);
  const rgba = s => { const n=num(s); return n.length>=4? n.slice(0,4) : [...n.slice(0,3),1]; };
  // Ebenen von der Wurzel abwaerts uebereinanderlegen (Alpha korrekt verrechnen)
  const bgOf = e => {
    const stapel=[];
    for(let n=e;n;n=n.parentElement){
      const cs=getComputedStyle(n);
      const c=rgba(cs.backgroundColor);
      if(c[3]>0) stapel.push(c);
      if(cs.backgroundImage && cs.backgroundImage!=='none') stapel.push([20,16,14,1]); // Verlauf grob
    }
    stapel.push([12,10,9,1]);           // Seitenhintergrund
    let out=stapel[stapel.length-1].slice(0,3);
    for(let i=stapel.length-2;i>=0;i--){
      const [r,g,b,a]=stapel[i];
      out=[r*a+out[0]*(1-a), g*a+out[1]*(1-a), b*a+out[2]*(1-a)];
    }
    return out;
  };
  const lum = c => { const [r,g,b]=c.map(v=>{v/=255; return v<=.03928? v/12.92 : Math.pow((v+.055)/1.055,2.4);});
    return .2126*r+.7152*g+.0722*b; };
  const seen={}, out=[];
  document.querySelectorAll('p,span,a,li,td,th,h1,h2,h3,h4,button,label').forEach(e=>{
    const t=(e.textContent||'').trim(); if(!t || e.children.length) return;
    const cs=getComputedStyle(e);
    if(cs.display==='none'||cs.visibility==='hidden'||parseFloat(cs.opacity)<.5) return;
    const fg=rgba(cs.color).slice(0,3), bg=bgOf(e);
    const l1=lum(fg), l2=lum(bg);
    const k=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);
    const px=parseFloat(cs.fontSize), fett=parseInt(cs.fontWeight)>=700;
    const noetig = (px>=24 || (px>=18.66&&fett)) ? 3 : 4.5;
    const key=cs.color+'|'+Math.round(px)+'|'+String(e.className).split(' ')[0];
    if(!seen[key]){ seen[key]={klasse:String(e.className).split(' ')[0]||e.tagName,
       px:Math.round(px), kontrast:Math.round(k*100)/100, noetig, text:t.slice(0,26)}; }
  });
  return Object.values(seen).filter(r=>r.kontrast<r.noetig).sort((a,b)=>a.kontrast-b.kontrast);
}"""

with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    pg=b.new_page(viewport={'width':390,'height':844})
    pg.goto('http://localhost:8765/', wait_until='networkidle'); pg.wait_for_timeout(700)
    res=pg.evaluate(JS)
    print(f'--- Kontraste unter WCAG AA: {len(res)} ---')
    for r in res: print(f"   {r['kontrast']:5} (noetig {r['noetig']})  {r['px']:3}px  {r['klasse']:20} \"{r['text']}\"")
    b.close()
