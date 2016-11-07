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

def AddAddress(raw_list):
    import django, os, sys, re
    os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
    sys.path.append("/opt/Kraken")
    django.setup()
    from Web_Scout.models import Addresses

    initial_address_list = re.findall(r'(?:25[0-5]|2[0-4][0-9]|1?[0-9]?[0-9])(?:\.(?:25[0-5]|2[0-4][0-9]|1?[0-9]?[0-9])){3}\/?[0-3]?[0-9]?', raw_list)
    address_list = []
    for address in initial_address_list:
        striped_address = address.strip()
        ip = striped_address.split('/')[0]
        try:
            cidr = striped_address.split('/')[1]
        except:
            cidr = "32"
        try:
            address_record = Addresses.objects.get(AddressID=ip.replace('.', '-') + '-' + cidr)
            continue
        except:
            address_list.append(ip + "/" + cidr)
            address_record = Addresses()
            address_record.AddressID = ip.replace('.', '-') + '-' + cidr
            address_record.Address = ip
            address_record.Cidr = cidr
            address_record.save()
    address_data = []
    for address in address_list:
        address_id = address.replace('.', '-').replace('/', '-')
        address_data.append([address_id, address])
    return address_data

def AddHostname(raw_list):
    import django, os, sys
    os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
    sys.path.append("/opt/Kraken")
    django.setup()
    from Web_Scout.models import Addresses

    hostnames = raw_list.split('\n')
    address_data = []
    for hostname in hostnames:
        striped_hostname = hostname.replace('\n', '').strip()
        try:
            address_record = Addresses.objects.get(striped_hostname.replace('.', '-'))
            continue
        except:
            address_record = Addresses()
            address_record.AddressID = striped_hostname.replace('.', '-')
            address_record.Hostname = striped_hostname
            address_record.save()
            address_data.append([striped_hostname.replace('.', '-'), striped_hostname])
    return address_data

def AddUrl(raw_list):
    import django, os, sys, socket
    os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
    sys.path.append("/opt/Kraken")
    django.setup()
    from Web_Scout.models import Hosts, Interfaces

    urls = raw_list.replace('\r', '').split('\n')
    address_data = []
    for url in urls:
        #extract domain
        protocol = url.split(':')[0]
        domain = url.split('/')[2]
        hostname = domain.split(':')[0]
        try:
            port = domain.split(':')[1]
        except:
            if protocol == 'http':
                port = '80'
            elif protocol == 'https':
                port = '443'
        ip = socket.gethostbyname_ex(hostname)[2][0]
        hostid = ip.replace('.', '-')

        intid = '-'.join(url.split('?')[0].split('/')[2:]).replace('.', '-')
        # check for IP, create host
        try:
            host_object = Hosts.objects.get(HostID=hostid)
            print ' host record found'
        except:
            host_object = Hosts()
            host_object.IP = ip
            host_object.HostID = hostid
            print 'new host created'
        host_object.Hostname = hostname
        host_object.save()

        # check for interface record, create interface under host
        try:
            interface_record = Interfaces.objects.get(IntID=intid)
            print 'url found'
        except:
            interface_record = host_object.interfaces_set.create()
            interface_record.IntID = intid
            print 'new url created'
        interface_record.Url = url
        interface_record.Port = port
        interface_record.ImgLink = "Web_Scout/" + intid + ".png"
        interface_record.Type = 'url'
        interface_record.save()
    return address_data

def DeleteAddress(address_list):
    import django, os, sys
    os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
    sys.path.append("/opt/Kraken")
    django.setup()
    from Web_Scout.models import Addresses

    deleted = []
    for address in address_list:
        print address
        try:
            address_record = Addresses.objects.get(AddressID=address)
            address_record.delete() 
            deleted.append(address)
        except:
            continue
    return deleted

def DeleteHost(host_list):
    import django, os, sys, re
    os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
    sys.path.append("/opt/Kraken")
    django.setup()
    from Web_Scout.models import Hosts

    deleted = []
    for host in host_list:
        print host
        try:
            host_record = Hosts.objects.get(HostID=host)
            host_record.delete()
            deleted.append(host)
        except:
            continue
    return deleted

def DeleteInterface(interface_list):
    import django, os, sys, re
    os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
    sys.path.append("/opt/Kraken")
    django.setup()
    from Web_Scout.models import Interfaces

    for interface in interface_list:
        print interface
        try:
            interface_record = Interfaces.objects.get(IntID=host)
            interface_record.delete()
        except:
            continue

def BulkAction(POSTItems, action, note=''):
    
    import django, os, sys, re
    os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
    sys.path.append("/opt/Kraken")
    django.setup()
    from Web_Scout.models import Hosts, Interfaces

    changedhosts = []
    changedinterfaces = []
    for key,value in POSTItems:
        if str(value) == "0":
            try:
                host = Hosts.objects.get(HostID=key)
                changedhosts.append(key)
                if str(action) == "bulkdelete":
                    host.delete()
                if action == "bulknote":
                    interfaces = host.interfaces_set.all()
                    interfaces.update(Notes=note)
                    for interface in interfaces:
                        changedinterfaces.append(interface.IntID)
                if action == "bulkreviewed":
                    host.Reviewed = True
                host.save()
            except:
                continue
    return [changedhosts, changedinterfaces]