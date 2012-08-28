import itertools
from collections import defaultdict
from django.core.urlresolvers import reverse
from django.shortcuts import render, get_object_or_404
from django.utils import simplejson
from zumanji.models import Project, Build, Test

HISTORICAL_POINTS = 25


def _get_historical_data(build, test_list):
    # fetch 50 previous builds for comparing results
    previous_builds = list(Build.objects.filter(
        datetime__lt=build.datetime
    ).exclude(
        id=build.id,
    ).order_by('-datetime')
     .values_list('id', flat=True)[:HISTORICAL_POINTS - 1][::-1])

    previous_tests = list(Test.objects.filter(
            build__in=previous_builds,
            label__in=[t.label for t in test_list]
        )
        .values_list('build', 'label', 'mean_duration', 'data')
        .order_by('-build__datetime'))

    historical = defaultdict(lambda: defaultdict(str))
    for build_id, label, duration, data in itertools.chain(previous_tests, (
        (t.build_id, t.label, t.mean_duration, t.data) for t in test_list)):
        if isinstance(data, basestring):
            data = simplejson.loads(data)
        history_data = [duration]
        for interface in ('redis', 'sql', 'cache'):
            if interface not in data:
                history_data.append(0)
            else:
                interface_duration = data[interface].get('mean_duration', 0)
                history_data[0] -= interface_duration
                history_data.append(interface_duration)
        historical[label][build_id] = history_data

    results = {}
    for test in test_list:
        results[test.id] = [
            historical[test.label][b]
            for b in ([(str, str, str, str)] * HISTORICAL_POINTS + previous_builds + [test.build_id])
        ][-HISTORICAL_POINTS:]
    return results


def _get_changes(last_build, objects):
    if not (last_build and objects):
        return {}

    qs = last_build.test_set.filter(label__in=[o.label for o in objects])

    last_build_objects = dict((o.label, o) for o in qs)
    changes = dict()

    # {group: [{notes: notes, type: type}]}
    for obj in objects:
        last_obj = last_build_objects.get(obj.label)
        obj_changes = {
            'interfaces': {},
            'status': 'new' if last_obj is None else None,
        }
        if last_obj:
            data = obj.data
            last_obj_data = last_obj.data
            for interface in ('redis', 'sql', 'cache'):
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


def index(request):
    build_list = list(Build.objects
        .order_by('-datetime')
        .select_related('revision', 'project'))

    return render(request, 'zumanji/index.html', {
        'build_list': build_list,
    })


def view_project(request, project_label):
    project = get_object_or_404(Project, label=project_label)

    build_list = list(Build.objects
        .filter(project=project)
        .order_by('-datetime')
        .select_related('revision', 'project'))

    return render(request, 'zumanji/index.html', {
        'project': project,
        'build_list': build_list,
    })


def view_build(request, project_label, build_id):
    build = get_object_or_404(Build, project__label=project_label, id=build_id)
    last_build = build.get_last_build()
    next_build = build.get_next_build()

    test_list = list(build.test_set
        .filter(parent__isnull=True)
        .order_by('-upper90_duration'))

    historical = _get_historical_data(build, test_list)
    for test in test_list:
        test.historical = historical.get(test.id)

    changes = _get_changes(last_build, test_list)

    return render(request, 'zumanji/build.html', {
        'build': build,
        'last_build': last_build,
        'next_build': next_build,
        'test_list': test_list,
        'changes': changes,
    })


def view_test(request, project_label, build_id, test_label):
    test = get_object_or_404(Test, project__label=project_label, build=build_id, label=test_label)
    project = test.project
    build = test.build

    test_list = list(Test.objects.filter(parent=test)
        .order_by('-upper90_duration'))

    # this is actually a <TestGroup>
    last_build = test.get_last_build()
    next_build = test.get_next_build()

    historical = _get_historical_data(build, [test])
    test.historical = historical.get(test.id)

    if last_build:
        tests_to_check = test_list
        changes = _get_changes(last_build.build, tests_to_check)
    else:
        changes = []

    data = dict(
        (k, simplejson.loads(v))
        for k, v in test.testdata_set.values_list('key', 'data')
    )

    breadcrumbs = [
        (reverse('zumanji:view_build', kwargs={'project_label': project.label, 'build_id': build.id}), 'Build #%s' % build.id)
    ]
    key = []
    for part in test.label.split('.'):
        key.append(part)
        test_label = '.'.join(key)
        breadcrumbs.append((reverse('zumanji:view_test', kwargs={'project_label': project.label, 'build_id': build.id, 'test_label': test_label}), part))

    return render(request, 'zumanji/test.html', {
        'breadcrumbs': breadcrumbs,
        'build': build,
        'last_build': last_build,
        'next_build': next_build,
        'test': test,
        'test_list': test_list,
        'changes': changes,
        'data': data,
    })
