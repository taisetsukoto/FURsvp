from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    if dictionary is None or key is None:
        return None
    return dictionary.get(key)