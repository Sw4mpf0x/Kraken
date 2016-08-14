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
import django
os.environ["DJANGO_SETTINGS_MODULE"] = "Kraken.settings"
sys.path.append("/opt/Kraken")
django.setup()
from Web_Scout.models import Hosts,Ports

try:
	from urllib.parse import quote
except:
	from urllib import quote

reload(sys)
sys.setdefaultencoding("utf8")

@task
def cleardb():
	try:
		Hosts.objects.all().delete()
		Ports.objects.all().delete()
	except:
		LogKrakenEvent('', 'Error clearing database', 'error')

@task
def removescreenshots():
	screenshotlist = [ f for f in os.listdir("/opt/Kraken/Web_Scout/static/Web_Scout/")]
	for screenshot in screenshotlist:
		os.remove('/opt/Kraken/Web_Scout/static/Web_Scout/' + screenshot)

@task
def nmap_parse(filepath):
	import xml.etree.cElementTree as ET
	import os
	HttpPorts = [80, 280, 443, 591, 593, 981, 1311, 2031, 2480, 3181, 4444, 4445, 4567, 4711, 4712, 5104, 5280, 7000, 7001, 7002, 8000, 8008, 8011, 8012, 8013, 8014, 8042, 8069, 8080, 8081, 8243, 8280, 8281, 8443, 8531, 8887, 8888, 9080, 9443, 11371 ,12443, 16080, 18091, 18092]

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
		ports = host.find('ports')
		for port in ports.findall('port'):
			if port[0].get('state') == 'open' and int(port.get('portid')) in HttpPorts or 'http' in str(port[1].get('extrainfo')) or 'http' in str(port[1].get('product')): 
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
					port_object.Product = port[1].get('extrainfo')
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
		host_object.Category = ""
		host_object.save()
	for row in Ports.objects.all():
		if Ports.objects.filter(PortID=row.PortID).count() > 1:
			row.delete()
	number_of_hosts = Hosts.objects.all().count()
	number_of_ports = Ports.objects.all().count()
	LogKrakenEvent('Celery', 'Parsing Complete. Hosts: ' + str(number_of_hosts) + ', Ports: ' + str(number_of_ports), 'info')


@task(time_limit=120)
def getscreenshot(urlItem, tout, debug, proxy,):

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

	def default_creds(port_record, source_code):
		#port_record.Default_Credentials = None
		#port_record.Category = None
		print 'Checking for default creds'
		try:
			sigpath = '/opt/Kraken/Web_Scout/signatures.txt'
			catpath = '/opt/Kraken/Web_Scout/categories.txt'
			with open(sigpath) as sig_file:
				signatures = sig_file.readlines()
	
			with open(catpath) as cat_file:
				categories = cat_file.readlines()
			
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
	
					# Set our variable to 1 if the signature was not identified.  If it is
					# identified, it will be added later on.  Find total number of
					# "signatures" needed to uniquely identify the web app
					# signature_range = len(page_sig)
	
					# This is used if there is more than one "part" of the
					# web page needed to make a signature Delimete the "signature"
					# by ";" before the "|", and then have the creds after the "|"
					if all([x.lower() in source_code.lower() for x in page_identifiers]):
						print('default cred found!!!! ' + credential_info)
						if port_record.Default_Credentials is None:
							port_record.Default_Credentials = credential_info
						else:
							port_record.Default_Credentials += '\n' + credential_info
						port_record.Product = page_id
						port_record.save()
				host_record = port_record.hosts
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

	# Set screenshot file name. If screenshot exists, go to next interface.
	screenshotName = '/opt/Kraken/Web_Scout/static/Web_Scout/'+urlItem[1]
	if(debug):
		print '[+] Got URL: '+urlItem[0]
		print '[+] screenshotName: '+screenshotName
	if(os.path.exists(screenshotName+".png")):
		if(debug):
	 		print "[-] Screenshot already exists, skipping"
	 	browser.quit()
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
					region.save(screenshotName+".png", 'PNG', optimize=True, quality=95)
					browser2.quit()
					return

			print '[+] Saving: '+screenshotName
			screen = browser.get_screenshot_as_png()
			im = Image.open(StringIO.StringIO(screen))
			region = im.crop(box)
			region.save(screenshotName+".png", 'PNG', optimize=True, quality=95)
			port_record = Ports.objects.get(PortID=urlItem[1])
			default_creds(port_record, browser.page_source)
			browser.quit()
	except Exception as e:
		print e
		browser.set_window_size(1024, 768)
		if(debug):
			exc_type, exc_value, exc_traceback = sys.exc_info()
			lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
			print ''.join('!! ' + line for line in lines) 
		browser.quit()
		shutil.copy('/opt/Kraken/Web_Scout/static/blank.png', screenshotName + 'png')
		return
	
@task
def startscreenshot():
	import datetime
	def signal_handler(signal, frame):
		print "[-] Ctrl-C received! Killing Thread(s)..."
		os._exit(0)
	
	signal.signal(signal.SIGINT, signal_handler)

	start_time = datetime.datetime.now()
	# Fire up the workers
	urlQueue	  = []
	total_count   = 0
	
	for host in Hosts.objects.all():
		for port in host.ports_set.all():
			urlQueue.append([port.Link, port.PortID])
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

	for port in Ports.objects.all():
		if not os.path.exists('/opt/Kraken/Web_Scout/static/Web_Scout/' + port.PortID + '.png'):
			shutil.copy('/opt/Kraken/Web_Scout/static/blank.png', '/opt/Kraken/Web_Scout/static/Web_Scout/' + port.PortID + '.png')
	end_time = datetime.datetime.now()
	total_time = end_time - start_time
	number_of_ports = Ports.objects.all().count()
	LogKrakenEvent('Celery', 'Screenshots Complete. Elapsed time: ' + str(total_time) + ' to screenshot ' + str(number_of_ports) + ' interfaces', 'info')