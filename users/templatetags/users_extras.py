from django import template
from django.urls import reverse
from users.utils import normalize_notification_link

register = template.Library()

ADMINISTRATION_QUERY_KEYS = (
    'user_search', 'user_page', 'group_search', 'group_page',
    'audit_search', 'audit_user_filter', 'audit_action_filter', 'audit_page',
    'blocked_search', 'blocked_source_filter', 'blocked_page',
    'tab', 'blog_page',
)

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def notification_link(link):
    return normalize_notification_link(link)

@register.filter
def get_avatar_sized_html(profile, size):
    return profile.get_avatar_html(size=size)

@register.simple_tag(takes_context=True)
def administration_url(context, **overrides):
    """Build an administration URL preserving current query state."""
    request = context['request']
    params = request.GET.copy()
    for key, value in overrides.items():
        if value is None or value == '':
            params.pop(key, None)
        else:
            params[key] = str(value)
    base = reverse('administration')
    encoded = params.urlencode()
    return f'{base}?{encoded}' if encoded else base

@register.inclusion_tag('users/partials/admin_state_fields.html', takes_context=True)
def admin_state_fields(context, exclude=''):
    exclude_set = {item.strip() for item in exclude.split(',') if item.strip()}
    fields = []
    for key in ADMINISTRATION_QUERY_KEYS:
        if key in exclude_set:
            continue
        value = context['request'].GET.get(key)
        if value:
            fields.append((key, value))
    return {'fields': fields} 