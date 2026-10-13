# Event Server Manager Bot

Bot Discord (Python, `discord.py>=2.6`) zarządzający serwerem poświęconym wydarzeniom. **Każdy kanał tekstowy w skonfigurowanej kategorii = jedno wydarzenie.** Kod i komentarze są po angielsku, użytkownik rozmawia po polsku. Całość to ~1000 linii, brak testów.

## Co robi bot

1. **Kanał w kategorii wydarzeń** (utworzony przez `/create-event` albo ręcznie) → `on_guild_channel_create` automatycznie tworzy w nim **prywatny wątek „aktualności”** (`<nazwa>-updates`, slowmode 300 s, `invitable=False`) oraz **przypiętą wiadomość** z przyciskami **Join/Leave** i licznikiem uczestników.
2. **Join** = dodanie użytkownika do wątku (widzi zmiany daty, miejsca, informacje). **Leave** = usunięcie z wątku.
3. **Licznik uczestników** = liczba członków wątku minus bot. Jedyne źródło prawdy: listenery `on_thread_member_join` / `on_raw_thread_member_remove` (łapią też ręczne zmiany w UI Discorda), nie same przyciski.
4. **Archiwizacja**: co godzinę (pętla `tasks.loop`) kanały wydarzeń z datą w przeszłości są przenoszone do kategorii-archiwum przypisanej do danej kategorii wydarzeń.
5. **Odzyskiwanie** po utracie pliku z danymi: przy starcie odtwarza rekordy z samego Discorda.

## Komendy slash (wszystkie zmieniające wymagają admina lub roli `MODERATOR_ROLE`)

- `/create-event title date location description` – tworzy kanał (w pierwszej istniejącej skonfigurowanej kategorii), embed ogłoszenia; @everyone widzi, ale nie pisze. `date` to wolny tekst.
- `/make-event` – naprawcza: robi z bieżącego kanału (w kategorii wydarzeń) wydarzenie: rekord + wątek + wiadomość z przyciskami (wspólna funkcja `setup_event_channel` w `cogs/auto_thread.py`, używana też przez listener). Jeśli rekord ma wątek, który został usunięty, odtwarza go.
- `/set-date date` – ustawia datę wydarzenia; działa w kanale wydarzenia lub w jego wątku; zapisuje w store i odświeża embed (jeśli jest). Pozwala archiwizować też kanały stworzone ręcznie.
- `/event-category add|remove|list` – które kategorie są „kategoriami wydarzeń” (per serwer). `list` dostępne dla wszystkich.
- `/archive-category add|remove|list` – mapowanie *kategoria wydarzeń → kategoria archiwum*. Kategoria wydarzeń ma max 1 archiwum, kilka może dzielić jedno. Kategoria nie może być jednocześnie wydarzeniową i archiwum (walidacja w obie strony). Usunięcie kategorii wydarzeń kasuje jej link do archiwum.
- `/language` – `en` / `pl` per serwer.

## Struktura

| Plik | Rola |
|---|---|
| `main.py` | `EventBot`; intents (`members` – **privileged**, musi być włączony w Developer Portal); ładuje cogi; sync komend (guild gdy `DEV_GUILD_ID`, inaczej globalnie); `bot.lang(guild)` |
| `config.py` | zmienne środowiskowe (`.env` lokalnie, Railway Variables w produkcji) |
| `storage.py` | dataclass `Event` + interfejs `EventStore` + `JsonEventStore` (jeden plik JSON, klucz = channel_id) |
| `guild_settings.py` | `GuildSettingsStore`: per-guild JSON (`event_categories`, `archives`, `language`) |
| `checks.py` | `is_admin_or_mod()` |
| `dates.py` | `parse_event_date(text)` – regexy `dd.mm.yyyy` i `yyyy-mm-dd`, zwraca **ostatnią** datę w tekście (zakres `15-16.11.2026` → 16-ty); godziny ignorowane |
| `i18n.py` | `t(lang, key, **kw)`; słowniki `en`/`pl` w jednym pliku; brak klucza → fallback do en; `from_locale` |
| `cogs/events.py` | `/create-event`, `build_embed` |
| `cogs/settings.py` | `/event-category`, `/archive-category`, `/language` (3 cogi w jednym pliku) |
| `cogs/auto_thread.py` | tworzenie wątku + wiadomości z przyciskami, listenery licznika |
| `cogs/join.py` | `JoinButton`/`LeaveButton` jako `DynamicItem`, `update_participant_count` |
| `cogs/archive.py` | `ArchiveSweepCog` – godzinna pętla przenoszenia |
| `cogs/recovery.py` | `on_ready` → odtworzenie rekordów, potem dispatch `events_recovered` |

