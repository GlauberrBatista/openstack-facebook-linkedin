import cgi
import json
import logging
import string
import random
import urllib

from django.conf import settings
from openstack_auth.user import User
from django.contrib import messages
from django.db import IntegrityError

from horizon.common.models import ExternalProfile
from keystoneclient.v3 import client as keystone_client
from openstack_auth.backend import KeystoneBackend
from openstack_auth.user import Token
from openstack_auth.user import create_user_from_token
from openstack_auth import exceptions
from openstack_auth import user as auth_user
from openstack_auth import utils



LOG = logging.getLogger(__name__)


class ExternalBackend:
	def _admin_client(self):
		return  keystone_client.Client(username=settings.ADMIN_USER, password=settings.ADMIN_PASSWORD, tenant_name=settings.ADMIN_TENANT, auth_url=settings.OPENSTACK_KEYSTONE_URL)

	def _get_facebook_profile(self, code=None, request=None):
		redirect_uri = request.build_absolute_uri('authentication_callback')
		args = {
			'code': code,
			'client_id': settings.FACEBOOK_APP_ID,
			'client_secret': settings.FACEBOOK_APP_SECRET,
			'redirect_uri': redirect_uri,
		}
		target = urllib.urlopen(
				'https://graph.facebook.com/oauth/access_token?'
				+ urllib.urlencode(args)).read()
		response = json.loads(target)
		access_token = response['access_token']

		try:
			fb_profile = urllib.urlopen(
				'https://graph.facebook.com/me?fields=name,id,email&access_token=%s' % access_token)
			fb_profile = json.load(fb_profile)
			facebook_id = fb_profile['id']
			facebook_email = fb_profile['email']
		except Exception as e:
			LOG.warn("Facebook get user profile Error: %s", e)
			messages.error(request, 'Your Facebook is not authorized to login.')
			return None

		members_list = []
		try:
			graph_data = None
			group_url = (
					"https://graph.facebook.com/"
					"%s/members?limit=1&access_token=%s"
					% (settings.FACEBOOK_GROUP_ID, access_token))
			f = urllib.urlopen(group_url)
			graph_data_json = f.read()
			f.close()
			graph_data = json.loads(graph_data_json)
			while 'next' in graph_data['paging']:
				next_page = group_url + "&after=%s" % graph_data['paging']['cursors']['after']
				f = urllib.urlopen(next_page)
				graph_data_json = f.read()
				f.close()
				graph_data = json.loads(graph_data_json)
				members_list.append(graph_data['data'][0]['id'])
		except Exception as e:
			LOG.warn("Facebook user validate error: %s", e)
			messages.error(request, 'Failed to retrieve group members.')
			return None

		valid = False
		if facebook_id in members_list:
			valid = True
		return dict(user_id=facebook_id, user_email=facebook_email, access_token=access_token, valid=valid)

	def _get_linkedin_profile(self, code=None, request=None):
		redirect_uri = request.build_absolute_uri('authentication_callback')
		args = {
			'code': code,
			'scope': 'r_basicprofile,r_emailaddress,rw_groups',
			'redirect_uri': redirect_uri,
			'client_id': settings.LINKEDIN_APP_KEY,
			'client_secret': settings.LINKEDIN_APP_SECRET,
		}

		# Get a legit access token
		target = urllib.urlopen(
				'https://www.linkedin.com/uas/oauth2/accessToken?'
				+ 'grant_type=authorization_code&'
				+ urllib.urlencode(args)).read()
		response = json.loads(target)
		access_token = response['access_token']

		# Read the user's profile information
		try:
			linkedin_user = urllib.urlopen(
					'https://api.linkedin.com/v1/people/~:(id,email-address)?'
					'format=json&oauth2_access_token=%s' % access_token).read()
			linkedin_user = json.loads(linkedin_user)
			linkedin_id = linkedin_user['id']
			linkedin_email = linkedin_user['emailAddress']
		except Exception as e:
			LOG.warn("LinkedIn get user profile Error: %s", e)
			messages.error(request, 'Your LinkedIn is not authorized to login.')
			return None

		# Validate the user
		try:
			memberships = urllib.urlopen(
					'https://api.linkedin.com/v1/people/~/'
					'group-memberships:(group:(id,name,),membership-state)?'
					'format=json&oauth2_access_token=%s' % access_token).read()
			memberships = json.loads(memberships)
			groups = memberships.get('values', [])
			group_ids = []
			for group in groups:
				group_ids.append(group['_key'])
		except Exception as e:
			LOG.warn("LinkedIn user validate error: %s", e)
			messages.error(request, 'Failed to retrieve group members.')
			return None

		valid = False
		if settings.LINKEDIN_GROUP_ID in group_ids:
			valid = True

		return dict(user_id=linkedin_id, user_email=linkedin_email, access_token=access_token, valid=valid)

	def authenticate(self, request=None, provider=None):
		""" Reads in a code and asks Provider if it's valid and
		what user it points to. """
		code = request.GET.get('code')
		keystone = KeystoneBackend()
		self.keystone = keystone
		try:
			profile_handle = getattr(self, '_get_%s_profile' % provider)
		except AttributeError:
			LOG.warn("Need to define _get_%s_profile function." % provider)
			return
		user_profile = profile_handle(code=code, request=request)
		if not user_profile:
			return
		if not user_profile['valid']:
			msg = "Failed to login, you are not in %s group." % provider
			messages.error(request, msg)
			return

		external_id = user_profile['user_id']
		external_email = user_profile['user_email']
		access_token = user_profile['access_token']

		username = "%s_%s" % (provider, external_id)
		tenant_name = username
		password = ""
		keystone_admin = self._admin_client()
		keystone_user_list = keystone_admin.users.list()
		for i in keystone_user_list:
			if username == i.name:
				user = keystone_admin.users.get(i.id)
				external_user = ExternalProfile.objects.get(user=user.id)
				password = external_user.password
				LOG.info("User %s found" % user.id)
				break
		else: 
			try:
				LOG.info('Creating new account for user %s' % username)
				keystone_admin = self._admin_client()
				password = "".join([random.choice(string.ascii_lowercase + string.digits) for i in range(8)])

				project = keystone_admin.projects.create(username, 'default', description="External account", enabled=True)
				user = keystone_admin.users.create(username, project=project.id, password=password, email=external_email, enabled=True)
				LOG.info("AAAAAA: %s" % dir(keystone_admin))
				keystone_admin.roles.grant(settings.MEMBER_USER_ROLE, user=user.id, project=project.id)
				
				LOG.info('Creating external profile for user %s' % username)
				external_user = ExternalProfile(user=user.id, external_id=external_id, access_token=access_token, password=password, project_id=project.id)
				LOG.info(external_user.user)
				external_user.save()
			except Exception as e:
				LOG.warn("Error creating user: %s, error: %s" % (username, e))
				return None
		try:
			domain_name = keystone_admin.domains.get(user.domain_id).name
			auth_user = keystone.authenticate(request=request, username=username, password=password, auth_url=settings.OPENSTACK_KEYSTONE_URL, user_domain_name=domain_name)
			return auth_user
		except Exception as e:
			messages.error(request, "Failed to login: %s" % e)
			return None

	def get_user(self, user_id):
		""" Just returns the user of a given ID. """
		try:
			keystone = KeystoneBackend()
			keystone.request = self.request
		except:
			return None
		return keystone.get_user(user_id)

	supports_object_permissions = False
	supports_anonymous_user = False
