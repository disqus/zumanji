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

    if not last_build:
        last_build_groups = dict()
        changes = dict()
    else:
        last_build_groups = dict((g.label, g) for g in last_build.testgroup_set.all())
        changes = dict()
        # {group: [{notes: notes, type: type}]}
        for group in test_group_list:
            last_group = last_build_groups.get(group.label)
            group_changes = {
                'interfaces': {},
                'status': 'new' if last_group is None else None,
            }
            if last_group:
                data = group.data
                last_group_data = last_group.data
                for interface in ('redis', 'sql', 'cache'):
                    if interface in data:
                        current = data[interface].get('mean_calls', 0)
                    else:
                        current = 0

                    if interface in last_group_data:
                        previous = last_group_data[interface].get('mean_calls', 0)
                    else:
                        previous = 0

                    change = current - previous
                    if change == 0:
                        continue

                    group_changes['interfaces'][interface] = {
                        'current': current,
                        'previous': previous,
                        'change': '+%s' % change if change > 0 else str(change),
                        'type': 'increase' if change > 0 else 'decrease',
                    }

            if group_changes['status'] != 'new' and not group_changes['interfaces']:
                continue

            changes[group] = group_changes

    return render(request, 'zumanji/build.html', {
        'build': build,
        'last_build': last_build,
        'next_build': next_build,
        'test_group_list': test_group_list,
        'changes': sorted(changes.iteritems(), key=lambda x: x[0].label),
    })


def view_test_group(request, group_id):
    group = TestGroup.objects.get(id=group_id)
    build = group.build
    test_list = list(group.test_set
        .order_by('-duration'))

    historical = _get_historical_data(build, [group])
    group.historical = historical.get(group.id)

    return render(request, 'zumanji/testgroup.html', {
        'build': build,
        'last_build': group.get_last_build(),
        'next_build': group.get_next_build(),
        'group': group,
        'test_list': test_list,
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
