import dateutil.parser
from datetime import timedelta
from django import template
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import simplejson
from django.utils.html import mark_safe
from django.utils.translation import ugettext as _
from zumanji.helpers import get_historical_data

register = template.Library()

from gravatar.templatetags.gravatar import *


@register.simple_tag
def zumanji_version():
    import zumanji
    return zumanji.VERSION


@register.filter
def format_historical(data):
    result = []
    for item in data:
        if item:
            result.append('|'.join(map(str, item)))
        else:
            result.append('')
    return ','.join(result)


@register.filter
def oneline(value):
    return value.split("\n")[0]


@register.filter
def date_from_iso(value):
    return dateutil.parser.parse(value)


@register.filter('range')
def range_filter(value):
    return range(int(value))


@register.filter
def as_json(value):
    return mark_safe(simplejson.dumps(value))


@register.inclusion_tag('zumanji/includes/sparkline.html')
def render_historical_sparkline(test):
    data = get_historical_data(test.build, [test])[test.id]
    historical = []
    for build_id, result in data:
        if build_id:
            historical.append({
                'url': reverse('zumanji:view_test', kwargs={
                    'project_label': test.project.label,
                    'build_id': build_id,
                    'test_label': test.label,
                }),
                'title': 'Build #%s' % build_id,
                'values': result,
            })
        else:
            historical.append({
                'values': result,
            })

    return {
        'columns': [c[1] for c in settings.ZUMANJI_CONFIG['call_types']],
        'test': test,
        'historical': historical,
    }


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


@register.filter
def timesince(value, now=None):
    from django.template.defaultfilters import timesince
    from django.utils import timezone
    if now is None:
        now = timezone.now()
    if not value:
        return _('never')
    if value < (now - timedelta(days=5)):
        return value.date()
    value = (' '.join(timesince(value, now).split(' ')[0:2])).strip(',')
    if value == _('0 minutes'):
        return _('just now')
    if value == _('1 day'):
        return _('yesterday')
    return value + _(' ago')
