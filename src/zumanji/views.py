from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.utils import simplejson
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from functools import wraps
from zumanji.forms import UploadJsonForm
from zumanji.helpers import get_trace_data, get_changes
from zumanji.models import Project, Build, BuildTag, Test
from zumanji.importer import import_build


NOTSET = object()


def api_auth(func):
    @wraps(func)
    def wrapped(request, *args, **kwargs):
        if request.REQUEST.get('api_key'):
            if request.REQUEST['api_key'] != settings.ZUMANJI_CONFIG.get('API_KEY', NOTSET):
                return HttpResponseForbidden('Invalid api_key')
            return func(request, *args, **kwargs)
        return csrf_protect(func)(request, *args, **kwargs)
    return csrf_exempt(wrapped)


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


def view_tag(request, project_label, tag_id):
    project = get_object_or_404(Project, label=project_label)
    tag = get_object_or_404(BuildTag, pk=tag_id)

    build_list = list(Build.objects
        .filter(project=project, tags=tag)
        .order_by('-datetime')
        .select_related('revision', 'project'))

    return render(request, 'zumanji/tag.html', {
        'project': project,
        'tag': tag,
        'build_list': build_list,
    })


def view_build(request, project_label, build_id, tag_id=None):
    filter_args = dict(project__label=project_label, id=build_id)
    tag = None
    if tag_id:
        tag = get_object_or_404(BuildTag, id=tag_id)
        filter_args["tags"] = tag

    build = get_object_or_404(Build, **filter_args)
    project = build.project
    previous_build = build.get_previous_build(tag=tag)
    next_build = build.get_next_build(tag=tag)

    test_list = list(build.test_set
        .filter(parent__isnull=True)
        .order_by('-upper90_duration'))

    compare_with = request.GET.get('compare_with')
    if compare_with:
        try:
            compare_build = Build.objects.get(project__label=project_label, id=compare_with)
        except Build.DoesNotExist:
            compare_build = None
    else:
        compare_build = previous_build

    changes = get_changes(compare_build, test_list)

    return render(request, 'zumanji/build.html', {
        'project': project,
        'tag': tag,
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

    trace_results = get_trace_data(test, compare_test)
    if previous_test_by_build:
        tests_to_check = test_list
        changes = get_changes(compare_build, tests_to_check)
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


@api_auth
@transaction.commit_on_success
def upload_project_build(request, project_label):
    project = get_object_or_404(Project, label=project_label)

    form = UploadJsonForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        data = simplejson.loads(request.FILES['json_file'].read())

        try:
            build = import_build(data, project=project.label, revision=form.cleaned_data.get('revision'))
        except Exception, e:
            form.errors['json_file'] = unicode(e)
        else:
            return HttpResponseRedirect(reverse('zumanji:view_build', kwargs={
                'project_label': project.label, 'build_id': build.id}))

    return render(request, 'zumanji/upload_build.html', {
        'project': project,
        'form': form,
    })
