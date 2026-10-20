"""Event announcement format.

A template is plain text with `{placeholders}` that is rendered into the announcement
embed's description. Core placeholders are title, date, location and description; any other
`{key}` is an extra field stored in `Event.extra` (see /set-field). Servers can replace the
default with their own template (see /event-template).

Rendering rules:
- A line whose placeholders are all empty is dropped, so a missing location or ticket link
  doesn't leave an orphaned "Where:" label behind.
- Values are substituted with a regex rather than str.format, so braces typed by users
  in a description can't break rendering."""
import re

from i18n import t
from storage import Event

CORE_KEYS = ("title", "date", "location", "description")
PLACEHOLDER = re.compile(r"\{([a-z_][a-z0-9_]*)\}")
EXTRA_KEY = re.compile(r"[a-z_][a-z0-9_]*")
TEMPLATE_LIMIT = 4000  # Discord's max for a modal text input
EMBED_DESCRIPTION_LIMIT = 4096


def default_template(lang: str) -> str:
    """The format events had before templates existed: title, description, then when/where."""
    return (
        "# {title}\n"
        "{description}\n"
        "\n"
        f"**{t(lang, 'field_when')}:** {{date}}\n"
        f"**{t(lang, 'field_where')}:** {{location}}"
    )


def event_values(event: Event) -> dict[str, str]:
    # Core fields last, so an extra can never shadow them.
    return {**event.extra, "title": event.title, "date": event.date, "location": event.location,
            "description": event.description}


def sample_values(template: str) -> dict[str, str]:
    """Made-up values for /event-template preview, including every extra key the template uses."""
    values = {key: f"<{key}>" for key in PLACEHOLDER.findall(template)}
    values.update(title="Sample event", date="15.11.2026", location="Warsaw", description="A short description.")
    return values


def render_template(template: str, values: dict[str, str]) -> str:
    lines = []
    for line in template.split("\n"):
        keys = PLACEHOLDER.findall(line)
        if keys and not any(values.get(key) for key in keys):
            continue
        lines.append(PLACEHOLDER.sub(lambda match: values.get(match.group(1), ""), line))
    return "\n".join(lines)[:EMBED_DESCRIPTION_LIMIT]


def validate_template(template: str) -> str | None:
    """An i18n key describing the problem, or None if the template is fine."""
    if not template.strip():
        return "template_empty"
    return None
