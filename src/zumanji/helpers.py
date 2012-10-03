import difflib
import itertools
from collections import defaultdict
from django.conf import settings
from django.utils.datastructures import SortedDict
from zumanji.models import Build, Test, TestData

HISTORICAL_POINTS = 25


def get_trace_data(test, previous_test=None):
    if previous_test:
        try:
            previous_trace = previous_test.testdata_set.get(key='trace').data
        except TestData.DoesNotExist:
            previous_trace = []
    else:
        previous_trace = []

    try:
        trace = test.testdata_set.get(key='trace').data
    except TestData.DoesNotExist:
        trace = []

    if not (trace or previous_trace):
        return {}

    previous_trace = SortedDict(('%s_%s' % (x, c['id']), c) for x, c in enumerate(previous_trace))
    trace = SortedDict(('%s_%s' % (x, c['id']), c) for x, c in enumerate(trace))

    seqmatch = difflib.SequenceMatcher()
    seqmatch.set_seqs(previous_trace.keys(), trace.keys())

    trace_diff = (
        {'test': previous_test, 'calls': []},  # left
        {'test': test, 'calls': []},  # left
    )
    for tag, i1, i2, j1, j2 in seqmatch.get_opcodes():
        if tag in ('equal', 'replace'):
            for key in previous_trace.keys()[i1:i2]:
                trace_diff[0]['calls'].append((tag, key, previous_trace[key]))
            for key in trace.keys()[j1:j2]:
                trace_diff[1]['calls'].append((tag, key, trace[key]))
        elif tag == 'delete':
            for key in previous_trace.keys()[i1:i2]:
                trace_diff[0]['calls'].append((tag, key, previous_trace[key]))
                trace_diff[1]['calls'].append((tag, key, None))
        elif tag == 'insert':
            for key in trace.keys()[j1:j2]:
                trace_diff[0]['calls'].append((tag, key, None))
                trace_diff[1]['calls'].append((tag, key, trace[key]))
        else:
            raise ValueError(tag)

    all_calls = dict(previous_trace)
    all_calls.update(trace)

    return {
        'diff': trace_diff,
        'calls': all_calls,
        'num_diffs': sum(sum(1 for t, _, c in n['calls'] if t != 'equal') for n in trace_diff),
    }


def get_historical_data(build, test_list):
    previous_builds = list(Build.objects.filter(
        datetime__lt=build.datetime,
        project=build.project,
    ).exclude(
        id=build.id,
    ).order_by('-datetime')
     .values_list('id', flat=True)[:HISTORICAL_POINTS - 1][::-1])

    previous_tests = list(Test.objects.filter(
        build__in=previous_builds,
        label__in=[t.label for t in test_list]
    )
    .order_by('-build__datetime'))

    historical = defaultdict(lambda: defaultdict(list))
    for test in itertools.chain(previous_tests, test_list):
        history_data = []
        for interface, _ in settings.ZUMANJI_CONFIG['call_types']:
            if interface not in test.data:
                history_data.append(0)
            else:
                interface_calls = test.data[interface].get('mean_calls')
                history_data.append(interface_calls)
        historical[test.label][test.build_id] = history_data

    padding = [(None, [])] * HISTORICAL_POINTS
    results = {}
    for test in test_list:
        results[test.id] = (padding + [
            (b, historical[test.label][b])
            for b in (previous_builds + [test.build_id])
        ])[-HISTORICAL_POINTS:]

    return results


def get_changes(previous_build, objects):
    if not (previous_build and objects):
        return {}

    qs = previous_build.test_set.filter(
        label__in=[o.label for o in objects],
    ).select_related('parent')

    previous_build_objects = dict((o.label, o) for o in qs)
    changes = dict()

    # {group: [{notes: notes, type: type}]}
    for obj in objects:
        last_obj = previous_build_objects.get(obj.label)
        obj_changes = {
            'interfaces': {},
            'status': 'new' if last_obj is None else None,
        }
        if last_obj:
            data = obj.data
            last_obj_data = last_obj.data
            for interface, _ in settings.ZUMANJI_CONFIG['call_types']:
                if interface in data:
                    current = data[interface].get('mean_calls', 0)
                else:
                    current = 0

                if interface in last_obj_data:
                    previous = last_obj_data[interface].get('mean_calls', 0)
                else:
                    previous = 0

                change = current - previous
                if change == 0:
                    continue

                obj_changes['interfaces'][interface] = {
                    'current': current,
                    'previous': previous,
                    'change': '+%s' % change if change > 0 else str(change),
                    'type': 'increase' if change > 0 else 'decrease',
                }

        if obj_changes['status'] != 'new' and not obj_changes['interfaces']:
            continue

        changes[obj] = obj_changes

    return sorted(changes.iteritems(),
        key=lambda x: sum(int(i['change']) for i in x[1]['interfaces'].values()),
        reverse=True)
