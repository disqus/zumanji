from django import template
from django.utils import simplejson

register = template.Library()


@register.filter
def format_historical(data):
    result = []
    for item in data:
        if item:
            result.append('|'.join(map(str, item)))
        else:
            result.append('')
    return ','.join(result)


@register.filter('range')
def range_filter(value):
    return range(int(value))


@register.filter
def as_json(value):
    return simplejson.dumps(value)
