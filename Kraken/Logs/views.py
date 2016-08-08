from django.shortcuts import render
from django.http import HttpResponse
from Web_Scout.models import Ports, Hosts
# Create your views here.

def index(request):
	return HttpResponse("Under Maintenance")

def reports(request):
	default_creds = Ports.objects.filter(DefaultCreds=True)
	http_auth = Ports.objects.filter(HttpAuth=True)
	comments = http_auth = Ports.objects.filter(HttpAuth=True)
	return render(request, 'Logs/Web_Scout.html', {'default_creds':default_creds, 'http_auth':http_auth})
