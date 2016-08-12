from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect
from django.utils.html import strip_tags
from django.http import HttpResponse
from models import Ports, Hosts, Tasks
import os
from . import tasks
from celery.result import AsyncResult
import json
from Kraken.krakenlib import BuildQuery, LogKrakenEvent
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
		port = Ports.objects.get(PortID=record)
		host = port.hosts
		port.Notes = note

		if http_auth == "Yes":
			port.HttpAuth = True
		else:
			port.HttpAuth = False
		if default_creds == "Yes":
			port.DefaultCreds = True
		else:
			port.DefaultCreds = False
		if reviewed == "Yes":
			host.Reviewed = True
			LogKrakenEvent(request.user, 'Reviewed - ' + host.IP + ' (' + host.Hostname + ')', 'info')
		else:
			host.Reviewed = False
		port.save()
		host.save()

		return HttpResponse()
	else:
		search = request.GET.get('search', '')
		reviewed = request.GET.get('hide_reviewed', '')
		org = request.GET.get('organize_by', 'IP')
		hosts_per_page = request.GET.get('hosts_per_page', '20')
		nav_list = [-10,-9,-8,-7,-6,-5,-4,-3,-2,-1]
		host_array = []

		if search:
			entry_query = BuildQuery(search, ['IP', 'Hostname', 'ports__Category', 'ports__Product'])
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
			task.Count = 0
			task.save()
			LogKrakenEvent(request.user, 'Database Cleared', 'info')
			return HttpResponse()
		elif request.POST['script'] == 'removescreenshots':
			job = tasks.removescreenshots.delay()
			try:
				task = Tasks.objects.get(Task='removescreenshots')
			except:
				task = Tasks()
				task.Task = 'removescreenshots'
			task.Task_Id = job.id
			task.Count = 0
			task.save()
			LogKrakenEvent(request.user, 'Screenshots Deleted', 'info')
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
				task.Count = 0
				task.save()
				LogKrakenEvent(request.user, 'Database populated with data from ' + path, 'info')
				return HttpResponse()
			else:
				return HttpResponse("File specified does not exist or is not accessible.")
		elif request.POST['script'] == 'screenshot':
			job = tasks.startscreenshot.delay()
			try:
				task = Tasks.objects.get(Task='screenshot')
			except:
				task = Tasks()
				task.Task = 'screenshot'
			task.Task_Id = job.id
			task.Count = 0
			task.save()
			LogKrakenEvent(request.user, 'Screenshot taking task initiated', 'info')
			return HttpResponse()
		else:
			return HttpResponse("Failure.")
	else:
		return render(request, 'Web_Scout/setup.html')

@login_required
def viewer(request):
	RecordID = request.GET['destination']
	PortRecord = Ports.objects.get(PortID=RecordID)
	HostRecord = PortRecord.hosts
	HostRecord.Reviewed = True
	HostRecord.save()
	LogKrakenEvent(request.user, 'Reviewed - ' + HostRecord.IP + ' (' + HostRecord.Hostname + ')', 'info')
	external = request.GET.get('external', '')
	if external == 'true':
		return redirect(PortRecord.Link)
	else:
		return render(request, 'Web_Scout/viewer.html', {'port':PortRecord, 'host':HostRecord})

@login_required
def task_state(request):
	#""" A view to report the progress to the user """
	data = 'Fail'
	if request.GET['task']:
		URL_task_id = request.GET['task']
		try:
			db_task = Tasks.objects.get(Task=URL_task_id)
		except:
			return HttpResponse()
		task = AsyncResult(db_task.Task_Id)
		data = task.result or task.state
	else:
		data = 'No task_id in the request'
	if data == 'SUCCESS' and db_task.Count < 4:
		db_task.Count += 1
		db_task.save()
	if db_task.Count < 3:
		json_data = json.dumps(data)
		return HttpResponse(json_data, content_type='application/json')
	else:
		return HttpResponse()
	