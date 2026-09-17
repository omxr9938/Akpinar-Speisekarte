# Akpinar Döner & Pizza — Online-Speisekarte

Die digitale Speisekarte von **Akpinar Döner & Pizza**, Neuöttinger Str. 20, 84503 Altötting
— erstellt aus der gedruckten Karte (Stand: gültig ab September 2026).

**Adresse der Seite:** <https://omxr9938.github.io/Akpinar-Speisekarte/>

---

## Was drin ist

| Bereich | Inhalt |
|---|---|
| Speisekarte | 100 Gerichte in 7 Kategorien: Pizza, Türkische Spezialitäten, Burger, Verschiedenes, Nudeln, Salate, Getränke |
| Special-Angebote | Familien-Pizza, Döner/Dürüm/Boxen, Pizzen, Nudeln |
| Service | Liefergebiete mit Mindestbestellwert, Öffnungszeiten (Sommer/Winter), Stempelkarte |
| Allergene | Vollständige Allergenliste als Tabelle, dazu der Hinweis auf die Zusatzstoff-Kennzeichnung |
| QR-Code | Zum Aufstellen, Aufkleben und Verteilen — siehe unten |

Die Seite ist für Handys gebaut (dort wird sie gescannt), funktioniert aber genauso auf
Tablet und Desktop. Zusätzlich gibt es:

- **Suche** über alle Gerichte — „döner“, „thunfisch“, „42“ …
- **Kategorie-Leiste**, die beim Scrollen mitwandert
- **Status-Anzeige** „Jetzt geöffnet / Gerade geschlossen“, berechnet aus den Öffnungszeiten
- **Anruf-Button** — ein Tipp auf die Nummer startet den Anruf
- **Route** — öffnet die Adresse in der Karten-App
- **Druck-Layout** — `Strg`/`Cmd` + `P` ergibt eine saubere Papier-Version

---

## QR-Code

Im Ordner [`qr/`](qr/):

| Datei | Wofür |
|---|---|
| `speisekarte-qr.svg` | Vektor mit Logo — **für den Druck** (Plakate, Schilder, beliebig skalierbar) |
| `speisekarte-qr.png` | 1960 px mit Logo — für Web, WhatsApp, Social Media |
| `speisekarte-qr-plain.svg` / `.png` | dieselben Codes ohne Logo — maximale Scan-Sicherheit |
| `tischaufsteller.html` | A4-Seite → gefaltet ein beidseitiger Tischaufsteller |
| `aufkleber.html` | A4-Seite mit 8 Kärtchen zum Ausschneiden oder als Aufkleber |
| `url.txt` | die Adresse, die im QR-Code steckt |

Die Druckvorlagen im Browser öffnen und über `Datei → Drucken` ausgeben
(A4, Skalierung 100 %, **Hintergrundgrafiken aktivieren**).

Alle Codes nutzen Fehlerkorrektur-Stufe **H** (30 %), damit das Logo in der Mitte nichts
kaputt macht. Sie wurden bis hinunter zu 80 px bzw. 30 mm Druckgröße gegengeprüft.

### QR-Code neu erzeugen

Nötig, sobald sich die Adresse ändert — zum Beispiel bei einer eigenen Domain:

```bash
pip install segno pillow
python3 qr/generate_qr.py --url https://www.akpinar-altoetting.de/
```

---

## Speisekarte pflegen

Alle Inhalte stehen in **einer** Datei: [`assets/data/menu.json`](assets/data/menu.json).
Die Seite selbst muss dafür nicht angefasst werden.

Ein Gericht sieht so aus:

```json
{
  "nr": "14",
  "name": "Döner-Pizza",
  "beschreibung": "Dönerfleisch, Zwiebeln",
  "zusatz": [],
  "preise": ["9,50", "12,50", "23,50"]
}
```

- `preise` hat so viele Einträge, wie die Kategorie Preisspalten hat
  (Pizza: Ø 28 / Ø 32 / Ø 50). `null` bedeutet „gibt es in dieser Größe nicht“ und
  wird als „–“ angezeigt.
- `zusatz` sind die hochgestellten Kennziffern der gedruckten Karte, z. B. `["1","2","3"]`.
- Preise werden als Text gepflegt (`"9,50"`), damit das deutsche Komma erhalten bleibt.

Nach dem Bearbeiten committen und pushen — der Rest passiert automatisch.

### Öffnungszeiten und Saison

`oeffnungszeiten.sommerVon` / `sommerBis` legen fest, welche Spalte als „aktuell“ gilt
und woraus die Status-Anzeige rechnet. Voreingestellt ist **April bis Oktober = Sommer**.
Steht in der gedruckten Karte kein Umstellungsdatum, ist das eine Annahme — bei Bedarf
einfach die beiden Zahlen ändern.

---

## Veröffentlichen

Die Seite liegt als statisches HTML im Repository und wird bei jedem Push auf `main`
über GitHub Actions veröffentlicht ([`.github/workflows/pages.yml`](.github/workflows/pages.yml)).

### Hosting bei Cloudflare Pages (empfohlen)

Cloudflare Pages liefert auch **private** Repositories kostenlos aus und erlaubt
einen eigenen Projektnamen als Adresse.

Einmalig einzurichten:

