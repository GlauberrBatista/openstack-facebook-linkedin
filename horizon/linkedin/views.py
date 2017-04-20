import urllib

from django.http import HttpResponseRedirect
from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth import authenticate
from openstack_auth.user import set_session_from_user
from django.core.urlresolvers import reverse
from openstack_auth.forms import Login


def login(request):
	""" First step of process, redirects user to linkedin,which redirects to authentication_callback. """
	args = {
		'client_id': settings.LINKEDIN_APP_KEY,
		'scope': 'r_basicprofile,r_emailaddress',
		'state': settings.LINKEDIN_STATE,
		'redirect_uri': request.build_absolute_uri(\
			reverse('horizon.linkedin.views.authentication_callback')
		)
	}

	return HttpResponseRedirect('https://www.linkedin.com/uas/oauth2/authorization?'
			 'response_type=code&' + urllib.urlencode(args))


def authentication_callback(request):
	""" Second step of the login process.
	It reads in a code from LinkedIn, then redirects back to the home page. """
	code = request.GET.get('code')
	user = authenticate(request=request, provider='linkedin')
	try:
		auth_login(request, user)
	except AttributeError:
		# No valid user returned
		return HttpResponseRedirect(request.build_absolute_uri('/'))
	set_session_from_user(request, user)
	region = request.user.endpoint
	region_name = dict(Login.get_region_choices()).get(region)
	request.session['region_endpoint'] = region
	request.session['region_name'] = region_name
	url = getattr(settings, "LOGIN_REDIRECT_URL", "/")
	resp = HttpResponseRedirect(url)

	return resp
