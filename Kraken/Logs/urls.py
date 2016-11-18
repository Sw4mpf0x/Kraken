from django.conf.urls import url

from . import views

app_name = 'Logs'
urlpatterns = [
    url(r'^LogView$', views.krakenlog, name='krakenlog'),
    url(r'^Reports$', views.reports, name='reports'),
]


