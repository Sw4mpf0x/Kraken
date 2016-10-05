from __future__ import absolute_import, division
from celery import task, current_task, group
from celery.utils.log import get_task_logger
from celery.result import AsyncResult
from time import sleep
from selenium import webdriver
from urlparse import urlparse
from random   import shuffle	
from PIL	  import Image, ImageDraw, ImageFont
from Kraken.krakenlib import LogKrakenEvent
import Queue
import argparse
import sys
import traceback
import os.path
import ssl
import M2Crypto
import requests
import re
import time
import signal
import StringIO
import shutil
import hashlib

try:
	from urllib.parse import quote
except:
	from urllib import quote

reload(sys)
sys.setdefaultencoding("utf8")

@task
def cleardb():
	import django
	os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
	sys.path.append("/opt/Kraken")
	django.setup()
	from Web_Scout.models import Hosts,Interfaces
	try:
		Hosts.objects.all().delete()
		Interfaces.objects.all().delete()
	except:
		LogKrakenEvent('', 'Error clearing database', 'error')

@task
def removescreenshots():
	screenshotlist = [ f for f in os.listdir("/opt/Kraken/Web_Scout/static/Web_Scout/")]
	for screenshot in screenshotlist:
		os.remove('/opt/Kraken/Web_Scout/static/Web_Scout/' + screenshot)

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

	# Known HTTP ports
	HttpPorts = [80, 280, 443, 591, 593, 981, 1311, 2031, 2480, 3181, 4444, 4445, 4567, 4711, 4712, 5104, 5280, 7000, 7001, 7002, 8000, 8008, 8011, 8012, 8013, 8014, 8042, 8069, 8080, 8081, 8243, 8280, 8281, 8443, 8531, 8887, 8888, 9080, 9443, 11371 ,12443, 16080, 18091, 18092]
	timestamp = datetime.datetime.now()

	# Parse Nmap XML file
	print('parsing ' + filepath) 
	nmap = ET.parse(filepath)
	root = nmap.getroot()

	# Loop through hosts
	for host in root.findall('host'):
		print('Host ' + host[1].get('addr') + ' found')
		ipaddress = host[1].get('addr')

		try:
			host_object = Hosts.objects.get(ipaddress.replace('.', '-'))
			host_object.Stale = False
			host_object.StaleLevel = 0
		except:
			if targetaddress:
				address_record = Addresses.objects.get(AddressID=targetaddress.replace('.', '-').replace('/', '-'))
				host_object = address_record.hosts_set.create()
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
		
		host_object.LastSeen = timestamp
		host_object.Category = ""
		host_object.save()

		# Loop through ports for each host
		ports = host.find('ports')
		for port in ports.findall('port'):
			if port[0].get('state') == 'open' and int(port.get('portid')) in HttpPorts or 'http' in str(port[1].get('extrainfo')) or 'http' in str(port[1].get('product')): 
				print('Port ' + port.get('portid') + ' found.')
				try:
					interface_object = Interfaces.objects.get(host_object.HostID + '-' + port.get('portid'))
				except:
					interface_object = host_object.interfaces_set.create()
				
				# Set port DeviceType
				try:
					host_object.DeviceType = port[1].get('devicetype')
					if not host_object.DeviceType:
						host_object.DeviceType = ""
				except:
					host_object.DeviceType = ""

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
		
				# Set port product
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
				
				# Set port identification
				interface_object.IntID = host_object.IP.replace('.', '-') + '-' + interface_object.Port

				interface_object.Banner = ""
				interface_object.ImgLink = "Web_Scout/" + host_object.IP.replace('.', '-') + '-' + interface_object.Port + ".png" 
				interface_object.Banner = ""

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
				interface_object.Type = 'port'
				interface_object.save()
		host_object.save()

	print('Checking for duplicates.')
	for row in Interfaces.objects.all():
		if Interfaces.objects.filter(IntID=row.IntID).count() > 1:
			row.delete()
	for row in Hosts.objects.all():
		if Hosts.objects.filter(HostID=row.HostID).count() > 1:
			row.delete()
	number_of_hosts = Hosts.objects.all().count()
	number_of_interfaces = Interfaces.objects.all().count()
	try:
		os.remove('/opt/Kraken/tmp/nmap.xml')
	except:
		print 'No nmap.xml to remove'
	LogKrakenEvent('Celery', 'Parsing Complete. Hosts: ' + str(number_of_hosts) + ', Interfaces: ' + str(number_of_interfaces), 'info')


