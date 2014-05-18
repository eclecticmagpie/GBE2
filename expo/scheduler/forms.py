from scheduler.models import *
#from scheduler.modelsLocations import Locations

from django import forms
from django.contrib.auth.models import User
import datetime
from django.utils.timezone import utc
from django.core.exceptions import ObjectDoesNotExist
from gbe_forms_text import *


class MasterEventTabularInline(admin.TabularInline):
    '''
    Tool to create and enter data into a Master Event.
    '''

    model = MasterEvent
    
    fieldsets = [
        (None, {'fields': ['name']}),
        ('Start Time', {'fields': ['start_time']}),
        ('Stop Time', {'fields': ['stop_time']}),
        ('Blocking', {'fields': ['blocking']}),
        ('Event Types',{'fields': ['event_type']}),
        ]

class EventTabularInline(admin.TabularInline):
    '''
    Tool to create and enter data into an Event.
    '''

    model = Event
    
    fieldsets = [
        (None, {'fields': ['name']}),
        ('Hard Time', {'fields': ['hard_time']}),
        ('Soft Time', {'fields': ['soft_time']}),
        ('Blocking', {'fields': ['blocking']}),
        ('Event Types', {'fields': ['event_type']}),
        ('Include Types', {'fields': ['item_type']})
        ]

class EventIncludes():
    '''
    The fields that contain multiple entries within a Master Event.
    '''

    fieldsets = [
        ('Included Items', {'fields': ['item_list']}),
        ('Viewable', {'fields': ['viewable']}),
        ]

    inlines = [MasterEventTabularInline, EventTabularInline]

class PropertiesInclude(admin.TabularInline):
    '''
    Properties of a data object, to control object interactions.
    '''

    model = Properties

    fieldsets = [
        ('Property', {'fields': ['property_name', 'property_info']}),
        ]

from scheduler.models import *
from scheduler.modelsLocations import Locations

from django import forms
from django.contrib.auth.models import User
import datetime
from django.utils.timezone import utc
from django.core.exceptions import ObjectDoesNotExist
from gbe_forms_text import *

class LocationsTabularInline(admin.TabularInline):
	  '''
	  Form to build a location, add properties to it, etc.
	  '''

	  model = Location

	  fieldsets = [
	      ('Location Name', {'fields': ['name', 'description', 'room_type']}),
	      ]

