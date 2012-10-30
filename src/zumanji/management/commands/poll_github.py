from django.db import transaction
from django.core.management.base import BaseCommand
from zumanji.models import Project, is_revision


class Command(BaseCommand):
    help = 'Updates all revisions by hammering GitHub'

    @transaction.commit_on_success
    def handle(self, **options):
        for project in Project.objects.filter(label__contains='/'):
            for revision in project.revision_set.all():
                if is_revision(revision.label):
                    revision.data = {}
                    if not revision.data:
                        revision.save()
