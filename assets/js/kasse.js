/* Kasse: Abholung oder Lieferung, Mindestbestellwert nach Ort, Vorschläge zum
   Auffüllen, Zahlungsart und Versand der Bestellung.

   Der Mindestbestellwert kommt aus den Lieferzonen der Speisekarte. Wird er
   verfehlt, zeigt die Seite nicht nur "zu wenig", sondern schlägt konkrete
   Kleinigkeiten vor, die den Betrag erreichen — das ist für den Gast der
   Unterschied zwischen Abbruch und Bestellung. */
(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var A;                     // window.AKPINAR
  var zustand = { weg: 'lieferung', ort: null, zahlung: null };

  function zuZahl(p) {
    if (p === null || p === undefined || p === '' || p === '-') return null;
    return parseFloat(String(p).replace(/[^\d,.-]/g, '').replace(',', '.'));
  }

  /** Alle Orte aus den Lieferzonen, mit ihrem Mindestbestellwert. */
  function orte() {
    var zonen = (A.daten.lieferung || {}).zonen || [];
    var liste = [];
    zonen.forEach(function (z) {
      var min = zuZahl(z.mindestbestellung);
      z.orte.split(',').forEach(function (o) {
        var name = o.replace('…', '').trim();
        if (name) liste.push({ ort: name, zone: z.zone, min: min });
      });
    });
    return liste;
  }

  function mindestwert() {
    if (zustand.weg === 'abholung') return 0;
    if (zustand.ort) return zustand.ort.min;
    return zuZahl((A.konfig.lieferung || {}).mindestbestellwert_standard) || 0;
  }

  /** Gerichte, die den Warenkorb günstig über den Mindestwert heben. */
  function vorschlaege(fehlbetrag) {
    var alle = [];
    (A.daten.kategorien || []).forEach(function (k) {
      k.items.forEach(function (it) {
        var p = zuZahl((it.preise || [])[0]);
        if (p !== null && p > 0) {
          alle.push({ name: it.name, nr: it.nr || '', preis: p, kategorie: k });
        }
      });
    });
    // Zuerst die, die den Fehlbetrag gerade so decken, dann aufsteigend
    var passend = alle.filter(function (x) { return x.preis >= fehlbetrag; })
                      .sort(function (a, b) { return a.preis - b.preis; });
    var rest = alle.filter(function (x) { return x.preis < fehlbetrag; })
                   .sort(function (a, b) { return b.preis - a.preis; });
    return passend.slice(0, 3).concat(rest.slice(0, 1));
  }

  function aktualisieren() {
    var box = $('#kasse');
    if (!box || !A.konfig) return;

    var s = A.summe();
    var min = mindestwert();
    var fehlt = Math.max(0, min - s);

    var zeile = $('#kasse-summe');
    if (zeile) zeile.textContent = A.euro(s);

    var hinweis = $('#kasse-min');
    if (hinweis) {
      if (zustand.weg === 'abholung') {
        hinweis.className = 'kasse__min ist-gut';
        hinweis.textContent = 'Abholung — kein Mindestbestellwert.';
      } else if (!zustand.ort) {
        hinweis.className = 'kasse__min';
        hinweis.textContent = 'Bitte wählen Sie Ihren Ort, dann sehen Sie den '
          + 'Mindestbestellwert.';
      } else if (fehlt > 0) {
        hinweis.className = 'kasse__min ist-knapp';
        hinweis.textContent = 'Mindestbestellwert für ' + zustand.ort.ort + ': '
          + A.euro(min) + ' — es fehlen noch ' + A.euro(fehlt) + '.';
      } else {
        hinweis.className = 'kasse__min ist-gut';
        hinweis.textContent = 'Mindestbestellwert für ' + zustand.ort.ort
          + ' erreicht.';
      }
    }

    // Vorschläge zum Auffüllen
    var vbox = $('#kasse-vorschlaege');
    if (vbox) {
      vbox.innerHTML = '';
      if (fehlt > 0 && A.korb().length) {
        vbox.appendChild(A.el('p', { class: 'kasse__vtitel',
          text: 'Damit wären Sie über dem Mindestbestellwert:' }));
        var reihe = A.el('div', { class: 'kasse__vliste' });
        vorschlaege(fehlt).forEach(function (v) {
          reihe.appendChild(A.el('button', {
            class: 'kasse__v', type: 'button',
            onclick: function () {
              A.korb().push({
                name: v.name, nr: v.nr, kategorie: v.kategorie.name,
                groesse: (v.kategorie.spaltenKurz && v.kategorie.spaltenKurz[0]) || '',
                ohne: [], extras: [], sossen: [], notiz: '', preis: v.preis, anzahl: 1
              });
              A.korbZeichnen();
            }
          }, [
            A.el('span', { class: 'kasse__vname', text: v.name }),
            A.el('span', { class: 'kasse__vpreis', text: '+ ' + A.euro(v.preis) })
          ]));
        });
        vbox.appendChild(reihe);
      }
    }

    var senden = $('#kasse-senden');
    if (senden) {
      var bereit = A.korb().length > 0 && fehlt === 0 && zustand.zahlung
        && (zustand.weg === 'abholung' || zustand.ort);
      senden.disabled = !bereit;
      senden.textContent = bereit ? 'Zahlungspflichtig bestellen'
                                  : 'Bestellung noch nicht vollständig';
    }
  }

  /** Bestelltext für WhatsApp. */
  function bestelltext() {
    var b = A.daten.betrieb;
    var z = [];
    z.push('*Bestellung — ' + b.name + '*');
    z.push('');
    A.korb().forEach(function (p) {
      var t = p.anzahl + '× ' + (p.nr ? 'Nr. ' + p.nr + ' ' : '') + p.name;
      if (p.groesse) t += ' (' + p.groesse + ')';
      z.push(t + '   ' + A.euro(p.preis * p.anzahl));
      if (p.sossen && p.sossen.length) z.push('   SOSSE: ' + p.sossen.join(' + '));
      if (p.ohne.length) z.push('   OHNE: ' + p.ohne.join(', '));
      if (p.extras.length) z.push('   EXTRA: ' + p.extras.join(', '));
      if (p.notiz) z.push('   ANMERKUNG: ' + p.notiz);
    });
    z.push('');
    z.push('*Summe: ' + A.euro(A.summe()) + '*');
    z.push('');
    z.push(zustand.weg === 'abholung' ? 'Abholung im Laden' : 'Lieferung');
    if (zustand.weg === 'lieferung') {
      z.push('Ort: ' + (zustand.ort ? zustand.ort.ort : '—'));
      var str = $('#f-strasse'), plz = $('#f-plz');
      if (str && str.value) z.push('Adresse: ' + str.value
        + (plz && plz.value ? ', ' + plz.value : ''));
    }
    z.push('Zahlung: ' + zustand.zahlung.name);
    var name = $('#f-name'), tel = $('#f-tel'), notiz = $('#f-notiz');
    if (name && name.value) z.push('Name: ' + name.value);
    if (tel && tel.value) z.push('Telefon: ' + tel.value);
    if (notiz && notiz.value) z.push('Anmerkung: ' + notiz.value);
    return z.join('\n');
  }

  function aufbauen() {
    A = window.AKPINAR;
    var box = $('#kasse');
    if (!box || !A.konfig) return;

    // Weg: Abholung / Lieferung
    var wegBox = $('#kasse-weg');
    [['lieferung', 'Lieferung'], ['abholung', 'Abholung']].forEach(function (w) {
      var b = A.el('button', {
        class: 'kasse__tab' + (w[0] === zustand.weg ? ' ist-an' : ''),
        type: 'button',
        onclick: function () {
          zustand.weg = w[0];
          Array.prototype.forEach.call(wegBox.children, function (c) {
            c.classList.remove('ist-an');
          });
          b.classList.add('ist-an');
          document.body.classList.toggle('ist-abholung', w[0] === 'abholung');
          aktualisieren();
        }
      }, [w[1]]);
      wegBox.appendChild(b);
    });

    // Ort
    var ortWahl = $('#f-ort');
    ortWahl.appendChild(A.el('option', { value: '', text: 'Bitte wählen …' }));
    orte().forEach(function (o, i) {
      ortWahl.appendChild(A.el('option', {
        value: String(i),
        text: o.ort + '  (ab ' + A.euro(o.min) + ')'
      }));
    });
    ortWahl.appendChild(A.el('option', { value: 'andere',
      text: 'Mein Ort ist nicht dabei' }));
    ortWahl.addEventListener('change', function () {
      if (ortWahl.value === 'andere') {
        zustand.ort = null;
        $('#f-ort-hinweis').hidden = false;
      } else {
        $('#f-ort-hinweis').hidden = true;
        zustand.ort = ortWahl.value === '' ? null : orte()[parseInt(ortWahl.value, 10)];
      }
      aktualisieren();
    });

    // Zahlung
    var zBox = $('#kasse-zahlung');
    A.konfig.zahlung.filter(function (z) { return z.aktiv; }).forEach(function (z) {
      var b = A.el('button', { class: 'kasse__zahl', type: 'button',
        onclick: function () {
          zustand.zahlung = z;
          Array.prototype.forEach.call(zBox.children, function (c) {
            c.classList.remove('ist-an');
          });
          b.classList.add('ist-an');
          aktualisieren();
        } }, [
        A.el('span', { class: 'kasse__zname', text: z.name }),
        A.el('span', { class: 'kasse__zbesch', text: z.beschreibung })
      ]);
      zBox.appendChild(b);
    });

    // Absenden
    $('#kasse-senden').addEventListener('click', function () {
      var nummer = (A.konfig.bestellweg || {}).nummer;
      var text = encodeURIComponent(bestelltext());
      window.open('https://wa.me/' + nummer + '?text=' + text, '_blank', 'noopener');
      $('#kasse-danach').hidden = false;
    });

    $('#kasse-leeren').addEventListener('click', function () {
      if (confirm('Warenkorb wirklich leeren?')) A.korbLeeren();
    });

    A.kasseAktualisieren = aktualisieren;
    aktualisieren();
  }

  document.addEventListener('bestellung-bereit', aufbauen);
})();
