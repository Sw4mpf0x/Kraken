from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect
from django.utils.html import strip_tags
from django.http import HttpResponse
from models import Addresses, Hosts, Interfaces, Tasks
import os
from . import tasks
from celery.result import AsyncResult
import json
from .forms import ParseForm
from Kraken.krakenlib import BulkAction, BuildQuery, LogKrakenEvent, AddUrl, AddAddress, AddHostname, DeleteAddress, DeleteHost
from django.contrib.auth.decorators import login_required

@login_required
def index(request):
	if request.method == 'POST':
		if request.POST.get('action') == "bulknote":
			data = BulkAction(request.POST.items(), request.POST.get('action'), request.POST.get('note', ''))
			json_data = json.dumps(data)
			return HttpResponse(json_data, content_type='application/json')

		elif request.POST.get('action') == "bulkreviewed":
			data = BulkAction(request.POST.items(), request.POST.get('action'))
			json_data = json.dumps(data)
			return HttpResponse(json_data, content_type='application/json')

		elif request.POST.get('action') == "bulkdelete":
			data = BulkAction(request.POST.items(), request.POST.get('action'))
			json_data = json.dumps(data)
			return HttpResponse(json_data, content_type='application/json')

		elif request.POST.get('action') == "note":
			note = request.POST.get('note')
			record = request.POST.get('record')
			default_creds = request.POST.get('default-creds')
			http_auth = request.POST.get('http-auth')
			reviewed = request.POST.get('reviewed')
			interface = Interfaces.objects.get(IntID=record)
			host = interface.hosts
			interface.Notes = note

			if http_auth == "Yes":
				interface.HttpAuth = True
			else:
				interface.HttpAuth = False
			if default_creds == "Yes":
				interface.DefaultCreds = True
			else:
				interface.DefaultCreds = False
			if reviewed == "Yes":
				host.Reviewed = True
				LogKrakenEvent(request.user, 'Reviewed - ' + host.IP + ' (' + host.Hostname + ')', 'info')
			else:
				host.Reviewed = False
			interface.save()
			host.save()
			return HttpResponse()
		elif request.POST.get('action') == "deletehost":
			host = request.POST.get('host')
			data = DeleteHost([host])
			json_data = json.dumps(data)
			return HttpResponse(json_data, content_type='application/json')		
	else:
		search = request.GET.get('search', '')
		reviewed = request.GET.get('hide_reviewed', '')
		org = request.GET.get('organize_by', 'IP')
		hosts_per_page = request.GET.get('hosts_per_page', '20')
		nav_list = [-10,-9,-8,-7,-6,-5,-4,-3,-2,-1]
		temp_host_array = []
		host_array = []

		if search:
			entry_query = BuildQuery(search, ['IP', 'Hostname', 'Category', 'interfaces__Product'])
			temp_host_array = Hosts.objects.all().filter(entry_query)

		if org in ("IP", "Hostname", "Rating"):
			if temp_host_array:
				temp_host_array = temp_host_array.order_by(org)
			else:
				temp_host_array = Hosts.objects.all().order_by(org)

		if reviewed == 'on':
			if temp_host_array:
				temp_host_array = temp_host_array.exclude(Reviewed=True)
			else:
				temp_host_array = Hosts.objects.all().filter(Reviewed=False)
	
		for host in temp_host_array:
			if len(host.interfaces_set.all()) > 0:
				host_array.append(host)

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
def inventory(request):
	search = request.GET.get('search', '')
	hosts_per_page = request.GET.get('hosts_per_page', '50')
	org = request.GET.get('organize_by', 'IP')
	nav_list = [-10,-9,-8,-7,-6,-5,-4,-3,-2,-1]
	temp_host_array = []
	host_array = []
	
	if search:
		host_query = BuildQuery(search, ['IP', 'Hostname', 'Category', 'interfaces__Product'])
		temp_host_array = Hosts.objects.all().filter(host_query)

	if org in ("IP", "Hostname", "Rating"):
		if temp_host_array:
			temp_host_array = temp_host_array.order_by(org)
		else:
			temp_host_array = Hosts.objects.all().order_by(org)

	for host in temp_host_array:
		if len(host.interfaces_set.all()) > 0:
			host_array.append(host)

	if int(hosts_per_page) in (50, 100, 150, 200, 300):
		paginator = Paginator(host_array, hosts_per_page)
	else:
		paginator = Paginator(host_array, 50)

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
	return render(request, 'Web_Scout/inventory.html', {'hosts':hosts, 'nav_list':nav_list, 'pagination_parameters': parameters, 'hosts_per_page': int(hosts_per_page), 'search':search, 'org':org})

