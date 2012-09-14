from django.contrib import admin
from zumanji.models import Project, Revision, Build


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('label',)
    search_fields = ('label',)

admin.site.register(Project, ProjectAdmin)


class RevisionAdmin(admin.ModelAdmin):
    list_display = ('label', 'project')
    list_filter = ('project',)
    search_fields = ('label', 'project__label')

admin.site.register(Revision, RevisionAdmin)


class BuildAdmin(admin.ModelAdmin):
    list_display = ('label', 'project', 'revision', 'num_tests', 'result', 'datetime')
    list_filter = ('datetime', 'project', 'result')
    search_fields = ('label', 'project__label', 'revision__label')
    raw_id_fields = ('revision',)

admin.site.register(Build, BuildAdmin)
