#/usr/bin/python

def BuildQuery(query_string, search_fields):
    import re
    from django.db.models import Q

    def NormalizeQuery(query_string,
                    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):

        return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)]
    ''' Returns a query, that is a combination of Q objects. That combination
        aims to search keywords within a model by testing the given search fields.
    '''
    # Thank you @squarepegsys
    # Taken from https://github.com/squarepegsys/django-simple-search/blob/master/django-simple-search/utils.py
    query = None # Query to search for every search term
    terms = NormalizeQuery(query_string)
    for term in terms:
        or_query = None # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})

            if or_query:
                or_query = or_query |q
            else:
                or_query = q


        if query:
            query = query | or_query
        else:
            query = or_query
    return query

def LogKrakenEvent(user, message, logtype):
    import datetime
    from Logs.models import KrakenLog
    log_entry = KrakenLog()
    log_entry.TimeStamp = datetime.datetime.now()
    log_entry.User = user
    log_entry.Message = message
    log_entry.Type = logtype
    log_entry.save()
