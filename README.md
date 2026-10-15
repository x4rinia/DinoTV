# DinoTV

DinoTV ist ein Kodi-Video-Add-on für **American Football**. Version 0.1.0 bietet einen NFL-Spielplan, transparente Sender- und Anbieterinformationen, Favoriten, Verlauf sowie die Wiedergabe eigener autorisierter HLS-, DASH-, M3U- und Kodi-Plugin-Quellen.

DinoTV enthält keine unautorisierten Pay-TV-Streams, keine Scraper für Zugangssperren und keine DRM- oder Geoblocking-Umgehung. Das Projekt ist ein unabhängiges Fanprojekt von X4rinia und nicht mit der NFL, ESPN, RTL, Sky, DAZN oder anderen genannten Anbietern verbunden.

## Kompatibilität

- Ziel und Metadatenprüfung: Kodi 21 „Omega“, Python 3, Fire TV und Android TV.
- Kodi 22: Die verwendeten Python-3- und Add-on-Schnittstellen sind statisch kompatibel; ein echter Kodi-22-Gerätetest steht noch aus.
- Bedienung: Kodi-native Listen und Dialoge, vollständig mit einer TV-Fernbedienung erreichbar.
- Ein Fire-TV-/Android-TV-Laufzeittest und echte Streamwiedergabe müssen noch auf einem Zielgerät bestätigt werden. Automatisierte Tests sind kein Ersatz dafür.

## Installation

Nach Veröffentlichung über GitHub Pages:

