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
        r'^(?P<pk>[0-9]+)/results/$',
        views.ResultsView.as_view(),
        name='results'),
    url(
        r'^new/query/$',
        views.new_query,
        name="new_query"),
    url(
        r'^query/(?P<pk>[0-9]+)/edit/$',
        views.query_edit,
        name='query_edit'),
    url(
        r'^(?P<query_id>[0-9]+)/define/$',
        views.define,
        name='define'),
]
