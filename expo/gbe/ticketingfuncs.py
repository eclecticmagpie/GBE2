# functions for connecting to ticketing code
import ticketing
from hashlib import md5
from datetime import datetime
from gbe.models import *

def compute_submission(bid_type, bid_id, user_id):
    baseURL = 'http://www.brownpapertickets.com/event/'

    classes = {'act':Act, 'vendor':Vendor}   # easier to eval, but this stuff comes from a form,
              # so we WILL NOT eval it, ever
 #   try:
    bid_class= classes[bid_type] 
 #   except IndexError:
 #       returnblob {'error'} = 'Bad bid type passed'
    bid = bid_class.objects.get(pk=bid_id)
    user = User.objects.get(pk=user_id)
    

    token_string =' '.join( map(str, [user, bid, datetime.now()]))
    token = md5(token_string).hexdigest()   
    bpt_event = ticketing.brown_paper.get_bpt_act_submit_event_id()
#    bpt_event = ticketing.models.BrownPaperEvents.objects.get(act_submission_event= True)

    link = baseURL + 'ref-'+token +'/'+bpt_event.bpt_event_id
    ref = create_referral(bid, user, token, bpt_event)
    return link


def create_referral(bid, user, token, bpt_event ):
    ref = ticketing.models.Referral()
    ref.user = user
    ref.gbe_event = bid
    ref.gbe_event_type = str(type(bid))
    ref.bpt_event = bpt_event
    ref.reference = token
    ref.codeword = '..'
    ref.save()
    return ref