1. Lade [`repository.dinotv-0.1.0.zip`](https://x4rinia.github.io/DinoTV/addons/repository.dinotv/repository.dinotv-0.1.0.zip) herunter.
2. Öffne Kodi und aktiviere bei Bedarf unter **System → Add-ons** die Installation aus unbekannten Quellen.
3. Wähle **Add-ons → Aus ZIP-Datei installieren** und die Repository-ZIP.
4. Öffne **Aus Repository installieren → DinoTV Repository → Video-Add-ons → DinoTV**.
5. Installiere und starte DinoTV.

### Fire TV

Lade die Repository-ZIP mit einem vertrauenswürdigen Downloader oder über ein freigegebenes lokales Laufwerk auf das Fire TV. Merke dir den Download-Ordner. Erlaube Kodi in den Fire-TV-Einstellungen den Dateizugriff, wähle in Kodi **Aus ZIP-Datei installieren**, öffne den Download-Ordner und installiere die Datei. Danach erfolgt die DinoTV-Installation direkt über das Repository. Der komplette Betrieb benötigt keinen Entwicklungs-PC.

## Funktionen

- Hauptmenü: Live NFL, Spielplan, deutsche und US-Sender, NFL Network/RedZone, College Football, Highlights/Replays, Favoriten, eigene Streams und Einstellungen.
- NFL-Spielplan mit lokaler deutscher Zeit, Teams, Logos, Status, Ergebnissen und nur tatsächlich von der Datenquelle gelieferten Broadcast-Angaben.
- Spielauswahl zeigt bekannte offizielle Anbieterwege; unbekannte Senderzuordnungen bleiben ausdrücklich unbekannt.
- Lokale Lieblingssender, Lieblingsmannschaften, Verlauf und individuelle Senderreihenfolge.
- Import einer lokalen M3U-Datei sowie manuell angelegte HTTPS-HLS-/DASH- oder `plugin://`-Quellen.
- Prüfung von URL-Schema, Abhängigkeiten, Netzwerk-Timeouts und verständliche Fehlermeldungen.
- Sicherer Export von Favoriten/Reihenfolge ohne persönliche URLs, Zugangsdaten oder Verlauf.

## Quellenstatus

Der eingebaute Katalog verwendet diese klaren Zustände:

- **Offizieller externer Anbieter:** offizielle Webseite, keine von DinoTV behauptete Direktwiedergabe.
- **Zugang oder Abo erforderlich:** offizieller Weg mit Anbieterzugang und gegebenenfalls regionalen Rechten.
- **Direkt in Kodi abspielbar:** nur eine vom Benutzer selbst hinterlegte, autorisierte Quelle.
- **Derzeit nicht unterstützt:** keine sichere/rechtlich klare Integration.

RTL/RTL+, NITRO, Sky/WOW, DAZN Game Pass, FOX, CBS/Paramount+, NBC/Peacock, ESPN, Prime Video, NFL Network, RedZone und NFL+ sind als offizielle Zugangswege katalogisiert. SportsHD, DaddyLive und NFLbite werden wegen unklarer Rechte nicht verlinkt, gescrapt oder abgespielt. Es werden keine erfundenen Sender-URLs ausgeliefert.

## Eigene Streams

Unter **Eigene Streams** kann eine autorisierte URL hinzugefügt werden. Netzwerkstreams müssen HTTPS verwenden. Unterstützt werden `.m3u8`, `.mpd`, `.m3u` und Kodi-`plugin://`-URLs. DASH benötigt das Kodi-Add-on InputStream Adaptive. Alternativ kann in den Einstellungen eine lokale M3U-Datei ausgewählt werden; unsichere HTTP- und unbekannte Formate werden übersprungen.

Persönliche Quellen liegen ausschließlich in Kodis Add-on-Profilordner (`userdata.json`) und gehören nicht ins Git-Repository. Zugangsdaten sollten nicht in URLs eingebettet werden.

## NFL-Spielplandaten

DinoTV nutzt den öffentlich erreichbaren ESPN-Scoreboard-Endpunkt ohne API-Schlüssel und speichert Antworten 30 Minuten lokal zwischen. Dies ist keine vertraglich garantierte API; bei Ausfall wird ein vorhandener Cache angezeigt. Übertragungszuordnungen werden nur übernommen, wenn der Endpunkt sie liefert. Daten können verzögert oder unvollständig sein.

## Entwicklung und Tests

```powershell
python -m unittest discover -s tests -v
python -m compileall -q plugin.video.dinotv
python tools/build_repository.py
python tools/check_live_schedule.py
```

Der Paketbau erzeugt `addons/addons.xml`, `addons/addons.xml.md5`, beide versionierten ZIPs und die Repository-Assets. Tests prüfen XML, ZIP-Hierarchie, Senderkatalog, fehlerhafte URLs, M3U, Favoriten/Verlauf, sicheren Export, Spielplanparser und Kodi-Hauptmenü-Routing mit lokaler API-Simulation. Der optionale Live-Check prüft nur den Spielplan-Endpunkt – niemals Videowiedergabe.

## Veröffentlichung und Updates

Der Workflow testet und baut jeden Push auf `main`, veröffentlicht GitHub Pages und erstellt bei einem Tag wie `v0.1.0` zusätzlich ein GitHub Release mit beiden ZIPs. In den Repository-Einstellungen muss einmalig **Settings → Pages → Source: GitHub Actions** ausgewählt werden. Danach bedient Kodi Updates über:

- Repository-Index: `https://x4rinia.github.io/DinoTV/addons/addons.xml`
- Installer: `https://x4rinia.github.io/DinoTV/addons/repository.dinotv/repository.dinotv-0.1.0.zip`

Vor einem Release müssen die Versionen in beiden `addon.xml`-Dateien und `CHANGELOG.md` angepasst werden. Der Workflow verwendet nur das automatisch bereitgestellte `GITHUB_TOKEN`; es sind keine Zugangsdaten im Projekt nötig.

## Fehlerbehebung

- **Spielplan leer:** Netzwerk prüfen und über Einstellungen aktualisieren; möglicherweise gibt es im gewählten Zeitraum keine Spiele.
- **Externer Link öffnet nicht:** Die Option für externe Links aktivieren und auf Android eine Browser-/Anbieter-App installieren.
- **DASH startet nicht:** InputStream Adaptive in Kodi installieren und aktivieren.
- **Eigene Quelle abgelehnt:** HTTPS und eine unterstützte Endung beziehungsweise eine korrekte `plugin://`-URL verwenden.
- **Stream nicht erreichbar:** Quelle außerhalb Kodi prüfen und einen autorisierten alternativen Anbieter wählen. DinoTV umgeht keine Sperren.

## Recht und Datenschutz

Marken, Logos und Programmdaten gehören ihren jeweiligen Inhabern. Nutzer sind für Berechtigung, Abo, Standortregeln und selbst eingetragene URLs verantwortlich. DinoTV überträgt keine Favoriten, Verläufe oder persönlichen Quellen an einen eigenen Server. Teamlogos und Spielplandaten werden zur Laufzeit von der Spielplandatenquelle geladen.

Lizenz: [MIT](LICENSE)
