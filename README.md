# ProfitEMS dla Home Assistant, wersja rozszerzona

Nieoficjalna, rozbudowana wersja integracji [ProfitEMS](https://profitems.pl). Dane instalacji z bramką EMS Connect trafiają do Home Assistant jako czujniki, liczniki energii, kalendarz planu i własna karta do dashboardu.

Integracja tylko odczytuje dane. Nie steruje falownikiem ani magazynem energii: o ich pracy decyduje system ProfitEMS. Projekt nie jest powiązany z PROFITEMS Sp. z o.o.

**[Zobacz kartę w przeglądarce](demo/index.html)**: demo na przykładowych danych, bez instalacji. Otwórz plik `demo/index.html` z repozytorium.

## Co dodaje względem oryginału

- **Karta do dashboardu** w trzech motywach (Diorama, Aurora, Foundation): przepływ energii, mapa cen RCE z planem pracy, bilans dnia i sygnały do automatyzacji. Motywy reagują na pogodę i porę dnia. Karta instaluje się razem z integracją.
- **Liczniki energii w kWh** do panelu Energia: produkcja, zużycie, pobór i oddawanie, ładowanie i rozładowanie magazynu.
- **Wartość energii wg RCE**: ile warta była energia oddana i pobrana, łącznie i dziś.
- **Kalendarz z planem pracy**: każdy blok planu to wydarzenie, z blokami, które już minęły tego dnia.
- **Usługa `profitems.cheapest_window`**: wskazuje najtańszy czas na pracę urządzenia.
- **Ceny ze znacznikami czasu** w atrybucie `prices`, dla cen godzinowych i 15-minutowych, z poprawną obsługą zmiany czasu.
- **Rzadsze zapytania**: integracja pyta API tuż po nowym odczycie (co 5 minut), a nie co minutę.
- **Diagnostyka** do zgłoszeń błędów (bez klucza) i **komunikat w Naprawach**, gdy bramka nie ma połączenia ponad godzinę.
- **Blueprinty** gotowych automatyzacji.

Jeśli używasz oryginalnej integracji, ta wersja ją zastępuje: ma tę samą domenę `profitems`, więc istniejące encje i automatyzacje zostają.

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
theme: diorama            # diorama, aurora albo foundation
weather_entity: weather.dom
```

| Opcja | Domyślnie | Znaczenie |
|---|---|---|
| `theme` | `diorama` | Motyw: `diorama` (jasna scena domu), `aurora` (neonowe pierścienie), `foundation` (złote orbity) |
| `device` | pierwsza bramka | Bramka ProfitEMS, gdy masz kilka instalacji |
| `title` | Dom | Tytuł karty |
| `weather_entity` | pierwsza encja `weather.*` | Pogoda pokazywana w motywie: chmury, deszcz, śnieg, mgła, burza |
| `show_weather` | `true` | `false` wyłącza pogodę w motywie |
| `price_resolution` | `auto` | `hour` uśrednia ceny 15-minutowe do godzin |
| `show_status`, `show_moment`, `show_prices`, `show_value`, `show_signals` | `true` | Sekcje karty |
| `load_fonts` | `false` | `true` pobiera czcionki motywu z Google Fonts. Domyślnie karta używa czcionek urządzenia i z niczym się nie łączy |
| `language` | język Home Assistant | `pl` albo `en` |

Pora dnia w motywie Diorama wynika z położenia słońca (`sun.sun`). Karta czyta tylko encje Home Assistant i nie wysyła zapytań do ProfitEMS.

**Mapa cen i planu** pokazuje ceny RCE dziś i jutro, plan pracy systemu w kolorach trybów, bieżący moment i najtańszą godzinę. Najedź na słupek albo go dotknij, żeby zobaczyć cenę i tryb w tym okresie. Ceny 15-minutowe są rysowane jako cienkie słupki, z osią w godzinach.

**Bilans dnia wg RCE** to szacunek: energia liczona z odczytów co 5 minut, wyceniona po cenie RCE netto z chwili odczytu, bez opłat dystrybucyjnych i podatków. API ProfitEMS nie podaje zysku ani liczników energii, więc integracja wylicza je sama.

## Czujniki

| Czujnik | Znaczenie |
|---|---|
| Poziom baterii | Naładowanie magazynu energii, % |
| Produkcja z paneli, Zużycie domu | Moc, W |
| Moc sieci | Dodatnia: pobór z sieci, ujemna: oddawanie do sieci, W |
| Moc magazynu | Ujemna: ładowanie, dodatnia: rozładowanie, W |
| Nadwyżka z paneli | O ile produkcja przewyższa zużycie domu, W |
| Tryb pracy | Bieżący tryb; plan w atrybutach `plan` (reszta doby) i `plan_today` (cała doba) |
| Cena RCE | Cena bieżącej godziny, zł/kWh netto; ceny w atrybutach `today`, `tomorrow` i `prices` |
| Najtańsza godzina dziś; Najtańsza godzina dziś, początek | Godzina 0–23 i ten sam moment jako znacznik czasu |
| Energia z paneli, zużyta w domu, pobrana z sieci, oddana do sieci, ładowania i rozładowania magazynu | kWh, do panelu Energia; suma dzisiejsza w atrybucie `today` |
| Wartość energii oddanej (RCE), Wartość energii pobranej (RCE) | zł; suma dzisiejsza w atrybucie `today` |
| Dostępna nadwyżka z paneli, Magazyn pełny, Trwa najtańsza godzina, Praca wyspowa | Tak lub nie |
| Plan (kalendarz) | Bloki planu na dziś jako wydarzenia |
| Połączenie, Ostatni odczyt, Sterowanie aktywne | Dane diagnostyczne |

Liczniki energii liczą energię od dodania integracji i przetrwają restart. Przerwy dłuższe niż 15 minut (np. awaria bramki) są pomijane, bo moc w tym czasie jest nieznana. Ceny i plan nie są zapisywane w historii, żeby nie powiększać bazy danych.

### Panel Energia

W **Ustawienia → Pulpity → Energia** wybierz:

- **Sieć elektryczna**: pobór z *Energia pobrana z sieci*, oddawanie do *Energia oddana do sieci*. Jako cenę oddawania możesz wskazać *Cena RCE*.
- **Panele słoneczne**: *Energia z paneli*.
- **Magazyn energii**: *Energia ładowania magazynu* i *Energia rozładowania magazynu*.

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

Do użytku domowego i niekomercyjnego za darmo, na licencji [PolyForm Noncommercial 1.0.0](LICENSE). **Użycie komercyjne, w tym sprzedaż, dołączanie do produktu lub usługi EMS i udostępnianie klientom, wymaga płatnej licencji od autora.** Pierwotna integracja ProfitEMS, na której ta wersja się opiera, jest na licencji MIT. Szczegóły w [NOTICE.md](NOTICE.md).

Nazwa i logo ProfitEMS należą do PROFITEMS Sp. z o.o.

## In English

Unofficial, extended ProfitEMS integration for Home Assistant, read-only. It adds a dashboard card with three themes (Diorama, Aurora, Foundation) that follow the weather, energy counters for the Energy dashboard, value at RCE prices, a plan calendar, a cheapest-window service and blueprints. Free for personal and noncommercial use under the PolyForm Noncommercial License 1.0.0; commercial use requires a paid license from the author, see NOTICE.md.
