from django.core.serializers.json import json

###  Include methods to pack and unpack json objects.  Packs data handed to
###  to us by forms, unpack objects handed to us models.


def JsonPack(data):
    '''
    Accepts data from a form upon submission, and packs it into a JSON object.
    This JSON object can be stored in a database with minial headache.
    '''

    return json.dumps(data)

def JsonUnpack(object):
    '''
    Accepts a JSON object (presumably one that was stored in the database) 
    and unpacks it into an embedded data object.
    '''

    return json.loads(object)
