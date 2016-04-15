#!/usr/bin/python

'''
Installation on Ubuntu:
apt-get install python-requests python-m2crypto phantomjs
If you run into: 'module' object has no attribute 'PhantomJS'
then pip install selenium (or pip install --upgrade selenium)
'''

from selenium import webdriver
from urlparse import urlparse
from random   import shuffle
from PIL      import Image, ImageDraw, ImageFont
import multiprocessing
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

def setupBrowserProfile(headless,proxy):
	browser = None
	if(proxy is not None):
		service_args=['--ignore-ssl-errors=true','--ssl-protocol=tlsv1','--proxy='+proxy,'--proxy-type=socks5']
	else:
		service_args=['--ignore-ssl-errors=true', '--ssl-protocol=any', '--web-security=false']

	while(browser is None):
		try:
			if(not headless):
				fp = webdriver.FirefoxProfile()
				fp.set_preference("webdriver.accept.untrusted.certs",True)
				fp.set_preference("security.enable_java", False)
				fp.set_preference("webdriver.load.strategy", "fast");
				if(proxy is not None):
					proxyItems = proxy.split(":")
					fp.set_preference("network.proxy.socks",proxyItems[0])
					fp.set_preference("network.proxy.socks_port",int(proxyItems[1]))
					fp.set_preference("network.proxy.type",1)
				browser = webdriver.Firefox(fp)
			else:
				browser = webdriver.PhantomJS(service_args=service_args, executable_path="phantomjs")
		except Exception as e:
			print e
			time.sleep(1)
			continue
	return browser


def writeImage(text, filename, fontsize=40, width=1024, height=200):
	image = Image.new("RGBA", (width,height), (255,255,255))
	draw = ImageDraw.Draw(image)
        if (os.path.exists("/usr/share/httpscreenshot/LiberationSerif-BoldItalic.ttf")):
            font_path = "/usr/share/httpscreenshot/LiberationSerif-BoldItalic.ttf"
        else:
            font_path = os.path.dirname(os.path.realpath(__file__))+"/LiberationSerif-BoldItalic.ttf"
	font = ImageFont.truetype(font_path, fontsize)
	draw.text((10, 0), text, (0,0,0), font=font)
	image.save(filename)


