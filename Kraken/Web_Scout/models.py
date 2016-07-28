from __future__ import unicode_literals

from django.db import models

# Create your models here.
class Hosts(models.Model):
	def __str__(self):
           	return self.IP
	IP = models.CharField(max_length=15)
	Hostname = models.CharField(max_length=75)
	DeviceType = models.CharField(max_length=25)
	OS = models.CharField(max_length=25)
	Rating = models.CharField(max_length=10)
	Reviewed = models.BooleanField(default=False)

class Ports(models.Model):
	def __str__(self):
		return self.Port
	hosts = models.ForeignKey(Hosts, on_delete=models.CASCADE)
	PortID = models.CharField(max_length=25)
	Port = models.CharField(max_length=6)
	Name = models.CharField(max_length=100)
	Product = models.CharField(max_length=100)
	Version = models.CharField(max_length=100)
	Extra_Info = models.CharField(max_length=200)
	Banner = models.CharField(max_length=300)
	ImgLink = models.CharField(max_length=100)
	Notes = models.CharField(max_length=500)
	Link = models.CharField(max_length=35)
	DefaultCreds = models.BooleanField(default=False)
	HttpAuth = models.BooleanField(default=False)

class Tasks(models.Model):
	def __str__(self):
		return self.Task
	Task = models.CharField(max_length=25)
	Task_Id = models.CharField(max_length=75)
