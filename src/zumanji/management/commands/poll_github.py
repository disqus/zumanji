from django.db import transaction
from django.core.management.base import BaseCommand
from optparse import make_option
from zumanji.github import github
from zumanji.models import Project, Revision


class Command(BaseCommand):
    help = 'Updates all revisions by hammering GitHub'

    option_list = BaseCommand.option_list + (
        make_option('--project', '-p', dest='projects', help='Limit to project(s)', action='append'),
        make_option('--refetch', '-r', dest='refetch', help='Refetch all data from GitHub', action='store_true'),
    )

    @transaction.commit_on_success
    def handle(self, projects=None, refetch=False, **options):
        if projects:
            project_list = list(Project.objects.filter(label__in=projects))
            assert len(projects) == len(projects), 'one or more project label was not found'
        else:
            project_list = Project.objects.filter(label__contains='/')

        for project in project_list:
            print "Project %r" % project.label
            for data in github.iter_commits(project.github_user, project.github_repo):
                print "  Revision %r (%s; %s)" % (data['sha'], data['commit']['author']['name'],
                    data['commit']['committer']['date'])
                rev, created = Revision.get_or_create(project, data['sha'], data=data)
                if not created:
                    if not rev.data or refetch:
                        rev.update_from_github(data)
                        rev.save()