def worker(urlQueue, tout, debug, headless, doProfile, vhosts, extraHosts, tryGUIOnFail, smartFetch, proxy, workerID):

	print('[*] Starting worker ' + workerID)
	
	browser = None
	try:
		browser = setupBrowserProfile(headless,proxy)

	except:
		print "[-] Oh no! Couldn't create the browser, Selenium blew up"
		exc_type, exc_value, exc_traceback = sys.exc_info()
		lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
		print ''.join('!! ' + line for line in lines)
		return

	while True:
		#Try to get a URL from the Queue
		if urlQueue.qsize() > 0:
			try:			
				curUrl = urlQueue.get(timeout=tout)
			except Queue.Empty:
				continue
			print '[+] '+str(urlQueue.qsize())+' URLs remaining'
			screenshotName = '/opt/Kraken/Web_Scout/static/Web_Scout/'+curUrl[3].replace('.', '')+curUrl[4]
			if(debug):
				print '[+] Got URL: '+curUrl[0]
				print '[+] screenshotName: '+screenshotName
			if(os.path.exists(screenshotName+".png")):
				if(debug):
			 		print "[-] Screenshot already exists, skipping"
				continue
		else:
			if(debug):
				print'[-] URL queue is empty, quitting.'
			browser.quit()
			return

		try:
			if(doProfile):
				[resp,curUrl] = autodetectRequest(curUrl, timeout=tout, vhosts=vhosts, urlQueue=urlQueue, extraHosts=extraHosts,proxy=proxy)
			else:
				resp = doGet(curUrl, verify=False, timeout=tout, vhosts=vhosts, urlQueue=urlQueue, extraHosts=extraHosts,proxy=proxy)
			if(resp is not None and resp.status_code == 401):
				print curUrl[0]+" Requires HTTP Basic Auth"
				writeImage(resp.headers.get('www-authenticate','NO WWW-AUTHENTICATE HEADER'),screenshotName+".png")
				continue

			elif(resp is not None):
				if(resp.text is not None):
					resp_hash = hashlib.md5(resp.text).hexdigest()
				else:
					resp_hash = None
				
				if smartFetch and resp_hash is not None and resp_hash in hash_basket:
					#We have this exact same page already, copy it instead of grabbing it again
					print "[+] Pre-fetch matches previously imaged service, no need to do it again!"
					shutil.copy2(hash_basket[resp_hash]+".png",screenshotName+".png")
				else:
					if smartFetch:
						hash_basket[resp_hash] = screenshotName

				
				browser.set_window_size(1024, 768)
				browser.set_page_load_timeout((tout))
				old_url = browser.current_url
				browser.get(curUrl[0].strip())
				if(browser.current_url == old_url):
					print "[-] Error fetching in browser but successfully fetched with Requests: "+curUrl[0]
					if(headless):
						if(debug):
							print "[+] Trying with sslv3 instead of TLS - known phantomjs bug: "+curUrl[0]
						browser2 = webdriver.PhantomJS(service_args=['--ignore-ssl-errors=true'], executable_path="phantomjs")
						old_url = browser2.current_url
						browser2.get(curUrl[0].strip())
						if(browser2.current_url == old_url):
							if(debug):
								print "[-] Didn't work with SSLv3 either..."+curUrl[0]
							browser2.close()
							placeholder.save(screenshotName+".png")
						else:
							print '[+] Saving: '+screenshotName
							#browser2.save_screenshot(screenshotName+".png")
							screen = browser.get_screenshot_as_png()
							im = Image.open(StringIO.StringIO(screen))
							region = im.crop(box)
							region.save(screenshotName+".png", 'PNG', optimize=True, quality=95)
							browser2.close()
							continue						

					if(tryGUIOnFail and headless):
						print "[+] Attempting to fetch with FireFox: "+curUrl[0]
						browser2 = setupBrowserProfile(False,proxy)
						old_url = browser2.current_url
						browser2.get(curUrl[0].strip())
						if(browser2.current_url == old_url):
							print "[-] Error fetching in GUI browser as well..."+curUrl[0]
							browser2.close()
							continue
						else:
							print '[+] Saving: '+screenshotName
							#browser2.save_screenshot(screenshotName+".png")
							screen = browser2.get_screenshot_as_png()
							im = Image.open(StringIO.StringIO(screen))
							region = im.crop(box)
							region.save(screenshotName+".png", 'PNG', optimize=True, quality=95)
							browser2.close()
							continue
					else:
						continue

				print '[+] Saving: '+screenshotName
				#browser.save_screenshot(screenshotName+".png")
				screen = browser.get_screenshot_as_png()
				im = Image.open(StringIO.StringIO(screen))
				region = im.crop(box)
				region.save(screenshotName+".png", 'PNG', optimize=True, quality=95)

		except Exception as e:
			print e
			print '[-] Something bad happened with URL: '+curUrl[0]
			if(curUrl[2] > 0):
				curUrl[2] = curUrl[2] - 1;
				urlQueue.put(curUrl)
			if(debug):
				exc_type, exc_value, exc_traceback = sys.exc_info()
				lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
				print ''.join('!! ' + line for line in lines) 
			browser.quit()
			placeholder.save(screenshotName+".png")
			browser = setupBrowserProfile(headless,proxy)
			continue


