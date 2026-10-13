"""Reads the free-text event date typed into /create-event."""
import re
from datetime import date

_DOTTED = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")  # 15.11.2026
_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")  # 2026-11-15


def parse_event_date(text: str) -> date | None:
    """The last calendar date found in the text, or None. Taking the last one means a range
    like "15-16.11.2026" counts as ending on the 16th. Times are ignored."""
    found = []
    for pattern, order in ((_DOTTED, (2, 1, 0)), (_ISO, (0, 1, 2))):
        for match in pattern.findall(text):
            year, month, day = (int(match[i]) for i in order)
            try:
                found.append(date(year, month, day))
            except ValueError:
                pass  # e.g. 31.02.2026
    return max(found, default=None)
