from django.conf.urls import patterns, include, url

from django.contrib.auth.views import *
from scheduler import views


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'GBE_scheduler.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    
    url(r'^class/?$',
        views.class_schedule, name = 'class_schedule'),
    url(r'^events/?$',
        views.event_schedule, name = 'event_schedule'),
    url(r'^panel/?$',
        views.panel_schedule, name = 'panel_schedule'),
    url(r'^calendar/?$',
        views.calendar, name = 'calendar'),
    url(r'^calendar/(?P<cal_type>w+)/?$',
        views.calendar_view, name = 'calendar_view')
)
