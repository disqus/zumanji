from django.db import transaction
from django.core.management.base import BaseCommand
from zumanji.models import Project
from zumanji.helpers import is_revision


class Command(BaseCommand):
    help = 'Updates all revisions by hammering GitHub'

    @transaction.commit_on_success
    def handle(self, **options):
        for project in Project.objects.filter(label__contains='/'):
            print "Project %r" % project
            for revision in project.revision_set.all():
                if is_revision(revision.label):
                    print "  Revision %r" % revision
                    revision.data = {}
                    if not revision.data:
                        revision.save()
