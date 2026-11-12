# Lowlevel-Mailinglisten

Hier bleiben die alten Diskussionen und Patches aus **tyndur-devel** und
**cdi-devel** erhalten. Das Archiv ist schreibgeschützt, nach Monaten und
Diskussionsfäden durchstöberbar und mit Pagefind durchsuchbar. Die Suche lässt
sich nach Mailingliste und Jahr filtern.

## Inhalt und Herkunft

Die älteren Daten stammen aus der neueren Kopie `mailman` der alten Mailman-Installation.
Die späteren Nachrichten aus dem mlmmj-Archiv liegen als Original-E-Mails unter
`messages/`, mit Prüfsummen in `messages-manifest.json`.
Die ursprünglichen öffentlichen Pipermail-Seiten, Monatsdownloads und Anhänge
liegen unter `archives/`; ihre Prüfsummen stehen in `source-manifest.json`.
Interne Mailman-Datenbanken, Zugangsdaten, Abonnentenlisten und Warteschlangen
gehören nicht zu diesem Repository.

| Liste | Zeitraum | Nachrichtenseiten |
| --- | --- | ---: |
| tyndur-devel | Oktober 2007 bis Mai 2021 | 2.697 |
| cdi-devel | August 2009 bis Mai 2017 | 401 |

Die ältere Kopie `mailman_backup` endet am 2. Mai 2009. Alle 833 Nachrichten-IDs
und sämtliche Anhänge dieser Kopie sind auch in der neueren enthalten. Der
Vergleich ist in `source-comparison.json` dokumentiert.

Aus mlmmj kommen 77 zusätzliche `tyndur-devel`-Nachrichten von 2020 und 2021
hinzu. Die 2.589 älteren `tyndur-devel`- und alle 401 `cdi-devel`-Nachrichten
wurden anhand ihrer `Message-ID` erkannt und nicht doppelt importiert. Die 31
nur in den Mailman-Seiten enthaltenen Nachrichten bleiben erhalten. Der
Importbericht steht in `mlmmj-import.json`. Insgesamt enthält das Archiv
**3.098 Nachrichtenseiten**. Crossposts bleiben in jeder betroffenen Liste
verfügbar.

Die erhaltenen HTML-Seiten sind vollständiger als die Roh-Mailboxen:
`tyndur-devel.mbox` enthält nur 2.589 Nachrichten. Deshalb verwenden wir die
Pipermail-Seiten als Grundlage. 14 dieser Seiten haben bereits im Original
keinen Nachrichtentext; sie bleiben mit ihrem Betreff und ihrer Navigation
erhalten.

Der Build führt beide Quellen in einem gemeinsamen Nachrichtenformat zusammen
(`build/messages.jsonl`). Jede Nachricht enthält dieselben Felder für Betreff,
Autor, Datum, Nachrichtentext, Antworten, Anhänge und Quelldatei. Daraus entstehen
für alle Jahrgänge dieselben deutschen Nachrichtenseiten, Monatsübersichten und
Sortierungen nach Diskussionsfaden, Datum, Betreff und Autor. Es gibt keine
getrennten Bereiche für Mailman und mlmmj.

Die ursprünglichen Diskussionsfäden werden aus den Pipermail-Indizes übernommen;
neuere Antworten werden anhand ihrer E-Mail-Referenzen zugeordnet. Die Navigation
zur vorherigen und nächsten Nachricht sowie zum vorherigen und nächsten Monat
umfasst beide Quellen. Ursprüngliche Nachrichtentexte, Patches, Anhangspfade und
Links auf Nachrichten oder Indexanker bleiben erhalten. Anhänge und
Monatsdownloads werden bytegenau übernommen. Für die späteren Nachrichten gibt
es zusätzlich den Download der Original-E-Mail.

## GitHub Pages

Dieses Verzeichnis ist ein eigenständiges Git-Repository. Nach dem Push in ein
GitHub-Repository unter **Settings → Pages → Build and deployment → Source**
**GitHub Actions** auswählen. Der Workflow baut und prüft das Archiv bei jedem
Push auf `main` und veröffentlicht `site/`.

Alle lokalen Links funktionieren auch unter einem Projektpfad wie
`https://lowlevel-eu.github.io/mailinglisten-archiv/`. Der Repositoryname kann
anders lauten; die Navigation und Suche ermitteln ihren Basispfad selbst.

## Lokal bauen

Voraussetzungen: Python ab 3.10 und Node.js ab 20.

```sh
npm ci
npm test
npm run build
python3 scripts/verify.py
node tests/search-smoke.mjs
python3 -m http.server --directory site 8000
```

Danach ist das Archiv unter `http://localhost:8000/` erreichbar. `site/`,
`build/` und `node_modules/` werden nicht eingecheckt. Die Prüfung vergleicht
alle Nachrichtentexte und Quelldateien, kontrolliert interne Links samt Ankern
und testet Suchergebnisse mit einem GitHub-Pages-Projektpfad.

Weitere mlmmj-Nachrichten lassen sich aus dem **öffentlichen Archivverzeichnis**
(Unterverzeichnisse `tyndur-devel/` und `cdi-devel/` mit nummerierten E-Mails)
importieren:

```sh
python3 scripts/import_mlmmj.py ../mlmmj/archives
npm run build
python3 scripts/verify.py
node tests/search-smoke.mjs
```

Der Import überspringt bereits vorhandene Nachrichten und bricht ab, wenn er
veränderte Originale überschreiben oder früher importierte Nachrichten entfernen
würde. Verzeichnisse mit Abonnenten- oder Verwaltungsdaten werden nicht gelesen.
