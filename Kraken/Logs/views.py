from django.shortcuts import render
from django.http import HttpResponse
from models import KrakenLog
from Web_Scout.models import Interfaces, Hosts
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from Kraken.krakenlib import BuildQuery
# Create your views here.

@login_required
def krakenlog(request):
	search = request.GET.get('search', '')
	entries_per_page = request.GET.get('entries_per_page', '50')
	entry_array = []
	nav_list = [-10,-9,-8,-7,-6,-5,-4,-3,-2,-1]
	
	if search:
		entry_query = BuildQuery(search, ['TimeStamp', 'User', 'Message', 'Type'])
		entry_array = KrakenLog.objects.all().order_by('-id').filter(entry_query)

	if not entry_array:
		entry_array = KrakenLog.objects.all().order_by('-id')

	if int(entries_per_page) in (50, 100, 150, 200, 300):
		paginator = Paginator(entry_array, entries_per_page)
	else:
		paginator = Paginator(entry_array, 50)

	parameters = ''
	for key,value in request.GET.items():
		if not key == 'page' and not value == "":
			parameters = parameters + '&' + key + '=' + value

	page = request.GET.get('page')
	try:
		entries = paginator.page(page)
	except PageNotAnInteger:
		entries = paginator.page(1)
	except EmptyPage:
		entries.paginator.page(paginator.num_pages)
	return render(request, 'Logs/LogView.html', {'entries':entries, 'nav_list':nav_list, 'pagination_parameters': parameters, 'entries_per_page': int(entries_per_page)})

@login_required
def reports(request):
	host_count = str(Hosts.objects.all().count())
	interface_count = str(Interfaces.objects.all().count())
	printer_count = str(Hosts.objects.filter(Category='printer').count())
	default_creds = Interfaces.objects.filter(DefaultCreds=True)
	http_auth = Interfaces.objects.filter(HttpAuth=True)
	notes = Interfaces.objects.exclude(Notes__exact='')
	return render(request, 'Logs/Web_Scout.html', {'default_creds':default_creds, 'http_auth':http_auth, 'notes':notes, 'host_count':host_count, 'interface_count':interface_count, 'printer_count':printer_count})
