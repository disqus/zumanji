from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'zumanji.views.index', name='index'),
    url(r'^project/(?P<project_label>[^/]+)$', 'zumanji.views.view_project', name='view_project'),
    url(r'^project/(?P<project_label>[^/]+)/upload$', 'zumanji.views.upload_project_build', name='upload_project_build'),
    url(r'^project/(?P<project_label>[^/]+)/tag/(?P<tag_id>\d+)$', 'zumanji.views.view_tag', name='view_tag'),
    url(r'^project/(?P<project_label>[^/]+)/build/(?P<build_id>\d+)$', 'zumanji.views.view_build', name='view_build'),
    url(r'^project/(?P<project_label>[^/]+)/tag/(?P<tag_id>\d+)/build/(?P<build_id>\d+)$', 'zumanji.views.view_build', name='view_build'),
    url(r'^project/(?P<project_label>[^/]+)/build/(?P<build_id>\d+)/report/(?P<test_label>[^/]+)$', 'zumanji.views.view_test', name='view_test'),
)
