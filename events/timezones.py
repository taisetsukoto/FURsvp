"""Event-local timezone resolution from US event location."""

from datetime import datetime, time

import pytz
from django.conf import settings

DEFAULT_EVENT_TIMEZONE = getattr(settings, 'TIME_ZONE', 'America/New_York')

# Primary IANA timezone per US state (used when city is unavailable).
US_STATE_TIMEZONES = {
    'Alabama': 'America/Chicago',
    'Alaska': 'America/Anchorage',
    'Arizona': 'America/Phoenix',
    'Arkansas': 'America/Chicago',
    'California': 'America/Los_Angeles',
    'Colorado': 'America/Denver',
    'Connecticut': 'America/New_York',
    'Delaware': 'America/New_York',
    'Florida': 'America/New_York',
    'Georgia': 'America/New_York',
    'Hawaii': 'Pacific/Honolulu',
    'Idaho': 'America/Boise',
    'Illinois': 'America/Chicago',
    'Indiana': 'America/Indiana/Indianapolis',
    'Iowa': 'America/Chicago',
    'Kansas': 'America/Chicago',
    'Kentucky': 'America/New_York',
    'Louisiana': 'America/Chicago',
    'Maine': 'America/New_York',
    'Maryland': 'America/New_York',
    'Massachusetts': 'America/New_York',
    'Michigan': 'America/Detroit',
    'Minnesota': 'America/Chicago',
    'Mississippi': 'America/Chicago',
    'Missouri': 'America/Chicago',
    'Montana': 'America/Denver',
    'Nebraska': 'America/Chicago',
    'Nevada': 'America/Los_Angeles',
    'New Hampshire': 'America/New_York',
    'New Jersey': 'America/New_York',
    'New Mexico': 'America/Denver',
    'New York': 'America/New_York',
    'North Carolina': 'America/New_York',
    'North Dakota': 'America/Chicago',
    'Ohio': 'America/New_York',
    'Oklahoma': 'America/Chicago',
    'Oregon': 'America/Los_Angeles',
    'Pennsylvania': 'America/New_York',
    'Rhode Island': 'America/New_York',
    'South Carolina': 'America/New_York',
    'South Dakota': 'America/Chicago',
    'Tennessee': 'America/Chicago',
    'Texas': 'America/Chicago',
    'Utah': 'America/Denver',
    'Vermont': 'America/New_York',
    'Virginia': 'America/New_York',
    'Washington': 'America/Los_Angeles',
    'West Virginia': 'America/New_York',
    'Wisconsin': 'America/Chicago',
    'Wyoming': 'America/Denver',
}

# Optional city overrides for well-known multi-timezone edge cases.
US_CITY_TIMEZONES = {
    ('Indiana', 'Gary'): 'America/Chicago',
    ('Indiana', 'Evansville'): 'America/Chicago',
    ('Kentucky', 'Bowling Green'): 'America/Chicago',
    ('Kentucky', 'Paducah'): 'America/Chicago',
    ('Texas', 'El Paso'): 'America/Denver',
    ('Florida', 'Pensacola'): 'America/Chicago',
    ('Idaho', 'Boise'): 'America/Boise',
}


def timezone_name_for_location(state=None, city=None):
    state = (state or '').strip()
    city = (city or '').strip()
    if state and city:
        override = US_CITY_TIMEZONES.get((state, city))
        if override:
            return override
    if state:
        return US_STATE_TIMEZONES.get(state, DEFAULT_EVENT_TIMEZONE)
    return DEFAULT_EVENT_TIMEZONE


def get_zone(tz_name):
    return pytz.timezone(tz_name or DEFAULT_EVENT_TIMEZONE)


def localize_in_zone(naive_dt, tz_name):
    tz = get_zone(tz_name)
    try:
        return tz.localize(naive_dt)
    except pytz.exceptions.AmbiguousTimeError:
        return tz.localize(naive_dt, is_dst=False)
    except pytz.exceptions.NonExistentTimeError:
        return tz.localize(naive_dt, is_dst=True)


def effective_end_date_for(event):
    end_date = getattr(event, 'end_date', None)
    return end_date or event.date


def compute_event_schedule(event):
    """Return (starts_at, ends_at, timezone_name) in UTC-aware datetimes."""
    tz_name = timezone_name_for_location(
        getattr(event, 'state', None),
        getattr(event, 'city', None),
    )
    start_local = datetime.combine(event.date, event.start_time or time(0, 0))
    end_local = datetime.combine(
        effective_end_date_for(event),
        event.end_time or time(0, 0),
    )
    return (
        localize_in_zone(start_local, tz_name),
        localize_in_zone(end_local, tz_name),
        tz_name,
    )


def timezone_abbreviation(tz_name, at=None):
    """Short label such as EST or PDT for display."""
    from django.utils import timezone as django_tz

    tz = get_zone(tz_name)
    moment = at or django_tz.now()
    if moment.tzinfo is None:
        moment = django_tz.make_aware(moment, django_tz.utc)
    return moment.astimezone(tz).tzname() or tz_name


def timezone_display_name(tz_name):
    """Human-readable timezone name derived from IANA id."""
    mapping = {
        'America/New_York': 'Eastern Time',
        'America/Chicago': 'Central Time',
        'America/Denver': 'Mountain Time',
        'America/Los_Angeles': 'Pacific Time',
        'America/Phoenix': 'Arizona Time',
        'America/Anchorage': 'Alaska Time',
        'Pacific/Honolulu': 'Hawaii Time',
        'America/Indiana/Indianapolis': 'Indiana Time',
        'America/Detroit': 'Eastern Time',
        'America/Boise': 'Mountain Time',
    }
    return mapping.get(tz_name, tz_name.replace('_', ' ').split('/')[-1])
