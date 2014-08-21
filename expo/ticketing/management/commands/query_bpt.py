## simple script to query Brown Paper Tickets and insert any transactions found into the database
## Depends on brown_paper.py

from django.core.management.base import BaseCommand, CommandError
from ticketing.brown_paper import *

class Command (BaseCommand):

    def handle(self, *args, **kwargs):
        api_call = orderlist_api_url % ( get_bpt_developer_id(), 
                                         get_bpt_act_submit_event_id(),
                                         get_bpt_account_id(),
                                     )
        
        result_tree = perform_bpt_api_call (api_call)
        parse_and_insert (result_tree)


    



