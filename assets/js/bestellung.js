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

  /** Verweise auf andere Gerichte, die keine Zutat sind. */
  var VERWEIS = /^(D[öo]ner\s+Classic|Nr\.\s*\d+|Inhalt\s+wie|wie\s+Nr)/i;

  /** Zutaten aus der Beschreibung lesen: "Salami und Peperoni" -> zwei Zutaten.
      Die Beschreibung ist die einzige Quelle dafür, was auf dem Gericht liegt.

      Sonderfall Verweise: Manche Gerichte beschreiben sich über ein anderes
      ("Döner Classic mit Sucuk und Weichkäse"). Der Verweis selbst ist keine
      Zutat und darf nicht als abwählbarer Punkt erscheinen — die Zutaten des
      Grundgerichts kommen ohnehin über die Basisliste dazu. Was hinter dem
      "mit" steht, ist dagegen sehr wohl eine Zutat. */
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
    // Basiszutaten, die zum Gericht nicht passen, herausnehmen: Bei einem
    // vegetarischen Döner soll man kein Fleisch abwählen können.
    var nichtBei = zutatenKonf.basis_nicht_bei || {};
    var kennung = ((gericht.name || '') + ' ' + (gericht.beschreibung || '')).toLowerCase();
    var basis = (zutatenKonf.basis || []).filter(function (z) {
      var muster = nichtBei[z];
      return !muster || !new RegExp(muster, 'i').test(kennung);
    });
    var ausBeschreibung = zutatenAus(gericht.beschreibung);
    // Beschreibung zuerst, Basis danach: Die Beschreibung nennt die Zutaten in
    // der Reihenfolge der Karte, und dort steht beim Döner das Fleisch vorne.
    var abwaehlbar = zusammenfassen(ausBeschreibung.concat(basis));

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
              getraenkeZeigen(g.label === zutatenKonf.menue_bei_groesse);
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

    // --- Getränkeauswahl, von beiden Menü-Arten genutzt
    //     Döner/Dürüm: erscheint, wenn der Menü-Schalter an ist.
    //     Burger: erscheint, wenn die Preisspalte "Menü" gewählt ist — dort
    //     steht das Menü bereits in der Karte und braucht keinen Schalter.
    var getraenkBox = el('div', { class: 'bf__getraenke', hidden: true });

    function getraenkeBauen() {
      var liste = konfig.menue_getraenke || [];
      if (!liste.length) return;
      getraenkBox.appendChild(el('p', { class: 'bf__titel', text: 'Getränk zum Menü' }));
      var gListe = el('div', { class: 'bf__chips' });
      liste.forEach(function (name) {
        var b = el('button', { class: 'bf__chip', type: 'button' },
          [document.createTextNode(name)]);
        b.addEventListener('click', function () {
          stand.getraenk = stand.getraenk === name ? null : name;
          Array.prototype.forEach.call(gListe.children, function (c) {
            c.classList.remove('ist-an');
          });
          if (stand.getraenk) b.classList.add('ist-an');
        });
        gListe.appendChild(b);
      });
      getraenkBox.appendChild(gListe);
    }

    function getraenkeZeigen(zeigen) {
      getraenkBox.hidden = !zeigen;
      if (!zeigen) {
        stand.getraenk = null;
        Array.prototype.forEach.call(getraenkBox.querySelectorAll('.bf__chip'),
          function (c) { c.classList.remove('ist-an'); });
      } else {
        // Die Auswahl klappt weit unten auf und läge sonst hinter der festen
        // Fußleiste — auf dem Handy sieht man dann gar nicht, dass es sie gibt.
        setTimeout(function () {
          if (getraenkBox.scrollIntoView) {
            getraenkBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }, 60);
      }
    }

    // --- Als Menü (Döner und Dürüm: Aufpreis-Schalter)
    var menueKonf = zutatenKonf.menue;
    var menueText = (gericht.name || '') + ' ' + (gericht.beschreibung || '');
    if (menueKonf && new RegExp(menueKonf.gilt_fuer, 'i').test(gericht.name)) {
      menuePreis = zuZahl(menueKonf.preis) || 0;

      var menueKnopf = el('button', { class: 'bf__menue', type: 'button' }, [
        el('span', { class: 'bf__menuehaken', 'aria-hidden': 'true' }, ['✓']),
        el('span', {}, [
          el('span', { class: 'bf__menuename', text: menueKonf.name }),
          el('span', { class: 'bf__menuebesch', text: menueKonf.beschreibung })
        ]),
        el('span', { class: 'bf__menuepreis', text: '+' + euro(menuePreis) })
      ]);

      menueKnopf.addEventListener('click', function () {
        stand.menue = !stand.menue;
        menueKnopf.classList.toggle('ist-an', stand.menue);
        getraenkeZeigen(stand.menue);
        preisAktualisieren();
      });

      getraenkeBauen();
      inhalt.appendChild(menueKnopf);
      inhalt.appendChild(getraenkBox);
    } else if (zutatenKonf.menue_bei_groesse) {
      // Burger: Das Menü steckt in der Preisspalte, der Preis stimmt also
      // schon. Es fehlt nur die Angabe, welches Getränk dazugehört.
      getraenkeBauen();
      inhalt.appendChild(getraenkBox);
      getraenkeZeigen(stand.groesse.label === zutatenKonf.menue_bei_groesse);
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
              if (box.scrollIntoView) {
                box.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }
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
    fetch('assets/data/bestellung.json?v=1ccc045f')
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
