import os.path
from django.db import transaction
from django.utils import simplejson
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from zumanji.importer import import_build


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

            build = import_build(data, project=options.get('project'),
                revision=options.get('revision'))
            transaction.commit()

            self.stdout.write('Imported %r (build_id=%r)\n' % (json_file, build.id))
