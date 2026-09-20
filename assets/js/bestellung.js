/* Bestellvorgang für Akpinar Döner & Pizza.
   Baut auf app.js auf: Sobald die Karte gerendert ist, bekommt jedes Gericht
   einen Bestellknopf. Ausgewählt wird in einem Fenster (Größe, Zutaten weg,
   Extras dazu), gesammelt wird im Warenkorb, abgeschickt wird per WhatsApp.

   Bewusst ohne Server: Eine reine HTML-Seite kann kein Geld annehmen und
   keine Mail verschicken. Die fertige Bestellung wird als Text in WhatsApp
   geöffnet, der Gast drückt auf Senden. Das kostet nichts, braucht keine
   Wartung und funktioniert ab dem ersten Tag. */
(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var daten, konfig;
  var korb = [];

  /* ------------------------------------------------------------ Hilfen -- */

  function euro(zahl) {
    return zahl.toFixed(2).replace('.', ',') + ' €';
  }

  function zuZahl(preis) {
    if (preis === null || preis === undefined || preis === '' || preis === '-') return null;
    return parseFloat(String(preis).replace(',', '.'));
  }

  function el(tag, attrs, kinder) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'class') n.className = v;
      else if (k === 'text') n.textContent = v;
      else if (k.slice(0, 2) === 'on') n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v === true ? '' : v);
    });
    (kinder || []).forEach(function (c) {
      if (c === null || c === undefined || c === false) return;
      n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    });
    return n;
  }

  /** Zutaten aus der Beschreibung lesen: "Salami und Peperoni" -> zwei Zutaten.
      Die Beschreibung ist die einzige Quelle dafür, was auf dem Gericht liegt. */
  function zutatenAus(beschreibung) {
    if (!beschreibung) return [];
    return beschreibung
      .replace(/\s+u\.\s+/g, ', ')
      .replace(/\s+und\s+/g, ', ')
      .split(',')
      .map(function (z) { return z.trim().replace(/^mit\s+/i, ''); })
      .filter(function (z) {
        // Sätze und Hinweise sind keine Zutaten
        return z && z.length < 34 && !/^(Nr\.|Inhalt|inkl\.)/i.test(z);
      });
  }

  /* -------------------------------------------------------- Warenkorb -- */

  function korbSpeichern() {
    try { localStorage.setItem('akpinar-korb', JSON.stringify(korb)); } catch (e) { /* egal */ }
  }

  function korbLaden() {
    try {
      var roh = localStorage.getItem('akpinar-korb');
      if (roh) korb = JSON.parse(roh) || [];
    } catch (e) { korb = []; }
  }

  function summe() {
    return korb.reduce(function (s, p) { return s + p.preis * p.anzahl; }, 0);
  }

  function anzahlGesamt() {
    return korb.reduce(function (s, p) { return s + p.anzahl; }, 0);
  }

  /* ------------------------------------------------- Auswahl-Fenster -- */

  function fensterOeffnen(gericht, kategorie) {
    var groessen = (kategorie.spalten || ['']).map(function (sp, i) {
      return { label: (kategorie.spaltenKurz && kategorie.spaltenKurz[i]) || sp || '',
               preis: zuZahl(gericht.preise[i]), index: i };
    }).filter(function (g) { return g.preis !== null; });

    if (!groessen.length) return;

    var zutatenKonf = (konfig.zutaten || {})[kategorie.id] || {};
    var basis = zutatenKonf.basis || [];
    var ausBeschreibung = zutatenAus(gericht.beschreibung);
    var abwaehlbar = basis.concat(ausBeschreibung).filter(function (z, i, a) {
      return a.indexOf(z) === i;
    });

    var stand = {
      groesse: groessen[0],
      weg: {},          // abgewählte Zutaten
      extras: [],       // gewählte Extras
      soße: zutatenKonf.sossen ? zutatenKonf.sossen.standard : null,
      anzahl: 1
    };

    var preisZeile = el('strong', { class: 'bf__preis' });

    function preisJetzt() {
      var p = stand.groesse.preis;
      stand.extras.forEach(function (e) { p += e.preis; });
      return p * stand.anzahl;
    }
    function preisAktualisieren() { preisZeile.textContent = euro(preisJetzt()); }

    var inhalt = el('div', { class: 'bf__body' });

    // --- Größe
    if (groessen.length > 1) {
      var gWahl = el('div', { class: 'bf__wahl' });
      groessen.forEach(function (g) {
        var b = el('button', {
          class: 'bf__opt' + (g === stand.groesse ? ' ist-an' : ''),
          type: 'button',
          onclick: function () {
            stand.groesse = g;
            stand.extras = [];   // Extras sind größenabhängig
            Array.prototype.forEach.call(gWahl.children, function (c) {
              c.classList.remove('ist-an');
            });
            b.classList.add('ist-an');
            extrasNeu();
            preisAktualisieren();
          }
        }, [el('span', { class: 'bf__optname', text: g.label.replace('\n', ' ') }),
            el('span', { class: 'bf__optpreis', text: euro(g.preis) })]);
        gWahl.appendChild(b);
      });
      inhalt.appendChild(el('p', { class: 'bf__titel', text: 'Größe' }));
      inhalt.appendChild(gWahl);
    }

    // --- Soße
    if (zutatenKonf.sossen) {
      var sWahl = el('div', { class: 'bf__wahl bf__wahl--schmal' });
      zutatenKonf.sossen.optionen.forEach(function (o) {
        var b = el('button', {
          class: 'bf__opt' + (o === stand.soße ? ' ist-an' : ''),
          type: 'button',
          onclick: function () {
            stand.soße = o;
            Array.prototype.forEach.call(sWahl.children, function (c) {
              c.classList.remove('ist-an');
            });
            b.classList.add('ist-an');
          }
        }, [el('span', { class: 'bf__optname', text: o })]);
        sWahl.appendChild(b);
      });
      inhalt.appendChild(el('p', { class: 'bf__titel', text: zutatenKonf.sossen.frage }));
      inhalt.appendChild(sWahl);
    }

    // --- Zutaten abwählen
    if (abwaehlbar.length) {
      inhalt.appendChild(el('p', { class: 'bf__titel', text: 'Zutaten weglassen' }));
      inhalt.appendChild(el('p', { class: 'bf__klein',
        text: 'Tippen Sie an, was nicht drauf soll — kostenlos.' }));
      var zListe = el('div', { class: 'bf__chips' });
      abwaehlbar.forEach(function (z) {
        var b = el('button', { class: 'bf__chip', type: 'button' }, [document.createTextNode(z)]);
        b.addEventListener('click', function () {
          if (stand.weg[z]) { delete stand.weg[z]; b.classList.remove('ist-weg'); }
          else { stand.weg[z] = true; b.classList.add('ist-weg'); }
        });
        zListe.appendChild(b);
      });
      inhalt.appendChild(zListe);
    }

    // --- Extras
    var extrasBox = el('div');
    inhalt.appendChild(extrasBox);

    function extrasNeu() {
      extrasBox.innerHTML = '';
      var moeglich = [];

      if (kategorie.extras && kategorie.extras.zeilen) {
        kategorie.extras.zeilen.forEach(function (z) {
          var p = zuZahl(z.preise[stand.groesse.index]);
          if (p !== null) moeglich.push({ name: z.name, preis: p, gruppe: true });
        });
      }
      (zutatenKonf.extras || []).forEach(function (e) {
        var p = zuZahl(e.preis);
        if (p !== null) moeglich.push({ name: e.name, preis: p });
      });

      if (!moeglich.length) return;

      extrasBox.appendChild(el('p', { class: 'bf__titel', text: 'Extras dazu' }));
      var liste = el('div', { class: 'bf__chips' });
      moeglich.forEach(function (e) {
        var b = el('button', { class: 'bf__chip bf__chip--extra', type: 'button' },
          [document.createTextNode(e.name + '  +' + euro(e.preis))]);
        b.addEventListener('click', function () {
          var i = stand.extras.indexOf(e);
          if (i >= 0) { stand.extras.splice(i, 1); b.classList.remove('ist-an'); }
          else { stand.extras.push(e); b.classList.add('ist-an'); }
          preisAktualisieren();
        });
        liste.appendChild(b);
      });
      extrasBox.appendChild(liste);
    }
    extrasNeu();

    // --- Anzahl
    var anzeige = el('span', { class: 'bf__anzahl', text: '1' });
    var anzahlBox = el('div', { class: 'bf__menge' }, [
      el('button', { class: 'bf__rund', type: 'button', 'aria-label': 'weniger',
        onclick: function () {
          if (stand.anzahl > 1) { stand.anzahl--; anzeige.textContent = stand.anzahl; preisAktualisieren(); }
        } }, ['−']),
      anzeige,
      el('button', { class: 'bf__rund', type: 'button', 'aria-label': 'mehr',
        onclick: function () {
          stand.anzahl++; anzeige.textContent = stand.anzahl; preisAktualisieren();
        } }, ['+'])
    ]);

    preisAktualisieren();

    var fenster = el('div', { class: 'bf', role: 'dialog', 'aria-modal': 'true',
                              'aria-label': gericht.name }, [
      el('div', { class: 'bf__karte' }, [
        el('div', { class: 'bf__kopf' }, [
          el('h2', { class: 'bf__name',
            text: (gericht.nr ? gericht.nr + '  ' : '') + gericht.name }),
          el('button', { class: 'bf__zu', type: 'button', 'aria-label': 'Schließen',
                         onclick: schliessen }, ['×'])
        ]),
        gericht.beschreibung ? el('p', { class: 'bf__besch', text: gericht.beschreibung }) : null,
        inhalt,
        el('div', { class: 'bf__fuss' }, [
          anzahlBox,
          el('button', { class: 'bf__rein', type: 'button', onclick: function () {
            hinzufuegen(gericht, kategorie, stand, preisJetzt() / stand.anzahl);
            schliessen();
          } }, [document.createTextNode('In den Warenkorb  '), preisZeile])
        ])
      ])
    ]);

    function schliessen() {
      document.removeEventListener('keydown', beiTaste);
      fenster.remove();
      document.body.classList.remove('bf-offen');
    }
    function beiTaste(e) { if (e.key === 'Escape') schliessen(); }

    fenster.addEventListener('click', function (e) { if (e.target === fenster) schliessen(); });
    document.addEventListener('keydown', beiTaste);
    document.body.appendChild(fenster);
    document.body.classList.add('bf-offen');
    $('.bf__zu', fenster).focus();
  }

  function hinzufuegen(gericht, kategorie, stand, einzelpreis) {
    var weg = Object.keys(stand.weg);
    korb.push({
      name: gericht.name,
      nr: gericht.nr || '',
      kategorie: kategorie.name,
      groesse: stand.groesse.label.replace('\n', ' '),
      ohne: weg,
      extras: stand.extras.map(function (e) { return e.name; }),
      soße: stand.soße,
      preis: einzelpreis,
      anzahl: stand.anzahl
    });
    korbSpeichern();
    korbZeichnen();
    korbOeffnen();
  }

  /* ---------------------------------------------------- Korb-Anzeige -- */

  function korbZeichnen() {
    var knopf = $('#korb-knopf');
    if (knopf) {
      knopf.hidden = korb.length === 0;
      $('#korb-anzahl', knopf).textContent = anzahlGesamt();
      $('#korb-summe', knopf).textContent = euro(summe());
    }
    var liste = $('#korb-liste');
    if (!liste) return;
    liste.innerHTML = '';
    if (!korb.length) {
      liste.appendChild(el('p', { class: 'korb__leer',
        text: 'Ihr Warenkorb ist noch leer.' }));
    }
    korb.forEach(function (p, i) {
      var zusatz = [];
      if (p.groesse) zusatz.push(p.groesse);
      if (p.soße) zusatz.push('Soße: ' + p.soße);
      if (p.ohne.length) zusatz.push('ohne ' + p.ohne.join(', '));
      if (p.extras.length) zusatz.push('mit ' + p.extras.join(', '));
      liste.appendChild(el('div', { class: 'korb__zeile' }, [
        el('span', { class: 'korb__anz', text: p.anzahl + '×' }),
        el('span', {}, [
          el('span', { class: 'korb__name', text: (p.nr ? p.nr + ' ' : '') + p.name }),
          zusatz.length ? el('span', { class: 'korb__zusatz', text: zusatz.join(' · ') }) : null
        ]),
        el('span', { class: 'korb__preis', text: euro(p.preis * p.anzahl) }),
        el('button', { class: 'korb__weg', type: 'button', 'aria-label': 'entfernen',
          onclick: function () { korb.splice(i, 1); korbSpeichern(); korbZeichnen(); } }, ['×'])
      ]));
    });
    kasseAktualisieren();
  }

  window.AKPINAR = window.AKPINAR || {};
  window.AKPINAR.korbZeichnen = korbZeichnen;
  window.AKPINAR.korb = function () { return korb; };
  window.AKPINAR.summe = summe;
  window.AKPINAR.euro = euro;
  window.AKPINAR.el = el;
  window.AKPINAR.korbLeeren = function () { korb = []; korbSpeichern(); korbZeichnen(); };

  function korbOeffnen() {
    var s = $('#korb');
    if (s) { s.classList.add('ist-offen'); document.body.classList.add('korb-offen'); }
  }
  function korbSchliessen() {
    var s = $('#korb');
    if (s) { s.classList.remove('ist-offen'); document.body.classList.remove('korb-offen'); }
  }
  window.AKPINAR.korbOeffnen = korbOeffnen;
  window.AKPINAR.korbSchliessen = korbSchliessen;

  function kasseAktualisieren() {
    if (window.AKPINAR.kasseAktualisieren) window.AKPINAR.kasseAktualisieren();
  }

  /* ------------------------------------------------------- Einhängen -- */

  function knoepfeAnbauen() {
    document.querySelectorAll('.item').forEach(function (li) {
      if (li._bestellbar || !li._gericht) return;
      var g = li._gericht, k = li._kategorie;
      var hatPreis = (g.preise || []).some(function (p) { return zuZahl(p) !== null; });
      if (!hatPreis) return;
      li._bestellbar = true;
      li.appendChild(el('button', {
        class: 'item__bestellen', type: 'button',
        'aria-label': g.name + ' bestellen',
        onclick: function () { fensterOeffnen(g, k); }
      }, ['+']));
    });
  }

  document.addEventListener('karte-fertig', function () {
    daten = window.AKPINAR.daten;
    fetch('assets/data/bestellung.json?v=ad949359')
      .then(function (r) { return r.json(); })
      .then(function (k) {
        konfig = k;
        window.AKPINAR.konfig = k;
        if (!k.aktiv) return;
        document.body.classList.add('bestellen-an');
        korbLaden();
        knoepfeAnbauen();
        korbZeichnen();
        var kk = $('#korb-knopf');
        if (kk) kk.addEventListener('click', korbOeffnen);
        var zu = $('#korb-zu');
        if (zu) zu.addEventListener('click', korbSchliessen);
        document.dispatchEvent(new CustomEvent('bestellung-bereit'));
      })
      .catch(function (e) { console.error('Bestellkonfiguration fehlt:', e); });
  });
})();
