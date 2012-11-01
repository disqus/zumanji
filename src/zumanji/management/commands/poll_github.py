from django.db import transaction
from django.core.management.base import BaseCommand
from zumanji.github import github
from zumanji.models import Project, Revision


class Command(BaseCommand):
    help = 'Updates all revisions by hammering GitHub'

    @transaction.commit_on_success
    def handle(self, **options):
        for project in Project.objects.filter(label__contains='/'):
            print "Project %r" % project.label
            for data in github.iter_commits(project.github_user, project.github_repo):
                print "  Revision %r (%s; %s)" % (data['sha'], data['commit']['author']['name'],
                    data['commit']['committer']['date'])
                rev, created = Revision.get_or_create(project, data['sha'], data=data)
                if not created and not rev.data:
                    rev.update_from_github(data)
                    rev.save()