@task(time_limit=120)
def getscreenshot(urlItem, tout, debug, proxy,):
	import django, os, sys
	os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
	sys.path.append("/opt/Kraken")
	django.setup()
	from Web_Scout.models import Hosts,Interfaces

	def timeoutFn(func, args=(), kwargs={}, timeout_duration=1, default=None):
		import signal
	
		class TimeoutError(Exception):
			pass
	
		def handler(signum, frame):
			raise TimeoutError()
	
		# set the timeout handler
		signal.signal(signal.SIGALRM, handler)
		signal.alarm(timeout_duration)
		try:
			result = func(*args, **kwargs)
		except TimeoutError as exc:
			result = default
		finally:
			signal.alarm(0)
	
		return result
	
	def setupBrowserProfile(tout, proxy):
		browser = None
		if(proxy is not None):
			service_args=['--ignore-ssl-errors=true','--ssl-protocol=tlsv1','--proxy='+proxy,'--proxy-type=socks5']
		else:
			service_args=['--ignore-ssl-errors=true', '--ssl-protocol=any', '--web-security=false']
	
		while(browser is None):
			try:
				browser = webdriver.PhantomJS(service_args=service_args, executable_path="phantomjs")
				browser.set_window_size(1024, 768)
				browser.set_page_load_timeout((tout))
			except Exception as e:
				print e
				browser.quit()
				time.sleep(1)
				continue
		return browser
	
	
	def writeImage(text, filename, fontsize=40, width=1024, height=200):
		image = Image.new("RGBA", (width,height), (255,255,255))
		draw = ImageDraw.Draw(image)
		font_path = os.path.dirname(os.path.realpath(__file__))+"/LiberationSerif-BoldItalic.ttf"
		font = ImageFont.truetype(font_path, fontsize)
		draw.text((10, 0), text, (0,0,0), font=font)
		image.save(filename)
	
	def doGet(*args, **kwargs):
		url		= args[0]
		proxy = kwargs.pop('proxy',None)
	
		kwargs['allow_redirects'] = False
		session = requests.session()
		if(proxy is not None):
			session.proxies={'http':'socks5://'+proxy,'https':'socks5://'+proxy}
		print 'Getting ' + url[0]
		resp = session.get(url[0],**kwargs)
		return resp
	
	def sslError(e):
		if('the handshake operation timed out' in str(e) or 'unknown protocol' in str(e) or 'Connection reset by peer' in str(e) or 'EOF occurred in violation of protocol' in str(e)):
			return True
		else:
			return False

	def default_creds(interface_record, source_code):
		print 'Checking for default creds'
		try:
			sigpath = '/opt/Kraken/Web_Scout/signatures.txt'
			catpath = '/opt/Kraken/Web_Scout/categories.txt'
			with open(sigpath) as sig_file:
				signatures = sig_file.readlines()
	
			with open(catpath) as cat_file:
				categories = cat_file.readlines()
			interface_record.Default_Credentials = ""
			interface_record.save()
			# Loop through and see if there are any matches from the source code
			# Kraken obtained
			if source_code is not None:
				print 'source code present'
				for sig in signatures:
					# Find the signature(s), split them into their own list if needed
					# Assign default creds to its own variable
					sig_list = sig.split('|')
					page_identifiers = sig_list[0].split(";")
					page_id = sig_list[1].strip()
					credential_info = sig_list[2].strip()
					module = sig_list[3].strip()
	
					# Set our variable to 1 if the signature was not identified.  If it is
					# identified, it will be added later on.  Find total number of
					# "signatures" needed to uniquely identify the web app
					# signature_range = len(page_sig)
	
					# This is used if there is more than one "part" of the
					# web page needed to make a signature Delimete the "signature"
					# by ";" before the "|", and then have the creds after the "|"
					if all([x.lower() in source_code.lower() for x in page_identifiers]):
						print('default cred found!!!! ' + credential_info)
						if interface_record.Default_Credentials is None:
							interface_record.Default_Credentials = credential_info
						else:
							interface_record.Default_Credentials += '\n' + credential_info
						if module:
							interface_record.Module = module
						interface_record.Product = page_id
						interface_record.save()
				host_record = interface_record.hosts
				for cat in categories:
					# Find the signature(s), split them into their own list if needed
					# Assign default creds to its own variable
					cat_split = cat.split('|')
					cat_sig = cat_split[0].split(";")
					cat_name = cat_split[1]
	
					# Set our variable to 1 if the signature was not identified.  If it is
					# identified, it will be added later on.  Find total number of
					# "signatures" needed to uniquely identify the web app
					# signature_range = len(page_sig)
	
					# This is used if there is more than one "part" of the
					# web page needed to make a signature Delimete the "signature"
					# by ";" before the "|", and then have the creds after the "|"
					if all([x.lower() in source_code.lower() for x in cat_sig]):
						host_record.Category = cat_name.strip()
						host_record.save()
						break
    	
		except IOError:
			print("[*] WARNING: Credentials file not in the same directory"
				" as Kraken")
			print '[*] Skipping credential check'
			return

	box = (0, 0, 1024, 768)
	browser = None
	interface_record = Interfaces.objects.get(IntID=urlItem[1])

	# Set screenshot file name. If screenshot exists, go to next interface.
	screenshotName = '/opt/Kraken/Web_Scout/static/Web_Scout/'+urlItem[1]
	if(debug):
		print '[+] Got URL: '+urlItem[0]
		print '[+] screenshotName: '+screenshotName
	if(os.path.exists(screenshotName+".png")):
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


	
	# Main screenshot taking logic.
	try:
		resp = doGet(urlItem, verify=False, timeout=tout, proxy=proxy)
		
		# Handle basic auth
		if(resp is not None and resp.status_code == 401):
			print urlItem[0]+" Requires HTTP Basic Auth"
			writeImage(resp.headers.get('www-authenticate','NO WWW-AUTHENTICATE HEADER'),screenshotName+".png")
			browser.quit()
			return
		
		# Handle all other responses
		elif(resp is not None):
			if(debug):
				print 'Got response for ' + urlItem[0]
			
			
			old_url = browser.current_url
			browser.get(urlItem[0].strip())
			if(browser.current_url == old_url):
				print "[-] Error fetching in browser but successfully fetched with Requests: "+urlItem[0]
				if(debug):
					print "[+] Trying with sslv3 instead of TLS - known phantomjs bug: "+urlItem[0]
				browser2 = webdriver.PhantomJS(service_args=['--ignore-ssl-errors=true'], executable_path="phantomjs")
				old_url = browser2.current_url
				browser2.get(urlItem[0].strip())
				if(browser2.current_url == old_url):
					if(debug):
						print "[-] Didn't work with SSLv3 either..."+urlItem[0]
					browser2.quit()
					shutil.copy('/opt/Kraken/Web_Scout/static/blank.png', screenshotName + 'png')
				else:
					print '[+] Saving: '+screenshotName
					screen = browser.get_screenshot_as_png()
					im = Image.open(StringIO.StringIO(screen))
					region = im.crop(box)
					interface_record.Retry = False
					interface_record.save()
					region.save(screenshotName+".png", 'PNG', optimize=True, quality=95)
					browser2.quit()
					return

			print '[+] Saving: '+screenshotName
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
		shutil.copy('/opt/Kraken/Web_Scout/static/blank.png', screenshotName + 'png')
		return
	
