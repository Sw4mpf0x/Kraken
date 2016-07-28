from django.conf.urls import url

from . import views

app_name = 'Web_Scout'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^setup/$', views.setup, name='setup'),
    url(r'^viewer/$', views.viewer, name='viewer'),
    url(r'^task_state$', views.task_state, name='task_state'),
]


