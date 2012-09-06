from django import template
from django.conf import settings
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


@register.filter
def get_key(value, key):
    return value[key]


@register.inclusion_tag('zumanji/includes/test_row.html')
def render_test_row(test):
    data = test.data
    columns = []
    for column, _ in settings.ZUMANJI_CONFIG['call_types']:
        result = data.get(column)
        if not result:
            columns.append(None)
        else:
            columns.append((result.get('mean_duration'), result.get('mean_calls')))

    return {
        'test': test,
        'columns': columns,
    }


@register.inclusion_tag('zumanji/includes/test_columns.html')
def render_test_columns():
    return {
        'columns': [c[1] for c in settings.ZUMANJI_CONFIG['call_types']]
    }


@register.inclusion_tag('zumanji/includes/change_row.html')
def render_change_row(change, compare_build):
    test, data = change

    columns = []
    for column, _ in settings.ZUMANJI_CONFIG['call_types']:
        result = data['interfaces'].get(column)
        if not result:
            columns.append(None)
        else:
            columns.append((result.get('type'), result.get('change')))

    return {
        'test': test,
        'columns': columns,
        'compare_build': compare_build,
    }
