from django.conf.urls import url

from . import views

app_name = 'Logs'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^reports/$', views.reports, name='reports'),
]


