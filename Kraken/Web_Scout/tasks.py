from __future__ import absolute_import, division
from celery import task, current_task, group
from time import sleep	
from PIL	  import Image, ImageDraw, ImageFont
from Kraken.krakenlib import LogKrakenEvent
import sys
import traceback
import os.path
import requests
import StringIO
import shutil
import signal
import ssl

reload(sys)
sys.setdefaultencoding("utf8")

@task
def cleardb():
	import django
	os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
	sys.path.append("/opt/Kraken")
	django.setup()
	from Web_Scout.models import Hosts,Interfaces

	# Delete all recods in the Hosts and Interfaces tables.
	try:
		Hosts.objects.all().delete()
		Interfaces.objects.all().delete()
		LogKrakenEvent('Celery', 'Hosts and interfaces cleared.', 'info')
	except:
		LogKrakenEvent('Celery', 'Error clearing database.', 'error')

@task
def removescreenshots():
	# Build list of all current screenshots.
	screenshotlist = [ f for f in os.listdir("/opt/Kraken/static/Web_Scout/")]
	
	# Remove each screenshot from the list.
	for screenshot in screenshotlist:
		os.remove('/opt/Kraken/static/Web_Scout/' + screenshot)
	LogKrakenEvent('Celery', 'Screenshots deleted.', 'info')

