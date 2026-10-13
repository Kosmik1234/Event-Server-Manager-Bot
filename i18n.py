"""Minimal localization: English and Polish.

Usage: `t(lang, "key", name=value)`. A missing key in a language falls back to English.
The language is chosen per server (see EventBot.lang in main.py), because most of the bot's
output - the join message, the participant counter, the event embed - is public and has no
single "user" whose language could be used."""

DEFAULT = "en"
LANGUAGES = {"en": "English", "pl": "Polski"}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # events
        "field_when": "📅 When",
        "field_where": "📍 Where",
        "no_categories": "No event categories configured yet. Ask an admin to run `/event-category add`.",
        "categories_missing": "None of the configured event categories exist anymore. Fix with `/event-category`.",
        "no_permission": (
            "I don't have permission to do that here. My role needs Manage Channels, Manage Threads, "
            "Create Private Threads, Send Messages and Embed Links on this category."
        ),
        "create_failed": "Something went wrong creating the channel. Check the bot's logs.",
        "event_created": "Event created: {channel}",
        "only_admins_create": "Only admins or moderators can create events.",
        # auto thread
        "thread_suffix": "updates",
        # event-category
        "category_added": "Added {category} to allowed event categories.",
        "category_exists": "{category} is already allowed.",
        "category_removed": "Removed {category} from allowed event categories.",
        "category_not_in_list": "{category} wasn't in the list.",
        "category_none": "No event categories configured yet. Add one with `/event-category add`.",
        "category_list_header": "Allowed event categories:",
        "category_gone": "`{id}` (category no longer exists)",
        "only_admins_change": "Only admins or moderators can change this.",
        # language
        "language_set": "Language set to {language}.",
        # join / leave
        "counter": "👥 Participants: {count}",
        "join_label": "Join Event",
        "leave_label": "Leave Event",
        "thread_gone": "This event's thread no longer exists.",
        "joined": "You've joined the event! See {thread}",
        "join_failed": "Couldn't add you to the event thread. Try again later.",
        "left": "You've left the event.",
        "leave_failed": "Couldn't remove you from the event thread. Try again later.",
    },
    "pl": {
        "field_when": "📅 Kiedy",
        "field_where": "📍 Gdzie",
        "no_categories": "Nie skonfigurowano jeszcze kategorii wydarzeń. Poproś administratora o użycie `/event-category add`.",
        "categories_missing": "Żadna ze skonfigurowanych kategorii wydarzeń już nie istnieje. Popraw to przez `/event-category`.",
        "no_permission": (
            "Nie mam tu odpowiednich uprawnień. Moja rola potrzebuje: Zarządzanie kanałami, Zarządzanie wątkami, "
            "Tworzenie prywatnych wątków, Wysyłanie wiadomości i Osadzanie linków w tej kategorii."
        ),
        "create_failed": "Coś poszło nie tak podczas tworzenia kanału. Sprawdź logi bota.",
        "event_created": "Wydarzenie utworzone: {channel}",
        "only_admins_create": "Tylko administratorzy lub moderatorzy mogą tworzyć wydarzenia.",
        "thread_suffix": "aktualizacje",
        "category_added": "Dodano {category} do dozwolonych kategorii wydarzeń.",
        "category_exists": "{category} jest już dozwolona.",
        "category_removed": "Usunięto {category} z dozwolonych kategorii wydarzeń.",
        "category_not_in_list": "{category} nie było na liście.",
        "category_none": "Nie skonfigurowano jeszcze kategorii wydarzeń. Dodaj jedną przez `/event-category add`.",
        "category_list_header": "Dozwolone kategorie wydarzeń:",
        "category_gone": "`{id}` (kategoria już nie istnieje)",
        "only_admins_change": "Tylko administratorzy lub moderatorzy mogą to zmienić.",
        "language_set": "Ustawiono język: {language}.",
        "counter": "👥 Uczestnicy: {count}",
        "join_label": "Dołącz do wydarzenia",
        "leave_label": "Opuść wydarzenie",
        "thread_gone": "Wątek tego wydarzenia już nie istnieje.",
        "joined": "Dołączyłeś/aś do wydarzenia! Zobacz {thread}",
        "join_failed": "Nie udało się dodać Cię do wątku wydarzenia. Spróbuj ponownie później.",
        "left": "Opuściłeś/aś wydarzenie.",
        "leave_failed": "Nie udało się usunąć Cię z wątku wydarzenia. Spróbuj ponownie później.",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    text = STRINGS.get(lang, {}).get(key) or STRINGS[DEFAULT][key]
    return text.format(**kwargs) if kwargs else text


def from_locale(locale: str | None) -> str:
    """Maps a Discord locale such as "pl" or "en-US" to a supported language."""
    code = (locale or "").split("-")[0]
    return code if code in LANGUAGES else DEFAULT
