from django import template

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