@task
def nmap_parse(filepath, targetaddress=''):
	import xml.etree.cElementTree as ET
	import os
	import datetime
	import django
	os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
	sys.path.append("/opt/Kraken")
	django.setup()
	from Web_Scout.models import Addresses, Hosts, Interfaces

	# Known HTTP ports.
	HttpPorts = [80, 280, 443, 591, 593, 981, 1311, 2031, 2480, 3181, 4444, 4445, 4567, 4711, 4712, 5104, 5280, 7000, 7001, 7002, 8000, 8008, 8011, 8012, 8013, 8014, 8042, 8069, 8080, 8081, 8243, 8280, 8281, 8443, 8531, 8887, 8888, 9080, 9443, 11371 ,12443, 16080, 18091, 18092]
	timestamp = datetime.datetime.now()

	# Parse Nmap XML using provided path. Uses xml.etree.cElementTree to parse.
	print('parsing ' + filepath) 
	nmap = ET.parse(filepath)
	root = nmap.getroot()

	# Loop through all hosts found.
	for host in root.findall('host'):
		print('Host ' + host[1].get('addr') + ' found')

		# Extract IP address
		ipaddress = host[1].get('addr')

		try:
			# Attempt to locate the each host in the Hosts database table.
			host_object = Hosts.objects.get(HostID=ipaddress.replace('.', '-'))
			print host_object
			print('Existing host')

			# If found, the host is no longer stale. If a host cannot be reached, 
			# it will not be in the Nmap XML.
			host_object.Stale = False
			host_object.StaleLevel = 0

			# After the initial scan, which designates each host as 'new', each 
			# subsequent scan will ensure the host is no longer indicated as new.
			host_object.New = False
		except:
			# If the host is not present in the database, create a host record.
			# targetaddress indicates that this parsing is the result of the scan 
			# functionality. When a scan is performed, hosts are created with a 
			# relationship to the address selected to scan
			if targetaddress:
				print "Creating new host record under Address"
				address_record = Addresses.objects.get(AddressID=targetaddress.replace('.', '-').replace('/', '-'))
				host_object = address_record.hosts_set.create()
				host_object.New = True
			else:
				host_object = Hosts()

		host_object.HostID = ipaddress.replace('.', '-')
		host_object.Rating = ""
		host_object.IP = ipaddress

		# Get hostname
		hostnames = host.find('hostnames')
		try:
			host_object.Hostname = hostnames[0].get('name')
			if not host_object.Hostname:
				host_object.Hostname = ""
		except:
			host_object.Hostname = ""
		
		# Timestamp to indicate that the host was seen during this scan.
		host_object.LastSeen = timestamp
		host_object.save()

		# Loop through all ports for each host
		ports = host.find('ports')
		for port in ports.findall('port'):
			# The port must be open and present in the HttpPorts list in order to be added.
			if port[0].get('state') == 'open' and int(port.get('portid')) in HttpPorts or 'http' in str(port[1].get('extrainfo')) or 'http' in str(port[1].get('product')): 
				print('Port ' + port.get('portid') + ' found.')
				
				# All interfaces records are tied to hosts in the database using relational mapping.
				# Attempt to locate interface record for this host and port combination.
				try:
					interface_object = Interfaces.objects.get(host_object.HostID + '-' + port.get('portid'))
				# If not, create one.
				except:
					interface_object = host_object.interfaces_set.create()
				
				# Set port Category using the Nmap devicetype value. This can change during the source code-based categorization
				# the screenshot process performs.
				try:
					host_object.Category = port[1].get('devicetype')
					if not host_object.Category:
						host_object.Category = ""
				except:
					host_object.Category = ""

				# Set host OS
				try:
					host_object.OS = port[1].get('ostype')
					if not host_object.OS:
						host_object.OS = ""
				except:
					host_object.OS = ""
				
				# Set port number and name
				interface_object.Port = port.get('portid')
				interface_object.Name = port[1].get('name')
				if not interface_object.Name:
					interface_object.Name = ""
		
				# Set port product. This can change during the source code-based credential
				# checking the screenshot process performs.
				try:
					interface_object.Product = port[1].get('extrainfo')
					if not interface_object.Product:
						interface_object.Product = ""
				except:
					interface_object.Product = ""

				# Set port version information
				try:
					interface_object.Version = port[1].get('version')
					if not interface_object.Version:
						interface_object.Version = ""
				except:
					interface_object.Version = ""
				
				# Set port database identification
				interface_object.IntID = host_object.IP.replace('.', '-') + '-' + interface_object.Port

				interface_object.Banner = ""
				# The ImgLink is used on the front end to display screenshots.
				interface_object.ImgLink = "Web_Scout/" + host_object.IP.replace('.', '-') + '-' + interface_object.Port + ".png" 
				interface_object.Banner = ""

				# Determine the corrent URL protocol to assign.
				# Hostname is preferred over IP due to virtual hosts.
				if host_object.Hostname:
					if interface_object.Port == "80":
						interface_object.Url = "http://" + host_object.Hostname
					elif interface_object.Port == "443" or interface_object.Port == "8443" or interface_object.Port == "12443":
						interface_object.Url = "https://" + host_object.Hostname
					else:
						interface_object.Url = "http://" + host_object.Hostname + ":" + interface_object.Port
				else:
					if interface_object.Port == "80":
						interface_object.Url = "http://" + host_object.IP
					elif interface_object.Port == "443" or interface_object.Port == "8443" or interface_object.Port == "12443":
						interface_object.Url = "https://" + host_object.IP
					else:
						interface_object.Url = "http://" + host_object.IP + ":" + interface_object.Port
				# Indicate that this Interface record is create from a port, 
				# rather than a specific URL path.
				interface_object.Type = 'port'
				interface_object.save()
		host_object.save()

	# Check Hosts and Interfaces table for duplicates and remove them. 
	print('Checking for duplicates.')
	for row in Interfaces.objects.all():
		if Interfaces.objects.filter(IntID=row.IntID).count() > 1:
			row.delete()
	for row in Hosts.objects.all():
		if Hosts.objects.filter(HostID=row.HostID).count() > 1:
			row.delete()

	number_of_hosts = Hosts.objects.all().count()
	number_of_interfaces = Interfaces.objects.all().count()
	LogKrakenEvent('Celery', 'Parsing Complete. Hosts: ' + str(number_of_hosts) + ', Interfaces: ' + str(number_of_interfaces), 'info')

