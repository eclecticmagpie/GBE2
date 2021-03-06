from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from scheduler.models import EventItem, LocationItem, WorkerItem, ActItem, ResourceAllocation
from gbetext import *    
from gbe_forms_text import *
from datetime import datetime
from datetime import timedelta
from expomodelfields import DurationField
from django.core.urlresolvers import reverse
from scheduler.functions import set_time_format
from model_utils.managers import InheritanceManager


import pytz

phone_regex='(\d{3}[-\.]?\d{3}[-\.]?\d{4})'

class Biddable (models.Model):
    '''
    Abstract base class for items which can be Bid
    Essentially, specifies that we want something with a title
    '''
    title = models.CharField(max_length=128)  
    description = models.TextField(blank=True)
    submitted = models.BooleanField(default=False)
                              
    accepted = models.IntegerField(choices=acceptance_states, 
                                   default=0, 
                                   blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name="biddable item"
        verbose_name_plural = "biddable items"
    def __unicode__(self):
        return self.title

    def typeof(self):
        return self.__class_

    def typeof(self):
        return self.__class__

    @property
    def ready_for_review(self):
        return self.submitted and self.accepted==0


class Profile(WorkerItem):
    '''
    The core data about any registered user of the GBE site, barring
    the information gathered up in the User object. (which we'll
    expose with properties, I suppose)
    '''
    user_object = models.OneToOneField(User) 
    display_name = models.CharField(max_length=128, blank=True) 
      
    # used for linking tickets  
    purchase_email = models.CharField(max_length=64, blank=True, default='') 
 
    # contact info - I'd like to split this out to its own object
    # so we can do real validation 
    # but for now, let's just take what we get

    address1 = models.CharField(max_length=128, blank=True)
    address2 = models.CharField(max_length=128, blank=True)
    city = models.CharField(max_length=128, blank=True)
    state = models.CharField(max_length=2, 
                             choices = states_options,
                             blank=True) 
    zip_code = models.CharField(max_length=10, blank=True)  # allow for ext. ZIP
    country = models.CharField(max_length=128, blank=True)
    # must have = a way to contact teachers & performers on site
    # want to have = any other primary phone that may be preferred offsite
    phone = models.CharField(max_length=50, 
                             validators=[ RegexValidator(regex=phone_regex,
                                                         message=phone_number_format_error) ])

    best_time = models.CharField(max_length=50, 
                                 choices=best_time_to_call_options, 
                                 default='Any', 
                                 blank=True)
    how_heard = models.TextField(blank=True)

    @property
    def review_header(self):
        return  (['Name', 'Username', 'Last Login', 'Email', 'Purchase Email', 'Phone', 'Action'])

    @property
    def review_summary(self):
        return  (self.display_name, self.user_object.username, self.user_object.last_login, 
                self.user_object.email, self.purchase_email, self.phone)
                
    def bids_to_review(self):
        reviews = []
        missing_reviews = []
        if  'Act Reviewers' in self.privilege_groups:
            reviews += Act().bids_to_review.exclude(bidevaluation__evaluator=self)
        if  'Class Reviewers' in self.privilege_groups:
            reviews += Class().bids_to_review.exclude(bidevaluation__evaluator=self)
        if  'Vendor Reviewers' in self.privilege_groups:
            reviews += Vendor().bids_to_review.exclude(bidevaluation__evaluator=self)
        if  'Volunteer Reviewers' in self.privilege_groups:
            reviews += Volunteer().bids_to_review.exclude(bidevaluation__evaluator=self)
        return reviews

    @property
    def contact_email(self):
        return self.user_object.email

    @property
    def contact_phone(self):
        return self.phone

    @property 
    def address(self):
        address_string =str(self.address1.strip() + '\n' + self.address2.strip()).strip()
        if len(address_string) == 0:
            return ''
        if     (len(self.city) == 0 or 
                len(self.country) == 0 or 
                len (self.state) == 0 or 
                len(self.zip_code) == 0):
            return ''
        return address_string + '\n' + ' '.join ((self.city + ',', 
                                                  self.state,  
                                                  self.zip_code, 
                                                  self.country))
        
    @property
    def special_privs(self):
        from special_privileges import special_privileges
        privs = [ special_privileges.get(group, None) for group in 
                  self.privilege_groups]
        return privs

    @property
    def privilege_groups(self):
        groups =  [ group.name for group in self.user_object.groups.all().order_by('name') ]
        return groups

    @property
    def alerts(self):
        import gbetext
        import gbe
        profile_alerts = []
        if ( len(self.display_name.strip()) == 0 or
             len(self.purchase_email.strip()) == 0  ):
             profile_alerts.append(gbetext.profile_alerts['empty_profile'] % 
                                   reverse ('profile_update', 
                                            urlconf=gbe.urls))
        expo_commitments = []
        expo_commitments += self.get_shows()
        expo_commitments += self.is_teaching()
        if (len(expo_commitments) > 0 and 
            len(self.phone.strip()) == 0):
            profile_alerts.append(gbetext.profile_alerts['onsite_phone']  % 
                                  reverse ('profile_update', 
                                           urlconf=gbe.urls))
        for act in self.get_acts():
            if act.accepted==3 and (len(act.get_scheduled_rehearsals()) == 0 or not act.tech.is_complete):
                profile_alerts.append(gbetext.profile_alerts['schedule_rehearsal'] %
                                      (act.title, reverse('act_techinfo_edit', 
                                                          urlconf=gbe.urls, args = [act.id])))
        return profile_alerts
    
    def get_volunteerbids(self):
        return self.volunteering.all()

    def get_performers(self):
        performers = self.get_personae()
        performers += self.get_troupes()
        performers += self.get_combos()
        return performers

    def get_personae(self):
        solos = self.personae.all()
        performers = list(solos)
 
        return performers
    
    def get_troupes(self):
        solos = self.personae.all()
        performers = list()
        for solo in solos:
            performers += solo.troupes.all()
        performers += Troupe.objects.filter(contact=self)
        perf_set = set(performers)
        return perf_set
    
    def get_combos(self):
        solos = self.personae.all()
        performers = list()
        for solo in solos:
            performers += solo.combos.all()
        performers += Combo.objects.filter(contact=self)
        perf_set = set(performers)
        return perf_set

    def get_acts(self):
        acts = []
        performers = self.get_performers()
        for performer in performers:
            acts += performer.acts.all()
        return acts

    def get_shows(self):
        acts = self.get_acts()
        shows = [EventItem.objects.filter(scheduler_events__resources_allocated__resource__actresource___item=act) 
                for act in acts if act.accepted==3]
        return sum([list(s) for s in shows], [])


    def get_schedule(self):
        '''
        Gets all of a person's schedule.  Every way the actual human could be committed:
        - via profile
        - via performer(s)
        - via performing in acts
        Returns schedule as a list of Scheduler.Events
        NOTE:  Things that haven't been booked with start times won't be here.
        '''
        from scheduler.models import Event
        acts = self.get_acts()
        events = sum([  list(Event.objects.filter(resources_allocated__resource__actresource___item=act))
                  for act in acts if act.accepted==3], [])
        for performer in self.get_performers():
            events += [e for e in Event.objects.filter(resources_allocated__resource__worker___item=performer)]
        events += [e for e in Event.objects.filter(resources_allocated__resource__worker___item=self)]
        return sorted(set(events), key=lambda event:event.start_time)

    def get_badge_name(self):
        badge_name = self.display_name
        if len(badge_name) == 0:
            badge_name = self.user_object.first_name
        return badge_name
 
    def is_teaching(self):
        '''
        return a list of classes this user is teaching
        (not a list of classes they are taking, that's another list)
        '''
        return self.workeritem.get_bookings('Teacher')

    def proposed_classes(self):
        
        classes = sum([list(teacher.is_teaching.all()) for teacher in self.personae.all()], [])
#        return list(set (classes))
        return classes

    def sched_payload(self):
        return { 'name': self.display_name }
                
    def __str__(self):
        return self.display_name
        
    @property
    def describe(self):
        return self.display_name
    
    def __unicode__(self):  
        return self.display_name
    
    class Meta:
        ordering = ['display_name']

        
class Performer (WorkerItem):
    '''
    Abstract base class for any solo, group, or troupe - anything that can appear
    in a show lineup or teach a class
    The fields are named as we would name them for a single performer. In all cases, 
    when applied to an aggregate (group or troup) they apply to the aggregate as a 
    whole. The Boston Baby Dolls DO NOT list awards won by members of the troupe, only
    those won by the troup. (individuals can list their own, and these can roll up if 
    we want). Likewise, the bio of the Baby Dolls is the bio of the company, not of 
    the members, and so forth. 
    '''
    objects = InheritanceManager()

    contact = models.ForeignKey(Profile, related_name='contact')
                                             # the single person the expo should 
                                             # talk to about Expo stuff. Could be the 
                                             # solo performer, or a member of the troupe,
                                             # or a designated agent, but this person
                                             # is authorized to make decisions about 
                                             # the Performer's expo appearances. 
    name = models.CharField(max_length=100,     # How this Performer is listed
                            unique=True)        # in a playbill. 
    homepage = models.URLField (blank = True)
    bio = models.TextField ()
    experience = models.PositiveIntegerField ()       # in years
    awards = models.TextField (blank = True)    
    promo_image = models.FileField(upload_to="uploads/images", 
                                   blank=True)

    festivals = models.TextField (blank = True)     # placeholder only
    
    def append_alerts(self, alerts):
        '''
        Find any alerts generated by this object's data and append them to the alerts dict
        presented as a parameter
        '''
        return alerts
    
    @property
    def promo_small(self):
        pieces = self.promo_image.name.split('/')
        pieces.insert(-1, 'mini')
        return '/'.join(pieces)

    @property
    def get_schedule(self):
        return Performer.objects.get_subclass(resourceitem_id=self.resourceitem_id).get_schedule()

    '''
        Gets all of the people performing in the act
        BB - my theory is that this should really be an abstract class, and it should be the
        subclasses, but we don't use Inheritance manager in GBE and I'm not ready for that design change.
        So... using None, because the Performer only has a contact point, not actual humans actually performing
    '''
    def get_profiles(self):
        return Performer.objects.get_subclass(resourceitem_id=self.resourceitem_id).get_profiles()

    @property
    def contact_email(self):
        return self.contact.user_object.email

    @property
    def contact_phone(self):
        return self.contact.user_object.phone
    
    @property
    def complete(self):
        return True
    
    @property
    def describe(self):
        return self.name

    def __unicode__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class Persona (Performer):
    '''
    The public persona of one person who performs or teaches. 
    May be aggregated into a group or a troupe, 
    or perform solo, or both. A single person might conceivably maintain two
    distinct performance identities and therefore have multiple
    Persona objects associated with their profile. For example, a
    person who dances under one name and teaches under another would have multiple
    Personae. 
    performer_profile is the profile of the user who dons this persona. 
    '''
    performer_profile = models.ForeignKey(Profile, related_name="personae")   

    '''
    Returns the single profile associated with this persona
    '''
    def get_profiles(self):
        return [self.performer_profile]


    @property
    def complete(self):
        return (self.performer_profile.complete and
                self.name is not '' and
                self.bio is not '')
        
    def append_alerts(self, alerts):
        '''
        Find any alerts generated by this object's data and append them to the alerts dict
        presented as a parameter
        '''
        alerts = super(Persona, self).append_alerts(alerts)
        return alerts
    
    class Meta:
        verbose_name_plural= 'personae'


            
class Troupe(Performer):
    '''
    Two or more performers working together as an established entity. A troupe
    connotes an entity with a stable membership, a history, and hopefully a
    future. This suggests that a troupe should have some sort of legal
    existence, though this is not required for GBE. Further specification
    welcomed. 
    Troupes are distinct from Combos in their semantics, but at this time they 
    share the same behavior. 
    '''
    membership = models.ManyToManyField (Persona, 
                                         related_name='troupes')

    '''
        Gets all of the people performing in the act.
        For troupe, that is every profile of every member in membership
    '''
    def get_profiles(self):
        profiles = []
        for member in Persona.objects.filter(troupes=self):
            profiles += member.get_profiles()
        return profiles

    def append_alerts(self, alerts):
        '''
        Find any alerts generated by this object's data and append them to the alerts dict
        presented as a parameter
        '''
        alerts = super(Troupe, self).append_alerts()
        return alerts



class Combo (Performer):
    '''
    Two or more performers (Personae), working together, on a temporary or ad-hoc
    basis. For example, two performers who put together a routine for the GBE
    but do not otherwise perform together would be a Combo and not a Troupe. 
    The distinction between Combo and Troupe is basically semantic, and the 
    separation is intended to aid in maintaining that semantic distinction. If 
    it is inconvenient, the separation need not persist in the code. 
    '''
    membership = models.ManyToManyField (Persona, 
                                         related_name='combos')
    '''
        Gets all of the people performing in the act.
        For  combo, that is every profile of every member in membership
    '''
    def get_profiles(self):
        profiles = []
        for member in Persona.objects.filter(combos=self):
            profiles += member.get_profiles()
        return profiles

    def append_alerts(self, alerts):
        '''
        Find any alerts generated by this object's data and append them to the alerts dict
        presented as a parameter
        '''
        alerts = super(Combo, self).append_alerts()
        return alerts


###################
# Technical info #
###################
class  AudioInfo(models.Model):
    '''
    Information about the audio required for a particular Act
    '''
    track_title = models.CharField (max_length=128, blank=True)
    track_artist = models.CharField (max_length=123, blank=True)
    track = models.FileField (upload_to='uploads/audio', blank=True)
    track_duration = DurationField(blank=True)
    need_mic = models.BooleanField (default=False, blank=True)
    own_mic = models.BooleanField(default=False, blank=True)
    notes = models.TextField (blank=True)    
    confirm_no_music = models.BooleanField (default=False)

    @property
    def dump_data(self):
       return [self.track_title, self.track_artist, self.track, self.track_duration,
               self.need_mic, self.own_mic, self.notes, self.confirm_no_music]

    @property
    def is_complete(self):
        return bool (self.confirm_no_music or
                (  self.track_title and
                   self.track_artist and
                   self.track_duration
                   ))


    @property
    def incomplete_warnings(self):
        if self.is_complete:
            return {}
        else:
            return {'audio':"Please confirm that you will have no audio playback for your performance"}


    def __unicode__(self):
        try:
            return "AudioInfo: "+ self.techinfo.act.title
        except:
            return "AudioInfo: (deleted act)"

    class Meta:
        verbose_name_plural='audio info'

class LightingInfo (models.Model):
    '''
    Information about the basic (not related to cues) lighting needs of a particular Act
      
    '''
    notes = models.TextField(blank=True, max_length=256)
    costume = models.TextField(blank=True, max_length=16)

    @property
    def dump_data(self):
       return [self.notes, self.costume]

    @property
    def is_complete (self):
        return True

    @property
    def incomplete_warnings(self):
        if self.is_complete:
            return {}
        else:
            return {"lighting":"Please check your lighting info."}

    def __unicode__(self):
        try:
            return "LightingInfo: "+self.techinfo.act.title
        except:
            return "LightingInfo: (deleted act)"

    class Meta:
        verbose_name_plural='lighting info'

	

class StageInfo(models.Model):
    '''
    Information about the stage requirements for a particular Act
    confirm field should be offered if the user tries to save with all values false and
    no notes
    '''
    act_duration = DurationField(blank=True)
    intro_text = models.TextField(blank=True)
    confirm = models.BooleanField (default = False)
    set_props = models.BooleanField (default=False)
    cue_props = models.BooleanField (default=False)
    clear_props = models.BooleanField (default=False)
    notes = models.TextField (blank=True)

    @property
    def dump_data(self):
       return [self.act_duration,self.intro_text,self.confirm, self.set_props,
               self.cue_props, self.clear_props, self.notes]
    
    @property
    def is_complete(self):
        return bool (self.set_props or 
                     self.clear_props or 
                     self.cue_props or self.confirm)

    @property
    def incomplete_warnings(self):
        if self.is_complete:
            return {}
        else:
            return {'stage':"Please confirm that you have no props requirements"}

    def __unicode__(self):
        try:
            return "StageInfo: " +self.techinfo.act.title
        except:
            return "StageInfo: (deleted act)"
    class Meta:
        verbose_name_plural='stage info'

class TechInfo (models.Model):
    '''
    Gathers up technical info about an act in a show.
    BB - doing 2 additional cues for now for an easy add to existing DB
      2015  - may want to consider a many to many field for 1+ cues 
    '''
    
    audio = models.OneToOneField (AudioInfo, blank=True)
    lighting = models.OneToOneField (LightingInfo, blank=True)
    stage = models.OneToOneField (StageInfo, blank=True)
    
    @property
    def is_complete(self):
        try:
            CueInfo.objects.get(techinfo=self, cue_sequence=0)
            cueinfopresent=True
        except CueInfo.DoesNotExist:
            cueinfopresent=False


        return bool (self.audio.is_complete and
                     self.lighting.is_complete and
                     self.stage.is_complete and 
                     cueinfopresent)
    
    def get_incomplete_warnings(self):
        warnings = {}
        
        warnings.update(self.lighting.incomplete_warnings)
        warnings.update(self.audio.incomplete_warnings)
        warnings.update(self.stage.incomplete_warnings)
        return warnings

    def __unicode__(self):
        try:
            return "Techinfo: "+ self.act.title
        except:
            return "Techinfo: (deleted act)"
    class Meta:
        verbose_name_plural='tech info'

class CueInfo(models.Model):
    '''
    Information about the lighting needs of a particular Act as they relate to one or more cues within the
    Act.  Each item is the change that occurs after a cue

    '''
    cue_sequence=models.PositiveIntegerField(default=0)
    cue_off_of = models.TextField(max_length=100)

    follow_spot = models.CharField (max_length=25,
                                    choices=follow_spot_options, 
                                    default=follow_spot_options[0])
    
    center_spot = models.CharField(max_length=20,
                                   choices=offon_options, default="OFF") 

    backlight = models.CharField(max_length=20,
                                 choices=offon_options, default="OFF") 

    cyc_color = models.CharField (max_length=25, 
                                  choices=cyc_color_options, 
                                  default=cyc_color_options[0])
    
    wash = models.CharField (max_length=25,
                             choices=stage_lighting_options, 
                             default=stage_lighting_options[0])
    sound_note = models.TextField(max_length=100, blank=True)
    
    techinfo = models.ForeignKey(TechInfo)


    @property
    def is_complete (self):
        return bool ( self.cue_off_of and self.cue_sequence and self.tech_info)

    def __unicode__(self):
        try:
            return self.techinfo.act.title+' - cue '+str(self.cue_sequence)
        except:
            return "Cue: (deleted act) - "+self.cue_sequence

    class Meta:
        verbose_name_plural='cue info'

#######
# Act #
#######

class Act (Biddable, ActItem):
    '''
    A performance, either scheduled or proposed.
    Until approved, an Act is simply a proposal. 
    Note: Act contains only information about a particular item that 
    can occupy a particular time slot in a particular performance. All
    information about performers is carried in Performer objects
    linked to Acts. 
    '''
    performer = models.ForeignKey(Performer,
                                  related_name='acts', 
                                  blank=True, 
                                  null=True )
         

    tech = models.OneToOneField(TechInfo, blank = True)
    video_link = models.URLField (blank = True)
    video_choice = models.CharField(max_length=2, 
                                    choices = video_options,
                                    blank=True) 
    shows_preferences = models.TextField(blank=True)
    why_you = models.TextField(blank=True)

    is_not_blank = ('len(%s) > 0', '%s cannot be blank')

    validation_list = [ (('title', 'Title'), is_not_blank),
                        (('description', 'Description'), is_not_blank),
                        ]
    
    def get_performer_profiles(self):
        '''
        Gets all of the performer's involved in the act.
        Useful for checking the schedules of the actual humans
        '''
        return self.performer.get_profiles()

    
    def validation_problems_for_submit(self):
        return [fn[1] %field[1] for (field, fn) in self.validation_list 
                if not eval(fn[0] % ('self.' + field[0]))]
 
    def typeof(self):
        return self.__class__

    @property 
    def contact_info(self):
                return (self.title, 
                 self.contact_email, 
                 self.accepted, 
                 self.performer.contact.phone, 
                 self.performer.contact.display_name,
                 )


    @property
    def contact_email(self):
        return self.performer.contact_email

    @property
    def contact_phone(self):
        return self.performer.contact_phone
 
    @property
    def bio(self):
        return self.performer
    
    @property
    def schedule_ready(self):
        return self.accepted == 3

    @property
    def schedule_headers(self):
        # This list can change
        return ['Performer', 'Act Title', 'Photo Link', 'Video Link', 'Bio Link', 'Order']

    @property
    def visible(self):
        return self.accepted==3
    
    @property
    def bids_to_review(self):
        return type(self).objects.filter(submitted=True).filter(accepted=0)
 
    @property
    def bid_review_header(self):
        return  (['Performer', 'Act Title', 'Last Update', 'State', 'Show', 'Reviews', 'Action'])

    @property
    def bid_review_summary(self):
        try:
            casting = ResourceAllocation.objects.filter(resource__actresource___item=self.resourceitem_id)[0]
            show_name = casting.event
        except:
            show_name = ''

        return  (self.performer.name, 
                   self.title, 
                   self.updated_at.astimezone(pytz.timezone('America/New_York')),
                   acceptance_states[self.accepted][1], show_name)


    @property
    def complete(self):
        return (self.performer.complete and
                len(self.title) > 0 and
                len(self.description) >0 and
                len(self.intro_text) >0 and
                len(self.video_choice) >0)

    @property
    def tech_ready(self):
        return (self.tech.is_complete and
                self.performer.complete and
                self.intro_text is not '')

    @property
    def alerts(self):
        '''
        Return a list of alerts pertaining to this object
        '''
        this_act_alerts=[]
        if self.complete:    
            if self.submitted:
                this_act_alerts.append(act_alerts['act_complete_submitted'] % self.id)
            else:
                this_act_alerts.append(act_alerts['act_complete_not_submitted'] % self.id)
        else:
            if self.submitted:
                this_act_alerts.append(act_alerts['act_incomplete_submitted'] % self.id)
            else:
                this_act_alerts.append(act_alerts['act_incomplete_not_submitted'] % self.id)
        
        return this_act_alerts

    @property
    def bid_fields(self):
        return (['performer',
                 'shows_preferences',
                 'title', 
                 'track_title',
                 'track_artist', 
                 'track_duration',
                 'act_duration',
                 'video_link',
                 'video_choice',
                 'description',
                 'why_you'],
                [ 'title', 'description', 'shows_preferences', 'performer'],
              )
    
    @property
    def bid_draft_fields(self):
        return (['title', 'performer'])

    @property
    def sched_payload(self):
        return { 'duration' : self.tech.stage.act_duration,
                 'title': self.title,
                 'description': self.description,
                 'details': {'type': 'act'}
             }
 
    @property
    def cast_shows(self):
        return ( ('No', 'No'), ('Yes', 'Yes'), ('Won', 'Yes - and Won!'))

    def __str__ (self):
        return str(self.performer) + ": "+self.title

				

class Room(LocationItem):
    '''
    A room at the expo center
    '''
    name = models.CharField(max_length=50)
    capacity = models.IntegerField()
    overbook_size = models.IntegerField()
    def __str__ (self):
        return self.name
    
class Event (EventItem):
    '''
    Event is the base class for any scheduled happening at the expo. 
    Events fall broadly into "shows" and "classes". Classes break down
    further into master classes, panels, workshops, etc. Shows are not
    biddable (though the Acts comprising them are) , but classes arise
    from participant bids.  
    '''
    objects = InheritanceManager()

    title = models.CharField(max_length=128)
    description = models.TextField()            # public-facing description 
    blurb = models.TextField(blank=True)        # short description
    duration = DurationField()

    notes = models.TextField(blank=True)  #internal notes about this event
    # removed because it is the single largest field Scratch and I trip over for no reason
    # this is deprecated with Resource Allocation which describes responsibilty more clearly with roles
    #owner = models.ManyToManyField(Profile)  # Responsible party
    
    event_id = models.AutoField(primary_key=True)
                                                
    def __str__(self):
        return self.title
    
    @property
    def sched_payload(self):
        
        return { 'title':self.title,
                 'description':self.description,
                 'duration':self.duration,
                 'details': {'type': ''}
               }

    @property
    def sched_duration(self):
        return self.duration
    
    @property
    def bio_payload(self):
        return None

    @property
    def calendar_type(self):
        return calendar_types[0]

    @property
    def get_tickets(self):
        return self.ticketing_item.all()
 
    class Meta:
        ordering = ['title']

class Show (Event):
    '''
    A Show is an Event consisting of a sequence of Acts.
    Future to do: remove acts as field of this class, do acceptance 
    and scheduling through scheduler  (post 2015)
    '''
    acts = models.ManyToManyField(Act, related_name="appearing_in", blank=True)
    mc = models.ManyToManyField(Persona, related_name="mc_for", blank=True)
    type = "Show"

    def __str__(self):
        return self.title
    
    @property
    def sched_payload(self):
        
        return { 'title':self.title,
                 'description':self.description,
                 'duration':self.duration,
                 'details': {'type': 'Show'}
               }
    @property
    def schedule_ready(self):
        return True      # shows are always ready for scheduling
    

class GenericEvent (Event):
    '''
    Any event except for a show or a class
    '''
    type = models.CharField(max_length=128, 
                            choices=event_options, 
                            blank=False, 
                            default="Special")
    volunteer_category = models.CharField(max_length=128,
                                          choices= volunteer_interests_options,
                                          blank = True, 
                                          default = "")

    def __str__(self):
        return self.title 

    @property
    def sched_payload(self):
        types = dict(event_options)
        payload =  {
            'type': self.type,
            'title':  self.title,
            'description' : self.description,
            'duration':self.duration,
            'details': {'type': types[self.type]},
#            'category': self.volunteer_category,
#            'parent_event': self.parent_event
            }

        if self.parent_event:
            payload['details']['parent_event'] = self.parent_event.detail_link
            payload['details']['volunteer_category'] = dict(volunteer_interests_options).get( self.volunteer_category, None)

        return payload

    @property
    def parent_event(self):
        
        if self.type != 'Volunteer':
            return None
        sevent = self.eventitem_ptr.scheduler_events.first()
        from  scheduler.models import EventContainer
        query = EventContainer.objects.filter(child_event = sevent)
        if query.count() == 0:
            return None
        parent =  query.first().parent_event
        return parent


    @property
    def schedule_ready(self):
        return True

class Class (Biddable, Event):
    '''
    A Class is an Event where one or a few people
    teach/instruct/guide/mediate and a number of participants
    spectate/participate.  Participation *may* be limited for workshops,
    but is rarely limited for anything else.  Occupancy information is requested to
    give us a general sense of the teacher's expectations.
    '''
    teacher = models.ForeignKey(Persona,  
                                related_name='is_teaching')
    
    #registration = models.ManyToManyField(Profile, 
    #                                      related_name='classes',
    #                                      blank=True)

    minimum_enrollment = models.IntegerField (blank=True, default=1)
    maximum_enrollment = models.IntegerField (blank=True, default=20)
    organization = models.CharField(max_length=128, blank=True)    
    type = models.CharField(max_length=128, 
                            choices=class_options, 
                            blank=True, 
                            default="Lecture")
    fee = models.IntegerField(blank=True, default=0)
    other_teachers = models.CharField(max_length=128, blank=True)
    length_minutes = models.IntegerField(choices=class_length_options, 
                                         default=60, blank=True)
    history =  models.TextField(max_length = 500, blank=True)
    run_before = models.TextField(max_length=500, blank=True)
    schedule_constraints = models.TextField(blank=True)
    space_needs = models.CharField(max_length=128, 
                                   choices=space_options, 
                                   blank=True, 
                                   default='Please Choose an Option')
    physical_restrictions =  models.TextField(max_length = 500, blank=True)
    multiple_run =  models.CharField(max_length=20,
                                choices=yesno_options, default="No") 

    @property
    def get_space_needs(self):
        needs = ""
        for top, top_opts in space_options:
            for key, sub_level in top_opts:
                if key == self.space_needs:
                    needs = top + " - " + sub_level

        return needs
    
    @property
    def sched_payload(self):
        
        payload = {}
        details = {}
        details= {'type' : self.type }
        if not self.fee == 0:
            details ['fee'] =  self.fee

        payload ['details'] = details
        payload['title'] =  self.event_ptr.title
        payload['description'] = self.event_ptr.description
        if not self.duration:
            from duration import Duration
            self.duration =  Duration (hours =1)
            self.save(update_fields=('duration',))
        payload['duration'] = self.duration.set_format("{1:0>2}:{2:0>2}")
        return payload

    @property
    def bio_payload(self):
        return [self.teacher]

    @property
    def calendar_type(self):
        return calendar_types[1]

    @property
    def bids_to_review(self):
        return type(self).objects.filter(submitted=True).filter(accepted=0)

    @property
    def get_bid_fields(self):
        '''
        Returns fields, required_fields as tuple of lists
        '''
        return  (['title',
                  'teacher',
                  'description', 
                  'maximum_enrollment',
                  'type', 
                  'fee', 
                  'length_minutes',
                  'history',
                  'schedule_constraints',
                  'space_needs',
              ], 
                 [ 'title', 'teacher', 'description', 'schedule_constraints'])


    @property
    def get_draft_fields(self):
        return  (['title', 'teacher'])

    @property
    def schedule_ready(self):
        return self.accepted==3

    @property
    def complete(self):
        return (self.title is not '' and
                self.teacher is not None and
                self.description is not '' and
                self.blurb is not '' 
                )
    @property
    def bid_review_header(self):
        return  (['Title', 'Teacher', 'Type', 'Last Update', 'State', 'Reviews', 'Action'])

    @property
    def bid_review_summary(self):
        return  (self.title, self.teacher, self.type,
                self.updated_at.astimezone(pytz.timezone('America/New_York')),
                acceptance_states[self.accepted][1])
    def __str__(self):
        return self.title
        

    class Meta:
        verbose_name_plural='classes'
    

    
class BidEvaluation(models.Model):
    '''
    A response to a bid, cast by a privileged GBE staff member
    '''
    evaluator = models.ForeignKey(Profile)
    vote = models.IntegerField(choices = vote_options)
    notes = models.TextField(blank='True')
    bid = models.ForeignKey(Biddable)

    def __unicode__(self):
        return self.bid.title+": "+self.evaluator.display_name


    
    
class PerformerFestivals(models.Model):
    festival = models.CharField(max_length=20, choices=festival_list)
    experience = models.CharField(max_length=20,
                                  choices=festival_experience, default='No')
    act = models.ForeignKey(Act)

    class Meta:
        verbose_name_plural='performer festivals'
    

class Volunteer(Biddable):
    '''
    Represents a conference attendee's participation as a volunteer. 
    '''
    profile = models.ForeignKey(Profile, related_name="volunteering")
    number_shifts = models.IntegerField(choices = volunteer_shift_options, default=1)
    availability = models.TextField()
    unavailability = models.TextField()
    interests = models.TextField()
    opt_outs = models.TextField(blank=True)
    pre_event = models.BooleanField(choices= boolean_options, default=False)
    background = models.TextField(blank=True)

    def __unicode__(self):
        return self.profile.display_name
    
    @property
    def bid_review_header(self):
        return  (['Name', 'Email', 'Hotel', '# Shifts', 'Scheduling Info',
                  'Interests',  'Pre-event', 'Background', 'State', 'Reviews', 'Action'])


    @property
    def bid_review_summary(self):
        interest_string = ''
        for option_id, option_value in volunteer_interests_options:
            if option_id in self.interests:
                interest_string += option_value + ', \n'
        availability_string = ''
        unavailability_string = ''
        for option_id, option_value in volunteer_availability_options:
            test = "u'"+option_id+"'"
            if test in self.availability:
                availability_string += option_value + ', \n'
            if test in self.unavailability:
                unavailability_string += option_value + ', \n'
        commitments = ''
        time_format = set_time_format(days = 2)
        for event in self.profile.get_schedule():
            commitments += str(event) + " - " + event.starttime.strftime(time_format) + ', \n'
        scheduling = "Availability: " + availability_string + "\n Conflicts: " + unavailability_string + "\n Commitments: " + commitments
        return  (self.profile.display_name, self.profile.user_object.email, self.profile.preferences.in_hotel,
                 self.number_shifts, scheduling, interest_string,
                 self.pre_event, self.background, acceptance_states[self.accepted][1])
    @property
    def bids_to_review(self):
        return type(self).objects.filter(submitted=True).filter(accepted=0)


class Vendor(Biddable):
    '''
    A request for space in the Expo marketplace. 
    Note that company name is stored in the title field inherited from Biddable, 
    and description is also inherited
    '''
    profile = models.ForeignKey(Profile)
    website = models.URLField(blank=True)
    physical_address = models.TextField()  # require physical address
    publish_physical_address = models.BooleanField(default=False)
    logo = models.FileField(upload_to="uploads/images", blank=True)
    want_help = models.BooleanField(choices = boolean_options, blank=True, default=False)
    help_description = models.TextField(blank=True)
    help_times = models.TextField(blank=True)
    def __unicode__(self): 
        return self.title  # "title" here is company name
    def validation_problems_for_submit(self):
        return []

    @property
    def bid_review_header(self):
        return  (['Bidder', 'Business Name', 'Website', 'Last Update', 'State', 'Reviews', 'Action'])

    @property
    def bid_review_summary(self):
        return (self.profile.display_name, self.title, self.website,
                self.updated_at.astimezone(pytz.timezone('America/New_York')),
                acceptance_states[self.accepted][1])
    @property
    def bids_to_review(self):
        return type(self).objects.filter(submitted=True).filter(accepted=0)


class AdBid(Biddable):
    '''
    A bid for an ad. What sort of ad? Don't know yet. To do: 
    use this
    '''
    company = models.CharField(max_length=128, blank=True)
    type = models.CharField(max_length=128, choices=ad_type_options)
    def __unicode__(self):  # Python 3: def __str__(self):
        return self.company;


class ArtBid(Biddable):
    '''
    Not used in 2015. Possibly in 2015
    '''
    bio = models.TextField(max_length=500, blank=True)
    works = models.TextField(max_length=500, blank=True)
    art1 = models.FileField(upload_to="uploads/images", blank=True)
    art2 = models.FileField(upload_to="uploads/images", blank=True)
    art3 = models.FileField(upload_to="uploads/images", blank=True)
    def __unicode__(self):  # Python 3: def __str__(self):
        return self.bidder.display_name;
                



class ClassProposal(models.Model):
    '''
    A proposal for a class that someone else ought to teach. 
    This is NOT a class bid, this is just a request that someone 
    implement this idea. 
    '''
    title = models.CharField(max_length = 128)
    name = models.CharField(max_length = 128, blank = True)
    email = models.EmailField(blank=True)
    proposal = models.TextField(max_length=100)
    type = models.CharField (max_length = 20, 
                             choices = class_proposal_choices,
                             default = 'Class')
    display = models.BooleanField(default = False)
    
    def __unicode__(self):
        return self.title
    
    @property
    def bid_review_header(self):
        return  (['Title', 'Proposal', 'Type', 'Submitter', 'Published','Action'])

    @property
    def bid_review_summary(self):
        if self.display:
            published = "Yes"
        else:
            published = ""
        return  (self.title, self.proposal, self.type, self.name, published)

    @property
    def presenter_bid_header(self):
        return  (['Title', 'Proposal'])

    @property
    def presenter_bid_info(self):
        return  (self.title, self.proposal, self.type)

class ConferenceVolunteer(models.Model):
    '''
    An individual wishing to participate in the conference as a volunteer
    (fits with the class proposal above)
    '''
    presenter = models.ForeignKey(Persona,  
                                related_name='conf_volunteer')
    bid = models.ForeignKey(ClassProposal)
    how_volunteer = models.CharField (max_length = 20, 
                             choices = conference_participation_types,
                             default = 'Any of the Above')
    qualification = models.TextField(blank='True')
    volunteering = models.BooleanField(blank='True')
    def __unicode__(self):
        return self.bid.title+": "+self.presenter.name
    
    @property
    def bid_fields(self):
        return (['volunteering',
                 'presenter',
                 'bid', 
                 'how_volunteer', 
                 'qualification'],
                ['presenter', 'bid', 'how_volunteer'],
              )
    @property
    def presenter_bid_header(self):
        return  (['Interested', 'Presenter', 'Role', 'Qualification'])


class ProfilePreferences(models.Model):
    '''
    User-settable preferences controlling interaction with the 
    Expo and with the site. 
    '''
    profile = models.OneToOneField(Profile,
                                   related_name='preferences')
    in_hotel = models.CharField(max_length=10, 
                                blank=True, 
                                choices= yes_no_maybe_options)
    inform_about = models.TextField(blank=True)
    show_hotel_infobox = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural='profile preferences'

