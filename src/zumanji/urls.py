from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'zumanji.views.index', name='index'),
    url(r'^B(?P<build_id>\d+)$', 'zumanji.views.view_build', name='view_build'),
    url(r'^G(?P<group_id>\d+)$', 'zumanji.views.view_test_group', name='view_test_group'),
    url(r'^T(?P<test_id>\d+)$', 'zumanji.views.view_test', name='view_test'),
)