# The framework for this functionality was taken from httpscreenshot.py 
# (https://github.com/breenmachine/httpscreenshot)
@task(time_limit=120)
def getscreenshot(urlItem, tout, debug, proxy, overwrite):
	import django, os, sys
	os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
	sys.path.append("/opt/Kraken")
	django.setup()
	from Web_Scout.models import Hosts,Interfaces
	from selenium import webdriver
	
	# Used to setup a headless, selenium PhantomJS web driver
	def setupBrowserProfile(tout, proxy):
		browser = None

		# Proxy framework for future implementation. Set PhantomJS arguments.
		# Arguments are used to disabled SSL security features in the web driver.
		if(proxy is not None):
			service_args=['--ignore-ssl-errors=true','--ssl-protocol=tlsv1','--proxy='+proxy,'--proxy-type=socks5']
		else:
			service_args=['--ignore-ssl-errors=true', '--ssl-protocol=any', '--web-security=false']
		
		# Create the web driver.
		while(browser is None):
			try:
				browser = webdriver.PhantomJS(service_args=service_args, executable_path="phantomjs")
				# The window size is used to control the size of the screenshot taken.
				browser.set_window_size(1024, 768)
				browser.set_page_load_timeout((tout))
			except Exception as e:
				print e
				browser.quit()
				sleep(1)
				continue
		return browser
	
	# Used to screenshot basic auth. Needs testing.
	def writeImage(text, filename, fontsize=200, width=1024, height=768):
		image = Image.new("RGBA", (width,height), (255,255,255))
		draw = ImageDraw.Draw(image)
		font_path = "/opt/Kraken/common/fonts/LiberationSerif-BoldItalic.ttf"
		font = ImageFont.truetype(font_path, fontsize)
		draw.text((80, 250), text, (0,0,0), font=font)
		image.save(filename)
	
	# Perform basic request to web interface to test HTTP response code.
	def doGet(*args, **kwargs):
		url		= args[0]
		proxy = kwargs.pop('proxy',None)
	
		kwargs['allow_redirects'] = False
		session = requests.session()
		if(proxy is not None):
			print proxy
			session.proxies={'http':'socks5://'+proxy,'https':'socks5://'+proxy}
		print '[+] Getting ' + url[0]
		try:
			resp = session.get(url[0],**kwargs)
		except requests.exceptions.Timeout:
			resp = "Timeout"
		except requests.exceptions.SSLError as e:
			print e
			resp = "SSL Error"
		return resp

	# Used to compare interface source code to a list of application signatures to 
	# determine potential defaults credentials and categorization.
	def default_creds(interface_record, source_code):
		print 'Checking for default creds'
		try:
			# File system paths to signature files.
			sigpath = '/opt/Kraken/Web_Scout/signatures.txt'

			with open(sigpath) as sig_file:
				signatures = sig_file.readlines()

			interface_record.Default_Credentials = ""
			interface_record.save()

			# Loop through and see if there are any matches from the source code
			# This functionality was adapted from EyeWitness (https://github.com/ChrisTruncer/EyeWitness)
			if source_code is not None:
				for sig in signatures:

					# Find the signature(s), split them into their own list if needed
					# Assign default creds to its own variable
					sig_list = sig.split('|')
					page_identifiers = sig_list[0].split(";")
					page_id = sig_list[1].strip()
					credential_info = sig_list[2].strip()
					module = sig_list[3].strip()
					category = sig_list[4].strip()
					rating = sig_list[5].strip()

					# Set our variable to 1 if the signature was not identified.  If it is
					# identified, it will be added later on.  Find total number of
					# "signatures" needed to uniquely identify the web app
					# signature_range = len(page_sig)
	
					# This is used if there is more than one "part" of the
					# web page needed to make a signature Delimete the "signature"
					# by ";" before the "|", and then have the creds after the "|"
					if all([x.lower() in source_code.lower() for x in page_identifiers]):
						print('Interface Identified as: ' + page_id)
						if interface_record.Default_Credentials is None:
							interface_record.Default_Credentials = credential_info
						else:
							interface_record.Default_Credentials += '\n' + credential_info
						if module:
							interface_record.hosts.Module = module
						interface_record.Product = page_id
						interface_record.hosts.Category = category
						interface_record.hosts.Rating = rating
						interface_record.hosts.save()
						interface_record.save()
				host_record = interface_record.hosts
    	
		except IOError:
			print("[-] WARNING: Credentials file not in the same directory"
				" as Kraken")
			print '[-] Skipping credential check'
			return

	# Set screenshot size. Matches screen size of web driver.
	box = (0, 0, 1024, 768)
	browser = None

	# Retrieve interface record.
	interface_record = Interfaces.objects.get(IntID=urlItem[1])

	# Set screenshot file name.
	screenshotName = '/opt/Kraken/static/Web_Scout/' + urlItem[1]
	if(debug):
		print '[+] Got URL: '+urlItem[0]
		print '[+] screenshotName: ' + screenshotName + '.png'

	# If screenshot exists and the option to overwrite screenshots was not 
	# selected, go to next interface.
	if os.path.exists(screenshotName+".png") and overwrite == False:
		if(debug):
	 		print "[-] Screenshot already exists, skipping"
	 	if not interface_record.Retry:
			return

	# Setup Headless Selenium instance
	try:
		browser = setupBrowserProfile(tout, proxy)
	except:
		if(debug):
			print "[-] Oh no! Couldn't create the browser, Selenium blew up"
			exc_type, exc_value, exc_traceback = sys.exc_info()
			lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
			print ''.join('!! ' + line for line in lines)
		return

	# Main screenshot-taking logic.
	try:
		resp = doGet(urlItem, verify=False, timeout=tout, proxy=proxy)
		
		# Handle basic auth
		try:
			if resp == "Timeout":
				print "[-] Connection to " + urlItem[0] + " timed out"
				writeImage("Timed Out",screenshotName + ".png")
				browser.quit()
				return
			elif(resp is not None and resp.status_code == 401):
				print urlItem[0]+" Requires HTTP Basic Auth"
				writeImage(resp.headers.get('www-authenticate','NO WWW-AUTHENTICATE HEADER'),screenshotName + ".png")
				browser.quit()
				return
		except:
			print "[-] SSL Exception for" + urlItem[0]
		
		# Handle all other responses
		if(resp is not None):
			if(debug):
				print '[+] Got response for ' + urlItem[0]
			
			
			old_url = browser.current_url
			browser.get(urlItem[0].strip())
			if(browser.current_url == old_url):
				print "[-] Error fetching in browser but successfully fetched with Requests: " + urlItem[0]
				if(debug):
					print "[+] Trying with sslv3 instead of TLS - known phantomjs bug: " + urlItem[0]
				browser2 = webdriver.PhantomJS(service_args=['--ignore-ssl-errors=true'], executable_path="phantomjs")
				old_url = browser2.current_url
				browser2.get(urlItem[0].strip())
				if(browser2.current_url == old_url):
					if(debug):
						print "[-] Didn't work with SSLv3 either..." + urlItem[0]
					browser2.quit()
					shutil.copy('/opt/Kraken/static/blank.png', screenshotName + '.png')
				else:
					print '[+] Saving: ' + screenshotName + '.png'
					screen = browser.get_screenshot_as_png()
					im = Image.open(StringIO.StringIO(screen))
					region = im.crop(box)
					interface_record.Retry = False
					interface_record.save()
					region.save(screenshotName+".png", 'PNG', optimize=True, quality=95)
					browser2.quit()
					return

			print '[+] Saving: ' + screenshotName + '.png'
			screen = browser.get_screenshot_as_png()
			im = Image.open(StringIO.StringIO(screen))
			region = im.crop(box)
			region.save(screenshotName+".png", 'PNG', optimize=True, quality=95)
			default_creds(interface_record, browser.page_source)
			interface_record.Retry = False
			interface_record.save()
			browser.quit()
	except Exception as e:
		print e
		browser.set_window_size(1024, 768)
		if(debug):
			exc_type, exc_value, exc_traceback = sys.exc_info()
			lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
			print ''.join('!! ' + line for line in lines) 
		browser.quit()
		interface_record.Retry = True
		interface_record.save()
		shutil.copy('/opt/Kraken/static/blank.png', screenshotName + '.png')
		return
	
