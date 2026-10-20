from datetime import date

import pytest

from dates import parse_event_date


@pytest.mark.parametrize("text, expected", [
    ("15.11.2026", date(2026, 11, 15)),
    ("5.1.2026", date(2026, 1, 5)),
    ("2026-11-15", date(2026, 11, 15)),
    ("sobota 15.11.2026, godz. 18:00", date(2026, 11, 15)),  # times are ignored
    ("15-16.11.2026", date(2026, 11, 16)),  # range -> the day it ends
    ("10.11.2026 lub 15.11.2026", date(2026, 11, 15)),
    ("15.11.2026 lub 10.11.2026", date(2026, 11, 15)),  # the latest wins, not the last written
    ("2026-11-10 i 12.11.2026", date(2026, 11, 12)),  # mixed formats
])
def test_parses_dates(text, expected):
    assert parse_event_date(text) == expected


@pytest.mark.parametrize("text", ["", "wkrótce", "15/11/2026", "15.11.26", "15 listopada 2026", "31.02.2026"])
def test_unreadable_dates_give_none(text):
    assert parse_event_date(text) is None


def test_invalid_date_is_skipped_but_valid_one_still_found():
    assert parse_event_date("31.02.2026 lub 01.03.2026") == date(2026, 3, 1)
