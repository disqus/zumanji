import datetime
import hashlib
import os.path
from collections import defaultdict
from django.db import transaction
from django.utils import simplejson
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from zumanji.models import Project, Revision, Build, BuildTag, Test


def convert_timestamp(timestamp):
    return datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f')


def count_leaves_with_tests(labels):
    # test.label: set(leaves)
    leaves = defaultdict(set)
    for label in labels:
        leaves[label].add(label)
        parent = label.rsplit('.', 1)[0]
        leaves[parent].add(label)
        while len(leaves[parent]) > 1 and '.' in parent:
            parent = parent.rsplit('.', 1)[0]
            leaves[parent].add(parent)

    return dict((k, len(v)) for k, v in leaves.iteritems())


def regroup_tests(tests):
    grouped = defaultdict(list)

    for test in tests:
        key = []
        for part in test['id'].split('.')[:-1]:
            key.append(part)
            grouped['.'.join(key)].append(test)

    return sorted(grouped.items(), key=lambda x: x[0])


def with_call_id(data):
    call_id = hashlib.md5(data['interface'])
    call_id.update(data['command'])
    call_id.update(data['filename'])
    call_id.update(data['function'])
    call_id = call_id.hexdigest()

    data['id'] = call_id
    return data


def format_v2_data(data):
    frame = data['stacktrace'][0]

    data['start'] = float(data['start'])
    if data.get('end') is not None:
        data['end'] = float(data['end'])
        duration = data['end'] - data['start']
    else:
        duration = 0.0

    return with_call_id({
        'interface': data['type'],
        'command': data['name'],
        'args': data['args'],
        'function': frame['function'],
        'filename': frame['filename'],
        'lineno': frame['lineno'],
        'duration': duration,
        'time': datetime.datetime.fromtimestamp(data['start']).isoformat(),
        'depth': len(data['stacktrace']),
        'stacktrace': data['stacktrace'],
    })


def format_v1_data(item):
    interface, data = item
    frame = data['stacktrace'][0]

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
        command = u':'.join(frame['filename'], frame['function'])
        args = []

    return with_call_id({
        'interface': interface,
        'command': command,
        'args': args,
        'function': frame['function'],
        'filename': frame['filename'],
        'lineno': frame['lineno'],
        'duration': data['duration'],
        'time': data['time'],
        'depth': len(data['stacktrace']),
        'stacktrace': data['stacktrace'],
    })


def percentile(values, percentile=90):
    return values[int(len(values) * (percentile / 100.0))]


def create_test_leaf(build, data, parent, version=1):
    if version == 1:
        format_data = format_v1_data

        interface_data = []
        for interface, values in data.get('interfaces', {}).iteritems():
            for item in values:
                interface_data.append((interface, item))

        interface_data.sort(key=lambda x: x[0])

    elif version == 2:
        format_data = format_v2_data

        interface_data = data.get('calls', [])
        interface_data.sort(key=lambda x: float(x['start']))

    else:
        raise ValueError('version')

    interface_data = [format_data(d) for d in interface_data]

    description = (data.get('doc') or '').strip()

    extra_data = defaultdict(lambda: {
        'mean_calls': 0,
        'mean_duration': 0.0,
    })
    for item in interface_data:
        extra_data[item['interface']]['mean_calls'] += 1
        extra_data[item['interface']]['mean_duration'] += item['duration']

    test = Test.objects.create(
        build=build,
        project=build.project,
        revision=build.revision,
        label=data['id'],
        description=description,
        mean_duration=data['duration'],
        upper90_duration=data['duration'],
        upper_duration=data['duration'],
        lower_duration=data['duration'],
        data=extra_data,
        parent=parent,
    )

    test.testdata_set.create(
        build=test.build,
        revision=test.revision,
        project=test.project,
        key='trace',
        data=interface_data,
    )

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

            self.stdout.write('Reading json file %r\n' % (json_file,))

            if not os.path.exists(json_file):
                raise CommandError('Json file %r does not exist' % json_file)

            with open(json_file, 'r') as fp:
                data = simplejson.loads(fp.read())

            version = int(data.get('version', 1))
            timestamp = convert_timestamp(data['time'])

            project_label = options.get('project') or data.get('project')
            assert project_label, 'You must specify a project with --project <label>'

            revision_label = options.get('revision') or data.get('revision')
            assert revision_label, 'You must specify a revision with --revision <label>'

            # We avoid recreating the core items that might get referenced by an ID in the interface
            project = Project.objects.get_or_create(
                label=project_label,
            )[0]

            revision = Revision.objects.get_or_create(
                project=project,
                label=revision_label,
            )[0]

            build, created = Build.objects.get_or_create(
                project=project,
                revision=revision,
                datetime=timestamp,
            )

            # Clean out old tests
            build.test_set.all().delete()

            # Clean out old tags
            build.tags.all().delete()
            # Add tags
            tag_list = [
                BuildTag.objects.get_or_create(label=tag_name)[0]
                for tag_name in data.get('tags', [])
            ]
            build.tags.add(*tag_list)

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

            grouped_tests = [(l, t) for l, t in grouped_tests if leaf_counts.get(l) >= 1]

            # Create branches
            for label, _ in grouped_tests:
                parent = find_parent(label)

                self.stdout.write('- Creating branch %r\n' % (label,))

                branch = Test.objects.create(
                    parent=parent,
                    project=project,
                    revision=revision,
                    build=build,
                    label=label,
                )
                tests_by_id[branch.label] = branch

            for label, tests in reversed(grouped_tests):
                branch = tests_by_id[label]

                # Create any leaves which do not exist yet
                for test_data in (t for t in tests if t['id'] not in tests_by_id):
                    self.stdout.write('- Creating leaf %r\n' % (test_data['id'],))

                    test = create_test_leaf(build, test_data, branch, version)
                    tests_by_id[test.label] = test

                    num_tests += 1
                    total_duration += test.mean_duration

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

                tests_by_id[branch.label] = Test.objects.filter(id=branch.id).update(
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
