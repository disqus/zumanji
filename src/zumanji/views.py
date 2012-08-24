from collections import defaultdict
from django.shortcuts import render
from django.utils import simplejson
from zumanji.models import Build, TestGroup, Test

HISTORICAL_POINTS = 25


def index(request):
    build_list = list(Build.objects
        .order_by('-datetime')
        .select_related('revision', 'project'))

    return render(request, 'zumanji/index.html', {
        'build_list': build_list,
    })


def view_build(request, build_id):
    build = Build.objects.get(id=build_id)
    test_group_list = list(build.testgroup_set
        .order_by('-upper90_duration'))

    # fetch 50 previous builds for comparing results
    previous_builds = list(Build.objects.filter(datetime__lt=build.datetime)
        .order_by('-datetime')
        .values_list('id', flat=True)[:HISTORICAL_POINTS - 1])

    previous_tests = list(TestGroup.objects.filter(build__in=previous_builds)
        .values_list('build', 'label', 'upper90_duration')
        .order_by('build__datetime'))

    historical = defaultdict(lambda: defaultdict(str))
    for build_id, label, duration in previous_tests:
        historical[label][build_id] = duration

    for group in test_group_list:
        group.historical = [
            historical[group.label][b]
            for b in ([str] * HISTORICAL_POINTS + previous_builds)
        ][-HISTORICAL_POINTS - 1:]
        group.historical.append(group.upper90_duration)

    return render(request, 'zumanji/build.html', {
        'build': build,
        'test_group_list': test_group_list,
    })


def view_test_group(request, group_id):
    group = TestGroup.objects.get(id=group_id)
    build = group.build
    test_list = list(group.test_set
        .order_by('-duration'))

    # fetch 50 previous builds for comparing results
    previous_builds = list(Build.objects.filter(datetime__lt=build.datetime)
        .order_by('-datetime')
        .values_list('id', flat=True)[:HISTORICAL_POINTS - 1])

    previous_tests = list(TestGroup.objects.filter(build__in=previous_builds, label=group.label)
        .values_list('build', 'upper90_duration')
        .order_by('build__datetime'))

    historical = defaultdict(str)
    for build_id, duration in previous_tests:
        historical[build_id] = duration

    group.historical = [
        historical[b]
        for b in ([str] * HISTORICAL_POINTS + previous_builds)
    ][-HISTORICAL_POINTS - 1:]
    group.historical.append(group.upper90_duration)

    return render(request, 'zumanji/testgroup.html', {
        'build': build,
        'group': group,
        'test_list': test_list,
    })


def view_test(request, test_id):
    test = Test.objects.get(id=test_id)
    group = test.group
    build = group.build

    # fetch 50 previous builds for comparing results
    previous_builds = list(Build.objects.filter(datetime__lt=build.datetime)
        .order_by('-datetime')
        .values_list('id', flat=True)[:HISTORICAL_POINTS - 1])

    previous_tests = list(TestGroup.objects.filter(build__in=previous_builds, label=group.label)
        .values_list('build', 'upper90_duration')
        .order_by('build__datetime'))

    historical = defaultdict(str)
    for build_id, duration in previous_tests:
        historical[build_id] = duration

    group.historical = [
        historical[b]
        for b in ([str] * HISTORICAL_POINTS + previous_builds)
    ][-HISTORICAL_POINTS - 1:]
    group.historical.append(group.upper90_duration)

    data = dict(
        (k, simplejson.loads(v))
        for k, v in test.testdata_set.values_list('key', 'data')
    )

    return render(request, 'zumanji/test.html', {
        'test': test,
        'build': build,
        'group': group,
        'trace': data['trace'],
    })
