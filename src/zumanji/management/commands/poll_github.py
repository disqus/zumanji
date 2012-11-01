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
            for commit in github.iter_commits(project.github_user, project.github_repo):
                print "  Revision %r (%s; %s)" % (commit['sha'], commit['commit']['author']['name'],
                    commit['commit']['committer']['date'])
                Revision.get_or_create(project, commit['sha'])
