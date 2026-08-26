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
    payload = dict(record.field_values or {})
    payload['_sd_margin'] = (
        str(record.sd_margin) if record.sd_margin is not None else ''
    )
    payload['_atisa_margin'] = (
        str(record.atisa_margin) if record.atisa_margin is not None else ''
    )
    return json_script(payload, f'record-json-{record.pk}')
