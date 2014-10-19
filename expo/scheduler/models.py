from django.db import models
from django.core.validators import RegexValidator
from datetime import datetime, timedelta
from model_utils.managers import InheritanceManager
from gbetext import *
from gbe.expomodelfields import DurationField

import pytz


##  Object classes for the scheduler and calendar portions of the
##  GBE web app


class Schedulable(models.Model):
    '''
    Interface for an item that can appear on a conference schedule - either an 
    event or a resource allocation. (resource allocations can include, eg, volunteer 
    commitments for a particular person, or for a particular event, or for a block
    of time - so this is a pretty flexible idea)
    Note that conference models should NEVER inherit this directly or indirectly. This is why we use the 
    indirection model: we don't want to store scheduler data in the conference model. 
    '''
    objects = InheritanceManager()
    start_time = models.DateTimeField(blank=True)

    @property 
    def duration(self):
        return self._duration
    
    @property
    def end_time(self):
        return self.start_time + self.duration
    
    def __unicode__(self):
        if self.start_time:
            return "Start: " + str(self.start_time.astimezone(pytz.timezone('America/New_York')))
        else:
            return "No Start Time"

    class Meta:
        verbose_name_plural='Schedulable Items'
    
class ResourceItem (models.Model):
    '''
    The payload for a resource
    '''
    objects = InheritanceManager()
    @property
    def payload(self):
        return self._payload

    @property 
    def _name(self):
        return self.sched_name

class Resource(models.Model):
    '''
    A person, place, or thing that can be allocated for an event. 
    A resource has a payload and properties derived from that payload. 
    This is basically a tag interface, allowing us to select all resources. 
    '''
    @property
    def item (self):
        return self._item

    pass
    
class LocationItem(ResourceItem):
    '''
    "Payload" object for a Location
    '''
    objects = InheritanceManager()


class Location(Resource):
    '''
    A resource which is a location. 
    '''
    objects = InheritanceManager()
    _item = models.ForeignKey(LocationItem)

class WorkerItem(ResourceItem):
    '''
    Payload object for a person as resource (staff/volunteer/teacher)
    '''
    objects = InheritanceManager()
    pass

class Worker (Resource):
    '''
    objects = InheritanceManager()
    An allocatable person
    '''
    _item = models.ForeignKey(WorkerItem)

class EquipmentItem(ResourceItem):
    '''
    Payload object for an allocatable item
    Not currently used
    '''
    objects = InheritanceManager()
    pass

class Equipment(Resource):
    '''
    An allocatable thing
    Not currently used. Probably needs a good bit of development before we can really use it
    (we'd like to be able to allocate single objects, sets of objects, and quantities of objects
    at the very least - this requires a bit of design)
    '''
    objects = InheritanceManager()
    _item = models.ForeignKey(EquipmentItem)

class EventItem (models.Model):
    '''
    The payload for an event (ie, a class, act, show, or generic event)
    The EventItem MUST NOT impose any DB usage on its implementing model classes. 
    ALL requirements must be stated as properties.
    '''
    objects = InheritanceManager()
    eventitem_id = models.AutoField(primary_key=True)

    @property
    def payload(self):
        return self.sched_payload

    @property 
    def duration(self):
        return self.sched_duration
    
    @property
    def describe(self):
        child = EventItem.objects.get_subclass(event=self.eventitem_id)
        ids = "event - " + str(child.event_id)
        try:
            ids += ', bid - ' + str(child.id)
        except:
            ids += ""
        return child.type + ":  " + str(child.sched_payload.get('title')) + "; ids: " + ids
    
    def __str__(self):
        return str(self.describe)
        
    def __unicode__(self):
        return unicode(self.describe)

class Event (Schedulable):
    '''
    An Event is a schedulable item with a conference model item as its payload. 
    '''
    objects = InheritanceManager()
    eventitem = models.ForeignKey(EventItem, related_name = "scheduler_events")

    @property
    def duration(self):
        return self.item._duration

    def __str__(self):
        try:
            return self.eventitem.describe
        except:
            return "No Event Item"

    def __unicode__(self):
        try:
            return self.eventitem.describe
        except:
            return "No Event Item"

class ResourceAllocation(Schedulable):
    '''
    Joins a particular Resource to a particular Event
    ResourceAllocations get their scheduling data from their Event. 
    '''
    objects = InheritanceManager()
    event = models.ForeignKey(Event, related_name="resources_allocated")
    resource = models.ForeignKey(Resource, related_name="allocations")

