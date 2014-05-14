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

