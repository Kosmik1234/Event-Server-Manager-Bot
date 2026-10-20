# Event Server Manager Bot

Bot Discord (Python, [discord.py](https://discordpy.readthedocs.io/) ≥ 2.6) do zarządzania serwerem poświęconym wydarzeniom. Zasada jest jedna: **każdy kanał tekstowy w skonfigurowanej kategorii wydarzeń = jedno wydarzenie.**

## Jak to działa

1. **Powstaje kanał w kategorii wydarzeń** – przez `/create-event` albo ręcznie przez moderatora. Bot automatycznie:
   - tworzy w nim **prywatny wątek uczestników** `<nazwa-kanału>-participants` (po polsku `-uczestnicy`), slowmode 5 min, bez możliwości zapraszania innych przez uczestników,
   - wysyła i przypina **wiadomość z przyciskami Join / Leave** oraz licznikiem `👥 Uczestnicy: N`.
2. **Join** dodaje użytkownika do wątku – tam trafiają informacje o zmianach daty, miejsca itp. **Leave** usuwa go z wątku. Nikt nie jest dodawany automatycznie (także twórca wydarzenia).
3. **Licznik** = liczba członków wątku minus bot. Aktualizują go zdarzenia Discorda o zmianie członkostwa wątku, więc liczy poprawnie także ręczne dodanie/usunięcie kogoś w interfejsie Discorda.
4. **Archiwizacja** – co godzinę (i raz po starcie) kanały wydarzeń, których data już minęła, są przenoszone do kategorii-archiwum przypisanej do ich kategorii wydarzeń. W dniu wydarzenia kanał jeszcze zostaje.
5. **Odzyskiwanie danych** – jeśli plik z danymi wydarzeń zginie, bot przy starcie odtwarza rekordy na podstawie samego Discorda (wątek, przypięta wiadomość, embed ogłoszenia).

Wiadomości bota są po angielsku lub po polsku – język ustawia się per serwer.

## Komendy

Komendy zmieniające cokolwiek (wszystkie poza `/get-date` i `list`) wymagają uprawnienia **Administrator** albo roli z `MODERATOR_ROLE`. Domyślnie są też ukryte dla zwykłych członków (wymagają Manage Server w pickerze komend).

| Komenda | Opis |
|---|---|
| `/create-event title date location description` | Tworzy kanał wydarzenia w pierwszej (wg kolejności na serwerze) istniejącej kategorii wydarzeń i publikuje embed z ogłoszeniem. @everyone widzi kanał, ale nie może pisać ani tworzyć wątków. `date` to dowolny tekst; jeśli bot nie umie z niego odczytać daty, ostrzega, że wydarzenie nie będzie archiwizowane. |
| `/make-event` | Naprawcza: robi wydarzenie z bieżącego kanału (musi leżeć w kategorii wydarzeń) – np. kanału sprzed dodania bota albo przeniesionego do kategorii. Jeśli wątek wydarzenia został usunięty, tworzy go od nowa. |
| `/set-date date` | Ustawia datę wydarzenia. Działa w kanale wydarzenia lub w jego wątku. Aktualizuje embed ogłoszenia, jeśli istnieje. Dzięki niej archiwizować da się też kanały utworzone ręcznie. |
| `/get-date` | Dostępna dla wszystkich. Pokazuje (tylko wywołującemu) datę wydarzenia i jak bot ją odczytał – czyli datę, której używa archiwizacja – albo ostrzeżenie, że jest nieczytelna. Działa w kanale wydarzenia lub w jego wątku; komunikat „Use this command in an event channel…” oznacza, że bot nie ma rekordu tego kanału. |
| `/set-field key [value]` | Ustawia (lub czyści, gdy brak wartości) własne pole wydarzenia, np. `tickets`, używane w szablonie jako `{tickets}`. Działa w kanale wydarzenia lub w jego wątku. Nazwy `title`, `date`, `location`, `description` są zarezerwowane. |
| `/event-template edit\|show\|preview\|reset\|apply` | Format ogłoszeń per serwer – patrz [Szablon ogłoszenia](#szablon-ogłoszenia). |
| `/event-category add\|remove\|list` | Które kategorie są kategoriami wydarzeń (per serwer). `list` dostępne dla wszystkich. Usunięcie kategorii kasuje też jej powiązanie z archiwum. |
| `/archive-category add\|remove\|list` | Mapowanie *kategoria wydarzeń → kategoria archiwum*. Każda kategoria wydarzeń ma maks. jedno archiwum, kilka może dzielić to samo. Kategoria nie może być jednocześnie kategorią wydarzeń i archiwum. `list` dostępne dla wszystkich. |
| `/language` | Język bota na serwerze: English / Polski. Bez ustawienia bot używa języka serwera z ustawień Discorda (polski → `pl`, wszystko inne → `en`). |

### Szablon ogłoszenia

Wygląd embeda z ogłoszeniem to szablon tekstowy z placeholderami, renderowany do opisu embeda. Każdy serwer może mieć własny; domyślny (`templates.py`) odtwarza dawny wygląd – tytuł, opis, potem „Kiedy” i „Gdzie” (z etykietami w języku serwera):

```
# {title}
{description}

**📅 Kiedy:** {date}
**📍 Gdzie:** {location}
```

- `/event-template edit` – otwiera okno z wieloliniowym edytorem (parametry komend slash nie pozwalają na entery), wypełnione obecnym szablonem.
- `/event-template show` – pokazuje aktualny szablon, `preview` – podgląd z przykładowymi danymi, `reset` – powrót do domyślnego.
- `/event-template apply` – przerenderowuje istniejące ogłoszenia (szablon zmienia tylko nowe i edytowane, dopóki go nie użyjesz).
- Placeholdery: `{title}`, `{date}`, `{location}`, `{description}` oraz dowolne `{klucz}` (małe litery, cyfry, `_`) – pole własne, ustawiane per wydarzenie przez `/set-field` i trzymane w `Event.extra`.
- Styl, kolejność i widoczność pól wynikają z szablonu: markdown Discorda (`**pogrubienie**`, `*kursywa*`, `# nagłówek`), kolejność linii, a ukrycie pola = nieumieszczenie go w szablonie.
- **Linia, w której wszystkie placeholdery są puste, jest pomijana** – wydarzenie bez linku do biletów nie pokaże „🎟 Bilety:” z pustą wartością.
- Wartości są podstawiane bez `str.format`, więc nawiasy klamrowe w opisie niczego nie psują. Wynik jest obcinany do 4096 znaków (limit opisu embeda).

### Format daty

Rozpoznawane formaty: `15.11.2026` (też `5.1.2026`) i `2026-11-15`. Godziny są ignorowane. Jeśli w tekście jest kilka dat, liczy się **najpóźniejsza** – zakres `15-16.11.2026` kończy się 16-go. Data porównywana jest z dzisiejszą datą w strefie `TIMEZONE`.

## Pierwsze uruchomienie na serwerze

1. Zaproś bota z uprawnieniami: **Manage Channels, Manage Threads, Create Private Threads, Send Messages, Send Messages in Threads, Embed Links, Manage Messages** (to ostatnie do przypinania).
2. `/event-category add <kategoria>` – wskaż kategorię wydarzeń.
3. Opcjonalnie `/archive-category add <kategoria wydarzeń> <kategoria archiwum>`.
4. Opcjonalnie `/language`.
5. `/create-event …` albo po prostu utwórz kanał w kategorii wydarzeń.

> Moderator bez uprawnienia Manage Threads nie widzi prywatnego wątku, dopóki sam nie kliknie Join.

## Instalacja i uruchomienie

Wymagany Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # uzupełnij token
python main.py
```

W [Discord Developer Portal](https://discord.com/developers/applications) → Bot → *Privileged Gateway Intents* trzeba włączyć **Server Members Intent** – bez niego bot nie wystartuje (jest potrzebny do śledzenia członków wątków).

### Zmienne środowiskowe

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `DISCORD_BOT_TOKEN` | – (wymagana) | Token bota. |
| `MODERATOR_ROLE` | `Moderator` | Nazwa **lub** ID roli, która (obok administratorów) może używać komend. |
| `DEV_GUILD_ID` | puste | ID serwera testowego. Jeśli ustawione, komendy synchronizują się tylko tam, ale natychmiast; bez niego globalnie (do godziny opóźnienia). |
| `EVENTS_FILE` | `data/events.json` | Plik z rekordami wydarzeń. |
| `GUILD_SETTINGS_FILE` | `data/guild_settings.json` | Plik z ustawieniami serwerów (kategorie, archiwa, język). |
| `TIMEZONE` | `Europe/Warsaw` | Strefa czasowa (nazwa IANA) do decydowania, czy data minęła. |

### Deploy (Railway)

`Procfile` uruchamia `worker: python main.py`. Zmienne ustawia się w zakładce Variables. **Pliki danych muszą leżeć na zamontowanym Volume** (np. `EVENTS_FILE=/data/events.json`, `GUILD_SETTINGS_FILE=/data/guild_settings.json`), inaczej znikają przy każdym deployu. Rekordy wydarzeń bot częściowo odtworzy (patrz niżej), ale ustawień serwerów – nie.

## Architektura

| Plik | Rola |
|---|---|
| `main.py` | Klasa `EventBot`: intenty, ładowanie cogów, synchronizacja komend, `bot.lang(guild)` (wybór języka). |
| `config.py` | Odczyt zmiennych środowiskowych (`.env` lokalnie). |
| `storage.py` | Dataclass `Event`, interfejs `EventStore`, implementacja `JsonEventStore`. |
| `guild_settings.py` | `GuildSettingsStore` – ustawienia per serwer w JSON. |
| `checks.py` | `is_admin_or_mod()` – sprawdzenie uprawnień do komend. |
| `dates.py` | `parse_event_date(text)` – odczyt daty z wolnego tekstu. |
| `i18n.py` | Teksty `en`/`pl`, `t(lang, key, **kw)`, `from_locale`. |
| `templates.py` | Domyślny szablon ogłoszenia, `render_template`, walidacja. |
| `cogs/events.py` | `/create-event`, `/make-event`, `/set-date`, `/get-date`, `/set-field`, `build_embed`, `refresh_announcement`. |
| `cogs/event_template.py` | `/event-template` (edit/show/preview/reset/apply). |
| `cogs/settings.py` | `/event-category`, `/archive-category`, `/language`. |
| `cogs/auto_thread.py` | `setup_event_channel` (wątek + przypięta wiadomość + rekord), listener tworzenia kanału, listenery licznika. |
| `cogs/join.py` | Przyciski Join/Leave, `update_participant_count`. |
| `cogs/archive.py` | `ArchiveSweepCog` – godzinna pętla archiwizacji. |
| `cogs/recovery.py` | Odtwarzanie rekordów przy starcie. |

### Dane

**Rekord wydarzenia** (`Event`, klucz = ID kanału): `channel_id`, `guild_id`, `title`, `date` (tekst), `location`, `description`, `creator_id`, `message_id` (embed ogłoszenia), `thread_id`, `join_message_id` (przypięta wiadomość z przyciskami), `extra` (słownik pól własnych do szablonu).

Kanały utworzone ręcznie dostają tylko `title` = nazwa kanału i pustą datę – nie są archiwizowane, dopóki ktoś nie użyje `/set-date`.

**Ustawienia serwera** (klucz = ID serwera): `event_categories` (lista ID), `archives` (ID kategorii wydarzeń → ID archiwum), `language`, `event_template` (własny szablon ogłoszenia; brak = domyślny).

Oba pliki są zapisywane w całości przy każdej zmianie – wystarcza przy małej skali. Przejście na bazę danych = nowa klasa implementująca `EventStore` podmieniona w `main.py`.

### Przebieg `/create-event`

1. Utworzenie kanału z uprawnieniami (everyone: bez pisania; bot: pisanie, wątki, przypinanie).
2. Zapis rekordu – **przed** wysłaniem embeda, bo listener `on_guild_channel_create` startuje od razu i szuka rekordu, żeby dopisać do niego wątek.
3. Listener tworzy wątek i przypiętą wiadomość z przyciskami, dopisuje `thread_id` i `join_message_id`.
4. Wysłanie embeda wyrenderowanego z szablonu serwera, ponowny odczyt rekordu i dopisanie `message_id`.

### Przyciski

Przyciski są `DynamicItem`-ami z ID wątku w `custom_id` (`join-event:<thread_id>`, `leave-event:<thread_id>`), więc działają po restarcie bota bez zaglądania do bazy.

### Odzyskiwanie

Przy pierwszym `on_ready` bot przechodzi po kanałach w kategoriach wydarzeń, które nie mają rekordu. Dla każdego:
- szuka prywatnego wątku utworzonego przez bota (także zarchiwizowanego); brak wątku → kanał pomijany,
- czyta do 100 najstarszych wiadomości bota: wiadomość z przyciskiem `join-event:<id>` to `join_message_id`, pierwsza z embedem to ogłoszenie (`message_id`),
- zapisuje rekord i przelicza licznik.

`creator_id` jest nie do odzyskania. **Uwaga:** od wprowadzenia szablonów odzyskiwanie nie czyta już tytułu, daty ani miejsca z embeda (ogłoszenie nie ma już pól o stałej kolejności) – odtworzony rekord ma tytuł z nazwy kanału i puste pozostałe pola, a opis zawiera cały tekst ogłoszenia. Parsowanie embeda według szablonu serwera jest do zrobienia. Kanały już przeniesione do archiwum nie są odtwarzane (nie leżą w kategorii wydarzeń). Po zakończeniu bot wysyła event `events_recovered` – dopiero wtedy startuje pętla archiwizacji.

### Archiwizacja

Pętla pomija wydarzenia, gdy: data jest nieczytelna lub dziś/w przyszłości, kanał nie istnieje lub nie ma kategorii, kategoria nie ma archiwum albo archiwum zostało usunięte. Błędy przenoszenia (np. brak uprawnień, kategoria pełna – limit 50 kanałów) są tylko logowane.

## Testy

```bash
pip install -r requirements-dev.txt
pytest
```

Testy w `tests/` nie łączą się z Discordem. Czyste moduły (`dates`, `templates`, `storage`, `guild_settings`, `i18n`) są testowane wprost. Komendy slash, przyciski, modal szablonu, listenery i pętla archiwizacji – przez wywołanie ich funkcji bezpośrednio z atrapą `Interaction` (`tests/conftest.py`). Osobny test sprawdza, że każda komenda poza `/get-date` i `list` ma sprawdzenie uprawnień, jest ukryta dla zwykłych członków i działa tylko na serwerze, oraz że `custom_id` przycisków ma stały format.

Nie sprawdzają zachowania na prawdziwym serwerze: uprawnień bota, limitów Discorda, wyglądu wiadomości ani tego, czy atrapy zgadzają się z prawdziwym API.

## Praca z gałęziami

- **`main`** – stabilna wersja, z której bot jest wdrażany.
- **`develop`** – tu scalamy nowe funkcje. Każda powstaje na własnej gałęzi (`claude/<nazwa>`) odchodzącej od `develop` i wraca do `develop`.
- **`develop` → `main`** tylko wtedy, gdy `develop` jest stabilny: testy przechodzą (`pytest`) i zmiany sprawdzono na prawdziwym serwerze Discorda. Merge z `--no-ff`, żeby w razie problemów dało się go cofnąć: `git revert -m 1 <commit merge'a>`.
- **Poprawki produkcyjne:** gałąź z `main`, scalana do `main` i do `develop`.

## Ograniczenia

- Nazwa kanału z tytułu zawiera tylko `[a-z0-9-]`, więc polskie znaki wypadają („Wędrówka” → `w-dr-wka`); pusty wynik → `event`.
- Odzyskiwanie danych (`cogs/recovery.py`) nie ma testów – i tak wymaga przepisania pod szablony.
