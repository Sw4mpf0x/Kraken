from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from django.http import HttpResponse
from models import Ports, Hosts
import subprocess
from actions import database_clear,nmap_parse
import os
# Create your views here.

def index(request):
	if request.method == 'POST':
		note = request.POST['note']
		record = request.POST['record']
		default_creds = request.POST['default-creds']
		http_auth = request.POST['http-auth']
		port = Ports.objects.get(PortID=record)
		port.Notes = note
		if http_auth == "Yes":
			port.HttpAuth = True
		else:
			port.HttpAuth = False
		if default_creds == "Yes":
			port.DefaultCreds = True
		else:
			port.DefaultCreds = False
		port.save()
		return HttpResponse(str(default_creds))
	else:
		nav_list = [-10,-9,-8,-7,-6,-5,-4,-3,-2,-1]
		host_array = Hosts.objects.all()
		paginator = Paginator(host_array, 20)
	
		page = request.GET.get('page')
		try:
			hosts = paginator.page(page)
		except PageNotAnInteger:
			hosts = paginator.page(1)
		except EmptyPage:
			hosts.paginator.page(paginator.num_pages)

		return render(request, 'Web_Scout/index.html', {'hosts':hosts, 'nav_list':nav_list})

def setup(request):
	if request.method == 'POST':
		if request.POST['script'] == 'clearDB':
			result = database_clear()
			return HttpResponse(result)
		elif request.POST['script'] == 'parse':
			path = request.POST['path']
			if os.path.exists(path):
				nmap_parse(path)
				return HttpResponse("Success. Script="+request.POST['script']+" and path="+path)
			else:
				return HttpResponse("File specified does not exist. Script="+request.POST['script']+" and path="+path)
		elif request.POST['script'] == 'screenshot':
			subprocess.call("python /opt/Kraken/Web_Scout/screenshot.py", shell=True)
			return HttpResponse()
		else:
			return HttpResponse("Nope. Script="+request.POST['script']+" and path="+request.POST['path'])
	else:
		return render(request, 'Web_Scout/setup.html')

def viewer(request):
	RecordID = request.GET['destination']
	PortRecord = Ports.objects.get(PortID=RecordID)
	return render(request, 'Web_Scout/viewer.html', {'port':PortRecord})

