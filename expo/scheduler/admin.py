from django.contrib import admin

from scheduler.models import *

admin.site.register(MasterEvent)
admin.site.register(Event)
#admin.site.register(Items)
admin.site.register(Locations)
admin.site.register(Properties)

