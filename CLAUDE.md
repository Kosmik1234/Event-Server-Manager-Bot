# Event Server Manager Bot – instrukcje dla Claude

Opis projektu, komend, architektury i deployu jest w **`README.md`** – przeczytaj go przed pracą nad kodem. Tutaj są tylko zasady pracy i pułapki.

## Zasady

- Kod, komentarze, docstringi i commity po **angielsku**; rozmowa z użytkownikiem i dokumentacja (`README.md`, ten plik) po **polsku**.
- Odpowiedzi krótkie i konkretne.
- Po zmianie zachowania bota (komendy, przepływy, dane, env) zaktualizuj `README.md`, żeby zgadzał się z kodem.
- Testy: `pip install -r requirements-dev.txt`, potem `pytest`. Przed commitem uruchom `pytest` i `python -m py_compile *.py cogs/*.py`. Nowa logika = nowe testy w `tests/` (czyste moduły wprost, kod z Discordem na atrapach `MagicMock`/`AsyncMock`, bez `pytest-asyncio` – używamy `asyncio.run`). Testy nie zastępują sprawdzenia na prawdziwym Discordzie (uprawnienia, limity, wygląd) – powiedz wprost, co nie zostało przetestowane.
- Pisz w stylu otaczającego kodu: proste funkcje, komentarze tłumaczące „dlaczego”, bez nadmiarowych abstrakcji.

## Checklisty

- Nowy tekst widoczny dla użytkownika → klucz w **obu** językach w `i18n.py` (`en` i `pl`).
- Nowy cog → `load_extension` w `EventBot.setup_hook` (`main.py`).
- Nowa komenda zmieniająca stan → `@app_commands.guild_only()`, `@app_commands.default_permissions(manage_guild=True)`, `@is_admin_or_mod()` oraz handler `.error` dla `CheckFailure`.
- Nowe pole własne ogłoszenia → nie dodawaj pola do `Event`, tylko klucz w `Event.extra` (`/set-field`).
- Nowe pole w `Event` → wartość domyślna (stare pliki JSON nie mają tego klucza) i przemyśl, czy recovery może je odtworzyć.
- Nowe uprawnienie bota → dopisz do listy w `README.md` i do overwrites w `/create-event`.

## Pułapki

- Ogłoszenie jest renderowane z szablonu (`templates.py`) do opisu embeda i nie ma pól o stałej kolejności. **Recovery (`cogs/recovery.py`) nadal czyta `fields[0]`/`fields[1]` i `embed.title`, więc po tej zmianie nie odzyska tytułu/daty/miejsca** – do naprawy przez parser według szablonu serwera.
- Linia szablonu z samymi pustymi placeholderami jest pomijana (to celowe). Wartości podstawiamy regexem, nie `str.format`.
- Odświeżanie ogłoszenia: zawsze przez `refresh_announcement` (`cogs/events.py`), nie ręcznym `edit(embed=...)`.
- **`/create-event` zapisuje rekord przed wysłaniem embeda**, a po wysłaniu czyta go ponownie – listener `on_guild_channel_create` w międzyczasie dopisuje `thread_id`/`join_message_id`. Nie nadpisuj rekordu starą kopią.
- Licznik aktualizują **tylko** listenery `on_thread_member_join` / `on_raw_thread_member_remove`, nie przyciski. Wersja *raw* przy usuwaniu jest celowa (nie-raw działa tylko dla członków w cache).
- `custom_id` przycisków (`join-event:<id>`, `leave-event:<id>`) jest używany przez `DynamicItem` i przez recovery – zmiana formatu psuje stare wiadomości.
- Wątek jest prywatny i nikogo nie dodajemy automatycznie – to świadoma decyzja, nie bug.
- Archiwizacja startuje dopiero po evencie `events_recovered`.
- `parse_event_date` zwraca **najpóźniejszą** datę z tekstu (`max`), nie ostatnią wystąpieniem.
- Wymagany privileged intent **Server Members** (`intents.members`).
- Handlery `CheckFailure` przy `/event-category list` i `/archive-category list` to martwy kod (te komendy nie mają checka).
- Część docstringów w kodzie nadal mówi o „updates thread” – to ten sam wątek uczestników.
