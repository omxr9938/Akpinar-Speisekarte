/* ==========================================================================
   Akpinar Döner · Pizza — Online-Speisekarte
   Renders assets/data/menu.json into the page. No dependencies.
   ========================================================================== */

(function () {
  'use strict';

  var $  = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  /** Create an element with attributes and children. Text is never parsed as HTML. */
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        var v = attrs[k];
        if (v === null || v === undefined || v === false) return;
        if (k === 'class') node.className = v;
        else if (k === 'text') node.textContent = v;
        else if (k === 'html') node.innerHTML = v;
        else node.setAttribute(k, v === true ? '' : v);
      });
    }
    (children || []).forEach(function (c) {
      if (c === null || c === undefined || c === false) return;
      node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    });
    return node;
  }

  /* ---------------------------------------------------------- rendering -- */

  /** One price cell, with a small label on narrow screens. */
  function priceCell(value, label) {
    if (!value) {
      return el('span', { class: 'item__price item__price--empty' }, [
        label ? el('span', { class: 'item__price-label', text: label }) : null,
        '–'
      ]);
    }
    return el('span', { class: 'item__price' }, [
      label ? el('span', { class: 'item__price-label', text: label }) : null,
      value,
      el('span', { class: 'cur', text: '€' })
    ]);
  }

  function renderItem(item, kat) {
    var body = el('div', { class: 'item__body' }, [
      el('span', { class: 'item__name', text: item.name })
    ]);

    if (item.zusatz && item.zusatz.length) {
      /* numbers are printed as "1)2)3)", the star stays a bare "*" */
      var marks = item.zusatz.map(function (z) {
        return z === '*' ? '*' : z + ')';
      }).join('');
      body.firstChild.appendChild(el('sup', { class: 'item__zusatz', text: marks }));
    }
    if (item.beschreibung) {
      body.appendChild(el('span', { class: 'item__desc', text: item.beschreibung }));
    }

    var prices = el('div', { class: 'item__prices' },
      item.preise.map(function (p, i) {
        return priceCell(p, (kat.spaltenKurz && kat.spaltenKurz[i]) || '');
      })
    );

    // Drei Schreibweisen nebeneinander ablegen, damit die Suche mit und ohne
    // Umlaut findet: "Döner" ist auch über "doener" und "doner" erreichbar.
    // Auf dem Handy tippt kaum jemand Umlaute, und "doner" ist hier der mit
    // Abstand häufigste Suchbegriff.
    var roh = [item.nr, item.name, item.beschreibung, kat.name]
      .filter(Boolean).join(' ').toLowerCase();
    var searchText = [roh, umlauteLang(roh), umlauteWeg(roh)].join(' ');

    return el('li', { class: 'item', 'data-search': searchText }, [
      item.nr ? el('span', { class: 'item__nr', text: item.nr }) : el('span', { class: 'item__nr' }),
      body,
      prices
    ]);
  }

  function renderCategory(kat) {
    var multi = kat.spalten.filter(Boolean).length > 1;

    var head = el('h2', { class: 'section__title', id: 'titel-' + kat.id }, [
      kat.bild ? el('img', {
        class: 'thumb', src: kat.bild, alt: '', loading: 'lazy', width: 58, height: 58
      }) : null,
      kat.name
    ]);

    var headWrap = el('div', { class: 'section__head' }, [
      head,
      kat.hinweis ? el('p', { class: 'section__note', text: kat.hinweis }) : null
    ]);

    /* column header row (wide screens, multi-price categories only) */
    var colHead = null;
    if (multi) {
      colHead = el('div', { class: 'menu-head' }, [el('span', { class: 'menu-head__spacer' })]
        .concat(kat.spalten.map(function (c) { return el('span', { text: c }); })));
    }

    var list = el('ul', { class: 'items', 'data-kat': kat.id },
      kat.items.map(function (i) { return renderItem(i, kat); }));

    var extra = [];

    if (kat.banner) {
      extra.push(el('p', { class: 'banner' }, [
        el('span', { html: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2 15 9l7 .6-5.3 4.6L18.3 21 12 17.3 5.7 21l1.6-6.8L2 9.6 9 9z"/></svg>' }),
        kat.banner
      ]));
    }

    if (kat.extras) {
      var ex = el('div', { class: 'extras' }, [
        el('p', { class: 'extras__title', text: kat.extras.titel })
      ]);
      kat.extras.zeilen.forEach(function (z) {
        ex.appendChild(el('div', { class: 'extras__row' }, [
          el('span', { text: z.name }),
          el('span', { class: 'item__prices' }, z.preise.map(function (p, i) {
            return priceCell(p, (kat.spaltenKurz && kat.spaltenKurz[i]) || '');
          }))
        ]));
      });
      if (kat.extras.fussnoten && kat.extras.fussnoten.length) {
        ex.appendChild(el('p', { class: 'extras__foot' },
          kat.extras.fussnoten.map(function (f) { return el('span', { text: f }); })));
      }
      extra.push(ex);
    }

    return el('section', {
      class: 'section' + (multi ? '' : ' section--single'),
      id: kat.id,
      'aria-labelledby': 'titel-' + kat.id
    }, [
      el('div', { class: 'wrap' }, [headWrap, colHead, list].concat(extra))
    ]);
  }

  /* ------------------------------------------------------------ offers -- */

  function renderOffers(a) {
    var box = $('#offers');
    box.appendChild(el('div', { class: 'offers__head' }, [
      el('h2', { class: 'offers__title', id: 'angebote-titel', text: a.titel }),
      el('p', { class: 'offers__sub', text: a.gueltigkeit }),
      a.zusatz ? el('p', { class: 'offers__extra', text: a.zusatz }) : null
    ]));

    var grid = el('div', { class: 'offers__grid' });
    a.gruppen.forEach(function (g) {
      grid.appendChild(el('div', { class: 'offer' }, [
        el('h3', { class: 'offer__title', text: g.titel }),
        g.hinweis ? el('p', { class: 'offer__note', text: '[ ' + g.hinweis + ' ]' }) : null,
        el('div', { class: 'offer__cards' }, g.karten.map(function (k) {
          return el('div', { class: 'card' + (k.breit ? ' card--wide' : '') }, [
            el('div', { class: 'card__title', text: k.titel }),
            k.sub ? el('div', { class: 'card__sub', text: k.sub }) : null,
            k.preis ? el('div', { class: 'card__price', text: k.preis }) : null
          ]);
        }))
      ]));
    });
    box.appendChild(grid);
  }

  /* -------------------------------------------------- delivery & hours -- */

  function renderDelivery(l) {
    var p = $('#lieferung');
    p.appendChild(el('h3', { class: 'panel__title', text: l.titel }));
    p.appendChild(el('p', { class: 'panel__claim', text: l.claim }));
    p.appendChild(el('div', { class: 'zone-head', text: l.spalte }));
    l.zonen.forEach(function (z) {
      p.appendChild(el('div', { class: 'zone' }, [
        el('span', { class: 'zone__nr', text: z.zone }),
        el('span', { class: 'zone__orte', text: z.orte }),
        el('span', { class: 'zone__min', text: z.mindestbestellung })
      ]));
    });
  }

  /** April–October counts as summer, per oeffnungszeiten.sommerVon/-Bis. */
  function currentSeasonIndex(o, now) {
    var m = now.getMonth() + 1;
    var isSummer = m >= (o.sommerVon || 4) && m <= (o.sommerBis || 10);
    return isSummer ? 0 : 1;
  }

  function renderHours(o) {
    var p = $('#oeffnungszeiten');
    var active = currentSeasonIndex(o, new Date());

    p.appendChild(el('h3', { class: 'panel__title', text: 'Öffnungszeiten' }));
    p.appendChild(el('p', { class: 'panel__claim', text: 'für Imbiss & Heimservice' }));

    var grid = el('div', { class: 'hours' });
    o.saisons.forEach(function (s, idx) {
      // Bewusst die Zeichenkette 'true' statt eines Booleans: el() macht aus
      // true ein leeres Attribut (data-active=""), das CSS greift aber auf
      // [data-active="true"] zu — die Hervorhebung blieb dadurch unsichtbar.
      grid.appendChild(el('div', { class: 'season', 'data-active': idx === active ? 'true' : null }, [
        el('p', { class: 'season__name', text: s.name + (idx === active ? ' · aktuell' : '') })
      ].concat(s.zeiten.map(function (z) {
        return el('div', { class: 'season__row' }, [
          el('span', { text: z.tage }), el('span', { text: z.zeit })
        ]);
      }))));
    });
    p.appendChild(grid);

    if (o.saisonHinweis) {
      p.appendChild(el('p', { class: 'extras__foot', text: o.saisonHinweis }));
    }
  }

  /** "Jetzt geöffnet" badge, derived from the active season's hours. */
  function renderStatus(o) {
    var now = new Date();
    var season = o.saisons[currentSeasonIndex(o, now)];
    var isSunday = now.getDay() === 0;
    var row = season.zeiten[isSunday ? 1 : 0];

    var m = row.zeit.match(/(\d{1,2})[.:](\d{2})\s*[–-]\s*(\d{1,2})[.:](\d{2})/);
    if (!m) return;

    var mins  = now.getHours() * 60 + now.getMinutes();
    var open  = (+m[1]) * 60 + (+m[2]);
    var close = (+m[3]) * 60 + (+m[4]);
    var isOpen = mins >= open && mins < close;

    var box = $('#status');
    box.hidden = false;
    box.classList.add(isOpen ? 'is-open' : 'is-closed');

    var text = $('#status-text');
    text.appendChild(el('b', { text: isOpen ? 'Jetzt geöffnet' : 'Gerade geschlossen' }));
    text.appendChild(document.createTextNode(
      isOpen ? ' · bis ' + m[3] + '.' + m[4] + ' Uhr'
             : ' · öffnet um ' + m[1] + '.' + m[2] + ' Uhr'
    ));
  }

  function renderStamp(s) {
    var box = $('#stempelkarte');
    box.appendChild(el('p', { class: 'stamp__title', text: s.titel }));
    box.appendChild(el('p', { class: 'stamp__text', text: s.text }));
    var dots = el('div', { class: 'stamp__dots', 'aria-hidden': 'true' });
    for (var i = 0; i < 10; i++) dots.appendChild(el('i'));
    box.appendChild(dots);
    box.appendChild(el('p', { class: 'stamp__note', text: s.hinweis }));
  }

  /* --------------------------------------------------------- allergens -- */

  function renderAllergens(a, z) {
    var box = $('#allergen-block');

    var cols = [];
    a.gruppen.forEach(function (g) {
      g.spalten.forEach(function (s) { cols.push({ grp: g.name, name: s }); });
    });

    var table = el('table', { class: 'allergens' });

    /* Groups with a single allergen span both header rows; groups with several
       get a name row on top and one vertical sub-column each below. */
    var r1 = el('tr', {}, [el('th', { class: 'grp', rowspan: 2, text: 'Speisen' })]);
    var r2 = el('tr');

    a.gruppen.forEach(function (g) {
      if (g.spalten.length === 1) {
        r1.appendChild(el('th', { class: 'grp', rowspan: 2, text: g.name }));
        return;
      }
      r1.appendChild(el('th', { class: 'grp', colspan: g.spalten.length, text: g.name }));
      g.spalten.forEach(function (s) {
        r2.appendChild(el('th', { class: 'vert', text: s }));
      });
    });

    table.appendChild(el('thead', {}, [r1, r2]));

    var tbody = el('tbody');
    a.zeilen.forEach(function (row) {
      var tr = el('tr', {}, [el('th', { scope: 'row', text: row.speise })]);
      cols.forEach(function (c) {
        var yes = row.enthaelt.indexOf(c.name) !== -1;
        tr.appendChild(el('td', {
          class: yes ? 'yes' : '',
          text: yes ? '×' : '',
          'aria-label': yes ? row.speise + ' enthält ' + c.name : ''
        }));
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    box.appendChild(el('details', { class: 'acc' }, [
      el('summary', { text: a.titel }),
      el('div', { class: 'acc__body' }, [
        el('p', { class: 'acc__note', text: a.hinweis }),
        el('p', { class: 'scroll-hint', text: 'Tabelle seitlich scrollen →' }),
        el('div', { class: 'table-scroll' }, [table])
      ])
    ]));

    var legende = el('div', { class: 'legend' }, [
      el('b', { text: z.titel + ': ' }),
      z.hinweis
    ]);

    if (z.marker && z.marker.length) {
      legende.appendChild(el('ul', { class: 'legend__list' },
        z.marker.map(function (m) {
          return el('li', {}, [
            el('b', { text: m.nr + ') ' }),
            m.text
          ]);
        })
      ));
    }

    // Zwei verschiedene Sternchen in der Karte: an den Gerichten meint es den
    // Schinken, im Extras-Block den Familienpizza-Preis. Beide getrennt nennen,
    // sonst bezieht ein Gast die Preisangabe auf die Fleischzusammensetzung.
    if (z.sternSpeisen) {
      legende.appendChild(el('p', { class: 'legend__stern', text: z.sternSpeisen }));
    }

    box.appendChild(legende);
  }

  /* ------------------------------------------------------------- chips -- */

  function renderChips(kategorien) {
    var box = $('#chips');
    kategorien.forEach(function (k) {
      box.appendChild(el('a', {
        class: 'chip',
        href: '#' + k.id,
        'data-target': k.id,
        text: k.kurz || k.name
      }));
    });

    /* highlight the section currently in view */
    if (!('IntersectionObserver' in window)) return;

    var chips = $$('.chip', box);
    var visible = {};

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { visible[e.target.id] = e.isIntersecting; });

      var active = kategorien.map(function (k) { return k.id; })
        .filter(function (id) { return visible[id]; })[0];

      chips.forEach(function (c) {
        var on = c.dataset.target === active;
        if (on) c.setAttribute('aria-current', 'true');
        else c.removeAttribute('aria-current');
        if (on) scrollChipIntoView(box, c);
      });
    }, { rootMargin: '-78px 0px -70% 0px', threshold: 0 });

    kategorien.forEach(function (k) {
      var s = document.getElementById(k.id);
      if (s) io.observe(s);
    });
  }

  function scrollChipIntoView(box, chip) {
    var l = chip.offsetLeft, r = l + chip.offsetWidth;
    if (l < box.scrollLeft || r > box.scrollLeft + box.clientWidth) {
      box.scrollTo({ left: l - 16, behavior: 'smooth' });
    }
  }

  /* -------------------------------------------------- Umlaut-Behandlung -- */

  /** ä -> ae, ö -> oe, ü -> ue, ß -> ss (deutsche Umschreibung). */
  function umlauteLang(s) {
    return s.replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue')
            .replace(/ß/g, 'ss');
  }

  /** ä -> a, ö -> o, ü -> u, ß -> s (Pünktchen einfach weg). */
  function umlauteWeg(s) {
    return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ß/g, 's');
  }

  /* ------------------------------------------------------------ search -- */

  function initSearch() {
    var input = $('#search');
    var wrap  = $('#search-wrap');
    var clear = $('#search-clear');
    var empty = $('#no-results');
    var term  = $('#no-results-term');
    var items = $$('.item');
    var sections = $$('#kategorien .section');

    var suchteVorher = false;
    var scrollVorSuche = 0;

    function apply() {
      var q = input.value.trim().toLowerCase();
      wrap.classList.toggle('has-value', q.length > 0);
      document.body.classList.toggle('is-searching', q.length > 0);

      // Beim Beginn einer Suche einmal zu den Treffern springen. Ohne das steht
      // der Kopfbereich über dem ersten Ergebnis und man müsste scrollen.
      // Bewusst nur beim Übergang von "leer" zu "etwas eingegeben" — bei jedem
      // Tastendruck zu springen wäre unruhig, besonders mit offener Tastatur.
      var suchtJetzt = q.length > 0;
      if (suchtJetzt && !suchteVorher) {
        scrollVorSuche = window.scrollY;
        zuTreffernSpringen();
      } else if (!suchtJetzt && suchteVorher) {
        // Zurück an die Stelle, an der die Suche begonnen wurde: Beim Leeren
        // tauchen Angebote und Service wieder auf und schieben den Inhalt nach
        // unten — ohne das säße man unvermittelt woanders.
        window.scrollTo({ top: scrollVorSuche, behavior: 'smooth' });
      }
      suchteVorher = suchtJetzt;

      if (!q) {
        items.forEach(function (i) { i.hidden = false; });
        sections.forEach(function (s) { s.hidden = false; });
        empty.classList.remove('show');
        return;
      }

      var hits = 0;
      sections.forEach(function (s) {
        var n = 0;
        $$('.item', s).forEach(function (i) {
          var feld = i.dataset.search;
          var match = feld.indexOf(q) !== -1
                   || feld.indexOf(umlauteLang(q)) !== -1
                   || feld.indexOf(umlauteWeg(q)) !== -1;
          i.hidden = !match;
          if (match) n++;
        });
        s.hidden = n === 0;
        hits += n;
      });

      term.textContent = '„' + input.value.trim() + '“';
      empty.classList.toggle('show', hits === 0);
    }

    /** Scrollt so, dass die Trefferliste direkt unter der Suchleiste beginnt. */
    function zuTreffernSpringen() {
      var ziel = document.getElementById('kategorien');
      if (!ziel) return;
      var leiste = document.querySelector('.toolbar');
      var hoehe = leiste ? leiste.getBoundingClientRect().height : 0;
      var y = window.scrollY + ziel.getBoundingClientRect().top - hoehe - 8;
      if (y > window.scrollY) window.scrollTo({ top: y, behavior: 'smooth' });
    }

    input.addEventListener('input', apply);
    input.addEventListener('search', apply);
    clear.addEventListener('click', function () {
      input.value = '';
      apply();
      input.focus();
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { input.value = ''; apply(); }
    });
  }

  /* ------------------------------------------------------------ to top -- */

  function initToTop() {
    var btn = $('#to-top');
    var toggle = function () { btn.classList.toggle('show', window.scrollY > 700); };
    window.addEventListener('scroll', toggle, { passive: true });
    btn.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    toggle();
  }

  /* --------------------------------------------------------------- run -- */

  function boot(data) {
    $('#stand').textContent = data.betrieb.stand;

    renderOffers(data.angebote);

    var host = $('#kategorien');
    data.kategorien.forEach(function (k) { host.appendChild(renderCategory(k)); });

    renderDelivery(data.lieferung);
    renderHours(data.oeffnungszeiten);
    renderStatus(data.oeffnungszeiten);
    renderStamp(data.stempelkarte);
    renderAllergens(data.allergene, data.zusatzstoffe);

    renderChips(data.kategorien);
    initSearch();
    initToTop();

    /* jump to the hash target once everything exists */
    if (location.hash) {
      var t = document.getElementById(location.hash.slice(1));
      if (t) t.scrollIntoView();
    }
  }

  fetch('assets/data/menu.json?v=23f34ef8')
    .then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(boot)
    .catch(function (err) {
      console.error('Speisekarte konnte nicht geladen werden:', err);
      $('#kategorien').appendChild(el('div', { class: 'wrap' }, [
        el('p', { class: 'no-results show', style: 'display:block' }, [
          'Die Speisekarte konnte nicht geladen werden. Bitte laden Sie die Seite neu oder rufen Sie uns an: ',
          el('a', { href: 'tel:+4986719580145', text: '08671-9580145' })
        ])
      ]));
    });
})();
