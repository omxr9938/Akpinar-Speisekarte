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
  // zeit: null heisst "so schnell wie moeglich", sonst { tag: 0|1, min: Minuten
  // seit Mitternacht, text: "18:30" }.
  var zustand = { weg: 'lieferung', ort: null, zahlung: null, zeit: null };

  var VORLAUF = 60;   // Mindestvorlauf in Minuten, vom Laden so gewuenscht
  var TAKT = 15;      // Raster der angebotenen Uhrzeiten

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

  /** Öffnungszeiten des Tages als Minuten seit Mitternacht.

      Dieselbe Saisonlogik wie die Statusanzeige oben auf der Seite: Sommer
      von April bis Oktober, sonst Winter. Sonntag hat in der Karte eine eigene
      Zeile, auch wenn dort zurzeit dasselbe steht. */
  function oeffnung(datum) {
    var o = A.daten.oeffnungszeiten;
    if (!o || !o.saisons) return null;
    var m = datum.getMonth() + 1;
    var sommer = m >= (o.sommerVon || 4) && m <= (o.sommerBis || 10);
    var saison = o.saisons[sommer ? 0 : 1];
    if (!saison) return null;
    var zeile = saison.zeiten[datum.getDay() === 0 ? 1 : 0] || saison.zeiten[0];
    var t = String(zeile.zeit).match(/(\d{1,2})[.:](\d{2})\s*[–-]\s*(\d{1,2})[.:](\d{2})/);
    if (!t) return null;
    return { von: (+t[1]) * 60 + (+t[2]), bis: (+t[3]) * 60 + (+t[4]) };
  }

  function alsUhrzeit(min) {
    var h = Math.floor(min / 60), m = min % 60;
    return (h < 10 ? '0' : '') + h + ':' + (m < 10 ? '0' : '') + m;
  }

  /** Wählbare Zeiten für heute und, falls heute nichts mehr geht, für morgen.

      Frühestens eine Stunde ab jetzt — so will es der Laden, und es ist auch
      die ehrliche Angabe: Alles darunter kann die Küche bei Andrang nicht
      zusagen. Aufgerundet auf die nächste Viertelstunde, damit runde Zeiten
      dastehen statt "18:37". */
  function zeitfenster(jetzt) {
    var raus = [];
    for (var tag = 0; tag < 2; tag++) {
      var datum = new Date(jetzt.getTime() + tag * 86400000);
      var off = oeffnung(datum);
      if (!off) continue;
      var frueheste = tag === 0
        ? Math.max(off.von, jetzt.getHours() * 60 + jetzt.getMinutes() + VORLAUF)
        : off.von;
      var erste = Math.ceil(frueheste / TAKT) * TAKT;
      var zeiten = [];
      for (var m = erste; m <= off.bis; m += TAKT) zeiten.push(m);
      if (zeiten.length) raus.push({ tag: tag, zeiten: zeiten });
      // Sobald heute etwas frei ist, reicht das - morgen nur als Ausweg,
      // wenn heute nichts mehr geht.
      if (tag === 0 && zeiten.length) break;
    }
    return raus;
  }

  /** Ist der Laden gerade offen? Nur dann ergibt "so schnell wie möglich"
      einen Sinn - sonst wäre es eine Zusage, die niemand halten kann. */
  function jetztOffen(jetzt) {
    var off = oeffnung(jetzt);
    if (!off) return false;
    var min = jetzt.getHours() * 60 + jetzt.getMinutes();
    return min >= off.von && min < off.bis;
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
        if (p === null || p <= 0) return;
        // Gerichte mit Pflichtfrage hier nicht anbieten: Der Vorschlag ist ein
        // einziger Klick, es gibt also keine Gelegenheit zu sagen, ob Pommes
        // oder Salat dazu soll. Wer so ein Gericht will, nimmt es aus der
        // Karte, dort wird gefragt.
        var w = (A.wahlenFuer ? A.wahlenFuer(it, k) : []);
        if (w.some(function (x) { return x.pflicht; })) return;
        alle.push({ name: it.name, nr: it.nr || '', preis: p, kategorie: k,
                    wahl: w.map(function (x) { return x.frage + ': ' + x.optionen[0]; }) });
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
                wahl: v.wahl || [],
                ohne: [], extras: [], sossen: [], menue: null, notiz: '',
                preis: v.preis, anzahl: 1
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

    zeitenZeichnen();

    var senden = $('#kasse-senden');
    if (senden) {
      // Ohne wählbare Zeit ist die Bestellung nicht ausführbar: Wenn der Laden
      // zu ist und auch morgen nichts mehr frei wäre, hilft dem Gast ein
      // abschickbares Formular nicht weiter.
      var zeitOk = zustand.zeit !== null || jetztOffen(new Date());
      var bereit = A.korb().length > 0 && fehlt === 0 && zustand.zahlung
        && zeitOk
        && (zustand.weg === 'abholung' || zustand.ort);
      senden.disabled = !bereit;
      senden.textContent = bereit ? 'Zahlungspflichtig bestellen'
                                  : 'Bestellung noch nicht vollständig';
    }
  }

  /** Die Zeitauswahl aufbauen.

      Wird bei jeder Änderung neu gezeichnet, weil sie von Abholung/Lieferung
      abhängt (nur die Beschriftung) und weil sich die Uhrzeit weiterdreht,
      während der Gast noch aussucht. */
  function zeitenZeichnen() {
    var box = $('#kasse-zeit');
    if (!box) return;
    var jetzt = new Date();
    var offen = jetztOffen(jetzt);
    var bloecke = zeitfenster(jetzt);
    var wort = zustand.weg === 'abholung' ? 'Abholung' : 'Lieferung';

    var titel = $('#zeit-titel');
    if (titel) titel.textContent = wort + ' — wann?';

    // Eine gewählte Zeit, die inzwischen zu früh geworden ist, wieder lösen.
    if (zustand.zeit) {
      var nochDa = bloecke.some(function (b) {
        return b.tag === zustand.zeit.tag
          && b.zeiten.indexOf(zustand.zeit.min) >= 0;
      });
      if (!nochDa) zustand.zeit = null;
    }
    // Ist der Laden zu, ist "so schnell wie möglich" keine Option — dann die
    // früheste wählbare Zeit vorbelegen.
    if (!offen && !zustand.zeit && bloecke.length) {
      var b0 = bloecke[0];
      zustand.zeit = { tag: b0.tag, min: b0.zeiten[0], text: alsUhrzeit(b0.zeiten[0]) };
    }

    box.innerHTML = '';

    if (offen) {
      var sofort = A.el('button', {
        class: 'kasse__zopt kasse__zopt--sofort' + (zustand.zeit ? '' : ' ist-an'),
        type: 'button'
      }, ['So schnell wie möglich']);
      sofort.addEventListener('click', function () {
        zustand.zeit = null;
        aktualisieren();
      });
      box.appendChild(sofort);
    }

    bloecke.forEach(function (b) {
      box.appendChild(A.el('span', { class: 'kasse__ztag',
        text: b.tag ? 'Morgen' : 'Heute' }));
      b.zeiten.forEach(function (m) {
        var an = zustand.zeit && zustand.zeit.tag === b.tag && zustand.zeit.min === m;
        var k = A.el('button', {
          class: 'kasse__zopt' + (an ? ' ist-an' : ''), type: 'button'
        }, [alsUhrzeit(m)]);
        k.addEventListener('click', function () {
          zustand.zeit = { tag: b.tag, min: m, text: alsUhrzeit(m) };
          aktualisieren();
        });
        box.appendChild(k);
      });
    });

    var hinweis = $('#kasse-zeit-hinweis');
    if (!hinweis) return;
    if (!bloecke.length) {
      hinweis.hidden = false;
      hinweis.textContent = 'Heute ist keine Bestellung mehr möglich. '
        + 'Bitte rufen Sie uns an oder bestellen Sie morgen wieder.';
    } else if (!offen) {
      hinweis.hidden = false;
      hinweis.textContent = 'Wir haben gerade geschlossen — bitte wählen Sie '
        + 'eine Zeit. Frühestens eine Stunde im Voraus.';
    } else {
      // Im Normalfall kein Hinweis: Die Auswahl erklärt sich selbst, und der
      // Kasten dazwischen hat nur Platz gekostet.
      hinweis.hidden = true;
      hinweis.textContent = '';
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
      // Bewusst keine Grossbuchstaben: toUpperCase() macht im Deutschen aus
      // "Sosse" ein "SOSSE" und aus der Auswahl des Gastes, "Tomatensosse",
      // ein "TOMATENSOSSE". Das traf auch "Groesse". Hervorgehoben wird
      // stattdessen mit den Sternchen, die WhatsApp fett setzt - die
      // Aenderungen springen dem Laden weiter ins Auge, aber die Woerter
      // bleiben richtig geschrieben.
      if (p.wahl && p.wahl.length) {
        p.wahl.forEach(function (w) {
          z.push('   ' + w.replace(/^([^:]+):/, '*$1:*'));
        });
      }
      if (p.menue) z.push('   *Menü:* kleine Pommes + ' + p.menue);
      if (p.sossen && p.sossen.length) z.push('   *Soße:* ' + p.sossen.join(' + '));
      if (p.ohne.length) z.push('   *Ohne:* ' + p.ohne.join(', '));
      if (p.extras.length) z.push('   *Extra:* ' + p.extras.join(', '));
      if (p.notiz) z.push('   *Anmerkung:* ' + p.notiz);
    });
    z.push('');
    z.push('*Summe: ' + A.euro(A.summe()) + '*');
    z.push('');
    z.push(zustand.weg === 'abholung' ? 'Abholung im Laden' : 'Lieferung');
    var wort = zustand.weg === 'abholung' ? 'Abholung' : 'Lieferung';
    z.push('*' + wort + ':* ' + (zustand.zeit
      ? (zustand.zeit.tag ? 'morgen ' : '') + 'um ' + zustand.zeit.text + ' Uhr'
      : 'so schnell wie möglich'));
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

    // Das Formular dient nur der Ausfüllhilfe. Abgeschickt wird nie: Die
    // Bestellung geht über den Knopf nach WhatsApp. Ohne diese Bremse würde
    // die Eingabetaste im Adressfeld die Seite neu laden und den Warenkorb
    // scheinbar verschwinden lassen.
    var form = $('#kasse-form');
    if (form) form.addEventListener('submit', function (e) { e.preventDefault(); });

    $('#kasse-leeren').addEventListener('click', function () {
      if (confirm('Warenkorb wirklich leeren?')) A.korbLeeren();
    });

    A.kasseAktualisieren = aktualisieren;
    aktualisieren();
  }

  document.addEventListener('bestellung-bereit', aufbauen);
})();
