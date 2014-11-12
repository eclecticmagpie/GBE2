from django.shortcuts import render, get_object_or_404, render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.forms import UserCreationForm
from django.template import loader, RequestContext
from scheduler.models import *
from scheduler.forms import *
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth import login, logout, authenticate
from django.forms.models import inlineformset_factory
import gbe_forms_text
from django.core.urlresolvers import reverse
from datetime import datetime
from datetime import time as dttime
from table import table
from gbe.duration import Duration
from scheduler.functions import tablePrep

# Create your views here.


def validate_profile(request):
    '''
    Return the user profile if any
    '''
    from gbe.models import Profile
    if request.user.is_authenticated():
        try:
            return request.user.profile
        except Profile.DoesNotExist:
            return False


def validate_perms(request, perms):
    '''
    Validate that the requesting user has the stated permissions
    Returns profile object if perms exist, False if not
    '''
    profile = validate_profile(request)
    if not profile:
        return False
    if any([perm in profile.privilege_groups for perm in perms]):
        return profile
    return False

def selfcast(sobj):
    '''
    Takes a scheduler object and casts it to its underlying type. 
    This can (will) fail if object ids are out of sync, see issue 145 
    Pretty rudimentary, can probably be improved
    '''
    try:
        return sobj.typeof().objects.get(pk=sobj.child.id)
    except:
        return sobj


def get_events_display_info():
    '''
    Helper for displaying lists of events. Gets a supply of conference event items and munges 
    them into displayable shape
    "Conference event items" = things in the conference model which extend EventItems and therefore 
    could be Events
    '''
    eventitems = EventItem.objects.select_subclasses()
    eventitems = [{'eventitem': item, 
                   'confitem':selfcast(item), 
                   'scheduled_events':item.scheduler_events.all()}
                  for item in eventitems]
    eventslist = [ {'title' : entry['confitem'].sched_payload['title'],
                    'locations': [event.location for event in entry['scheduled_events']],
                    'datetime': [event.start_time for event in entry['scheduled_events']],
                    'duration': entry['confitem'].sched_payload['duration'],
                    'type':entry['confitem'].sched_payload['details']['type'],
                    'detail': reverse('detail_view', urlconf='scheduler.urls', 
                                      args = [entry['eventitem'].eventitem_id]),
                    'edit': reverse('edit_event', urlconf='scheduler.urls', 
                                    args =  [entry['eventitem'].eventitem_id]),
                    }
                   for entry in eventitems]
    return eventslist

def get_event_display_info(eventitem_id):
    '''
    Helper for displaying a single of event. Same idea as get_events_display_info - but for
    only one eventitem.  
    '''
    item = selfcast(EventItem.objects.get_subclass(event=eventitem_id))
    
    eventitem_view = {'event': item, 
                      'scheduled_events':item.scheduler_events.all()}

    return eventitem_view

def class_schedule(request):
    '''
    Schedule a class.
    '''

    pass



def event_schedule(request, event_id):
    '''
    Schedule a event: create a scheduler.event object, set start time/day, and allocate a room
    '''
    


@login_required
def event_list(request):
    '''
    List of events (all)
    '''
    profile = validate_perms(request, ('Scheduling Mavens',))
    if not profile:
        return HttpResponseRedirect(reverse('home', urlconf = 'gbe.urls'))
                                                             
    header  = [ 'Title','Location','Date/Time','Duration','Type','Detail', 'Edit Schedule']
    events = get_events_display_info()


    template = 'scheduler/events_review_list.tmpl'
    return render(request, template, { 'events':events, 'header':header})




def panel_schedule(request):
    '''
    Schedule a panel.
    '''

    pass

def calendar(request, cal_format = 'Block'):
    '''
    Top level calendar object.  Overall calendar for a site, sets some options,
    then calls calendar_view.
    '''

    pass

#def calendar_view(request, cal_type = 'Event', cal_format = 'Block'):
#    '''
#    Accepts a calendar type, and renders a calendar for that type.  Type can be
#    an event class, an event instance (shows what is scheduled within that
#    event), an event reference (shows a calendar of just every instance of
#    that event), or a schedulable items (which shows a calendar for that item).
#    '''

#    pass

def detail_view(request, eventitem_id):
    '''
    Takes the id of a single event and displays all its details in a template
    '''
    eventitem_view = get_event_display_info(eventitem_id)
    template = 'scheduler/event_detail.tmpl'
    return render(request, template, {'eventitem': eventitem_view,
                                      'show_tickets': True,
                                      'tickets': eventitem_view['event'].get_tickets,
                                      'user_id':request.user.id})


