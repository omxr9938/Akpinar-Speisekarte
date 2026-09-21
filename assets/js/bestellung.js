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

  /** Die Overlays auf die tatsächlich sichtbare Höhe setzen.

      Ein fest positioniertes Fenster mit inset:0 behält auf iOS seine Höhe,
      wenn die Tastatur aufgeht: Der sichtbare Bereich schrumpft, die Box
      nicht. Der Rollbereich reicht dadurch hinter die Tastatur. Tippt man
      dann auf einen Ausfüllvorschlag, rollt Safari das Feld in den sichtbaren
      Bereich — und schießt dabei bis ans Ende der Seite.

      visualViewport meldet, was wirklich zu sehen ist, samt Versatz nach oben,
      wenn die Tastatur die Seite hochschiebt. Ohne die Schnittstelle bleibt es
      beim alten Verhalten (CSS-Rückfallwert 100 %). */
  function sichtHoehe() {
    var vv = window.visualViewport;
    var w = document.documentElement.style;
    w.setProperty('--sichthoehe', (vv ? vv.height : window.innerHeight) + 'px');
    w.setProperty('--sichtoben', (vv ? vv.offsetTop : 0) + 'px');
  }

  /** Verweise auf andere Gerichte, die keine Zutat sind. */
  var VERWEIS = /^(D[öo]ner\s+Classic|Nr\.\s*\d+|Inhalt\s+wie|wie\s+Nr)/i;

  /** Zutaten aus der Beschreibung lesen: "Salami und Peperoni" -> zwei Zutaten.
      Die Beschreibung ist die einzige Quelle dafür, was auf dem Gericht liegt.

      Sonderfall Verweise: Manche Gerichte beschreiben sich über ein anderes
      ("Döner Classic mit Sucuk und Weichkäse"). Der Verweis selbst ist keine
      Zutat und darf nicht als abwählbarer Punkt erscheinen — die Zutaten des
      Grundgerichts kommen ohnehin über die Basisliste dazu. Was hinter dem
      "mit" steht, ist dagegen sehr wohl eine Zutat. */
  /** Verweist die Beschreibung auf ein anderes Gericht?

      Das entscheidet, ob die Basiszutaten dazugehören. "Döner Classic mit
      Weichkäse" nennt die Füllung nicht, die muss aus der Basisliste kommen.
      "Fleisch, Pommes oder gem. Salat, Soße" nennt sie vollständig — dort die
      Basisliste danebenzulegen erfindet Zutaten, die es gar nicht gibt. */
  function verweistAufAnderes(beschreibung) {
    if (!beschreibung) return false;
    return beschreibung
      .replace(/\s+u\.\s+/g, ', ')
      .replace(/\s+und\s+/g, ', ')
      .split(',')
      .some(function (teil) { return VERWEIS.test(teil.trim()); });
  }

  function zutatenAus(beschreibung) {
    if (!beschreibung) return [];
    var roh = beschreibung
      .replace(/\s+u\.\s+/g, ', ')
      .replace(/\s+und\s+/g, ', ')
      .split(',');

    var raus = [];
    roh.forEach(function (teil) {
      var z = teil.trim();
      if (!z) return;

      if (VERWEIS.test(z)) {
        // "Döner Classic mit Sucuk" -> nur "Sucuk" behalten
        var mit = z.split(/\s+mit\s+/i);
        if (mit.length > 1) raus.push(mit.slice(1).join(' mit ').trim());
        return;
      }
      z = z.replace(/^mit\s+/i, '').trim();
      // Sätze und Hinweise sind keine Zutaten
      if (z && z.length < 34 && !/^(inkl\.|nur\b|als\b)/i.test(z)) raus.push(z);
    });
    return raus;
  }

  /** Doppelte Zutaten zusammenführen, auch wenn die Karte abkürzt:
      "Blaukr." und "Blaukraut" sind dasselbe. Zusammengeführt wird nur, wenn
      die kürzere Schreibweise auf einen Punkt endet — sonst würde
      "Tomaten" fälschlich mit "Tomatensoße" verschmelzen. */
  /** Abkürzungen der gedruckten Karte ausschreiben.

      Auf dem Papier ist "Blaukr." eine Platzersparnis, auf dem Handy steht die
      Zutat als eigener Knopf und liest sich dort wie ein Tippfehler. Die Liste
      steht in bestellung.json, damit sie mit der Karte gepflegt werden kann. */
  function ausschreiben(z) {
    var lang = (konfig.abkuerzungen || {})[z];
    return lang || z;
  }

  function zusammenfassen(liste) {
    var raus = [];
    liste.forEach(function (z) {
      var kurz = z.replace(/\.$/, '');
      for (var i = 0; i < raus.length; i++) {
        var v = raus[i];
        var vKurz = v.replace(/\.$/, '');
        if (v === z) return;
        // bereits vorhandener Eintrag ist die Abkürzung -> durch die lange ersetzen
        if (/\.$/.test(v) && z.toLowerCase().indexOf(vKurz.toLowerCase()) === 0) {
          raus[i] = z;
          return;
        }
        // neuer Eintrag ist die Abkürzung -> verwerfen
        if (/\.$/.test(z) && v.toLowerCase().indexOf(kurz.toLowerCase()) === 0) {
          return;
        }
      }
      raus.push(z);
    });
    return raus;
  }

  /** Auswahlfragen, die fuer dieses Gericht gelten.

      Die Karte schreibt bei manchen Gerichten mehrere Moeglichkeiten hin, ohne
      sich festzulegen: "mit Pommes, Reis oder Salat", "Alle Pizzen mit
      Tomaten- oder Sahnesosse", "Rigatoni / Spaghetti / Tortellini". Der Gast
      muss sich entscheiden, sonst raet die Kueche. Genau das ging vorher
      nicht — man konnte den Doener-Teller bestellen, ohne je zu sagen, ob
      Pommes oder Salat dazu sollen. */
  function wahlenFuer(gericht, kategorie) {
    return (konfig.wahlen || []).filter(function (w) {
      if (w.kategorie && w.kategorie !== kategorie.id) return false;
      if (w.gilt_fuer && !new RegExp(w.gilt_fuer, 'i').test(gericht.name || '')) return false;
      if (w.nicht_bei && new RegExp(w.nicht_bei, 'i').test(gericht.name || '')) return false;
      return !!(w.optionen && w.optionen.length);
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

  /** Ein Element im Bestellfenster sichtbar machen.

      Bewusst ohne scrollIntoView und ohne Animation: Im festen Overlay ist
      beides unzuverlässig. Gerollt wird die Karte selbst (.bf__karte ist das
      Element mit dem Rollbalken), und zwar synchron. */
  function rollen(ziel) {
    var karte = ziel.closest ? ziel.closest('.bf__karte') : null;
    if (!karte) return;
    var kr = karte.getBoundingClientRect();
    var zr = ziel.getBoundingClientRect();
    // Zielposition: so weit hochrollen, dass das Element mit etwas Luft
    // oberhalb der Fußleiste steht.
    var fuss = karte.querySelector('.bf__fuss');
    var platz = fuss ? fuss.getBoundingClientRect().height : 0;
    var sichtbar = kr.height - platz;
    var neu = karte.scrollTop + (zr.top - kr.top) - Math.max(12, (sichtbar - zr.height) / 2);
    karte.scrollTop = Math.max(0, neu);
  }

  function fensterOeffnen(gericht, kategorie) {
    // Eigene Größen am Gericht haben Vorrang vor den Spalten der Kategorie.
    var groessen = gericht.groessen
      ? gericht.groessen.map(function (g, i) {
          return { label: g.label, preis: zuZahl(g.preis), index: i };
        })
      : (kategorie.spalten || ['']).map(function (sp, i) {
          return { label: (kategorie.spaltenKurz && kategorie.spaltenKurz[i]) || sp || '',
                   preis: zuZahl(gericht.preise[i]), index: i };
        });
    groessen = groessen.filter(function (g) { return g.preis !== null; });

    if (!groessen.length) return;

    var zutatenKonf = (konfig.zutaten || {})[kategorie.id] || {};
    // Die Basiszutaten sind die Füllung des Standard-Döners. Sie gehören nur
    // zu Gerichten, deren Beschreibung auf ein anderes verweist und die
    // Füllung deshalb nicht selbst aufzählt. Vorher hingen sie an jedem
    // Gericht der Kategorie — die Döner-Box bekam Salat, Tomaten, Zwiebeln
    // und Blaukraut angedichtet, das Käse-Pide sogar Fleisch.
    var nichtBei = zutatenKonf.basis_nicht_bei || {};
    var kennung = ((gericht.name || '') + ' ' + (gericht.beschreibung || '')).toLowerCase();
    var basis = verweistAufAnderes(gericht.beschreibung)
      ? (zutatenKonf.basis || []).filter(function (z) {
          var muster = nichtBei[z];
          return !muster || !new RegExp(muster, 'i').test(kennung);
        })
      : [];

    // Umgekehrter Fall: Die Karte nennt bei den Döner-Boxen nur die Beilage,
    // Soße ist trotzdem drauf und soll abwählbar sein.
    var nachtrag = [];
    (zutatenKonf.extra_abwaehlbar || []).forEach(function (e) {
      if (e.gilt_fuer && !new RegExp(e.gilt_fuer, 'i').test(gericht.name || '')) return;
      nachtrag = nachtrag.concat(e.zutaten || []);
    });
    var ausBeschreibung = zutatenAus(gericht.beschreibung);
    // Beschreibung zuerst, Basis danach: Die Beschreibung nennt die Zutaten in
    // der Reihenfolge der Karte, und dort steht beim Döner das Fleisch vorne.
    var abwaehlbar = zusammenfassen(
      ausBeschreibung.concat(basis).concat(nachtrag).map(ausschreiben));

    var wahlen = wahlenFuer(gericht, kategorie);
    // Was zur Auswahl steht, gehört nicht mehr unter "Zutaten weglassen":
    // "Pommes oder gem. Salat" stand sonst als ein einziger abwählbarer Punkt
    // da, obwohl es in Wahrheit eine Entscheidung zwischen zweien ist.
    wahlen.forEach(function (w) {
      if (!w.verdeckt) return;
      var muster = new RegExp(w.verdeckt, 'i');
      abwaehlbar = abwaehlbar.filter(function (z) { return !muster.test(z); });
    });

    var stand = {
      groesse: groessen[0],
      // Pflichtfragen starten leer, damit niemand versehentlich eine Beilage
      // bekommt, die er nicht wollte. Bei den übrigen ist die erste Angabe der
      // Karte vorausgewählt (Tomatensoße, Rigatoni) — das ist ohnehin der
      // Normalfall und erspart bei 28 Pizzen je einen Pflichtklick.
      wahl: wahlen.map(function (w) { return w.pflicht ? null : w.optionen[0]; }),
      weg: {},          // abgewählte Zutaten
      extras: [],       // gewählte Extras
      sossen: [],
      menue: false,
      getraenk: null,
      anzahl: 1
    };

    // Vor preisJetzt() deklarieren: Der Menue-Block steht weiter unten im
    // Fenster, sein Aufpreis geht aber in die Preisberechnung darueber ein.
    var menuePreis = 0;
    var preisZeile = el('strong', { class: 'bf__preis' });

    function preisJetzt() {
      var p = stand.groesse.preis;
      stand.extras.forEach(function (e) { p += e.preis; });
      if (stand.menue) p += menuePreis;
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
            if (zutatenKonf.menue_bei_groesse) {
              if (g.label === zutatenKonf.menue_bei_groesse) {
                // Menü-Spalte gewählt: gleich fragen, welches Getränk dazu
                // gehört. Wird abgebrochen, bleibt die Spalte trotzdem stehen
                // — der Preis stimmt ja, nur die Angabe fehlt dann noch.
                getraenkWaehlen(function (name) {
                  if (name) stand.getraenk = name;
                });
              } else {
                stand.getraenk = null;
              }
            }
            preisAktualisieren();
          }
        }, [el('span', { class: 'bf__optname', text: g.label.replace('\n', ' ') }),
            el('span', { class: 'bf__optpreis', text: euro(g.preis) })]);
        gWahl.appendChild(b);
      });
      inhalt.appendChild(el('p', { class: 'bf__titel', text: 'Größe' }));
      inhalt.appendChild(gWahl);
    }

    // --- Auswahlfragen (genau eine Antwort je Frage)
    var wahlKnoepfe = [];
    wahlen.forEach(function (w, wi) {
      var box = el('div', { class: 'bf__chips' });
      var knoepfe = [];
      w.optionen.forEach(function (o) {
        var b = el('button', {
          class: 'bf__chip bf__chip--wahl' + (stand.wahl[wi] === o ? ' ist-an' : ''),
          type: 'button'
        }, [document.createTextNode(o)]);
        b.addEventListener('click', function () {
          stand.wahl[wi] = o;
          knoepfe.forEach(function (k) { k.classList.remove('ist-an'); });
          b.classList.add('ist-an');
          box.classList.remove('ist-fehlend');
        });
        knoepfe.push(b);
        box.appendChild(b);
      });
      wahlKnoepfe.push(box);
      inhalt.appendChild(el('p', { class: 'bf__titel',
        text: w.frage + (w.pflicht ? ' — bitte wählen' : '') }));
      inhalt.appendChild(box);
    });

    // --- Soße (mehrere gleichzeitig möglich)
    if (zutatenKonf.sossen) {
      var sWahl = el('div', { class: 'bf__chips' });
      zutatenKonf.sossen.optionen.forEach(function (o) {
        var b = el('button', { class: 'bf__chip bf__chip--sosse', type: 'button' },
          [document.createTextNode(o)]);
        b.addEventListener('click', function () {
          var i = stand.sossen.indexOf(o);
          if (i >= 0) { stand.sossen.splice(i, 1); b.classList.remove('ist-an'); }
          else { stand.sossen.push(o); b.classList.add('ist-an'); }
        });
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

    // --- Getränk zum Menü
    //
    // Bewusst ein eigenes, kleines Fenster statt eines Blocks, der unten im
    // Bestellfenster aufklappt. Der Block lag rund 630 Pixel tief, also unter
    // dem Bildrand jedes Telefons, und wurde nur durch Scrollen sichtbar.
    // Dreimal gemeldet, zweimal "repariert" — erst mit weicher Animation, dann
    // mit direktem Rollen. Beides hängt davon ab, dass das Rollen im festen
    // Overlay greift. Ein eigenes Fenster in der Bildmitte hängt von gar
    // nichts ab: Es ist da, wo der Gast ohnehin hinsieht.
    //
    // Ein Tipp genügt: Getränk antippen wählt es aus und schließt das Fenster.
    function getraenkWaehlen(fertig) {
      var liste = konfig.menue_getraenke || [];
      if (!liste.length) { fertig(null); return; }

      var gewaehlt = null;
      function zu() {
        document.removeEventListener('keydown', beiTaste2);
        fenster2.remove();
        fertig(gewaehlt);
      }
      function beiTaste2(e) { if (e.key === 'Escape') zu(); }

      var chips = el('div', { class: 'bf__chips bf__chips--gross' });
      liste.forEach(function (name) {
        var b = el('button', {
          class: 'bf__chip' + (stand.getraenk === name ? ' ist-an' : ''),
          type: 'button'
        }, [document.createTextNode(name)]);
        b.addEventListener('click', function () { gewaehlt = name; zu(); });
        chips.appendChild(b);
      });

      var fenster2 = el('div', {
        class: 'bf bf--klein', role: 'dialog', 'aria-modal': 'true',
        'aria-label': 'Getränk zum Menü'
      }, [
        el('div', { class: 'bf__karte' }, [
          el('div', { class: 'bf__kopf' }, [
            el('h2', { class: 'bf__name', text: 'Getränk zum Menü' }),
            el('button', { class: 'bf__zu', type: 'button',
                           'aria-label': 'Schließen', onclick: zu }, ['×'])
          ]),
          el('div', { class: 'bf__body' }, [
            el('p', { class: 'bf__klein',
                      text: 'Im Menüpreis enthalten — bitte wählen.' }),
            chips
          ])
        ])
      ]);
      fenster2.addEventListener('click', function (e) {
        if (e.target === fenster2) zu();
        e.stopPropagation();
      });
      document.addEventListener('keydown', beiTaste2);
      document.body.appendChild(fenster2);
      var erster = chips.querySelector('.bf__chip');
      if (erster && erster.focus) erster.focus();
    }

    // --- Als Menü (Döner und Dürüm: Aufpreis-Schalter)
    var menueKonf = zutatenKonf.menue;
    var menueKnopf = null;

    function menueBeschriften() {
      if (!menueKnopf) return;
      var z = $('.bf__menuebesch', menueKnopf);
      if (!z) return;
      z.textContent = stand.getraenk
        ? menueKonf.beschreibung + ' — ' + stand.getraenk
        : menueKonf.beschreibung;
    }

    if (menueKonf && new RegExp(menueKonf.gilt_fuer, 'i').test(gericht.name)) {
      menuePreis = zuZahl(menueKonf.preis) || 0;

      menueKnopf = el('button', { class: 'bf__menue', type: 'button' }, [
        el('span', { class: 'bf__menuehaken', 'aria-hidden': 'true' }, ['✓']),
        el('span', {}, [
          el('span', { class: 'bf__menuename', text: menueKonf.name }),
          el('span', { class: 'bf__menuebesch', text: menueKonf.beschreibung })
        ]),
        el('span', { class: 'bf__menuepreis', text: '+' + euro(menuePreis) })
      ]);

      menueKnopf.addEventListener('click', function () {
        if (stand.menue) {
          // Zweiter Tipp: Menü wieder aus.
          stand.menue = false;
          stand.getraenk = null;
          menueKnopf.classList.remove('ist-an');
          menueBeschriften();
          preisAktualisieren();
          return;
        }
        getraenkWaehlen(function (name) {
          // Ohne Getränk kein Menü: Das Getränk ist im Preis enthalten, ein
          // Menü ohne Angabe müsste der Laden nachfragen.
          if (!name) return;
          stand.menue = true;
          stand.getraenk = name;
          menueKnopf.classList.add('ist-an');
          menueBeschriften();
          preisAktualisieren();
        });
      });

      inhalt.appendChild(menueKnopf);

    } else if (zutatenKonf.menue_bei_groesse) {
      // Burger: Das Menü steckt in der Preisspalte, der Preis stimmt also
      // schon. Es fehlt nur die Angabe, welches Getränk dazugehört. Die Frage
      // kommt, sobald die Menü-Spalte gewählt wird — siehe groesseGewaehlt().
      if (stand.groesse.label === zutatenKonf.menue_bei_groesse) {
        getraenkWaehlen(function (name) { stand.getraenk = name || null; });
      }
    }

    // --- Notiz
    var notiz = el('textarea', {
      class: 'bf__notiz',
      id: 'bf-notiz',
      rows: '2',
      placeholder: 'z. B. gut durchgebacken, extra scharf, Soße separat'
    });
    inhalt.appendChild(el('label', { class: 'bf__titel', for: 'bf-notiz',
      text: 'Anmerkung zu diesem Gericht' }));
    inhalt.appendChild(notiz);

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
            // Ohne Antwort auf eine Pflichtfrage nicht in den Korb: Eine
            // Bestellung "Döner-Teller" ohne Beilage kann die Küche nicht
            // ausführen, und per WhatsApp fällt es erst beim Kochen auf.
            var offen = -1;
            wahlen.forEach(function (w, wi) {
              if (w.pflicht && !stand.wahl[wi] && offen < 0) offen = wi;
            });
            if (offen >= 0) {
              var box = wahlKnoepfe[offen];
              box.classList.add('ist-fehlend');
              rollen(box);
              return;
            }
            // Menü ohne Getränk: Das Getränk ist im Preis enthalten, wer es
            // nicht angibt, verschenkt es. Beim Döner kann das gar nicht mehr
            // passieren — dort gibt es kein Menü ohne Getränk. Beim Burger
            // steckt das Menü in der Preisspalte, da wird hier nachgefragt.
            var brauchtGetraenk = zutatenKonf.menue_bei_groesse
              && stand.groesse.label === zutatenKonf.menue_bei_groesse;
            if (brauchtGetraenk && !stand.getraenk) {
              getraenkWaehlen(function (name) { if (name) stand.getraenk = name; });
              return;
            }
            stand.notiz = notiz.value.trim();
            // Hier bestimmen, nicht in hinzufuegen(): zutatenKonf ist nur in
            // diesem Fenster bekannt, nicht in der Funktion darunter.
            stand.istMenue = !!(stand.menue
              || (zutatenKonf.menue_bei_groesse
                  && stand.groesse.label === zutatenKonf.menue_bei_groesse));
            stand.wahlText = wahlen.map(function (w, wi) {
              return w.frage + ': ' + stand.wahl[wi];
            }).filter(function (t, i) { return !!stand.wahl[i]; });
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
    function beiTaste(e) {
      // Nicht schließen, solange die Getränkewahl darüber offen ist: Sonst
      // nimmt ein Escape beide Fenster mit und der Gast steht wieder in der
      // Karte, obwohl er nur die Getränkewahl abbrechen wollte.
      if (e.key === 'Escape' && !document.querySelector('.bf--klein')) schliessen();
    }

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
      wahl: stand.wahlText || [],
      ohne: weg,
      extras: stand.extras.map(function (e) { return e.name; }),
      sossen: stand.sossen || [],
      menue: stand.istMenue ? (stand.getraenk || 'Getränk nach Wahl') : null,
      notiz: stand.notiz || '',
      preis: einzelpreis,
      anzahl: stand.anzahl
    });
    korbSpeichern();
    korbZeichnen();
    bestaetigen(gericht.name, stand.anzahl);
  }

  /** Kurze Rückmeldung, dass etwas im Korb gelandet ist. Ohne sie wüsste der
      Gast nicht, ob der Knopf gewirkt hat — der Warenkorb öffnet sich
      bewusst nicht mehr, damit er weiter aussuchen kann. */
  function bestaetigen(name, anzahl) {
    var alt = document.querySelector('.bestaetigung');
    if (alt) alt.remove();
    var box = el('div', { class: 'bestaetigung', role: 'status' }, [
      el('span', { class: 'bestaetigung__text',
        text: anzahl + '× ' + name + ' hinzugefügt' }),
      el('button', { class: 'bestaetigung__korb', type: 'button',
        onclick: function () { box.remove(); korbOeffnen(); } }, ['Zum Warenkorb'])
    ]);
    document.body.appendChild(box);
    requestAnimationFrame(function () { box.classList.add('ist-da'); });
    setTimeout(function () {
      box.classList.remove('ist-da');
      setTimeout(function () { box.remove(); }, 260);
    }, 3200);
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
      // Vor allem anderen: Die Antwort auf eine Pflichtfrage gehört zur
      // Bestellung selbst, nicht zu den Zusätzen.
      if (p.wahl && p.wahl.length) zusatz = zusatz.concat(p.wahl);
      // Bei Burgern heißt die Größe bereits "Menü" — dann nicht doppelt nennen.
      if (p.menue) {
        zusatz.push((/^men/i.test(p.groesse || '') ? 'inkl. Pommes + ' : 'Als Menü: Pommes + ')
          + p.menue);
      }
      if (p.sossen && p.sossen.length) zusatz.push('Soße: ' + p.sossen.join(' + '));
      if (p.ohne.length) zusatz.push('ohne ' + p.ohne.join(', '));
      if (p.extras.length) zusatz.push('mit ' + p.extras.join(', '));
      if (p.notiz) zusatz.push('„' + p.notiz + '“');
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

  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', sichtHoehe);
    window.visualViewport.addEventListener('scroll', sichtHoehe);
  }
  window.addEventListener('resize', sichtHoehe);
  window.addEventListener('orientationchange', sichtHoehe);
  sichtHoehe();

  window.AKPINAR = window.AKPINAR || {};
  window.AKPINAR.korbZeichnen = korbZeichnen;
  // Die Kasse braucht das für ihre Vorschlagsknöpfe: Ein Gericht mit
  // Pflichtfrage darf dort nicht mit einem Klick im Korb landen, und die
  // übrigen brauchen wenigstens ihre Vorgabeantwort.
  window.AKPINAR.wahlenFuer = wahlenFuer;
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
    fetch('assets/data/bestellung.json?v=b52f3e04')
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