def doGet(*args, **kwargs):
	url        = args[0]
	doVhosts   = kwargs.pop('vhosts'    ,None)
	urlQueue   = kwargs.pop('urlQueue'  ,None)
	extraHosts = kwargs.pop('extraHosts',None)
	proxy = kwargs.pop('proxy',None)

	kwargs['allow_redirects'] = False
	session = requests.session()
	if(proxy is not None):
		session.proxies={'http':'socks5://'+proxy,'https':'socks5://'+proxy}
	resp = session.get(url[0],**kwargs)

	#If we have an https URL and we are configured to scrape hosts from the cert...
	if(url[0].find('https') != -1 and url[1] == True):
		#Pull hostnames from cert, add as additional URLs and flag as not to pull certs
		host = urlparse(url[0]).hostname
		port = urlparse(url[0]).port
		if(port is None):
			port = 443
		names = []
		try:
			cert     = ssl.get_server_certificate((host,port),ssl_version=ssl.PROTOCOL_SSLv23)
			x509     = M2Crypto.X509.load_cert_string(cert.decode('string_escape'))
			subjText = x509.get_subject().as_text()
			names    = re.findall("CN=([^\s]+)",subjText)
			altNames = x509.get_ext('subjectAltName').get_value()
			names.extend(re.findall("DNS:([^,]*)",altNames))
		except:
			pass

		for name in names:
			if(name.find('*.') != -1):
				name = name.replace('*.','')
				if(name not in extraHosts):
					extraHosts[name] = 1
					urlQueue.put(['https://'+name+':'+str(port),False,url[2]])
					print '[+] Added host '+name
			else:
				if (name not in extraHosts):
					extraHosts[name] = 1
					urlQueue.put(['https://'+name+':'+str(port),False,url[2]])
					print '[+] Added host '+name
		return resp
	else:	
		return resp


def autodetectRequest(url, timeout, vhosts=False, urlQueue=None, extraHosts=None,proxy=None):
	'''Takes a URL, ignores the scheme. Detect if the host/port is actually an HTTP or HTTPS
	server'''
	resp = None
	host = urlparse(url[0]).hostname
	port = urlparse(url[0]).port

	if(port is None):
		if('https' in url[0]):
			port = 443
		else:
			port = 80

	try:
		#cert = ssl.get_server_certificate((host,port))
		
		cert = timeoutFn(ssl.get_server_certificate,kwargs={'addr':(host,port),'ssl_version':ssl.PROTOCOL_SSLv23},timeout_duration=3)

		if(cert is not None):
			if('https' not in url[0]):
				url[0] = url[0].replace('http','https')
				#print 'Got cert, changing to HTTPS '+url[0]

		else:
			url[0] = url[0].replace('https','http')
			#print 'Changing to HTTP '+url[0]


	except Exception as e:
		url[0] = url[0].replace('https','http')
		#print 'Changing to HTTP '+url[0]
	try:
		resp = doGet(url,verify=False, timeout=timeout, vhosts=vhosts, urlQueue=urlQueue, extraHosts=extraHosts, proxy=proxy)
	except Exception as e:
		print 'HTTP GET Error: '+str(e)
		print url[0]

	return [resp,url]


def sslError(e):
	if('the handshake operation timed out' in str(e) or 'unknown protocol' in str(e) or 'Connection reset by peer' in str(e) or 'EOF occurred in violation of protocol' in str(e)):
		return True
	else:
		return False

def signal_handler(signal, frame):
        print "[-] Ctrl-C received! Killing Thread(s)..."
	os._exit(0)
signal.signal(signal.SIGINT, signal_handler)

def timeoutImage():
	temp_timeout_image = Image.new('RGBA',(0, 0))
	draw = ImageDraw.Draw(temp_timeout_image)
	draw.line((0, 0) + temp_timeout_image.size, fill=128)
	draw.line((0, temp_timeout_image.size[1], temp_timeout_image.size[0], 0), fill=128)
	del draw
	return temp_timeout_image.crop(box)

if __name__ == '__main__':

	#Fire up the workers
	global box
	box           = (0, 0, 1024, 768)
	placeholder   = timeoutImage()
	urlQueue      = multiprocessing.Queue()
	manager       = multiprocessing.Manager()
	hostsDict     = manager.dict()
	workers       = []
	hash_basket   = {}
	current_count = 0
	total_count   = 0


	for i in range(20):
		p = multiprocessing.Process(target=worker, args=(urlQueue, 20, False, True, False, True, hostsDict, False, False, None, "Worker-" + str(i)))
		workers.append(p)
		p.start()

	for host in Hosts.objects.all():
		for port in host.ports_set.all():
			urlQueue.put([port.Link, False, 0, host.IP, port.Port])
			current_count += 1
			total_count +=1

	for p in workers:
	        p.join()
			