@task
def startscreenshot():
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

	jobs = group(getscreenshot.s(item, 20, True, None) for item in urlQueue)
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

	for interface in Interfaces.objects.all():
		if not os.path.exists('/opt/Kraken/Web_Scout/static/Web_Scout/' + interface.IntID + '.png'):
			interface.Retry = True
			interface.save()
			shutil.copy('/opt/Kraken/Web_Scout/static/blank.png', '/opt/Kraken/Web_Scout/static/Web_Scout/' + interface.IntID + '.png')
	end_time = datetime.datetime.now()
	total_time = end_time - start_time
	number_of_interfaces = Interfaces.objects.all().count()
	LogKrakenEvent('Celery', 'Screenshots Complete. Elapsed time: ' + str(total_time) + ' to screenshot ' + str(number_of_interfaces) + ' interfaces', 'info')

@task
def runmodule(interfaceid):
	from importlib import import_module
	try:
		interface_record = Interfaces.objects.get(IntID=interfaceid)
		URL = interface_record.Url
		interface_module = interface_record.Module
		module = import_module("Web_Scout.modules." + interface_module)
		result, credentials = module.run()
		if result == 'Success':
			interface_record.DefaultCreds = True
			interface_record.Notes = 'Successfully authenticated with: (' + credentials + ')\n' + interface_record.Notes
			interface_record.save()
		return result, credentials
	except:
		return "error", "error"

@task
def runmodules(interfacelist=""):
	import datetime
	if not interfacelist:
		interfacelist = Interfaces.objects.exclude(Module__exact='')
	
	total_count = len(interfacelist)
	start_time = datetime.datetime.now()
	
	jobs = group(runmodule.s(interface.IntID) for interface in interfacelist)
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
def scan(addresses):
	from subprocess import Popen
	import datetime
	import django
	os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
	sys.path.append("/opt/Kraken")
	django.setup()
	from Web_Scout.models import Hosts

	current_task.update_state(state='SCANNING')
	timestamp = datetime.datetime.now()

	# Create list of address ranges to scan
	#with open('/opt/Kraken/tmp/addresses.txt', 'wb+') as file:
	#	print addresses
	#	for address in addresses:
	#		file.write(address+"\n")

	# Perform scan
	for address in addresses:
		args = ['nmap', '-sV', address, '-oX', '/opt/Kraken/tmp/scan.xml', '-p80,280,443,591,593,981,1311,2031,2480,3181,4444,4445,4567,4711,4712,5104,5280,7000,7001,7002,8000,8008,8011,8012,8013,8014,8042,8069,8080,8081,8243,8280,8281,8443,8531,8887,8888,9080,9443,11371,12443,16080,18091,18092']
		print 'Beginning Nmap Scan.'
		scan_process = Popen(args)
		scan_process.wait()
		print 'scan complete'

		# Parse into database
		nmap_parse('/opt/Kraken/tmp/scan.xml', address)

	for address in addresses:
		# Figure out how to tie supplied ranges/hostnames to individual records
		if datetime.datetime.strptime(row.LastSeen, '%Y-%m-%d %H:%M:%S.%f') < timestamp:
			print 'Host is stale'
			row.Stale = True
			row.StaleLevel += 1
	print 'deleting files'
	#os.remove('/opt/Kraken/tmp/addresses.txt')
	#os.remove('/opt/Kraken/tmp/scan.xml')
	LogKrakenEvent('Celery', 'Scanning Complete.', 'info')

