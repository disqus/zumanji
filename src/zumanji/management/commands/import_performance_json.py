import datetime
import os.path
from collections import defaultdict
from django.db import transaction
from django.utils import simplejson
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from zumanji.models import Project, Revision, Build, Test, TestData


def count_leaves_with_tests(labels):
    # test.label: set(leaves)
    counts = defaultdict(int)
    for label in labels:
        counts[label.rsplit('.', 1)[0]] += 1

    return counts


def regroup_tests(tests):
    grouped = defaultdict(list)

    for test in tests:
        key = []
        for part in test['id'].split('.')[:-1]:
            key.append(part)
            grouped['.'.join(key)].append(test)

    return sorted(grouped.items(), key=lambda x: x[0])


def format_data(interface, data):
    stacktrace = data['stacktrace'][0]

    if interface == 'sql':
        command = data['query']
        args = data['query_params']
    elif interface in ('redis', 'pipelined_redis'):
        command = data['command']
        if 'actions' in data:
            args = data['actions']
        else:
            args = [data['other_args']]
    elif interface == 'cache':
        command = data['action']
        args = [data['key']]
    else:
        command = (stacktrace['name'], stacktrace['function_name'])
        args = []

    return {
        'interface': interface,
        'command': command,
        'args': args,
        'line': stacktrace['line_number'],
        'code': stacktrace['code'],
        'function': stacktrace['function_name'],
        'module': stacktrace['name'],
        'filename': stacktrace['file_name'],
        'duration': data['duration'],
        'time': data['time'],
        'depth': len(data['stacktrace']),
    }


def percentile(values, percentile=90):
    return values[int(len(values) * (percentile / 100.0))]


def create_test_leaf(build, data, parent):
    interface_data = []
    for interface, values in data.get('interfaces', {}).iteritems():
        for item in values:
            interface_data.append((interface, item))

    interface_data = [format_data(*d) for d in sorted(interface_data, key=lambda x: x[0])]

    description = (data.get('doc') or '').strip()

    extra_data = defaultdict(lambda: {
        'mean_calls': 0,
        'mean_duration': 0.0,
    })
    for item in interface_data:
        extra_data[item['interface']]['mean_calls'] += 1
        extra_data[item['interface']]['mean_duration'] += item['duration']

    test, created = Test.objects.get_or_create(
        build=build,
        label=data['id'],
        defaults=dict(
            description=description,
            mean_duration=data['duration'],
            upper90_duration=data['duration'],
            upper_duration=data['duration'],
            lower_duration=data['duration'],
            data=extra_data,
            parent=parent,
        )
    )
    if not created:
        test.parent = parent
        test.data = extra_data
        test.save()

    td, created = TestData.objects.get_or_create(
        test=test,
        key='trace',
        defaults=dict(
            data=interface_data,
        )
    )
    if not created and td.data != interface_data:
        td.data = interface_data
        td.save()

    return test


class Command(BaseCommand):
    args = '<json_file json_file ...>'
    help = 'Imports the specified JSON files'

    option_list = BaseCommand.option_list + (
        make_option('--project', '-p', dest='project', help='Project Label'),
        make_option('--revision', '-r', dest='revision', help='Revision Label'),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        for json_file in args:
            if not os.path.exists(json_file):
                raise CommandError('Json file %r does not exist' % json_file)

            with open(json_file, 'r') as fp:
                data = simplejson.loads(fp.read())

            timestamp = datetime.datetime.strptime(data['time'], '%Y-%m-%dT%H:%M:%S.%f')

            project_label = options.get('project') or data.get('project')
            assert project_label, 'You must specify a project with --project <label>'

            revision_label = options.get('revision') or data.get('revision')
            assert revision_label, 'You must specify a revision with --revision <label>'

            project = Project.objects.get_or_create(
                label=project_label,
            )[0]

            revision = Revision.objects.get_or_create(
                project=project,
                label=revision_label,
            )[0]

            build, created = Build.objects.get_or_create(
                revision=revision,
                datetime=timestamp,
            )

            num_tests = 0
            total_duration = 0.0
            tests_by_id = {}
            grouped_tests = regroup_tests(data['tests'])

            # Eliminate useless parents (parents which only have a single child)
            leaf_counts = count_leaves_with_tests((t['id'] for t in data['tests']))

            def find_parent(label):
                if '.' not in label:
                    return None

                key = label.split('.')[:-1]
                while key:
                    path = '.'.join(key)
                    if path in tests_by_id:
                        return tests_by_id[path]
                    key.pop()
                return None

            for label, tests in grouped_tests:
                if leaf_counts.get(label) < 1:
                    continue

                print 'Creating branch', label

                branch = Test.objects.get_or_create(
                    project=project,
                    revision=revision,
                    build=build,
                    label=label,
                )[0]

                for test_data in tests:
                    if test_data['id'] not in tests_by_id:
                        test = create_test_leaf(build, test_data, branch)
                        num_tests += 1
                        total_duration += test.mean_duration
                        tests_by_id[test.label] = test

                # Update aggregated data
                group_durations = []
                interface_durations = defaultdict(list)

                for test in (tests_by_id[t['id']] for t in tests):
                    group_durations.append(test.mean_duration)
                    for interface, values in test.data.iteritems():
                        interface_durations[interface].append(values)

                group_num_tests = len(group_durations)
                group_total_duration = sum(group_durations)
                group_durations.sort()

                td_data = {}
                for interface, values in interface_durations.iteritems():
                    durations = [v['mean_duration'] for v in values]
                    td_data[interface] = {
                        'mean_calls': sum(v['mean_calls'] for v in values),
                        'mean_duration': sum(durations),
                        'upper_duration': durations[-1],
                        'lower_duration': durations[0],
                        'upper90_duration': percentile(durations, 90),
                    }

                parent = find_parent(label)

                branch = Test.objects.filter(id=branch.id).update(
                    parent=parent,
                    label=label,
                    num_tests=group_num_tests,
                    mean_duration=group_total_duration,
                    upper_duration=group_durations[-1],
                    lower_duration=group_durations[0],
                    upper90_duration=percentile(group_durations, 90),
                    data=td_data,
                )

            Build.objects.filter(id=build.id).update(
                num_tests=num_tests,
                total_duration=total_duration,
            )

            transaction.commit()
            self.stdout.write('Imported %r (build_id=%r)\n' % (json_file, build.id))