@task
def startscreenshot(overwrite=False, proxy=None):
	import datetime
	import django, os, sys
	os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
	sys.path.append("/opt/Kraken")
	django.setup()
	from Web_Scout.models import Hosts,Interfaces

	def signal_handler(signal, frame):
		print "[-] Ctrl-C received! Killing Thread(s)..."
		os._exit(0)
	
	signal.signal(signal.SIGINT, signal_handler)

	start_time = datetime.datetime.now()

	# Fire up the workers
	urlQueue	  = []
	total_count   = 0
	
	for host in Hosts.objects.all():
		for interface in host.interfaces_set.all():
			urlQueue.append([interface.Url, interface.IntID])
			total_count +=1
	
	if proxy == None:
		timeout = 45
	else:
		timeout = 90

	jobs = group(getscreenshot.s(item, timeout, True, proxy, overwrite) for item in urlQueue)
	result = jobs.apply_async()

	while not result.ready():
		print 'Failed Tasks? ' + str(result.failed())
		print 'Waiting? ' + str(result.waiting())
		print 'Completed: ' + str(result.completed_count())
		print 'Total: ' + str(total_count)
		process_percent = int((result.completed_count() / total_count) * 100)
		sleep(.1)
		print 'Percentage Complete: ' + str(process_percent) + '%'
		current_task.update_state(state='PROGRESS', meta={'process_percent': process_percent })
		sleep(30)

	for interface in Interfaces.objects.all():
		if not os.path.exists('/opt/Kraken/static/Web_Scout/' + interface.IntID + '.png'):
			interface.Retry = True
			interface.save()
			shutil.copy('/opt/Kraken/static/blank.png', '/opt/Kraken/static/Web_Scout/' + interface.IntID + '.png')
	end_time = datetime.datetime.now()
	total_time = end_time - start_time
	number_of_interfaces = Interfaces.objects.all().count()
	LogKrakenEvent('Celery', 'Screenshots Complete. Elapsed time: ' + str(total_time) + ' to screenshot ' + str(number_of_interfaces) + ' interfaces', 'info')

