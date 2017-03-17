# OFL - OpenStack Facebook LinkedIn

This is a plugin for Facebook and LinkedIn users authenticate against OpenStack based clouds. Users can only authenticate if they belong to specific groups in LinkedIn or Facebook.

At this moment, it's not working, since I just started the project.

## Installation

Copy 'horizon' folder to /usr/lib/python2.7/site-packages/

## Config

Need to change couple things in Horizon settings:

Add the following lines to /etc/openstack-dashboard/local_settings
```
FACEBOOK_APP_ID = ""
FACEBOOK_APP_SECRET = ""
FACEBOOK_SCOPE = "email"

LINKEDIN_APP_KEY = ""
LINKEDIN_APP_SECRET = ""
LINKEDIN_STATE = ""
LINKEDIN_GROUP_ID = ""

ADMIN_USER = ""
ADMIN_TENANT = ""
ADMIN_PASSWORD = ""
MEMBER_USER_ROLE = ""

DATABASES = {'default': {'ENGINE': 'django.db.backends.mysql',
						 'NAME': '',
						 'USER': '',
						 'PASSWORD': ''}}
```
Add the following lines to /usr/share/openstack-dashboard/openstack_dashboard/settings.py

Add to INSTALLED_APPS:
```
	'horizon.common',
	'horizon.linkedin',
```

Add to AUTHENTICATION_BACKENDS (place it first other backends):
```
	'horizon.common.backend.ExternalBackend'
```
Add these lines:

```
AUTH_PROFILE_MODULE = 'horizon.common.backend.ExternalBackend'
AUTH_USER_MODEL = 'auth.User'
```
Now, sync the database:

```
/usr/share/openstack-dashboard/./manage.py sync_db
```