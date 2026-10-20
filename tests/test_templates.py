from storage import Event
from templates import (
    EMBED_DESCRIPTION_LIMIT, PLACEHOLDER, default_template, event_values, render_template, sample_values,
    validate_template,
)


def make_event(**kw) -> Event:
    defaults = dict(channel_id=1, guild_id=1, title="Fest", date="15.11.2026", location="Warsaw", description="Fun")
    return Event(**{**defaults, **kw})


def test_default_template_en():
    text = render_template(default_template("en"), event_values(make_event()))
    assert text == "# Fest\nFun\n\n**📅 When:** 15.11.2026\n**📍 Where:** Warsaw"


def test_default_template_uses_server_language():
    assert "Kiedy" in default_template("pl")
    assert "When" in default_template("en")


def test_line_with_only_empty_placeholders_is_dropped():
    text = render_template(default_template("en"), event_values(make_event(location="", description="")))
    assert text == "# Fest\n\n**📅 When:** 15.11.2026"


def test_line_with_some_values_is_kept():
    assert render_template("{date} — {location}", {"date": "15.11.2026", "location": ""}) == "15.11.2026 — "


def test_lines_without_placeholders_are_kept():
    assert render_template("Hello\n{missing}\nBye", {}) == "Hello\nBye"


def test_extra_fields():
    event = make_event(extra={"tickets": "http://x"})
    assert render_template("🎟 [Tickets]({tickets})", event_values(event)) == "🎟 [Tickets](http://x)"
    assert render_template("🎟 {tickets}", event_values(make_event())) == ""


def test_extra_cannot_shadow_core_fields():
    event = make_event(extra={"title": "Hacked", "date": "never"})
    assert render_template("{title} {date}", event_values(event)) == "Fest 15.11.2026"


def test_braces_in_user_text_do_not_break_rendering():
    event = make_event(description="Use {curly} and {0} braces }{")
    assert "Use {curly} and {0} braces }{" in render_template("{description}", event_values(event))


def test_unknown_placeholder_syntax_is_left_alone():
    assert render_template("{Title} {bad-key}", {"title": "x"}) == "{Title} {bad-key}"


def test_output_is_truncated_to_embed_limit():
    text = render_template("{description}", {"description": "x" * 10_000})
    assert len(text) == EMBED_DESCRIPTION_LIMIT


def test_validate_template():
    assert validate_template("# {title}") is None
    assert validate_template("") == "template_empty"
    assert validate_template("  \n ") == "template_empty"


def test_sample_values_cover_extras_and_core():
    values = sample_values("{title} {tickets}")
    assert values["tickets"] == "<tickets>"
    assert values["title"] == "Sample event"
    assert all(values[key] for key in PLACEHOLDER.findall("{title}{date}{location}{description}"))