1. Konto anlegen auf <https://dash.cloudflare.com/sign-up> (kostenlos)
2. *Workers & Pages* → *Create* → *Pages* → *Connect to Git*
3. GitHub verbinden und dieses Repository auswählen
4. Projektname vergeben — er bestimmt die Adresse:
   `<projektname>.pages.dev`
5. Build-Einstellungen: **Framework preset** auf *None*,
   **Build command** leer lassen, **Build output directory** auf `/`
6. *Save and Deploy*

Die Seite ist danach unter `<projektname>.pages.dev` erreichbar und wird bei
jedem Push auf `main` neu veröffentlicht.

Anschließend die Adresse im Projekt umstellen und die Druckvorlagen neu
erzeugen:

```
python3 tools/set-site-url.py https://<projektname>.pages.dev/
python3 qr/generate_qr.py
```

Die Datei [`_headers`](_headers) steuert dabei das Caching und wird von
Cloudflare automatisch berücksichtigt.

### Eigene Domain

Ohne gekaufte Domain gehört die Adresse immer dem Hoster — `.pages.dev` bei
Cloudflare, `.github.io` bei GitHub. Endungen wie `.speisekarte` existieren
nicht; der Teil nach dem letzten Punkt muss eine registrierte Endung sein.

Passende echte Endungen für ein Lokal sind etwa `.menu`, `.pizza`, `.bayern`
oder schlicht `.de`. Eine eigene Domain kostet je nach Endung rund 10–30 Euro
im Jahr und hat einen praktischen Vorteil: Sie bleibt bei einem Hosterwechsel
gleich — **gedruckte QR-Codes behalten ihre Gültigkeit.**

Einrichtung: Domain beim Anbieter kaufen, in Cloudflare unter
*Workers & Pages* → Projekt → *Custom domains* eintragen, dann wieder
`tools/set-site-url.py` und `qr/generate_qr.py` laufen lassen.

### Hosting bei GitHub Pages (aktuell aktiv)

**Voraussetzung: Das Repository muss öffentlich sein.** GitHub Pages ist im
Free-Plan nur für öffentliche Repositories verfügbar.

**Einmalig nötig:** unter *Settings → Pages* bei *Source* **„GitHub Actions"**
auswählen. Diesen Schritt kann der Workflow nicht selbst übernehmen — der
`GITHUB_TOKEN` darf mit `pages: write` zwar auf eine bestehende Pages-Site
deployen, aber keine neue anlegen.

Danach läuft jeder Push auf `main` automatisch live.


Eigene Domain bei GitHub Pages: Datei `CNAME` im Wurzelverzeichnis anlegen mit
der Domain als Inhalt, beim Anbieter einen CNAME-Eintrag auf
`omxr9938.github.io` setzen, danach `tools/set-site-url.py` und
`qr/generate_qr.py` laufen lassen.

---

## Lokal ansehen

```bash
python3 -m http.server 8000
# dann http://localhost:8000 öffnen
```

Ein einfacher Doppelklick auf `index.html` reicht nicht — die Speisekarte wird per
`fetch` geladen, und das verlangt einen echten Webserver.

---

## Aufbau

```
index.html                  Grundgerüst der Seite
assets/css/styles.css       Gestaltung (dunkel, Gold, Rot — wie die gedruckte Karte)
assets/js/app.js            baut die Seite aus menu.json auf, Suche und Navigation
assets/data/menu.json       ← hier stehen alle Gerichte und Preise
assets/img/logo.webp        Logo für die Seite (Kopfbereich)
assets/img/logo-small.webp  Logo für den Fuß und die Kärtchen
assets/img/logo-original.jpg  Logo im Original, unbearbeitet
assets/img/emblem-180.png   Emblem als App-Icon, favicon-32.png als Favicon
assets/img/                 Fotos und Hintergrund, aus der PDF-Karte übernommen
qr/                         QR-Codes, Druckvorlagen und das Erzeugungs-Skript
```

Kein Framework, kein Build-Schritt, keine externen Abhängigkeiten zur Laufzeit außer den
Schriften von Google Fonts (mit System-Schriften als Rückfallebene).

---

## Logo

Das Logo liegt unbearbeitet als `assets/img/logo-original.jpg` bei. Für die Seite ist
sein Hintergrund auf exaktes Schwarz gezogen und es wird per `mix-blend-mode: screen`
eingebunden — dadurch verschwindet der schwarze Hintergrund auf jedem dunklen Untergrund
restlos, ohne dass die schwarzen Flächen **innerhalb** des goldenen Rahmens ausgestanzt
werden müssten. Im Druck wird das Blending abgeschaltet; dort erscheint das Logo als
schwarzes Schild auf weißem Papier.

Ein neues Logo einbauen: Bild als `assets/img/logo.webp` (Kopf) und
`assets/img/logo-small.webp` (Fuß) ablegen — am besten wieder mit schwarzem Hintergrund,
damit das Blending greift.

---

## Hinweise

- Die **Zusatzstoff-Kennzeichnung** (die hochgestellten Ziffern) ist in der gedruckten
  Karte nicht ausgeschrieben. Die Seite verweist deshalb auf den Aushang im Lokal.
  Sobald die Legende vorliegt, gehört sie unter `zusatzstoffe` in die `menu.json`.
- Die **Allergenliste** ist vollständig aus der gedruckten Karte übernommen.
- Alle Preise stammen aus der Karte mit Stand **September 2026**.
