from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from django.http import HttpResponse
from models import Ports, Hosts, Tasks
import subprocess
import os
from . import tasks
from celery.result import AsyncResult
import json
#import models
from search import build_query
from django.contrib.auth.decorators import login_required
# Create your views here.

@login_required
def index(request):
	if request.method == 'POST':
		note = request.POST.get('note')
		record = request.POST.get('record')
		default_creds = request.POST.get('default-creds')
		http_auth = request.POST.get('http-auth')
		reviewed = request.POST.get('reviewed')
		port = Ports.objects.filter(PortID=record)
		host = port[0].hosts
		port.update(Notes=note)

		if http_auth == "Yes":
			port.update(HttpAuth=True)
		else:
			port.update(HttpAuth=False)
		if default_creds == "Yes":
			port.update(DefaultCreds=True)
		else:
			port.update(DefaultCreds=False)
		if reviewed == "Yes":
			host.Reviewed = True
		else:
			host.Reviewed = False
		host.save()

		return HttpResponse(str(default_creds))
	else:
		search = request.GET.get('search', '')
		reviewed = request.GET.get('hide_reviewed', '')
		org = request.GET.get('organize_by', 'IP')
		hosts_per_page = request.GET.get('hosts_per_page', '20')
		nav_list = [-10,-9,-8,-7,-6,-5,-4,-3,-2,-1]
		host_array = []

		if search:
			entry_query = build_query(search, ['IP', 'Hostname'])
			host_array = Hosts.objects.all().filter(entry_query)

		if org in ("IP", "Hostname", "Rating"):
			if host_array:
				host_array = host_array.order_by(org)
			else:
				host_array = Hosts.objects.all().order_by(org)

		if reviewed == 'on':
			if host_array:
				host_array = host_array.exclude(Reviewed=True)
			else:
				host_array = Hosts.objects.all().filter(Reviewed=False)
		
		if int(hosts_per_page) in (20, 30, 40, 50, 100):
			paginator = Paginator(host_array, hosts_per_page)
		else:
			paginator = Paginator(host_array, 20)
	
		parameters = ''
		for key,value in request.GET.items():
			if not key == 'page' and not value == "":
				print value
				parameters = parameters + '&' + key + '=' + value

		page = request.GET.get('page')
		try:
			hosts = paginator.page(page)
		except PageNotAnInteger:
			hosts = paginator.page(1)
		except EmptyPage:
			hosts.paginator.page(paginator.num_pages)
		return render(request, 'Web_Scout/index.html', {'hosts':hosts, 'nav_list':nav_list, 'pagination_parameters': parameters, 'hosts_per_page': int(hosts_per_page), 'search':search, 'reviewed':reviewed, 'org':org})

@login_required
def setup(request):
	if request.method == 'POST':
		if request.POST['script'] == 'cleardb':
			job = tasks.cleardb.delay()
			try:
				task = Tasks.objects.get(Task='cleardb')
			except:
				task = Tasks()
				task.Task = 'cleardb'
			task.Task_Id = job.id
			task.save()
			return HttpResponse()
		elif request.POST['script'] == 'removescreenshots':
			job = tasks.removescreenshots.delay()
			try:
				task = Tasks.objects.get(Task='removescreenshots')
			except:
				task = Tasks()
				task.Task = 'removescreenshots'
			task.Task_Id = job.id
			task.save()
			return HttpResponse()
		elif request.POST['script'] == 'parse':
			path = request.POST['path']
			if os.path.exists(path):
				job = tasks.nmap_parse.delay(path)
				try:
					task = Tasks.objects.get(Task='parse')
				except:
					task = Tasks()
					task.Task = 'parse'
				task.Task_Id = job.id
				task.save()
				#return HttpResponse("Success. Script="+request.POST['script']+" and path="+path)
				return HttpResponse()
			else:
				return HttpResponse("File specified does not exist. Script="+request.POST['script']+" and path="+path)
		elif request.POST['script'] == 'screenshot':
			#subprocess.call("python /opt/Kraken/Web_Scout/screenshot.py", shell=True)
			job = tasks.startscreenshot.delay()
			try:
				task = Tasks.objects.get(Task='screenshot')
			except:
				task = Tasks()
				task.Task = 'screenshot'
			task.Task_Id = job.id
			task.save()
			return HttpResponse()
		else:
			return HttpResponse("Nope. Script="+request.POST['script']+" and path="+request.POST['path'])
	else:
		return render(request, 'Web_Scout/setup.html')

@login_required
def viewer(request):
	RecordID = request.GET['destination']
	PortRecord = Ports.objects.get(PortID=RecordID)
	HostRecord = PortRecord.hosts
	return render(request, 'Web_Scout/viewer.html', {'port':PortRecord, 'host':HostRecord})

@login_required
def task_state(request):
	#""" A view to report the progress to the user """
	data = 'Fail'
	#if request.is_ajax():
	if request.GET['task']:
		URL_task_id = request.GET['task']
		#INSERT validation for URL_task_id
		try:
			db_task = Tasks.objects.get(Task=URL_task_id)
		except:
			return HttpResponse()
		task = AsyncResult(db_task.Task_Id)
		#task = AsyncResult(str(URL_task_id))
		data = task.result or task.state
	else:
		data = 'No task_id in the request'
	#else:
	#	data = 'This is not an ajax request'

	json_data = json.dumps(data)

	return HttpResponse(json_data, content_type='application/json')