@task
def runmodule(hostid):
	import datetime
	import django, os, sys
	os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
	sys.path.append("/opt/Kraken")
	django.setup()
	from Web_Scout.models import Hosts
	from importlib import import_module
	
	try:
		print hostid
		host_record = Hosts.objects.get(HostID=hostid)
		interface_records = host_record.interfaces_set.all()
		host_module = host_record.Module
		module = import_module("Web_Scout.modules." + host_module)
		result, credentials = module.run(host_record.IP)
		if result == 'Success':
			print "Default Credentials Configured: " + host_record.IP + "."
			for interface in interface_records:
				interface.DefaultCreds = True
				interface.Notes = interface.Product + '. Successfully authenticated with: (' + credentials + ')\n' + interface.Notes
				interface.save()
		else:
			print "Default Credentials NOT Configured: " + host_record.IP + "."
		return result, credentials
	except:
		return "error", "error"

@task
def runmodules(hostlist=""):
	import datetime
	import django, os, sys
	os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
	sys.path.append("/opt/Kraken")
	django.setup()
	from Web_Scout.models import Hosts
	from importlib import import_module
	import datetime
	
	if not hostlist:
		hostlist = Hosts.objects.exclude(Module__exact='')
	
	total_count = len(hostlist)
	LogKrakenEvent('Celery', 'Running modules on ' + str(total_count) + ' hosts.', 'info')

	start_time = datetime.datetime.now()
	
	jobs = group(runmodule.s(host.HostID) for host in hostlist)
	result = jobs.apply_async()
	while not result.ready():
		print 'Failed Tasks? ' + str(result.failed())
		print 'Waiting? ' + str(result.waiting())
		print 'Completed: ' + str(result.completed_count())
		print 'Total: ' + str(total_count)
		process_percent = int((result.completed_count() / total_count) * 100)
		sleep(.1)
		print 'Percentage Complete: ' + str(process_percent) + '%'
		current_task.update_state(state='PROGRESS', meta={'process_percent': process_percent })
		sleep(5)
	end_time = datetime.datetime.now()
	total_time = end_time - start_time
	LogKrakenEvent('Celery', 'Mass Module Execution Complete. Elapsed time: ' + str(total_time) + ' to test ' + str(total_count) + ' interfaces', 'info')

@task
def nmap_web(address):
	from subprocess import Popen
	args = ['nmap', '-sV', address, '-oX', '/opt/Kraken/tmp/' + address.replace('/', '-').replace('.', '-') + '.xml', '-p80,280,443,591,593,981,1311,2031,2480,3181,4444,4445,4567,4711,4712,5104,5280,7000,7001,7002,8000,8008,8011,8012,8013,8014,8042,8069,8080,8081,8243,8280,8281,8443,8531,8887,8888,9080,9443,11371,12443,16080,18091,18092']
	print 'Beginning Nmap Scan.'
	scan_process = Popen(args)
	scan_process.wait()
	print 'scan complete'

	# Parse into database
	nmap_parse('/opt/Kraken/tmp/' + address.replace('/', '-').replace('.', '-') + '.xml', address)

