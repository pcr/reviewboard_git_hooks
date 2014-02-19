from django.conf.urls import patterns, url

urlpatterns = patterns('setssh.views',
    url(r'^$', 'setssh'),
)
