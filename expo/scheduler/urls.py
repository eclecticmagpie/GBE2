from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'GBE_scheduler.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

# some of my urls
    url(r'^scheduler/?$',
        views.scheduler, name = 'scheduler'),
    url(r'^Events/?$',
        views.events, name = 'events'),
    url(r'^Calendar',
        views.scheduler.events, name = 'scheduler_events'),
    url(r'^scheduler/event',
        views.scheduler.schedule_event, name = 'scheduler_event'),
    url(r'^scheduler/master_event/?$',
        views.master, name = 'master').
    url(r'^scheduler/master_event/create/?$',
        views.master.create, name = 'master_create'),
    url(r'^scheduler/master_event/edit',
        views.master.edit, name = 'master_edit'),
    url(r'^scheduler/event/create/?$',
        views.event.create, name = 'scheduler_event_create'),
    url(r'^scheduler/event/edit/?$',
        views.event.edit, name = 'scheduler_event_edit'),
    url(r'^Class_Schedule/?$',
        views.scheduler.class, name = 'scheduler_class'),

    url(r'^Classes/?$',
        views.class, name = 'class'),
    url(r'^Classes/Descriptions/?$',
        views.class.list, name = 'class_list'),
    url(r'^Classes/Edit/?$',
        views.class.edit, name = 'class_edit'),
    url(r'^Classes/Create/?$',
        views.class.create, name = 'class_create'),
    url(r'^Classes/Teacher_Bios/?$',
        views.class.bio, name = 'class_bio'),

# some site specific urls
    url(r'^DisplayEvent/?$',
        views.display_event, name = 'display_event'),
)  
