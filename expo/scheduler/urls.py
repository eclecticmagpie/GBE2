from django.conf.urls import patterns, include, url
from django.contrib.auth.views import *
from scheduler import views


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'GBE_scheduler.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

# some of my urls
    url(r'^scheduler/?$',
        views.scheduler, name = 'scheduler'),
    url(r'^Events/?$',
        views.events, name = 'events'),
    url(r'^Calendar/?$',
        views.scheduler.events, name = 'scheduler_events'),
    url(r'^scheduler/event/?$',
        views.scheduler.schedule_event, name = 'scheduler_event'),

    url(r'^scheduler/master_event/?$',
        views.master, name = 'master'),
    url(r'^scheduler/master_event/create/?$',
        views.master.create, name = 'master_create'),
    url(r'^scheduler/master_event/edit',
        views.master.edit, name = 'master_edit'),
    url(r'^scheduler/event/create/?$',
        views.event.create, name = 'scheduler_event_create'),
    url(r'^scheduler/event/edit/?$',
        views.event.edit, name = 'scheduler_event_edit'),

    url(r'^Class_Schedule/?$',
        views.scheduler.classes, name = 'scheduler_class'),
    url(r'^Classes/?$',
        views.classes, name = 'class'),
    url(r'^Classes/Descriptions/?$',
        views.classes.list, name = 'class_list'),
    url(r'^classes/edit/?$',
        views.classes.edit, name = 'class_edit'),
    url(r'^Classes/Create/?$',
        views.classes.create, name = 'class_create'),
    url(r'^Classes/Teacher_Bios/?$',
        views.classes.bio, name = 'class_bio'),

    url(r'^Shows/?$',
        views.show, name = 'show'),
    url(r'^Shows/Schedule/?$',
        views.show.schedule, name ='show_schedule'),
    url(r'^Shows/Details/?$',
        views.show.list, name = 'show_list'),

# some site specific urls
    url(r'^DisplayEvent/?$',
        views.display_event, name = 'display_event'),
)  
