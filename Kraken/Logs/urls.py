from django.conf.urls import url

from . import views

app_name = 'Logs'
urlpatterns = [
    url(r'^LogView.html$', views.krakenlog, name='krakenlog'),
    url(r'^Reports.html$', views.reports, name='reports'),
]