@task
def scan(addresses):
	from subprocess import Popen
	import datetime
	import django
	os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
	sys.path.append("/opt/Kraken")
	django.setup()
	from Web_Scout.models import Addresses, Hosts

	current_task.update_state(state='SCANNING')
	timestamp = datetime.datetime.now()
	initial_host_count = len(Hosts.objects.all())
	total_count = len(addresses)

	# Perform scan
	jobs = group(nmap_web.s(address) for address in addresses)
	result = jobs.apply_async()
	while not result.ready():
		process_percent = int((result.completed_count() / total_count) * 100)
		sleep(.1)
		print 'Percentage Complete: ' + str(process_percent) + '%'
		current_task.update_state(state='PROGRESS', meta={'process_percent': process_percent })
		sleep(5)

	for address in addresses:
		try:
			filepath = '/opt/Kraken/tmp/' + address.replace('/', '-').replace('.', '-') + '.xml'
			print 'deleting ' + filepath
		#	os.remove(filepath)
		except:
			print 'No nmap.xml to remove'

		# Figure out how to tie supplied ranges/hostnames to individual records
		print 'Checking for stale hosts'
		try:
			for host in Addresses.objects.get(AddressID=address.replace('.', '-').replace('/', '-')).hosts_set.all():
				print 'host ' + host.IP + ' found.'
				if datetime.datetime.strptime(host.LastSeen, '%Y-%m-%d %H:%M:%S.%f') < timestamp:
					print 'Host is stale'
					host.Stale = True
					host.StaleLevel += 1
					host.save()
				else:
					print 'host ' + host.IP + ' is not stale.'
		except:
			LogKrakenEvent('Celery', 'Unable to find Address record during stale check.', 'error')

	post_scan_host_count = len(Hosts.objects.all())
	LogKrakenEvent('Celery', 'Scanning Complete. ' + str(post_scan_host_count - initial_host_count) + ' new hosts found.', 'info')

