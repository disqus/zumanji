import difflib
import itertools
from collections import defaultdict
from django.core.urlresolvers import reverse
from django.shortcuts import render, get_object_or_404
from django.utils.datastructures import SortedDict
from zumanji.models import Project, Build, Test, TestData

HISTORICAL_POINTS = 25


def _get_trace_data(test, previous_test=None):
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
        .order_by('-build__datetime'))

    historical = defaultdict(lambda: defaultdict(str))
    for test in itertools.chain(previous_tests, test_list):
        history_data = [test.mean_duration]
        for interface in ('redis', 'sql', 'cache'):
            if interface not in test.data:
                history_data.append(0)
            else:
                interface_duration = test.data[interface].get('mean_duration', 0)
                history_data[0] -= interface_duration
                history_data.append(interface_duration)
        historical[test.label][test.build_id] = history_data

    results = {}
    for test in test_list:
        results[test.id] = [
            historical[test.label][b]
            for b in ([(str, str, str, str)] * HISTORICAL_POINTS + previous_builds + [test.build_id])
        ][-HISTORICAL_POINTS:]
    return results


def _get_changes(previous_build, objects):
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

    return render(request, 'zumanji/project.html', {
        'project': project,
        'build_list': build_list,
    })


def view_build(request, project_label, build_id):
    build = get_object_or_404(Build, project__label=project_label, id=build_id)
    project = build.project
    previous_build = build.get_previous_build()
    next_build = build.get_next_build()

    test_list = list(build.test_set
        .filter(parent__isnull=True)
        .order_by('-upper90_duration'))

    historical = _get_historical_data(build, test_list)
    for test in test_list:
        test.historical = historical.get(test.id)

    compare_with = request.GET.get('compare_with')
    if compare_with:
        try:
            compare_build = Build.objects.get(project__label=project_label, id=compare_with)
        except Build.DoesNotExist:
            compare_build = None
    else:
        compare_build = previous_build

    changes = _get_changes(compare_build, test_list)

    return render(request, 'zumanji/build.html', {
        'project': project,
        'build': build,
        'previous_build': previous_build,
        'compare_build': compare_build,
        'next_build': next_build,
        'test_list': test_list,
        'changes': changes,
    })


def view_test(request, project_label, build_id, test_label):
    test = get_object_or_404(Test, project__label=project_label, build=build_id, label=test_label)
    project = test.project
    build = test.build

    test_list = list(Test.objects.filter(parent=test)
        .order_by('-upper90_duration')
        .select_related('parent'))

    # this is actually a <Test>
    previous_test_by_build = test.get_test_in_previous_build()
    next_test_by_build = test.get_test_in_next_build()

    historical = _get_historical_data(build, [test])
    test.historical = historical.get(test.id)

    breadcrumbs = [
        (reverse('zumanji:view_build', kwargs={'project_label': project.label, 'build_id': build.id}), 'Build #%s' % build.id)
    ]
    last = ''
    for node in test.get_context():
        node_label = node.label[len(last):]
        breadcrumbs.append(
            (reverse('zumanji:view_test', kwargs={
                'project_label': project.label,
                'build_id': build.id,
                'test_label': node.label,
            }), node_label)
        )
        last = node.label + '.'  # include the dot

    previous_builds = list(test.get_previous_builds().select_related('revision')[:50])

    compare_with = request.GET.get('compare_with')
    if compare_with:
        try:
            compare_build = Build.objects.get(project__label=project_label, id=compare_with)
        except Build.DoesNotExist:
            compare_build = None
    else:
        compare_build = previous_test_by_build.build if previous_test_by_build else None

    if compare_build:
        try:
            compare_test = compare_build.test_set.get(label=test.label)
        except Test.DoesNotExist:
            compare_test = None
    else:
        compare_test = None

    trace_results = _get_trace_data(test, compare_test)
    if previous_test_by_build:
        tests_to_check = test_list
        changes = _get_changes(compare_build, tests_to_check)
    else:
        changes = []

    return render(request, 'zumanji/test.html', {
        'breadcrumbs': breadcrumbs,
        'project': project,
        'build': build,
        'previous_test_by_build': previous_test_by_build,
        'next_test_by_build': next_test_by_build,
        'previous_builds': previous_builds,
        'test': test,
        'test_list': test_list,
        'changes': changes,
        'compare_build': compare_build,
        'trace_results': trace_results,
    })
