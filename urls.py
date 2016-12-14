from django.conf.urls import url

from . import views

app_name = 'queryforce'
urlpatterns = [
    url(
        r'^$',
        views.IndexView.as_view(),
        name='index'),
    url(
        r'^(?P<pk>[0-9]+)/$',
        views.DetailView.as_view(),
        name='detail'),
    url(
        r'^(?P<pk>[0-9]+)/raw/$',
        views.raw_results,
        name='raw_results'),
]
