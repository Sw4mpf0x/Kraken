from __future__ import unicode_literals

from django.db import models

# Create your models here.

class KrakenLog(models.Model):
	TimeStamp = models.CharField(max_length=100)
	User = models.CharField(max_length=25)
	Message = models.CharField(max_length=150)
	Type = models.CharField(max_length=20)
	