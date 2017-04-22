from django.db import models
#from django.contrib.auth.models import User
from django.conf import settings
from openstack_auth.user import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class ExternalProfile(models.Model):
    #user = models.OneToOneField(User)
    #user = settings.AUTH_USER_MODEL
    user = models.CharField(max_length=32)
    external_id = models.CharField(max_length=150)
    access_token = models.CharField(max_length=1024)
    password =  models.CharField(max_length=150)
    project_id = models.CharField(max_length=150)