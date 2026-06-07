import re

from django.core.cache import cache
from django.core.exceptions import ValidationError

BLOCKED_TERMS_CACHE_KEY = 'users:blocked_terms:v1'
BLOCKED_TERMS_CACHE_TIMEOUT = 300

LEET_REPLACEMENTS = str.maketrans({
    '0': 'o',
    '1': 'i',
    '3': 'e',
    '4': 'a',
    '5': 's',
    '7': 't',
    '@': 'a',
    '$': 's',
})

MODERATION_ERROR_MESSAGE = (
    'This name contains language that is not allowed on FURsvp. '
    'Please choose a different name.'
)


def normalize_for_matching(text):
    if not text:
        return ''
    normalized = text.lower().translate(LEET_REPLACEMENTS)
    return re.sub(r'[^a-z0-9]', '', normalized)


def clear_blocked_terms_cache():
    cache.delete(BLOCKED_TERMS_CACHE_KEY)


def get_blocked_terms():
    cached = cache.get(BLOCKED_TERMS_CACHE_KEY)
    if cached is not None:
        return cached

    from users.models import BlockedTerm

    terms = list(
        BlockedTerm.objects.filter(is_active=True).values('term', 'match_mode')
    )
    cache.set(BLOCKED_TERMS_CACHE_KEY, terms, BLOCKED_TERMS_CACHE_TIMEOUT)
    return terms


def is_text_blocked(text):
    normalized = normalize_for_matching(text)
    if not normalized:
        return False

    for entry in get_blocked_terms():
        term_norm = normalize_for_matching(entry['term'])
        if not term_norm:
            continue

        if entry['match_mode'] == 'exact':
            if normalized == term_norm:
                return True
            continue

        if len(term_norm) < 4:
            if normalized == term_norm:
                return True
        elif term_norm in normalized:
            return True

    return False


def validate_user_display_text(text):
    if text and is_text_blocked(text):
        raise ValidationError(MODERATION_ERROR_MESSAGE)
