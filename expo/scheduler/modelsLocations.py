from django.db import models
from django.core.validators import RegexValidator
from gbetext import *    # all literal text including option sets lives in gbetext.py
from django.core.serializers.json import json

###  Object classes to manage locations and rooms.

class Locations(models.Model, Schedulable, Properties):
    '''
    The types of locations available at the event site.  Has
    Properties for the various qualities of the space (has carpet
    or no, has movement space, has tables and chairs, etc).
    '''

    def __str__(self):
        return name

    name = models.CharField(max_length=32)
    description = models.TextField()

    ###  room_type is a choice from available room types,
    ###  which are stored as a JSON object containing 
    ###  a tuple of tuple pairs.  Can only have one type,
    ###  otherwise, is a type of property
    room_type = models.CharField(max_length=16)


