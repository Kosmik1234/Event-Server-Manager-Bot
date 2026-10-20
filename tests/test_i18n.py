import string

import i18n
from i18n import STRINGS, from_locale, t


def _fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_both_languages_have_the_same_keys():
    assert set(STRINGS["en"]) == set(STRINGS["pl"])


def test_both_languages_use_the_same_format_arguments():
    for key in STRINGS["en"]:
        assert _fields(STRINGS["en"][key]) == _fields(STRINGS["pl"][key]), key


def test_t_formats_and_falls_back_to_english():
    assert t("en", "date_set", date="x") == "Event date set to: x"
    assert t("pl", "date_set", date="x") == "Ustawiono datę wydarzenia: x"
    assert t("de", "date_set", date="x") == "Event date set to: x"  # unknown language


def test_from_locale():
    assert from_locale("pl") == "pl"
    assert from_locale("en-US") == "en"
    assert from_locale("de") == i18n.DEFAULT
    assert from_locale(None) == i18n.DEFAULT
