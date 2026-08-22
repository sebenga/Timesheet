from django import template
from django.utils.html import json_script

register = template.Library()


@register.filter
def dict_get(mapping, key):
    if not mapping:
        return ''
    return mapping.get(key, '')


@register.simple_tag
def record_values_script(record):
    return json_script(record.field_values or {}, f'record-json-{record.pk}')