Deploy: `Procfile` (`worker: python main.py`), Railway; dane muszą leżeć na zamontowanym Volume (`EVENTS_FILE`, `GUILD_SETTINGS_FILE`). Env: `DISCORD_BOT_TOKEN`, `MODERATOR_ROLE`, `DEV_GUILD_ID`, `EVENTS_FILE`, `GUILD_SETTINGS_FILE`, `TIMEZONE` (domyślnie `Europe/Warsaw`) – patrz `.env.example`.

## Model danych (`Event`)

`channel_id`, `guild_id`, `title`, `date` (tekst!), `location`, `description`, `creator_id`, `message_id` (embed), `thread_id`, `join_message_id` (przypięta wiadomość z przyciskami). Kanały stworzone ręcznie mają tylko `title = nazwa kanału` i puste `date` → **nigdy nie są archiwizowane**. Lookup po wątku: `store.get_by_thread`.

## Niuanse, o których łatwo zapomnieć

- **Kolejność w `/create-event`**: rekord zapisujemy *przed* wysłaniem embeda, bo `on_guild_channel_create` odpala się od razu po utworzeniu kanału i szuka rekordu (żeby podpiąć wątek do rekordu). Po wysłaniu embeda rekord jest czytany ponownie (listener mógł dopisać `thread_id`/`join_message_id`).
- Wątek jest **prywatny** i zawiera wyłącznie uczestników: nikt (także twórca wydarzenia i osoba wywołująca komendę) nie jest dodawany automatycznie, członkostwo tylko przez przyciski Join/Leave. Moderator bez Manage Threads nie zobaczy wątku, dopóki nie kliknie Join. `creator_id` jest tylko zapisywany w rekordzie.
- Przyciski mają `thread_id` w `custom_id` (`join-event:<id>`, `leave-event:<id>`), więc działają po restarcie bez DB. Rejestracja przez `bot.add_dynamic_items` w `cogs/join.py:setup`.
- Recovery: znajduje wątek jako prywatny wątek, którego właścicielem jest bot (także zarchiwizowane), czyta ostatnie 100 wiadomości bota; z embeda odczytuje title/description oraz `fields[0]`=data, `fields[1]`=miejsce (stąd kolejność pól w `build_embed` jest kontraktem!). `creator_id` nie da się odzyskać.
- Archiwizacja pomija: nieczytelną datę, `event_date >= today` (czyli w dniu wydarzenia jeszcze nie), brak archiwum, usuniętą kategorię. Błąd (np. kategoria pełna – limit 50 kanałów) jest tylko logowany.
- Sweep startuje dopiero po evencie `events_recovered` (żeby nie działać na niepełnych danych).
- Nowy tekst użytkownika → dodać klucz do **obu** języków w `i18n.py`.
- Nowy cog → dodać `load_extension` w `EventBot.setup_hook` (`main.py`).
- Wymagane uprawnienia bota: Manage Channels, Manage Threads, Create Private Threads, Send Messages (+ in Threads), Embed Links, Manage Messages (przypinanie).
- Nazwa kanału z tytułu: tylko `[a-z0-9-]`, więc polskie znaki wypadają (np. „Wędrówka” → `w-dr-wka`); fallback `event`.
- Storage jest synchroniczny i zapisuje cały plik przy każdej zmianie – wystarczające przy małej skali; zamiana na DB = nowa klasa implementująca `EventStore` i podmiana w `main.py`.
- `/event-category list` i `/archive-category list` nie mają `is_admin_or_mod`, ale mają handler błędu `CheckFailure` (martwy kod dla list).