def edit_event(request, eventitem_id):
    '''
    Add an item to the conference schedule and/or set its schedule details (start
    time, location, duration, or allocations)
    Takes a scheduler.EventItem id
    '''
    profile = validate_perms(request, ('Scheduling Mavens',))
    if not profile:
        return HttpResponseRedirect(reverse('home', urlconf = 'gbe.urls'))

    if request.method=='POST':
        item =  EventItem.objects.get_subclass(eventitem_id=eventitem_id)        

        if len(item.scheduler_events.all())==0:
               # Creating a new scheduler.Event and allocating a room
            event_form = EventScheduleForm(request.POST, 
                                     prefix='event')
        else:
            event_form = EventScheduleForm(request.POST, 
                                           instance = item.scheduler_events.all()[0],
                                           prefix='event')
        if (event_form.is_valid()  and True):
            s_event=event_form.save(commit=False)
            s_event.eventitem = item
            data = event_form.cleaned_data
            s_event.save()            
            from gbe.models import Room
            li  = Room.objects.get(name=data.get('location'))
            
            try:
                res = Location.objects.get(_item=li)
            except:
                res = Location()
                res._item = li.locationitem
                res.save()        
        

            loc_allocation = ResourceAllocation()
            loc_allocation.event = s_event
            loc_allocation.resource = res
            loc_allocation.save()
                # next: set duration on child
            

            item.duration = data['duration']
            item.save(update_fields=['duration'])

            return HttpResponseRedirect(reverse('home', urlconf='gbe.urls'))
        else:
            return HttpResponseRedirect(reverse('home', urlconf='gbe.urls'))
    eventitem_view = get_event_display_info(eventitem_id)
    template = 'scheduler/event_schedule.tmpl'
    eventform = EventScheduleForm( prefix='event')
    return render(request, template, {'eventitem': eventitem_view,
                                      'form': eventform,
                                      'show_tickets': True,
                                      'tickets': eventitem_view['event'].get_tickets,
                                      'user_id':request.user.id})
    
def calendar_view(request, cal_type = 'Event', cal_times = (datetime(2015, 02, 20, 18, 00), datetime(2015, 02, 23, 00,00))):
    '''
    A view to query the database for events of type cal_type over the period of time cal_times,
    and turn the information into a calendar in black format for display.

    Or it will be, eventually.  Right now it is using dummy event information for testing purposes.
    Will add in database queries once basic funcationality is completed.
    '''

    duration = Duration(minutes = 60)

    events = []
    events.append({'text': 'Horizontal Pole Dancing 101', \
        'link': 'http://some.websi.te', \
        'starttime': datetime(2015, 02, 07, 9, 00), \
        'stoptime': datetime(2015, 02, 07, 10, 00), \
        'location': 'Paul Revere', 'Type': 'Movement Class'})

    events.append({'text': 'Shimmy Shimmy, Shake', \
        'link': 'http://some.new.websi.te', \
        'starttime': datetime(2015, 02, 07, 13, 00), \
        'stoptime': datetime(2015, 02, 07, 14, 00), \
        'location': 'Paul Revere', 'Type': 'Movement Class'})

    events.append({'text': 'Jumpsuit Removes', \
        'link': 'http://some.other.websi.te', \
        'starttime': datetime(2015, 02, 07, 10, 00), \
        'stoptime': datetime(2015, 02, 07, 11, 00), \
        'location': 'Paul Revere', 'Type': 'Movement Class'})

    events.append({'text': 'Tax Dodging for Performers', \
        'link': 'http://yet.another.websi.te', \
        'starttime': datetime(2015, 02, 07, 11, 00), \
        'stoptime': datetime(2015, 02, 07, 12, 00), \
        'location': 'Paul Revere', 'Type': 'Business Class'})

    events.append({'text': 'Butoh Burlesque', \
        'link': 'http://japanese.websi.te', \
        'starttime': datetime(2015, 02, 07, 9, 00), \
        'stoptime': datetime(2015, 02, 07, 10, 00), \
        'location': 'Thomas Atkins', 'Type': 'Movement Class'})

    events.append({'text': 'Kick Left, Kick Face, Kick Ass: Burly-Fu', \
        'link': 'http://random.new.websi.te', \
        'starttime': datetime(2015, 02, 07, 14, 00), \
        'stoptime': datetime(2015, 02, 07, 16, 00),\
        'location': 'Thomas Atkins', 'Type': 'Movement Class'})

    events.append({'text': 'Muumuus A-Go-Go',
        'shortDesc': 'Dancing in Less-then-Sexy Clothing', \
        'link': 'http://some.bad.websi.te', \
        'starttime': datetime(2015, 02, 07, 10, 00), \
        'stoptime': datetime(2015, 02, 07, 12, 00), \
        'location': 'Thomas Atkins', 'Type': 'Movement Class'})

    events.append({'text': 'From Legalese to English, Contracts in Burlesque', \
        'link': 'http://still.another.websi.te', \
        'starttime': datetime(2015, 02, 07, 12, 00), \
        'stoptime': datetime(2015, 02, 07, 13, 00), \
        'location': 'Thomas Atkins', 'Type': 'Business Class'})


    Table = {}
    Table['rows'] = tablePrep(events, duration)
    Table['Name'] = 'Event Calendar for the Great Burlesque Expo of 2015'
    Table['Link'] = 'http://burlesque-expo.com'
    Table['X_Name'] = {}
    Table['X_Name']['Text'] = 'Rooms'
    Table['X_Name']['Link'] = 'http://burlesque-expo.com/class_rooms'   ## Fix This!!!

    template = 'scheduler/Sched_Display.tmpl'

    return render(request, template, Table)