@login_required
def setup(request):
	if request.method == 'POST':
		if request.POST.get('action') == 'cleardb':
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
		elif request.POST.get('action') == 'removescreenshots':
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
		elif request.POST.get('action') == 'parse':
			form = ParseForm(request.POST, request.FILES)
			if form.is_valid:
				with open('/opt/Kraken/tmp/nmap.xml', 'wb+') as destination:
					for chunk in request.FILES["parsefile"].chunks():
						destination.write(chunk)
				job = tasks.nmap_parse.delay('/opt/Kraken/tmp/nmap.xml')
				try:
					task = Tasks.objects.get(Task='parse')
				except:
					task = Tasks()
					task.Task = 'parse'
				task.Task_Id = job.id
				task.Count = 0
				task.save()
				return render(request, 'Web_Scout/setup.html', {'form':form, 'uploaded':True, 'failedupload':False})

			else:
				return render(request, 'Web_Scout/setup.html', {'form':form, 'uploaded':False, 'failedupload':True})
		elif request.POST.get('action') == 'screenshot':
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
		elif request.POST.get('action') == 'addurl':
			raw_list = request.POST.get('address-textarea')
			address_data = AddUrl(raw_list)
			json_data = json.dumps(address_data)
			return HttpResponse(json_data, content_type='application/json')
		elif request.POST.get('action') == 'runmodules':
			job = tasks.runmodules.delay()
			try:
				task = Tasks.objects.get(Task='runmodules')
			except:
				task = Tasks()
				task.Task = 'runmodules'
			task.Task_Id = job.id
			task.Count = 0
			task.save()
			LogKrakenEvent(request.user, 'Running default credential checks.', 'info')
			return HttpResponse()
		elif request.POST.get('action') == 'scan':
			address_list = []
			error_message = []

			for key,value in request.POST.items():
				if str(value) == "on":
					try:
						address_object = Addresses.objects.get(AddressID=key)
						if address_object.Hostname:
							address_list.append(address_object.Hostname)
						else:
							address_list.append(address_object.Address + '/' + address_object.Cidr)
					except:
						error_message.append(key + ' not found in database.')
						continue

			job = tasks.scan.delay(address_list)

			try:
				task = Tasks.objects.get(Task='scan')
			except:
				task = Tasks()
				task.Task = 'scan'
			task.Task_Id = job.id
			task.Count = 0
			task.save()

			json_data = json.dumps(error_message)
			return HttpResponse(json_data, content_type='application/json')
		elif request.POST.get('action') == 'addaddress':
			raw_list = request.POST.get('address-textarea')
			print raw_list
			address_data = AddAddress(raw_list)
			json_data = json.dumps(address_data)
			return HttpResponse(json_data, content_type='application/json')
		elif request.POST.get('action') == 'addhostname':
			raw_list = request.POST.get('address-textarea')
			address_data = AddHostname(raw_list)
			json_data = json.dumps(address_data)
			return HttpResponse(json_data, content_type='application/json')
		elif request.POST.get('action') == 'delete':
			address_list = []
			for key,value in request.POST.items():
				if str(value) == "on":
					address_list.append(key)
			DeleteAddress(address_list)
			json_data = json.dumps(address_list)
			return HttpResponse(json_data, content_type='application/json')
		else:
			return HttpResponse("Failure.")
	else:
		form = ParseForm()
		addresses = Addresses.objects.all()
		return render(request, 'Web_Scout/setup.html', {'addresses':addresses, 'form':form, 'uploaded':False, 'failedupload':False})

@login_required
def viewer(request):
	RecordID = request.GET['destination']
	InterfaceRecord = Interfaces.objects.get(IntID=RecordID)
	HostRecord = InterfaceRecord.hosts
	HostRecord.Reviewed = True
	HostRecord.save()
	LogKrakenEvent(request.user, 'Reviewed - ' + HostRecord.IP + ' (' + HostRecord.Hostname + ')', 'info')
	external = request.GET.get('external', '')
	if external == 'true':
		return redirect(InterfaceRecord.Url)
	else:
		return render(request, 'Web_Scout/viewer.html', {'interface':InterfaceRecord, 'host':HostRecord})

@login_required
def task_state(request):
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

@login_required
def runmodule(request):
	interface = request.GET['interface']
	result, credentials = tasks.runmodule(interface)
	data = [result, credentials]
	json_data = json.dumps(data)
	return HttpResponse(json_data, content_type='application/json')

@login_required
def runmodules(request):
	interfacelist = request.GET.get('interfaces', '')
	if interfacelist:
		interfacelist = interfacelist.split(',')
		tasks.runmodules.delay(interfacelist)
	else:
		tasks.runmodules.delay()

	return HttpResponse()
	
