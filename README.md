# ProfitEMS dla Home Assistant, wersja rozszerzona

Propozycja rozwoju integracji [ProfitEMS](https://profitems.pl): co jeszcze może pokazać Home Assistant i jak może to wyglądać. Dane instalacji z bramką EMS Connect trafiają do Home Assistant jako czujniki, liczniki energii, kalendarz planu i własna karta do dashboardu. Wszystko korzysta z obecnego API ProfitEMS, bez żadnych zmian po stronie serwera.

Integracja tylko odczytuje dane. Nie steruje falownikiem ani magazynem energii: o ich pracy decyduje system ProfitEMS. Projekt nie jest powiązany z PROFITEMS Sp. z o.o.

**[Zobacz kartę w przeglądarce](https://gratak.github.io/profit_ems/demo/)**: demo na przykładowych danych, bez instalacji.

## Co dodaje względem oryginału

- **Karta do dashboardu** w czterech motywach (ProfitEMS, Diorama, Aurora, Foundation): przepływ energii, mapa cen RCE z planem pracy, bilans dnia i sygnały do automatyzacji. Motywy reagują na pogodę i porę dnia. Karta instaluje się razem z integracją.
- **Liczniki energii w kWh** do panelu Energia: produkcja, zużycie, pobór i oddawanie, ładowanie i rozładowanie magazynu.
- **Wartość energii wg RCE**: ile warta była energia oddana i pobrana, łącznie i dziś.
- **Praca magazynu**: co magazyn robił w ostatnich dniach, godzina po godzinie: kiedy się ładował, kiedy oddawał energię, ile kWh i po jakiej średniej cenie RCE.
- **Kalendarz z planem pracy**: każdy blok planu to wydarzenie, z blokami, które już minęły tego dnia.
- **Usługa `profitems.cheapest_window`**: wskazuje najtańszy czas na pracę urządzenia.
- **Ceny ze znacznikami czasu** w atrybucie `prices`, dla cen godzinowych i 15-minutowych, z poprawną obsługą zmiany czasu.
- **Rzadsze zapytania**: integracja pyta API tuż po nowym odczycie (co 5 minut), a nie co minutę.
- **Diagnostyka** do zgłoszeń błędów (bez klucza) i **komunikat w Naprawach**, gdy bramka nie ma połączenia ponad godzinę.
- **Blueprinty** gotowych automatyzacji.

Ta wersja ma tę samą nazwę wewnętrzną (`profitems`) co oficjalna integracja, więc nie da się zainstalować obu naraz. Do wypróbowania wystarczy jedna z nich.

## Wymagania

- Home Assistant 2026.3 lub nowszy
- Instalacja z bramką EMS Connect i konto w aplikacji ProfitEMS

## Instalacja

1. W HACS otwórz menu **Custom repositories** i dodaj `https://github.com/gratak/profit_ems` jako **Integration**.
2. Zainstaluj ProfitEMS i uruchom ponownie Home Assistant.
3. W aplikacji ProfitEMS wybierz **Konto → Moja instalacja → Dostęp dla Home Assistant → Utwórz klucz**. Klucz jest widoczny tylko raz.
4. W Home Assistant wybierz **Ustawienia → Urządzenia i usługi → Dodaj integrację → ProfitEMS** i wklej klucz.

Klucz przestaje działać po wyłączeniu w aplikacji, po zmianie lub resecie hasła do konta oraz po przypisaniu instalacji do innego właściciela. Home Assistant poprosi wtedy o nowy klucz.

## Karta

Po instalacji karta jest na liście kart jako **ProfitEMS**; nie trzeba dodawać zasobów. Wszystko ustawisz w edytorze wizualnym. W YAML:

```yaml
type: custom:profitems-card
theme: profitems          # profitems, diorama, aurora albo foundation
weather_entity: weather.dom
```

| Opcja | Domyślnie | Znaczenie |
|---|---|---|
| `theme` | `diorama` | Motyw: `profitems` (barwy i znak ProfitEMS), `diorama` (jasna scena domu), `aurora` (neonowe pierścienie), `foundation` (złote orbity) |
| `device` | pierwsza bramka | Bramka ProfitEMS, gdy masz kilka instalacji |
| `title` | Dom | Tytuł karty |
| `weather_entity` | pierwsza encja `weather.*` | Pogoda pokazywana w motywie: chmury, deszcz, śnieg, mgła, burza |
| `show_weather` | `true` | `false` wyłącza pogodę w motywie |
| `price_resolution` | `auto` | `hour` uśrednia ceny 15-minutowe do godzin |
| `show_status`, `show_moment`, `show_prices`, `show_value`, `show_history`, `show_signals` | `true` | Sekcje karty |
| `load_fonts` | `false` | `true` pobiera czcionki motywu z Google Fonts. Domyślnie karta używa czcionek urządzenia i z niczym się nie łączy |
| `language` | język Home Assistant | `pl` albo `en` |

Pora dnia w motywie Diorama wynika z położenia słońca (`sun.sun`). Karta czyta tylko encje Home Assistant i nie wysyła zapytań do ProfitEMS.

**Mapa cen i planu** pokazuje ceny RCE dziś i jutro, plan pracy systemu w kolorach trybów, bieżący moment i najtańszą godzinę. Najedź na słupek albo go dotknij, żeby zobaczyć cenę i tryb w tym okresie. Ceny 15-minutowe są rysowane jako cienkie słupki, z osią w godzinach.

**Praca magazynu** pokazuje na wykresie, w których godzinach magazyn się ładował (słupki w górę), a w których oddawał energię (w dół), na tle ceny RCE. Pod spodem jest lista okresów, np. „01:00–05:00 Ładowanie z sieci, +12,4 kWh, śr. 0,32 zł/kWh, −4,48 zł”. Kwota to wartość energii pobranej z sieci albo do niej oddanej, po cenie RCE netto. Historię zbiera integracja z odczytów co 5 minut, od chwili instalacji, i przechowuje 7 dni.

**Zysk dziś** karta bierze z ProfitEMS: to ta sama wartość co „Zysk dzisiaj” w aplikacji, z podziałem na zysk z paneli, z pracy systemu i ze sprzedaży, przeliczana co godzinę. Gdy ProfitEMS jej nie podaje (np. nieobsługiwana taryfa), karta pokazuje **bilans dnia wg RCE**, czyli szacunek: energia liczona z odczytów co 5 minut, wyceniona po cenie RCE netto z chwili odczytu, bez opłat dystrybucyjnych i podatków.

## Czujniki

| Czujnik | Znaczenie |
|---|---|
| Poziom baterii | Naładowanie magazynu energii, % |
| Produkcja z paneli, Zużycie domu | Moc, W |
| Moc sieci | Dodatnia: pobór z sieci, ujemna: oddawanie do sieci, W |
| Moc magazynu | Ujemna: ładowanie, dodatnia: rozładowanie, W |
| Nadwyżka z paneli | O ile produkcja przewyższa zużycie domu, W |
| Tryb pracy | Bieżący tryb; plan w atrybutach `plan` (reszta doby), `plan_today` (cała doba) i `plan_tomorrow` (jutro, od 22:00) |
| Cena RCE | Cena bieżącej godziny, zł/kWh netto; ceny w atrybutach `today` i `tomorrow`, z początkiem i końcem każdej godziny w `prices_today` i `prices_tomorrow`, oba dni razem w `prices` |
| Produkcja z paneli dziś, Zużycie domu dziś, Pobór z sieci dziś, Oddawanie do sieci dziś, Ładowanie magazynu dziś, Rozładowanie magazynu dziś | Liczniki energii z falownika od jego północy, kWh; do panelu Energia |
| Wartość energii dziś | Wartość energii od północy, liczona tak samo jak „Zysk dzisiaj” w aplikacji, zł; podział (z paneli, z systemu ProfitEMS, sprzedaż) w atrybutach |
| Energia … (szacunek) | Liczniki kWh wyliczane przez integrację z mocy co 5 minut, tylko dla liczników, których falownik nie podaje |
| Wartość energii oddanej (RCE), Wartość energii pobranej (RCE) | Narastająco w zł, wg ceny RCE; suma dzisiejsza w atrybucie `today` |
| Najtańsza godzina dziś; Najtańsza godzina dziś, początek | Godzina 0–23 i ten sam moment jako znacznik czasu |
| Magazyn teraz | Ładowanie, rozładowanie albo bez pracy; w atrybutach `hours` (godzina po godzinie z ostatnich 7 dni: energia, cena RCE, tryb, poziom naładowania) i `sessions` (okresy ładowania i rozładowania ze średnią ceną) |
| Dostępna nadwyżka z paneli, Magazyn pełny, Trwa najtańsza godzina, Praca wyspowa | Tak lub nie |
| Plan (kalendarz) | Bloki planu na dziś i jutro jako wydarzenia |
| Połączenie, Ostatni odczyt, Sterowanie aktywne | Dane diagnostyczne |

Które liczniki energii podaje falownik:

| Marka | Liczniki |
|---|---|
| Deye, Sofar, MUST | wszystkie sześć |
| FoxESS | produkcja, zużycie domu, pobór i oddawanie; bez ładowania i rozładowania magazynu |
| SolaX | tylko produkcja |

Liczniki, których falownik nie podaje, są dodawane jako wyłączone; zamiast nich integracja dodaje swój szacunek z odczytów mocy. Szacunek liczy energię od dodania integracji i przetrwa restart; przerwy dłuższe niż 15 minut są pomijane. Falownik zeruje swoje liczniki według własnego zegara, więc moment zerowania może różnić się od północy. „Wartość energii dziś” system ProfitEMS przelicza co godzinę. Ceny i plan nie są zapisywane w historii, żeby nie powiększać bazy danych.

Dane o pracy instalacji są aktualizowane co 5 minut. Podczas okresu nauki system tylko obserwuje instalację: tryb to „Obserwacja”, a plan jest pusty.

### Panel Energia

W **Ustawienia → Pulpity → Energia** wybierz:

- **Sieć elektryczna**: pobór z *Pobór z sieci dziś*, oddawanie do *Oddawanie do sieci dziś*. Jako cenę oddawania możesz wskazać *Cena RCE*.
- **Panele słoneczne**: *Produkcja z paneli dziś*.
- **Magazyn energii**: *Ładowanie magazynu dziś* i *Rozładowanie magazynu dziś*.

Jeśli falownik któregoś licznika nie podaje, wskaż zamiast niego czujnik z dopiskiem *(szacunek)*.

## Usługa: najtańszy czas

`profitems.cheapest_window` znajduje okres o najniższej średniej cenie RCE dla urządzenia pracującego przez podany czas. Niczego nie włącza; wynik wykorzystaj w automatyzacji.

```yaml
action: profitems.cheapest_window
data:
  duration: "02:00:00"
  day: any        # any (od teraz), today albo tomorrow
response_variable: okno
```

Odpowiedź: `found`, `start`, `end`, `average_price` i `prices` z cenami w wybranym oknie.

## Blueprinty

- [Urządzenie przy pełnym magazynie i nadwyżce](blueprints/automation/profitems/grzalka_przy_nadwyzce.yaml): np. grzałka, gdy magazyn jest pełny, a nadwyżka przekracza próg.
- [Uruchom urządzenie w najtańszym czasie](blueprints/automation/profitems/najtanszy_czas.yaml): codziennie planuje pracę na najtańsze godziny.

Import: **Ustawienia → Automatyzacje i sceny → Blueprinty → Importuj blueprint** i wklej adres pliku z GitHub.

Moc urządzeń dobierz do swojej instalacji i przepisów dotyczących jej pracy. Za działanie automatyzacji i podłączonych urządzeń odpowiada użytkownik.

## Zgłoszenia

Błędy i propozycje zgłaszaj w zakładce [Issues](https://github.com/gratak/profit_ems/issues). Dołącz diagnostykę: **Ustawienia → Urządzenia i usługi → ProfitEMS → ⋮ → Pobierz diagnostykę**. Klucz dostępu nie trafia do pliku.

## Licencja

[PolyForm Noncommercial 1.0.0](LICENSE). Pierwotna integracja ProfitEMS jest na licencji MIT, zobacz [LICENSE-MIT-PROFITEMS](LICENSE-MIT-PROFITEMS).

Nazwa i logo ProfitEMS należą do PROFITEMS Sp. z o.o.

## In English

Unofficial, extended ProfitEMS integration for Home Assistant, read-only. It adds a dashboard card with three themes (Diorama, Aurora, Foundation) that follow the weather, energy counters for the Energy dashboard, value at RCE prices, a plan calendar, a cheapest-window service and blueprints. License: PolyForm Noncommercial 1.0.0; the original ProfitEMS integration is MIT-licensed, see LICENSE-MIT-PROFITEMS.
