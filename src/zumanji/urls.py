from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'zumanji.views.index', name='index'),
    url(r'^(?P<project_label>[^/]+)$', 'zumanji.views.view_project', name='view_project'),
    url(r'^(?P<project_label>[^/]+)/build/(?P<build_id>\d+)$', 'zumanji.views.view_build', name='view_build'),
    url(r'^(?P<project_label>[^/]+)/build/(?P<build_id>\d+)/result/(?P<test_label>[^/]+)$', 'zumanji.views.view_test', name='view_test'),
)