@task
def genreport(notes, order, report_name, hosts_per_page):
	import os
	import django
	import sys
	from shutil import make_archive, rmtree
	from datetime import date
	from shutil import copytree
	from django.core.paginator import Paginator
	os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
	sys.path.append("/opt/Kraken")
	django.setup()
	from Web_Scout.models import Hosts,Interfaces
	
	def RiskRating(ratingnumber=0):
		if ratingnumber:
			if int(ratingnumber) == 1:
				return "High"
			elif int(ratingnumber) == 2:
				return "Medium"
			elif int(ratingnumber) == 3:
				return "Low"
		else:
			return ""
	
	date = date.today().strftime("%B %d,%Y")

	# Cleanup previous files
	if os.path.isfile('/opt/Kraken/tmp/KrakenReport.zip'):
		os.remove('/opt/Kraken/tmp/KrakenReport.zip')
	if os.path.exists('/opt/Kraken/tmp/report/'):
		rmtree('/opt/Kraken/tmp/report/')


	# Create report folder
	os.mkdir("/opt/Kraken/tmp/report")
	os.mkdir("/opt/Kraken/tmp/report/html")
	
	# Copy screenshots
	copytree("/opt/Kraken/static/Web_Scout/", "/opt/Kraken/tmp/report/screenshots/")
	
	# Copy CSS
	copytree("/opt/Kraken/common/css/", "/opt/Kraken/tmp/report/css/")
	copytree("/opt/Kraken/common/js/", "/opt/Kraken/tmp/report/js/")
	
	# Create pages
	host_array = Hosts.objects.all().order_by(order)
	
	if int(hosts_per_page) in (25, 50, 100, 200):
		paginator = Paginator(host_array, hosts_per_page)
	else:
		paginator = Paginator(host_array, 25)
	
	for page in paginator.page_range:
		pagefile = open("/opt/Kraken/tmp/report/html/page" + str(page) + ".html", "w")
	
		# Header and pagination
		header = """
<html>
	<head>
		<script src="../js/jquery-2.1.1.js"></script>
  		<link href="../css/bootstrap.min.css" rel="stylesheet" type="text/css">
  		<script src="../js/bootstrap.min.js"></script>
		<meta charset="UTF-8">
	</head>
<body style="background-color: #d9d9d9">
	<div class="container" style="width: 1000px">
		<div class="well" style="background-color: #222;color: #9d9d9d">
			<div style="text-align: center">
				<h2>{}</h2>
				<h2>Kraken Report</h2>
				<p>Date: {}</p> 
			</div>
		</div>
		<nav>
		<div align="center">
			<ul class="pagination" align="center">\n""".format(report_name, date)
		pagefile.write(header)
		hosts = paginator.page(page)
		if hosts.has_previous():
			pagefile.write("				<li><a href=\"page{}.html\">&laquo;</a>\n".format(str(hosts.previous_page_number())))
		if hosts.paginator.num_pages < 12:
			for page in hosts.paginator.page_range:
				if hosts.number == page:
					pagefile.write("<li class=\"active\"><a href=\"page{}.html\"> {} <span class=\"sr-only\">(current)</span></a></li>\n".format(str(page), str(page)))
				else:
					pagefile.write("<li><a href=\"page{}.html\"> {} </a></li>\n".format(str(page), str(page)))
		elif hosts.paginator.num_pages > 11:
			if hosts.number < 7:
				for page in [1,2,3,4,5,6,7,8,9,10,11]:
					if hosts.number == page:
						pagefile.write("<li class=\"active\"><a href=\"page{}.html\"> {} <span class=\"sr-only\">(current)</span></a></li>\n".format(str(page), str(page)))
					else:
						pagefile.write("<li><a href=\"page{}.html\"> {} </a></li>\n".format(str(page), str(page)))
		elif hosts.number + 5 <= hosts.paginator.num_pages:
			pagefile.write("<li><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.previous_page_number - 4), str(hosts.previous_page_number - 4)))
			pagefile.write("<li><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.previous_page_number - 3), str(hosts.previous_page_number - 3)))
			pagefile.write("<li><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.previous_page_number - 2), str(hosts.previous_page_number - 2)))
			pagefile.write("<li><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.previous_page_number - 1), str(hosts.previous_page_number - 1)))
			pagefile.write("<li><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.previous_page_number), str(hosts.previous_page_number)))
			pagefile.write("<li class=\"active\"><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.number), str(hosts.number)))
			pagefile.write("<li><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.next_page_number), str(hosts.next_page_number)))
			pagefile.write("<li><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.next_page_number + 1), str(hosts.next_page_number + 1)))
			pagefile.write("<li><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.next_page_number + 2), str(hosts.next_page_number + 2)))
			pagefile.write("<li><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.next_page_number + 3), str(hosts.next_page_number + 3)))
			pagefile.write("<li><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.next_page_number + 4), str(hosts.next_page_number + 4)))
		elif hosts.number + 5 > hosts.paginator.num_pages:
			for minus_number in [10,9,8,7,6,5,4,3,2,1]:
				if hosts.number == hosts.paginator.num_pages - minus_number:
					pagefile.write("<li class=\"active\"><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.paginator.num_pages - minus_number), str(hosts.paginator.num_pages - minus_number)))
				else:
					pagefile.write("<li><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.paginator.num_pages - minus_number), str(hosts.paginator.num_pages - minus_number)))
			if hosts.paginator.num_pages == hosts.number:
				pagefile.write("<li class=\"active\"><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.paginator.num_pages), str(hosts.paginator.num_pages)))
			else:
				pagefile.write("<li><a href=\"page{}.html\"> {} </a></li>\n".format(str(hosts.paginator.num_pages), str(hosts.paginator.num_pages)))
		if hosts.has_next():
			pagefile.write("<li><a href=\"page{}.html\">&raquo;</a></li>\n".format(str(hosts.next_page_number())))
		pagefile.write("""
		</ul>			
	</div>
</nav>""")

		# Host entries
		for host in hosts:
			pagefile.write("""
<div class="well">
	<h4 style="text-align:center">{} ({})</h4>
	<p><b>Product</b>: {}<br>
	<b>Category</b>: {}<br>
	<b>Risk Rating</b>: {}</p>
	<hr>
	<h4>Interfaces:</h4>
	<div class="row">\n""".format(host.IP, host.Hostname, host.interfaces_set.all()[0].Product, host.Category, RiskRating(host.Rating)))
			
			# Interface entries
			for interface in host.interfaces_set.all():
				pagefile.write("""
		<div class="col-md-6">
			<img style="border:1px solid black" align="center" width="400" src="../screenshots/{}.png">
			<p style="clear: right"><b>Port</b>: {}<br>\n""".format(interface.IntID, interface.Port))
				if notes == "none" or notes == "only":
					pagefile.write("			<b>Notes</b>: {}<br>\n".format(interface.Notes))
				pagefile.write("""
			<a href="{}">Open</a></p>
		</div>\n""".format(interface.Url))
			pagefile.write("""
	</div>
</div>\n""")
		pagefile.close()
	make_archive('/opt/Kraken/tmp/KrakenReport', 'zip', '/opt/Kraken/tmp/report/')
	rmtree('/opt/Kraken/tmp/report/')
