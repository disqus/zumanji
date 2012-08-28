import itertools
from collections import defaultdict
from django.shortcuts import render
from django.utils import simplejson
from zumanji.models import Build, TestGroup, Test

HISTORICAL_POINTS = 25


def _get_historical_data(build, group_list):
    # fetch 50 previous builds for comparing results
    previous_builds = list(Build.objects.filter(
        datetime__lt=build.datetime
    ).exclude(
        id=build.id,
    ).order_by('-datetime')
     .values_list('id', flat=True)[:HISTORICAL_POINTS - 1])

    previous_tests = list(TestGroup.objects.filter(
            build__in=previous_builds,
            label__in=[g.label for g in group_list]
        )
        .values_list('build', 'label', 'upper90_duration', 'data')
        .order_by('build__datetime'))

    historical = defaultdict(lambda: defaultdict(str))
    for build_id, label, duration, data in itertools.chain(previous_tests, (
        (g.build_id, g.label, g.upper90_duration, g.data) for g in group_list)):
        if isinstance(data, basestring):
            data = simplejson.loads(data)
        history_data = [duration]
        for interface in ('redis', 'sql', 'cache'):
            if interface not in data:
                history_data.append(0)
            else:
                interface_duration = data[interface].get('upper90_duration', 0)
                history_data[0] -= interface_duration
                history_data.append(interface_duration)
        historical[label][build_id] = history_data

    results = {}
    for group in group_list:
        results[group.id] = [
            historical[group.label][b]
            for b in ([(str, str, str, str)] * HISTORICAL_POINTS + previous_builds + [group.build_id])
        ][-HISTORICAL_POINTS:]
    return results


def _get_changes(last_build, objects):
    if not (last_build and objects):
        return {}

    model = type(objects[0])
    if model == Test:
        qs = last_build.test_set.filter(test_id__in=[o.test_id for o in objects])
        calls_key = 'calls'
    elif model == TestGroup:
        qs = last_build.testgroup_set.filter(label__in=[o.label for o in objects])
        calls_key = 'mean_calls'
    else:
        raise NotImplementedError

    last_build_objects = dict(
        (getattr(o, 'test_id', o.label), o)
        for o in qs
    )
    changes = dict()

    # {group: [{notes: notes, type: type}]}
    for obj in objects:
        last_obj = last_build_objects.get(getattr(obj, 'test_id', obj.label))
        obj_changes = {
            'interfaces': {},
            'status': 'new' if last_obj is None else None,
        }
        if last_obj:
            data = obj.data
            last_obj_data = last_obj.data
            for interface in ('redis', 'sql', 'cache'):
                if interface in data:
                    current = data[interface].get(calls_key, 0)
                else:
                    current = 0

                if interface in last_obj_data:
                    previous = last_obj_data[interface].get(calls_key, 0)
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


def index(request):
    build_list = list(Build.objects
        .order_by('-datetime')
        .select_related('revision', 'project'))

    return render(request, 'zumanji/index.html', {
        'build_list': build_list,
    })


def view_build(request, build_id):
    build = Build.objects.get(id=build_id)
    last_build = build.get_last_build()
    next_build = build.get_next_build()

    test_group_list = list(build.testgroup_set
        .order_by('-upper90_duration'))

    historical = _get_historical_data(build, test_group_list)
    for group in test_group_list:
        group.historical = historical.get(group.id)

    changes = _get_changes(last_build, test_group_list)

    return render(request, 'zumanji/build.html', {
        'build': build,
        'last_build': last_build,
        'next_build': next_build,
        'test_group_list': test_group_list,
        'changes': changes,
    })


def view_test_group(request, group_id):
    group = TestGroup.objects.get(id=group_id)
    build = group.build
    test_list = list(group.test_set
        .order_by('-duration'))

    # this is actually a <TestGroup>
    last_build = group.get_last_build()

    historical = _get_historical_data(build, [group])
    group.historical = historical.get(group.id)

    changes = _get_changes(last_build.build, test_list)

    return render(request, 'zumanji/testgroup.html', {
        'build': build,
        'last_build': last_build,
        'next_build': group.get_next_build(),
        'group': group,
        'test_list': test_list,
        'changes': changes,
    })


def view_test(request, test_id):
    test = Test.objects.get(id=test_id)
    group = test.group
    build = group.build

    historical = _get_historical_data(build, [group])
    group.historical = historical.get(group.id)

    data = dict(
        (k, simplejson.loads(v))
        for k, v in test.testdata_set.values_list('key', 'data')
    )

    return render(request, 'zumanji/test.html', {
        'test': test,
        'build': build,
        'last_build': test.get_last_build(),
        'next_build': test.get_next_build(),
        'group': group,
        'trace': data['trace'],
    })
