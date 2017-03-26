from django.conf.urls import patterns, url

urlpatterns = patterns('horizon',
    url(r'^login$', 'facebook.views.login'),
    url(r'^authentication_callback$', 'facebook.views.authentication_callback'),
)
