from django.conf.urls import patterns, url

urlpatterns = patterns('horizon',
    url(r'^login$', 'linkedin.views.login'),
    url(r'^authentication_callback$', 'linkedin.views.authentication_callback'),
)
