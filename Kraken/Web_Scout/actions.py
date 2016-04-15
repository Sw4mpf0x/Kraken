def database_clear():
	import psycopg2 as psql
	try:
		conn = psql.connect("dbname='kraken_db' user='kraken' host='127.0.0.1' password='kraken'")
		cur = conn.cursor()
		print "Clearing tables..."
		cur.execute("""DELETE FROM "Web_Scout_ports";""")
		cur.execute("""DELETE FROM "Web_Scout_hosts";""")
		conn.commit()
		conn.close()
		return "Database successfully cleared."
	except:
		return "Unable to connect to database..."

def nmap_parse(filepath):
	import xml.etree.cElementTree as ET
	import os,sys
	import django
	os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
	sys.path.append("/opt/Kraken")
	django.setup()
	from Web_Scout.models import Hosts,Ports

	nmap = ET.parse(filepath)
	root = nmap.getroot()
	for host in root.findall('host'):
		host_object = Hosts()
		host_object.Rating = ""
		host_object.IP = host[1].get('addr')
		hostnames = host.find('hostnames')
		try:
			host_object.Hostname = hostnames[0].get('name')
			if not host_object.Hostname:
				host_object.Hostname = ""
		except:
			host_object.Hostname = ""
		host_object.save()
		for port in host[3].findall('port'):
			port_object = host_object.ports_set.create()
			try:
				host_object.DeviceType = port[1].get('devicetype')
				if not host_object.DeviceType:
					host_object.DeviceType = ""
			except:
				host_object.DeviceType = ""
			try:
				host_object.OS = port[1].get('ostype')
				if not host_object.OS:
					host_object.OS = ""
			except:
				host_object.OS = ""
			
			port_object.Port = port.get('portid')
			port_object.Name = port[1].get('name')
			if not port_object.Name:
				port_object.Name = ""
	
			try:
				port_object.Product = port[1].get('product')
				if not port_object.Product:
					port_object.Product = ""
			except:
				port_object.Product = ""
			try:
				port_object.Version = port[1].get('version')
				if not port_object.Version:
					port_object.Version = ""
			except:
				port_object.Version = ""
			try:
				port_object.Extra_Info = port[1].get('extra_info')
				if not port_object.Extra_Info:
					port_object.Extra_Info = ""
			except:
				port_object.Extra_Info = ""
			
			port_object.PortID = host_object.IP.replace('.', '') + port_object.Port

			#Need to test this
			port_object.Banner = ""
			port_object.ImgLink = "Web_Scout/" + host_object.IP.replace('.', '') + port_object.Port + ".png" 
			port_object.Banner = ""

			if host_object.Hostname:
				if port_object.Port == "80":
					port_object.Link = "http://" + host_object.Hostname
				elif port_object.Port == "443" or port_object.Port == "8443" or port_object.Port == "12443":
					port_object.Link = "https://" + host_object.Hostname
				else:
					port_object.Link = "http://" + host_object.Hostname + ":" + port_object.Port
			else:
				if port_object.Port == "80":
					port_object.Link = "http://" + host_object.IP
				elif port_object.Port == "443" or port_object.Port == "8443" or port_object.Port == "12443":
					port_object.Link = "https://" + host_object.IP
				else:
					port_object.Link = "http://" + host_object.IP + ":" + port_object.Port
			
			port_object.save()
		host_object.save()


