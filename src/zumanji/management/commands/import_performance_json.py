import datetime
import os.path
from collections import defaultdict
from django.db import transaction
from django.utils import simplejson
from django.core.management.base import BaseCommand, CommandError
from zumanji.models import Project, Revision, Build, Test, TestGroup, TestData


def regroup_tests(tests):
    grouped = defaultdict(list)

    for test in tests:
        grouper = test['id']
        if '_' in grouper:
            grouper = grouper.rsplit('_', 1)[0]
        grouped[grouper].append(test)

    return grouped


def format_data(interface, data):
    stacktrace = data['stacktrace'][0]

    return {
        'interface': interface,
        'line': stacktrace['line_number'],
        'code': stacktrace['code'],
        'function': stacktrace['function_name'],
        'module': stacktrace['name'],
        'filename': stacktrace['file_name'],
        'duration': data['duration'],
        'time': data['time'],
    }


class Command(BaseCommand):
    args = '<json_file json_file ...>'
    help = 'Imports the specified JSON files'

    @transaction.commit_on_success
    def handle(self, *args, **options):
        for json_file in args:
            if not os.path.exists(json_file):
                raise CommandError('Json file %r does not exist' % json_file)

            with open(json_file, 'r') as fp:
                data = simplejson.loads(fp.read())

            timestamp = datetime.datetime.strptime(data['time'], '%Y-%m-%dT%H:%M:%S.%f')

            project = Project.objects.get_or_create(
                label='disqus-web',
            )[0]

            revision = Revision.objects.get_or_create(
                project=project,
                label=data['time'],
            )[0]

            build, created = Build.objects.get_or_create(
                revision=revision,
                datetime=timestamp,
            )

            num_tests = 0
            total_duration = 0.0
            for group_label, tests in regroup_tests(data['tests']).iteritems():
                group = TestGroup.objects.get_or_create(
                    build=build,
                    label=group_label,
                )[0]
                group_durations = []

                for test_data in tests:
                    group_durations.append(test_data['duration'])

                    test = Test.objects.get_or_create(
                        group=group,
                        label=test_data['id'],
                        defaults=dict(
                            duration=test_data['duration'],
                            data=test_data['api_data'],
                        )
                    )[0]

                    data = []
                    for key in ('redis', 'sql', 'cache'):
                        if not test_data.get(key):
                            continue
                        for chunk in test_data[key]:
                            ts = datetime.datetime.strptime(chunk['time'], '%Y-%m-%dT%H:%M:%S.%f')

                            data.append((ts, key, chunk))

                    data = [format_data(*d[1:]) for d in sorted(data, key=lambda x: x[0])]

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

                TestGroup.objects.filter(id=group.id).update(
                    num_tests=group_num_tests,
                    mean_duration=group_total_duration,
                    upper_duration=group_durations[-1],
                    lower_duration=group_durations[0],
                    upper90_duration=group_durations[int(group_num_tests * (90 / 100.0))],
                )

                num_tests += group_num_tests
                total_duration += group_total_duration

            Build.objects.filter(id=build.id).update(
                num_tests=num_tests,
                total_duration=total_duration,
            )

            transaction.commit()
            self.stdout.write('Imported %r (build_id=%r)' % (json_file, build.id))
