from django.db import models
from django.contrib.auth.models import User
import gbe

class BrownPaperSettings(models.Model):
    '''
    This class is used to hold basic settings for the interface with BPT.  It should
    contain only one row and almost never changes.
    '''
    developer_token = models.CharField(max_length=15, primary_key=True)
    client_username = models.CharField(max_length=30)
    last_poll_time = models.DateTimeField()
    
    def __unicode__(self):
        return 'Settings:  %s (%s) - %s' % (self.developer_token, 
                                            self.client_username, 
                                            self.last_poll_time)
    
    
class BrownPaperEvents(models.Model):
    '''
    This class is used to hold the BPT event list.  It defines with Brown Paper Ticket
    Events should be queried to obtain information on the Ticket Items above.  This 
    information mainly remains static - it is setup info for the interface with BPT.
    '''
    bpt_event_id = models.CharField(max_length=10, primary_key=True)
    primary = models.BooleanField(default=False)
    act_submission_event = models.BooleanField(default=False)
    
    def __unicode__(self):
        return self.bpt_event_id
        
class TicketItem(models.Model):
    '''
    This class represents a type of ticket.  Examples include 'The Whole Shebang',
    'Fan Admission', 'The Main Event', and so forth.  A ticket may admit to multiple
    events.  
    '''    
    ticket_id = models.CharField(max_length=30)
    title = models.CharField(max_length=50)
    description = models.TextField()
    active = models.BooleanField(default=False)
    cost = models.DecimalField(max_digits=20, decimal_places=2)
    linked_events = models.ManyToManyField('gbe.Event')
    datestamp = models.DateTimeField(auto_now=True)
    modified_by = models.CharField(max_length=30)

    def __unicode__(self):
        return '%s %s' % (self.ticket_id, self.title)
        
class Purchaser(models.Model):
    '''
    This class is used to hold the information for a given person who has purchased 
    a ticket at BPT.  It has all the information we can gather from BPT about the
    user.  It is meant to be mapped to a given User in our system, if we can.
    
    These are pretty much all char fields since we don't know the format of what 
    BPT (or another system) will hand back.


    Added reference, since that is a piece of data that BPT will hand back. -jpk
    '''
    
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=50, blank=True)
    state = models.CharField(max_length=50, blank=True)
    zip = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, blank=True)
    email = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    reference = models.CharField(max_length=64, blank=True) ## no, reference belongs to transaction

    # Note - if no reference exists, we have to do the hard/fun part.
    
    matched_to_user = models.ForeignKey(User,  blank=True)
    
    def __unicode__(self):
        return '%s %s (%s)' % (self.first_name, self.last_name, self.email)
        

        #jpk: rewrite this if equality ever matters. Users are not this precise. 
        # is there any case where we care about equality that isn't reference equality?
    def __eq__(self, other):
        if not isinstance(other, Purchaser):
            return False
        
        if ((self.first_name != other.first_name) or 
            (self.last_name != other.last_name) or 
            (self.address != other.address) or 
            (self.city != other.city) or 
            (self.state != other.state) or 
            (self.zip != other.zip) or 
            (self.country != other.country) or 
            (self.email != other.email) or 
            (self.phone != other.phone)):
            return False
        return True
    
    def __ne__(self, other):
        if not isinstance(other, Purchaser):
            return True
        return not self.__eq__(other)
    
    
class Transaction(models.Model):
    ''' 
    This class holds transaction records from an external source - in this case,
    Brown Paper Tickets.  Transactions are associated to a purchaser and a specific
    ticket item.
    
    Notes (jpk):
    Assuming that reference is the id that we give to BPT and they return. This will be an md5
      or other reasonable hash of a string representing the particular purchase. For example, 
      cat of username-actname-date-time-index.
      -- increased size of reference in case we want to use an algorithm that produces a larger
         digest, ie sha256
    DO NOT TRUST the amount field. We have no way of knowing the price actually paid. For 
    example, we don't know if the user has used some sort of discount code. We can produce 
    the expected amount for this transaction in a report, but we should not build it into the db
    '''
    
    ticket_item = models.ForeignKey(TicketItem, blank=True)
    purchaser = models.ForeignKey(Purchaser)
    amount = models.DecimalField(max_digits=20, decimal_places=2, blank=True)
    order_date = models.DateTimeField(blank=True)
    shipping_method = models.CharField(max_length=50, blank=True)
    order_notes = models.TextField(blank=True)
    reference = models.CharField(max_length=64, blank=True)
    payment_source = models.CharField(max_length=30, blank=True)
    import_date = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return '%s (%s)' % (self.reference, self.purchaser)
    
class Referral(models.Model):
    '''
    Represents a referral of a user from GBE to BPT. A referral is any occasion when
    GBE generates a link to a BPT purchase and presents that link to a GBE user.
    
    user: GBE user object
    datetime: the timestamp when the referral was generated
    reference: the reference generated for this referral.
    codeword: a GBE-internal human-readable word (randomly selected from the dictionary)
       (we might not use this)
    event: the event cited in the referral. (may not correspond to what they 
        actually purchase - note that we can only pass one event to BPT)


    There are many complications about linking Transactions to Referrals and Purchasers. 

    '''
    user = models.ForeignKey(User)
    gbe_event = models.ForeignKey('gbe.Event')
    gbe_event_type = models.CharField(max_length=40, blank=True)
    bpt_event = models.ForeignKey(BrownPaperEvents)
    datetime = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=64)
    codeword = models.CharField(max_length=20)


# I want this field, but django is resisting 

    def __unicode__(self):
        return '%s %s %s %s' %(self.user.profile.display_name, 
                               self.datetime, 
                               self.codeword, 
                               self.gbe_event)
