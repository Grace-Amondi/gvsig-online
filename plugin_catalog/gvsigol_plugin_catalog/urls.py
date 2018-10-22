from django.conf.urls import url

urlpatterns = [
   # url(r'^catalog/get_editor/(?P<metadata_id>.*)/$', 'gvsigol_plugin_catalog.views.metadata_form', name='metadata_form'),
   url(r'^catalog/get_query/$', 'gvsigol_plugin_catalog.views.get_query', name='get_query'),
   url(r'^catalog/get_metadata/(?P<metadata_id>.+)/$', 'gvsigol_plugin_catalog.views.get_metadata', name='get_metadata'),
   url(r'^catalog/get_metadata_id/(?P<layer_ws>.+)/(?P<layer_name>.+)/$', 'gvsigol_plugin_catalog.views.get_metadata_id', name='get_metadata_id'),

]