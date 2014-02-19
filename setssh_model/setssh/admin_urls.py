from django.conf.urls import patterns, url

patterns('setssh.views',
    url(r'^$', 'configure'),
)