from __future__ import unicode_literals

from django.db import models

# Create your models here.
class Addresses(models.Model):
	AddressID = models.CharField(max_length=18)
	Hostname = models.CharField(max_length=100)
	Address = models.CharField(max_length=18)
	Cidr = models.CharField(max_length=2)

class Hosts(models.Model):
	def __str__(self):
		return self.IP
	addresses = models.ForeignKey(Addresses, on_delete=models.SET_NULL, blank=True, null=True)
	HostID = models.CharField(max_length=12)
	IP = models.CharField(max_length=15)
	Hostname = models.CharField(max_length=75)
	OS = models.CharField(max_length=25)
	Rating = models.CharField(max_length=10)
	Reviewed = models.BooleanField(default=False)
	Category = models.CharField(max_length=25)
	LastSeen = models.CharField(max_length=100)
	New = models.BooleanField(default=False)
	Stale = models.BooleanField(default=False)
	StaleLevel = models.IntegerField(default=0)

class Interfaces(models.Model):
	def __str__(self):
		return self.Port
	hosts = models.ForeignKey(Hosts, on_delete=models.CASCADE)
	IntID = models.CharField(max_length=25)
	Port = models.CharField(max_length=6)
	Name = models.CharField(max_length=100)
	Product = models.CharField(max_length=100)
	Version = models.CharField(max_length=100)
	Banner = models.CharField(max_length=300)
	ImgLink = models.CharField(max_length=100)
	Notes = models.CharField(max_length=500)
	Url = models.CharField(max_length=35)
	DefaultCreds = models.BooleanField(default=False)
	HttpAuth = models.BooleanField(default=False)
	Default_Credentials = models.CharField(max_length=100)
	Retry = models.BooleanField(default=False)
	Module = models.CharField(max_length=6)
	Type = models.CharField(max_length=4)

class Tasks(models.Model):
	def __str__(self):
		return self.Task
	Task = models.CharField(max_length=25)
	Task_Id = models.CharField(max_length=75)
	Count = models.IntegerField(default=0)
