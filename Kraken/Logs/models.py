from __future__ import unicode_literals

from django.db import models

# Create your models here.

class Log(models.Model):
	TimeStamp
	User = models.CharField(max_length=25)
	Type = models.CharField(max_length=20)
	Message = models.CharField(max_length=150)