import datetime
import os.path
from collections import defaultdict
from django.db import transaction
from django.utils import simplejson
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from zumanji.models import Project, Revision, Build, Test, TestGroup, TestData


def regroup_tests(tests):
    grouped = defaultdict(list)

    for test in tests:
        grouper = test.get('group') or test.get('label') or test['id']
        grouped[grouper].append(test)

    return grouped


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
            for grouper, tests in regroup_tests(data['tests']).iteritems():
                group = TestGroup.objects.get_or_create(
                    build=build,
                    label=grouper,
                )[0]
                group_durations = []
                # {interface: {test_id: [duration]}}
                interface_durations = defaultdict(lambda: defaultdict(list))

                for test_data in tests:
                    group_durations.append(test_data['duration'])
                    data = []
                    extra_data = defaultdict(lambda: {
                        'calls': 0,
                        'duration': 0.0,
                    })

                    for interface, values in test_data.get('interfaces', {}).iteritems():
                        for item in values:
                            ts = datetime.datetime.strptime(item['time'], '%Y-%m-%dT%H:%M:%S.%f')

                            data.append((ts, interface, item))
                            interface_durations[interface][test_data['id']].append(item['duration'])

                    data = [format_data(*d[1:]) for d in sorted(data, key=lambda x: x[0])]

                    for item in data:
                        extra_data[item['interface']]['calls'] += 1
                        extra_data[item['interface']]['duration'] += item['duration']

                    test_label = test_data.get('label') or test_data['id']

                    test, created = Test.objects.get_or_create(
                        group=group,
                        test_id=test_data['id'],
                        defaults=dict(
                            description=(test_data.get('doc') or '').strip(),
                            duration=test_data['duration'],
                            data=extra_data,
                            label=test_label,
                        )
                    )
                    if not created:
                        test.data = extra_data
                        test.label = test_label
                        test.save()

                    td, created = TestData.objects.get_or_create(
                        test=test,
                        key='trace',
                        defaults=dict(
                            data=data,
                        )
                    )
                    if not created and td.data != data:
                        td.data = data
                        td.save()

                group_num_tests = len(group_durations)
                group_total_duration = sum(group_durations)
                group_durations.sort()

                td_data = {}
                for interface, values in interface_durations.iteritems():
                    durations = [sum(v) for k, v in values.iteritems()]
                    td_data[interface] = {
                        'mean_calls': len(durations),
                        'mean_duration': sum(durations),
                        'upper_duration': durations[-1],
                        'lower_duration': durations[0],
                        'upper90_duration': percentile(durations, 90),
                    }

                TestGroup.objects.filter(id=group.id).update(
                    num_tests=group_num_tests,
                    mean_duration=group_total_duration,
                    upper_duration=group_durations[-1],
                    lower_duration=group_durations[0],
                    upper90_duration=percentile(group_durations, 90),
                    data=td_data,
                )

                num_tests += group_num_tests
                total_duration += group_total_duration

            Build.objects.filter(id=build.id).update(
                num_tests=num_tests,
                total_duration=total_duration,
            )

            transaction.commit()
            self.stdout.write('Imported %r (build_id=%r)\n' % (json_file, build.id))
