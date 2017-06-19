'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
from gvsigol_services.rest_geoserver import FailedRequestError
from geoserver import workspace
from PIL._util import isStringType
from operator import isNumberType
'''
@author: Cesar Martinez <cmartinez@scolab.es>
'''

from models import Workspace, Datastore, LayerGroup, Layer, LayerReadGroup, LayerWriteGroup, Enumeration, EnumerationItem,\
    LayerLock
from forms_services import WorkspaceForm, DatastoreForm, LayerForm, LayerUpdateForm, DatastoreUpdateForm
from forms_geoserver import CreateFeatureTypeForm
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponse
from django.views.decorators.http import require_http_methods, require_safe,require_POST, require_GET
from django.shortcuts import render_to_response, redirect, RequestContext
from backend_mapservice import backend as mapservice_backend
from backend_postgis import Introspect
from gvsigol_services.backend_resources import resource_manager
from gvsigol_auth.utils import superuser_required, staff_required
from django.contrib.auth.models import User 
from gvsigol_core.models import ProjectLayerGroup
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from gvsigol.settings import FILEMANAGER_DIRECTORY, LANGUAGES
from django.utils.translation import ugettext as _
from gvsigol_services.models import LayerResource
from gvsigol.settings import GVSIGOL_SERVICES, CONTROL_FIELDS
from django.core.urlresolvers import reverse
from gvsigol_core import utils as core_utils
from gvsigol_auth.models import UserGroup
from django.shortcuts import render
from django.utils import timezone
from gvsigol import settings
import locks_utils
import requests
import logging
import signals
import urllib
import utils
import json
import ast
import re
import os
import unicodedata
logger = logging.getLogger(__name__)

_valid_name_regex=re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@superuser_required
def workspace_list(request):
    response = {
        'workspaces': Workspace.objects.values()
    }
    return render_to_response('workspace_list.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
@require_http_methods(["GET", "POST", "HEAD"])
def workspace_add(request):
    if request.method == 'POST':
        form = WorkspaceForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            if _valid_name_regex.search(name) == None:
                form.add_error(None, _("Invalid workspace name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name))
            else:
                # first create the ws on the backend
                if mapservice_backend.createWorkspace(form.cleaned_data['name'],
                    form.cleaned_data['uri'],
                    form.cleaned_data['description'],
                    form.cleaned_data['wms_endpoint'],
                    form.cleaned_data['wfs_endpoint'],
                    form.cleaned_data['wcs_endpoint'],
                    form.cleaned_data['cache_endpoint']):
                    
                    isPublic = False
                    if form.cleaned_data['is_public']:
                        isPublic = True
                        
                    # save it on DB if successfully created
                    newWs = Workspace(**form.cleaned_data)
                    newWs.created_by = request.user.username
                    newWs.is_public = isPublic
                    newWs.save()
                    mapservice_backend.reload_nodes()
                    return HttpResponseRedirect(reverse('workspace_list'))
                else:
                    # FIXME: the backend should raise an exception to identify the cause (e.g. workspace exists, backend is offline)
                    form.add_error(None, _("Error: workspace could not be created"))
                
    else:
        form = WorkspaceForm()
            
    return render(request, 'workspace_add.html', {'form': form, 'service_base_url': mapservice_backend.getBaseUrl()})

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@superuser_required
def workspace_import(request):
    """
    FIXME: Not implemented yet.
    Imports on gvSIG Online an existing workspace and all its depending stores, layers, styles, etc  
    """
    if request.method == 'POST':
        #form = None #FIXME
        #if form.is_valid():
        #    #get existing ws and associated resources from Geoserver REST API 
        #    pass
        ##
        # get selected ws
        # recursively import the proposed ws
        pass
    else:
        # create empty form
        # FIXME: probably does not work
        workspaces = mapservice_backend.get_workspaces()
        workspace_names = [n for n in workspaces['name']]
        querySet = Workspace.objects.all().exclude(name__in=workspace_names)
        response = {
            'workspaces': querySet.values()
        }
        return render_to_response('workspace_import.html', response, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@superuser_required
def workspace_delete(request, wsid):
    try:
        ws = Workspace.objects.get(id=wsid)
        if mapservice_backend.deleteWorkspace(ws):
            datastores = Datastore.objects.filter(workspace_id=ws.id)
            for ds in datastores:
                layers = Layer.objects.filter(datastore_id=ds.id)
                for l in layers:
                    mapservice_backend.deleteLayerStyles(l)
            ws.delete()
            mapservice_backend.reload_nodes()
            return HttpResponseRedirect(reverse('workspace_list'))
        else:
            return HttpResponseBadRequest()
    except:
        return HttpResponseNotFound('<h1>Workspace not found{0}</h1>'.format(ws.name)) 
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def workspace_update(request, wid):
    if request.method == 'POST':
        description = request.POST.get('workspace-description')
        isPublic = False
        if 'is_public' in request.POST:
            isPublic = True
        
        workspace = Workspace.objects.get(id=int(wid))
        
        workspace.description = description
        workspace.is_public = isPublic
        workspace.save()   
        return redirect('workspace_list')

    else:
        workspace = Workspace.objects.get(id=int(wid))
        return render_to_response('workspace_update.html', {'wid': wid, 'workspace': workspace}, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@staff_required
def datastore_list(request):
    
    datastore_list = None
    if request.user.is_superuser:
        datastore_list = Datastore.objects.all()
    else:
        datastore_list = Datastore.objects.filter(created_by__exact=request.user.username)
        
    response = {
        'datastores': datastore_list
    }
    return render_to_response('datastore_list.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def datastore_add(request):
    if request.method == 'POST':
        post_dict = request.POST.copy()
        type = request.POST.get('type')
        if type == 'c_GeoTIFF':
            file = post_dict.get('file')
            post_dict['connection_params'] = post_dict.get('connection_params').replace('url_replace', file)
        form = DatastoreForm(post_dict)
        if form.is_valid():
            name = form.cleaned_data['name']
            if _valid_name_regex.search(name) == None:
                form.add_error(None, _("Invalid datastore name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name))
            else:
                # first create the datastore on the backend
                if mapservice_backend.createDatastore(form.cleaned_data['workspace'],
                                                      form.cleaned_data['type'],
                                                      form.cleaned_data['name'],
                                                      form.cleaned_data['description'],
                                                      form.cleaned_data['connection_params']):
                    # save it on DB if successfully created
                    newRecord = Datastore(
                        workspace=form.cleaned_data['workspace'],
                        type=form.cleaned_data['type'],
                        name=form.cleaned_data['name'],
                        description=form.cleaned_data['description'],
                        connection_params=form.cleaned_data['connection_params'],
                        created_by=request.user.username
                    )
                    newRecord.save()
                    mapservice_backend.reload_nodes()
                    return HttpResponseRedirect(reverse('datastore_list'))
                else:
                    # FIXME: the backend should raise an exception to identify the cause (e.g. datastore exists, backend is offline)
                    form.add_error(None, _('Error: Data store could not be created'))
            
    else:
        form = DatastoreForm()
        if not request.user.is_superuser:
            form.fields['workspace'].queryset = Workspace.objects.filter(created_by__exact=request.user.username).order_by('name')
    return render(request, 'datastore_add.html', {'fm_directory': FILEMANAGER_DIRECTORY + "/", 'form': form})

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def datastore_update(request, datastore_id):
    datastore = Datastore.objects.get(id=datastore_id)
    if datastore==None:
        return HttpResponseNotFound(_('Datastore not found'))
    if request.method == 'POST':
        form = DatastoreUpdateForm(request.POST)
        if form.is_valid():
                dstype = datastore.type
                description = form.cleaned_data.get('description')
                connection_params = form.cleaned_data.get('connection_params')
                if mapservice_backend.updateDatastore(datastore.workspace.name, datastore.name,
                                                      description, dstype, connection_params):
                    # REST API does not allow to can't change the workspace or name of a datastore 
                    #datastore.workspace = workspace
                    #datastore.name = name
                    datastore.description = description
                    datastore.connection_params = connection_params
                    datastore.save()
                    mapservice_backend.reload_nodes()
                    return HttpResponseRedirect(reverse('datastore_list'))
                else:
                    form.add_error(None, _("Error updating datastore"))
    else:
        form = DatastoreUpdateForm(instance=datastore)
    return render(request, 'datastore_update.html', {'form': form, 'datastore_id': datastore_id, 'workspace_name': datastore.workspace.name})

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@staff_required
def datastore_delete(request, dsid):
    try:
        ds = Datastore.objects.get(id=dsid)
        if mapservice_backend.deleteDatastore(ds.workspace, ds):
            layers = Layer.objects.filter(datastore_id=ds.id)
            for l in layers:
                mapservice_backend.deleteLayerStyles(l)
            Datastore.objects.all().filter(name=ds.name).delete()
            mapservice_backend.reload_nodes()
            return HttpResponseRedirect(reverse('datastore_list'))
        else:
            return HttpResponseBadRequest()
    except:
        return HttpResponseNotFound('<h1>Datastore not found{0}</h1>'.format(ds.name)) 

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@staff_required
def layer_list(request):
    
    layer_list = None
    if request.user.is_superuser:
        layer_list = Layer.objects.all()
    else:
        layer_list = Layer.objects.filter(created_by__exact=request.user.username)
        
    response = {
        'layers': layer_list
    }
    return render_to_response('layer_list.html', response, context_instance=RequestContext(request))
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layer_delete(request, layer_id):
    try:
        layer = Layer.objects.get(pk=layer_id)
        mapservice_backend.deleteGeoserverLayerGroup(layer.layer_group)
        mapservice_backend.deleteResource(layer.datastore.workspace, layer.datastore, layer)
        mapservice_backend.deleteLayerStyles(layer)
        signals.layer_deleted.send(sender=None, layer=layer)
        if not 'no_thumbnail.jpg' in layer.thumbnail.name:
            if os.path.isfile(layer.thumbnail.path):
                os.remove(layer.thumbnail.path)
        Layer.objects.all().filter(pk=layer_id).delete()
        mapservice_backend.setDataRules()
        core_utils.toc_remove_layer(layer)
        mapservice_backend.createOrUpdateGeoserverLayerGroup(layer.layer_group)
        mapservice_backend.reload_nodes()
        return HttpResponseRedirect(reverse('datastore_list'))
        
    except Exception as e:
        return HttpResponseNotFound('<h1>Error deleting layer: {0}</h1>'.format(layer_id)) 


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def backend_datastore_list(request):
    """
    Lists the resources existing on a data store, retrieving the information
    directly from the backend (which may differ from resources available on
    Django DB). Useful to register new resources on Django DB. 
    """
    if 'id_workspace' in request.GET:
        id_ws = request.GET['id_workspace']
        ws = Workspace.objects.get(id=id_ws)
        if ws:
            datastores = mapservice_backend.getDataStores(ws)
            datastores_sorted = sorted(datastores) 
            return HttpResponse(json.dumps(datastores_sorted))
    return HttpResponseBadRequest()


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def backend_resource_list_available(request):
    """
    Lists the resources existing on a data store, retrieving the information
    directly from the backend (which may differ from resurces available on
    Django DB). Useful to register new resources on Django DB. 
    """
    if 'id_datastore' in request.GET:
        id_ds = request.GET['id_datastore']
        ds = Datastore.objects.get(id=id_ds)
        if ds:
            resources = mapservice_backend.getResources(ds.workspace.name, ds.name, ds.type, 'available')
            resources_sorted = sorted(resources) 
            return HttpResponse(json.dumps(resources_sorted))
    return HttpResponseBadRequest()


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def backend_resource_list(request):
    """
    Lists the resources existing on a data store, retrieving the information
    directly from the backend (which may differ from resurces available on
    Django DB). Useful to register new resources on Django DB. 
    """
    if 'id_datastore' in request.GET:
        type = 'all'
        if 'type' in request.GET:
            type = request.GET['type']
        id_ds = request.GET['id_datastore']
        ds = Datastore.objects.get(id=id_ds)
        if ds:
            resources = mapservice_backend.getResources(ds.workspace.name, ds.name, ds.type, type)
            resources_sorted = sorted(resources) 
            return HttpResponse(json.dumps(resources_sorted))
    return HttpResponseBadRequest()


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def backend_fields_list(request):
    """
    Lists the resources existing on a data store, retrieving the information
    directly from the backend (which may differ from resources available on
    Django DB). Useful to register new resources on Django DB. 
    """
    
    if 'name_datastore' in request.GET and 'id_workspace' in request.GET and 'name_resource' in request.GET:
        name = request.GET['name_resource']
        ds_name = request.GET['name_datastore']
        id_ws = request.GET['id_workspace']
        ws = Workspace.objects.get(id=id_ws)
        ds = Datastore.objects.get(name=ds_name, workspace=ws)
        if ds:
            resources = mapservice_backend.getResource(ds.workspace.name, ds.name, name)
            result_resources = []
            layer = Layer.objects.filter(datastore=ds, name=name).first()
            conf = None
            if layer and layer.conf:
                conf = ast.literal_eval(layer.conf)
            for resource in resources:
                if conf:
                    for f in conf['fields']:
                        if f['name'] == resource:
                            field = {}
                            field['name'] = f['name']
                            for id, language in LANGUAGES:
                                field['title-'+id] = f['title-'+id]
                            result_resources.append(field)
                else:
                    field = {}
                    field['name'] = resource
                    for id, language in LANGUAGES:
                        field['title-'+id] = resource
                    result_resources.append(field)
                    
            result_resources_sorted = sorted(result_resources) 
            return HttpResponse(json.dumps(result_resources_sorted))
    
    return HttpResponseBadRequest()    



@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_add(request):
    if request.method == 'POST':
        form = LayerForm(request.POST)
        abstract = request.POST.get('md-abstract')
        is_visible = False
        if 'visible' in request.POST:
            is_visible = True
        
        is_queryable = False
        if 'queryable' in request.POST:
            is_queryable = True
            
        cached = False
        if 'cached' in request.POST:
            cached = True
            
        single_image = False
        if 'single_image' in request.POST:
            single_image = True
        
        if form.is_valid():
            try:
                # first create the resource on the backend
                mapservice_backend.createResource(form.cleaned_data['datastore'].workspace,
                                      form.cleaned_data['datastore'],
                                      form.cleaned_data['name'],
                                      form.cleaned_data['title'])
                # save it on DB if successfully created
                newRecord = Layer(**form.cleaned_data)
                newRecord.created_by = request.user.username
                newRecord.type = form.cleaned_data['datastore'].type
                newRecord.visible = is_visible
                newRecord.queryable = is_queryable
                newRecord.cached = cached
                newRecord.single_image = single_image
                newRecord.abstract = abstract
                newRecord.save()
                
                if form.cleaned_data['datastore'].type != 'e_WMS':
                    datastore = Datastore.objects.get(id=newRecord.datastore.id)
                    workspace = Workspace.objects.get(id=datastore.workspace_id)
                    
                    style_name = workspace.name + '_' + newRecord.name + '_default'
                    mapservice_backend.createDefaultStyle(newRecord, style_name)
                    mapservice_backend.setLayerStyle(newRecord, style_name)
                    newRecord = mapservice_backend.updateThumbnail(newRecord, 'create')
                    newRecord.save()
                    
                core_utils.toc_add_layer(newRecord)
                mapservice_backend.createOrUpdateGeoserverLayerGroup(newRecord.layer_group)
                mapservice_backend.reload_nodes()
                return HttpResponseRedirect(reverse('layer_permissions_update', kwargs={'layer_id': newRecord.id}))
            
            except Exception as e:
                try:
                    msg = e.get_message()
                except:
                    msg = _("Error: layer could not be published")
                # FIXME: the backend should raise more specific exceptions to identify the cause (e.g. layer exists, backend is offline)
                form.add_error(None, msg)
    else:
        form = LayerForm()
        if not request.user.is_superuser:
            form.fields['datastore'].queryset = Datastore.objects.filter(created_by__exact=request.user.username)
            form.fields['layer_group'].queryset = LayerGroup.objects.filter(created_by__exact=request.user.username)
    return render(request, 'layer_add.html', {'form': form})


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_update(request, layer_id):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(layer_id))
        workspace = request.POST.get('workspace')
        datastore = request.POST.get('datastore')
        name = request.POST.get('name')
        title = request.POST.get('title')
        #style = request.POST.get('style')
        layer_group_id = request.POST.get('layer_group')
        is_visible = False
        if 'visible' in request.POST:
            is_visible = True
        
        is_queryable = False
        if 'queryable' in request.POST:
            is_queryable = True
            
        cached = False
        if 'cached' in request.POST:
            cached = True
            
        single_image = False
        if 'single_image' in request.POST:
            single_image = True
                
        old_layer_group = LayerGroup.objects.get(id=layer.layer_group_id)
        
        if mapservice_backend.updateResource(workspace, datastore, name, title):
            layer.title = title
            layer.cached = cached
            layer.visible = is_visible
            layer.queryable = is_queryable 
            layer.single_image = single_image 
            layer.layer_group_id = layer_group_id
            layer.save()
            
            new_layer_group = LayerGroup.objects.get(id=layer.layer_group_id)
            
            if old_layer_group.id != new_layer_group.id:
                core_utils.toc_move_layer(layer, old_layer_group)
                mapservice_backend.createOrUpdateGeoserverLayerGroup(old_layer_group)
                mapservice_backend.createOrUpdateGeoserverLayerGroup(new_layer_group)
                                
            mapservice_backend.reload_nodes()   
            return HttpResponseRedirect(reverse('layer_permissions_update', kwargs={'layer_id': layer_id}))
            
    else:
        layer = Layer.objects.get(id=int(layer_id))
        datastore = Datastore.objects.get(id=layer.datastore.id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        form = LayerUpdateForm(instance=layer)
        return render(request, 'layer_update.html', {'layer': layer, 'workspace': workspace, 'form': form, 'layer_id': layer_id})
    
    
def layer_autoconfig(layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    fields = []
    conf = {}
    available_languages = []
    for id, language in LANGUAGES:
        available_languages.append(id)
    
    datastore = Datastore.objects.get(id=layer.datastore_id)
    workspace = Workspace.objects.get(id=datastore.workspace_id)
    (ds_type, resource) = mapservice_backend.getResourceInfo(workspace.name, datastore, layer.name, "json")
    resource_fields = utils.get_alphanumeric_fields(utils.get_fields(resource))
    for f in resource_fields:
        field = {}
        field['name'] = f['name']
        for id, language in LANGUAGES:
            field['title-'+id] = f['name']
        field['visible'] = True
        field['editableactive'] = True
        field['editable'] = True
        for control_field in settings.CONTROL_FIELDS:
            if field['name'] == control_field['name']:
                field['editableactive'] = False
                field['editable'] = False
        field['infovisible'] = False
        fields.append(field)
        
    conf['fields'] = fields
        
    json_conf = conf
    layer.conf = json_conf
    layer.save()
    
    
 
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_config(request, layer_id):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(layer_id))
        
        conf = {}
        fields = []
        counter = int(request.POST.get('counter'))
        for i in range(1, counter+1):
            field = {}
            field['name'] = request.POST.get('field-name-' + str(i))
            for id, language in LANGUAGES:
                field['title-'+id] = request.POST.get('field-title-'+id+'-' + str(i))
            field['visible'] = False
            if 'field-visible-' + str(i) in request.POST:
                field['visible'] = True
            field['infovisible'] = False
            if 'field-infovisible-' + str(i) in request.POST:
                field['infovisible'] = True
            field['editable'] = False
            if 'field-editable-' + str(i) in request.POST:
                field['editableactive'] = True
                field['editable'] = True
                for control_field in settings.CONTROL_FIELDS:
                    if field['name'] == control_field['name']:
                        field['editableactive'] = False
                        field['editable'] = False
            fields.append(field)
        conf['fields'] = fields
        
        json_conf = conf
        layer.conf = json_conf
        layer.save()
        
        return redirect('layer_list')
            
    else:
        layer = Layer.objects.get(id=int(layer_id))
        fields = []
        available_languages = []
        for id, language in LANGUAGES:
            available_languages.append(id)
        
        try:
            conf = ast.literal_eval(layer.conf)
            fields_used = []
            for f in conf['fields']:
                field = {}
                field['name'] = f['name']
                fields_used.append(f['name'])
                for id, language in LANGUAGES:
                    field['title-'+id] = f['title-'+id]
                field['visible'] = f['visible']
                field['editable'] = f['editable']
                field['editableactive'] = True
                for control_field in settings.CONTROL_FIELDS:
                    if field['name'] == control_field['name']:
                        field['editableactive'] = False
                        field['editable'] = False
                field['infovisible'] = f['infovisible']
                fields.append(field)
                
            datastore = Datastore.objects.get(id=layer.datastore_id)
            workspace = Workspace.objects.get(id=datastore.workspace_id)
            (ds_type, resource) = mapservice_backend.getResourceInfo(workspace.name, datastore, layer.name, "json")
            resource_fields = utils.get_alphanumeric_fields(utils.get_fields(resource))
            for f in resource_fields:
                field = {}
                field['name'] = f['name']
                if not f['name'] in fields_used:
                    for id, language in LANGUAGES:
                        field['title-'+id] = f['name']
                    field['visible'] = True
                    field['editableactive'] = True
                    field['editable'] = True
                    for control_field in settings.CONTROL_FIELDS:
                        if field['name'] == control_field['name']:
                            field['editableactive'] = False
                            field['editable'] = False
                    field['infovisible'] = False
                    fields.append(field)
    
                
                
        except: 
            datastore = Datastore.objects.get(id=layer.datastore_id)
            workspace = Workspace.objects.get(id=datastore.workspace_id)
            (ds_type, resource) = mapservice_backend.getResourceInfo(workspace.name, datastore, layer.name, "json")
            resource_fields = utils.get_alphanumeric_fields(utils.get_fields(resource))
            for f in resource_fields:
                field = {}
                field['name'] = f['name']
                for id, language in LANGUAGES:
                    field['title-'+id] = f['name']
                field['visible'] = True
                field['editableactive'] = True
                field['editable'] = True
                for control_field in settings.CONTROL_FIELDS:
                    if field['name'] == control_field['name']:
                        field['editableactive'] = False
                        field['editable'] = False
                field['infovisible'] = False
                fields.append(field)
    
        return render(request, 'layer_config.html', {'layer': layer, 'layer_id': layer.id, 'fields': fields, 'fields_json': json.dumps(fields), 'available_languages': LANGUAGES, 'available_languages_array': available_languages})
    

@require_POST
@staff_required
def layer_boundingbox_from_data(request):
    try:
        #layer = Layer.objects.get(pk=layer_id)
        ws_name = request.POST['workspace']
        layer_name = request.POST['layer']
        if ":" in layer_name:
            layer_name = layer_name.split(":")[1]
        workspace = Workspace.objects.get(name=ws_name)
        layer_query_set = Layer.objects.filter(name=layer_name, datastore__workspace=workspace)
        layer = layer_query_set[0]
        
        mapservice_backend.updateBoundingBoxFromData(layer)  
        mapservice_backend.clearCache(workspace.name, layer)
        mapservice_backend.updateThumbnail(layer, 'update')
        
        layer_group = LayerGroup.objects.get(id=layer.layer_group_id)
        mapservice_backend.createOrUpdateGeoserverLayerGroup(layer_group)
        mapservice_backend.clearLayerGroupCache(layer_group.name)
        mapservice_backend.reload_nodes()
        
        return HttpResponse('{"response": "ok"}', content_type='application/json')
    
    except Exception as e:
        return HttpResponseNotFound('<h1>Layer not found: {0}</h1>'.format(layer.id))

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def cache_clear(request, layer_id):
    if request.method == 'GET':
        layer = Layer.objects.get(id=int(layer_id)) 
        datastore = Datastore.objects.get(id=layer.datastore.id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        mapservice_backend.clearCache(workspace.name, layer)
        mapservice_backend.reload_nodes()
        return redirect('layer_list')
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layergroup_cache_clear(request, layergroup_id):
    if request.method == 'GET':
        layergroup = LayerGroup.objects.get(id=int(layergroup_id)) 
        mapservice_backend.clearLayerGroupCache(layergroup.name)
        mapservice_backend.reload_nodes()
        return redirect('layergroup_list')
    

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layer_permissions_update(request, layer_id):
    if request.method == 'POST':
        assigned_read_roups = []
        for key in request.POST:
            if 'read-usergroup-' in key:
                assigned_read_roups.append(int(key.split('-')[2]))
                
        assigned_write_groups = []
        for key in request.POST:
            if 'write-usergroup-' in key:
                assigned_write_groups.append(int(key.split('-')[2]))
        
        try:     
            layer = Layer.objects.get(id=int(layer_id))
        except Exception as e:
            return HttpResponseNotFound('<h1>Layer not found{0}</h1>'.format(layer.name))
        
        agroup = UserGroup.objects.get(name__exact='admin')
        
        read_groups = []
        write_groups = []
        
        # clean existing groups and assign them again if necessary
        LayerReadGroup.objects.filter(layer=layer).delete()
        if len(assigned_read_roups) > 0:
            lrag = LayerReadGroup()
            lrag.layer = layer
            lrag.group = agroup
            lrag.save()
            read_groups.append(agroup)
        for group in assigned_read_roups:
            try:
                group = UserGroup.objects.get(id=group)
                lrg = LayerReadGroup()
                lrg.layer = layer
                lrg.group = group
                lrg.save()
                read_groups.append(group)
            except:
                pass
        
        LayerWriteGroup.objects.filter(layer=layer).delete()
        if not layer.type.startswith('c_'):
            lwag = LayerWriteGroup()
            lwag.layer = layer
            lwag.group = agroup
            lwag.save()
            write_groups.append(agroup)
        for group in assigned_write_groups:
            try:
                group = UserGroup.objects.get(id=group)
                lwg = LayerWriteGroup()
                lwg.layer = layer
                lwg.group = group
                lwg.save()
                write_groups.append(group)
            except:
                pass
                
                
        mapservice_backend.setLayerDataRules(layer, read_groups, write_groups)
        mapservice_backend.reload_nodes()
        return redirect('layer_list')
    else:
        try:
            layer = Layer.objects.get(pk=layer_id)
            groups = utils.get_all_user_groups_checked_by_layer(layer)   
            return render_to_response('layer_permissions_add.html', {'layer_id': layer.id, 'name': layer.name, 'groups': groups}, context_instance=RequestContext(request))
        except Exception as e:
            return HttpResponseNotFound('<h1>Layer not found: {0}</h1>'.format(layer_id))
   
def get_resources_from_workspace(request):
    # FIXME
    if request.method == 'POST':
        wid = request.POST.get('workspace_id')
        layer_list = Layer.objects.all()
        
        resources = []
        for r in layer_list:
            if not resource_published(r):
                datastore = Datastore.objects.get(id=r.datastore_id)
                resource = {}
                if datastore.workspace_id == int(wid):
                    resource['id'] = r.id
                    resource['name'] = r.name
                    resources.append(resource)
                
        response = {
            'resources': resources
        }     
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
def resource_published(resource):
    # FIXME
    published = False
    layers = Layer.objects.all()
    for layer in layers:
        if layer.resource.id == resource.id:
            published = True
            
    return published
    

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layergroup_list(request):
    
    layergroups_list = None
    if request.user.is_superuser:
        layergroups_list = LayerGroup.objects.all()
    else:
        layergroups_list = LayerGroup.objects.filter(created_by__exact=request.user.username)
        
    layergroups = []
    for lg in layergroups_list:
        if lg.name != '__default__':
            projects = []
            project_layergroups = ProjectLayerGroup.objects.filter(layer_group_id=lg.id)
            for alg in project_layergroups:
                projects.append(alg.project.name)
            layergroup = {}
            layergroup['id'] = lg.id
            layergroup['name'] = lg.name
            layergroup['title'] = lg.title
            layergroup['cached'] = lg.cached
            layergroup['projects'] = '; '.join(projects)
            layergroups.append(layergroup)
                      
    response = {
        'layergroups': layergroups
    }     
    return render_to_response('layergroup_list.html', response, context_instance=RequestContext(request))


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layergroup_add(request):
    if request.method == 'POST':
        name = request.POST.get('layergroup_name') + '_' + request.user.username
        title = request.POST.get('layergroup_title')
        
        cached = False
        if 'cached' in request.POST:
            cached = True
        
        if name != '':
            if _valid_name_regex.search(name) == None:
                message = _("Invalid layer group name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name)
                return render_to_response('layergroup_add.html', {'message': message}, context_instance=RequestContext(request))
        
            exists = False
            layergroups = LayerGroup.objects.all()
            for lg in layergroups:
                if name == lg.name:
                    exists = True
                    
            if not exists:
                layergroup = LayerGroup(
                    name = name,
                    title = title,
                    cached = cached,
                    created_by = request.user.username
                )
                layergroup.save()
            
            else:
                message = _(u'Layer group name already exists')
                return render_to_response('layergroup_add.html', {'message': message}, context_instance=RequestContext(request))
            
        else:
            message = _(u'You must enter a name for layer group')
            return render_to_response('layergroup_add.html', {'message': message}, context_instance=RequestContext(request))
            
        mapservice_backend.reload_nodes()
        return redirect('layergroup_list')
    
    else:
        return render_to_response('layergroup_add.html', {}, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layergroup_update(request, lgid):
    if request.method == 'POST':
        name = request.POST.get('layergroup_name')
        title = request.POST.get('layergroup_title')
        
        cached = False
        if 'cached' in request.POST:
            cached = True
        
        layergroup = LayerGroup.objects.get(id=int(lgid))
        mapservice_backend.deleteGeoserverLayerGroup(layergroup)
        
        sameName = False
        if layergroup.name == name:
            sameName = True
            
        exists = False
        layergroups = LayerGroup.objects.all()
        for lg in layergroups:
            if name == lg.name:
                exists = True
        
        old_name = layergroup.name
        
        if sameName:
            layergroup.title = title
            layergroup.cached = cached
            layergroup.save()   
            core_utils.toc_update_layer_group(layergroup, old_name, name)
            mapservice_backend.createOrUpdateGeoserverLayerGroup(layergroup)
            mapservice_backend.reload_nodes()
            return redirect('layergroup_list')
             
        else:      
            if not exists:   
                if _valid_name_regex.search(name) == None:
                    message = _("Invalid layer group name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name)
                    return render_to_response('layergroup_add.html', {'message': message}, context_instance=RequestContext(request))
                
                layergroup.name = name
                layergroup.title = title
                layergroup.cached = cached
                layergroup.save()
                core_utils.toc_update_layer_group(layergroup, old_name, name)
                mapservice_backend.createOrUpdateGeoserverLayerGroup(layergroup)
                mapservice_backend.reload_nodes()
                return redirect('layergroup_list')
                
            else:
                message = _(u'Layer group name already exists')
                return render_to_response('layergroup_update.html', {'message': message, 'layergroup': layergroup}, context_instance=RequestContext(request))

    else:
        layergroup = LayerGroup.objects.get(id=int(lgid))
        
        return render_to_response('layergroup_update.html', {'lgid': lgid, 'layergroup': layergroup}, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layergroup_delete(request, lgid):        
    if request.method == 'POST':
        layergroup = LayerGroup.objects.get(id=int(lgid))
        layers = Layer.objects.filter(layer_group_id=layergroup.id)    
        projects_by_layergroup = ProjectLayerGroup.objects.filter(layer_group_id=layergroup.id)
        for p in projects_by_layergroup:
            p.project.toc_order = core_utils.toc_remove_layergroups(p.project.toc_order, [layergroup.id])
            p.project.save()
            
        for layer in layers:  
            default_layer_group = LayerGroup.objects.get(name__exact='__default__')
            layer.layer_group = default_layer_group
            layer.save()  
                 
        mapservice_backend.deleteGeoserverLayerGroup(layergroup)
        layergroup.delete()
        mapservice_backend.setDataRules()
        mapservice_backend.reload_nodes()
        response = {
            'deleted': True
        }     
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


def prepare_string(s):
    return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')).replace (" ", "_").replace ("-", "_").lower()

@require_http_methods(["GET", "POST", "HEAD"])
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layer_create(request):
    layer_type = "gs_vector_layer"
    if request.method == 'POST':
        
        abstract = request.POST.get('md-abstract')
        is_visible = False
        if 'visible' in request.POST:
            is_visible = True
        
        is_queryable = False
        if 'queryable' in request.POST:
            is_queryable = True
            
        cached = False
        if 'cached' in request.POST:
            cached = True
            
        single_image = False
        if 'single_image' in request.POST:
            single_image = True
            
        form = CreateFeatureTypeForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                form.cleaned_data['name'] = prepare_string(form.cleaned_data['name'])
                mapservice_backend.createTable(form.cleaned_data)

                # first create the resource on the backend
                mapservice_backend.createResource(form.cleaned_data['datastore'].workspace,
                                      form.cleaned_data['datastore'],
                                      form.cleaned_data['name'],
                                      form.cleaned_data['title'])
                # save it on DB if successfully created
                newRecord = Layer(
                    datastore = form.cleaned_data['datastore'],
                    layer_group = form.cleaned_data['layer_group'],
                    name = form.cleaned_data['name'],
                    title = form.cleaned_data['title'],
                    abstract = abstract,
                    created_by = request.user.username,
                    type = form.cleaned_data['datastore'].type,
                    visible = is_visible,
                    queryable = is_queryable,
                    cached = cached,
                    single_image = single_image   
                )
                newRecord.save()
                
                if form.cleaned_data['datastore'].type != 'e_WMS':
                    datastore = Datastore.objects.get(id=newRecord.datastore.id)
                    workspace = Workspace.objects.get(id=datastore.workspace_id)
                    
                    style_name = workspace.name + '_' + newRecord.name + '_default'
                    mapservice_backend.createDefaultStyle(newRecord, style_name)
                    mapservice_backend.setLayerStyle(newRecord, style_name)
                    mapservice_backend.updateThumbnail(newRecord, 'create')
                    newRecord.save()
                    
                core_utils.toc_add_layer(newRecord)
                mapservice_backend.createOrUpdateGeoserverLayerGroup(newRecord.layer_group)
                mapservice_backend.reload_nodes()
                
                layer_autoconfig(newRecord.id)
                
                return HttpResponseRedirect(reverse('layer_permissions_update', kwargs={'layer_id': newRecord.id}))
            
            except Exception as e:
                try:
                    msg = e.get_message()
                except:
                    msg = _("Error: layer could not be published")
                # FIXME: the backend should raise more specific exceptions to identify the cause (e.g. layer exists, backend is offline)
                form.add_error(None, msg)
                
                data = {
                    'form': form,
                    'message': msg,
                    'layer_type': layer_type
                }
                return render(request, "layer_create.html", data)
                
        else:
            data = {
                'form': form,
                'layer_type': layer_type
            }
            return render(request, "layer_create.html", data)
        
    else:
        form = CreateFeatureTypeForm(user=request.user)
        enumeration_list = None
        if request.user.is_superuser:
            enumeration_list = Enumeration.objects.all()
        else:
            enumeration_list = Enumeration.objects.filter(created_by__exact=request.user.username)
            users = User.objects.all()
            for user in users:
                if user.is_superuser:
                    enumeration_list2 = Enumeration.objects.filter(created_by__exact=user.username)
                    enumeration_list = enumeration_list | enumeration_list2
        data = {
            'form': form,
            'layer_type': layer_type,
            'enumerations': enumeration_list
        }
        return render(request, "layer_create.html", data)
        
    return HttpResponseBadRequest()


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def enumeration_list(request):
    
    enumeration_list = None
    if request.user.is_superuser:
        enumeration_list = Enumeration.objects.all()
    else:
        enumeration_list = Enumeration.objects.filter(created_by__exact=request.user.username)
        
    enumerations = []
    for e in enumeration_list:
        enum = {}
        enum['id'] = e.id
        enum['name'] = e.name
        enum['title'] = e.title
        enumerations.append(enum)
                      
    response = {
        'enumerations': enumerations
    }     
    return render_to_response('enumeration_list.html', response, context_instance=RequestContext(request))


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def enumeration_add(request):
    if request.method == 'POST':
        name = request.POST.get('enumeration_name')
        title = request.POST.get('enumeration_title')
        
        aux_title = ''.join(title.encode('ASCII', 'ignore').split())[:4]
        aux_title = aux_title.lower()
        
        name = name + '_' + re.sub("[!@#$%^&*()[]{};:,./<>?\|`~-=_+ ]", "", aux_title)
                
        if title != '':
            enum = Enumeration(
                name = name,
                title = title,
                created_by = request.user.username
            )
            enum.save()
            
            for key in request.POST:
                if 'item-content' in key:
                    item = EnumerationItem(
                        enumeration = enum,
                        name = request.POST.get(key),
                        selected = False,
                        order = len(EnumerationItem.objects.filter(enumeration=enum))
                    )
                    item.save()
            
        else:
            index = len(Enumeration.objects.all())
            enum_name = 'enm_' + str(index)
            message = _(u'You must enter a title for enumeration')
            return render_to_response('enumeration_add.html', {'message': message, 'enum_name': enum_name}, context_instance=RequestContext(request))

        return redirect('enumeration_list')
    
    else:
        index = len(Enumeration.objects.all())
        enum_name = 'enm_' + str(index)
        return render_to_response('enumeration_add.html', {'enum_name': enum_name}, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def enumeration_update(request, eid):
    if request.method == 'POST':
        name = request.POST.get('enumeration_name')
        title = request.POST.get('enumeration_title')
        
        enum = Enumeration.objects.get(id=int(eid))

        enum.name = name
        enum.title = title
        enum.save()
        
        items = EnumerationItem.objects.filter(enumeration_id=enum.id)
        for i in items:
            i.delete()
            
        for key in request.POST:
            if 'item-content' in key:
                item = EnumerationItem(
                    enumeration = enum,
                    name = request.POST.get(key),
                    selected = False,
                    order = len(EnumerationItem.objects.filter(enumeration=enum))
                )
                item.save()
        
        return redirect('enumeration_list')
            
    else:
        enum = Enumeration.objects.get(id=int(eid))
        items = EnumerationItem.objects.filter(enumeration_id=enum.id).order_by('order')
        
        return render_to_response('enumeration_update.html', {'eid': eid, 'enumeration': enum, 'items': items, 'count': len(items) + 1}, context_instance=RequestContext(request))
   

@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def get_enumeration(request):
    if request.method == 'POST':
        enum_name = request.POST.get('enum_name')
        enum = Enumeration.objects.get(name__exact=enum_name)
        enum_items = EnumerationItem.objects.filter(enumeration_id=enum.id).order_by('order')
        
        items = []
        for i in enum_items:
            item = {}
            item['name'] = i.name
            item['selected'] = i.selected
            items.append(item)
            
        response = {
            'title': enum.title,
            'items': items
        }

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
      
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def enumeration_delete(request, eid):        
    if request.method == 'POST':
        enum = Enumeration.objects.get(id=int(eid))
        enum.delete()
        response = {
            'deleted': True
        }     
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


@require_GET
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def get_geom_tables(request, datastore_id):
    if request.method == 'GET':
        try:
            ds = Datastore.objects.get(pk=datastore_id)
            tables = mapservice_backend.getGeomColumns(ds)
            data = { 'tables': tables}
            return render(request, 'geom_table_list.html', data)
        except:
            pass
    return HttpResponseBadRequest()

@csrf_exempt
def get_feature_info(request):
    if request.method == 'POST':      
        url = request.POST.get('url')
        query_layer = request.POST.get('query_layer')
        ws = request.POST.get('workspace')

        req = requests.Session()
        lang = request.LANGUAGE_CODE
        if 'username' in request.session and 'password' in request.session:
            if request.session['username'] is not None and request.session['password'] is not None:
                req.auth = (request.session['username'], request.session['password'])
                #req.auth = ('admin', 'geoserver')
                
        features = None           
        try:
            w = Workspace.objects.get(name__exact=ws)
            #ds = Datastore.objects.filter(workspace=w)
            #layers = Layer.objects.filter(name__exact=query_layer)
            
            #layer = None
            #for l in layers:
            #    if l.datastore.id == ds.id:
            #        layer = l
                    
            layer = Layer.objects.get(name=query_layer, datastore__workspace__name=w.name)

            response = req.get(url, verify=False)
            geojson = json.loads(response.text)
                
            
            for i in range(0, len(geojson['features'])):
                fid = geojson['features'][i].get('id').split('.')[1]
                layer_resources = LayerResource.objects.filter(layer_id=layer.id).filter(feature=fid)
                resources = []
                for lr in layer_resources:
                    (type, url) = utils.get_resource_type(lr)
                    resource = {
                        'type': type,
                        'url': url,
                        'name': lr.path.split('/')[-1]
                    }
                    resources.append(resource)
                geojson['features'][i]['resources'] = resources
                geojson['features'][i]['all_correct'] = response.text
                geojson['features'][i]['feature'] = fid
                
            features = geojson['features']
            
        except Exception as e:
            print e.message
            logger.exception("get_feature_info")
            response = req.get(url, verify=False)
            geojson = json.loads(response.text)
            for i in range(0, len(geojson['features'])):
                geojson['features'][i]['resources'] = []
            features = geojson['features']
                
        response = {
            'features': features
        }

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@csrf_exempt
def get_unique_values(request):
    if request.method == 'POST':
        layer_name = request.POST.get('layer_name')
        layer_ws = request.POST.get('layer_ws')
        field = request.POST.get('field')
        
        workspace = Workspace.objects.get(name__exact=layer_ws)
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=workspace.name)
        
        connection = ast.literal_eval(layer.datastore.connection_params)
        
        host = connection.get('host')
        port = connection.get('port')
        schema = connection.get('schema')
        database = connection.get('database')
        user = connection.get('user')
        password = connection.get('passwd')
        
        unique_fields = utils.get_distinct_query(host, port, schema, database, user, password, layer.name, field)
    
        return HttpResponse(json.dumps({'values': unique_fields}, indent=4), content_type='application/json')


def is_numeric_type(type):
    if type == 'smallint' or type == 'integer' or type == 'bigint' or type == 'decimal' or type == 'numeric' or type == 'real' or type == 'double precision' or type == 'smallserial' or type == 'serial' or type == 'bigserial':
        return True;
    return False;


def is_string_type(type):
    if type == 'character varying' or type == 'varchar' or type == 'character' or type == 'char' or type == 'text':
        return True;
    return False;

@csrf_exempt
def get_datatable_data(request):
    if request.method == 'POST':      
        layer_name = request.POST.get('layer_name')
        workspace = request.POST.get('workspace')     
        wfs_url = request.POST.get('wfs_url')
        if len(GVSIGOL_SERVICES['CLUSTER_NODES']) >= 1:
            wfs_url = GVSIGOL_SERVICES['CLUSTER_NODES'][0] + '/' + workspace + '/wfs'
        property_name = request.POST.get('property_name')
        properties_with_type = request.POST.get('properties_with_type')
        start_index = request.POST.get('start')
        max_features = request.POST.get('length')
        draw = request.POST.get('draw')
        search_value = request.POST.get('search[value]')
        cql_filter = request.POST.get('cql_filter')
        
        values = None
        recordsTotal = 0
        recordsFiltered = 0
        
        encoded_property_name = property_name.encode('utf-8')
        
        try:
            if search_value == '':
                values = {
                    'SERVICE': 'WFS',
                    'VERSION': '1.1.0',
                    'REQUEST': 'GetFeature',
                    'TYPENAME': layer_name,
                    'OUTPUTFORMAT': 'application/json',
                    'MAXFEATURES': max_features,
                    'STARTINDEX': start_index,
                    'PROPERTYNAME': encoded_property_name,
                }
                if cql_filter != '':
                    values['cql_filter'] = cql_filter
                    
                recordsTotal = mapservice_backend.getFeatureCount(request, wfs_url, layer_name, None)
                recordsFiltered = mapservice_backend.getFeatureCount(request, wfs_url, layer_name, cql_filter)
                #recordsFiltered = recordsTotal
                
            else:
                properties = properties_with_type.split(',')
                encoded_value = search_value.encode('ascii', 'replace')
                
                raw_search_cql = '('
                for p in properties:
                    if p.split('|')[0] != 'id':
                        if is_string_type(p.split('|')[1]):
                            raw_search_cql += p.split('|')[0] + " ILIKE '%" + encoded_value.replace('?', '_') +"%'"
                            raw_search_cql += ' OR '
                            
                        elif is_numeric_type(p.split('|')[1]):
                            if search_value.isdigit():
                                raw_search_cql += p.split('|')[0] + ' = ' + search_value
                                raw_search_cql += ' OR '
                            
                if raw_search_cql.endswith(' OR '):
                    raw_search_cql = raw_search_cql[:-4]
                    
                raw_search_cql += ')'
                
                values = {
                    'SERVICE': 'WFS',
                    'VERSION': '1.1.0',
                    'REQUEST': 'GetFeature',
                    'TYPENAME': layer_name,
                    'OUTPUTFORMAT': 'application/json',
                    'MAXFEATURES': max_features,
                    'STARTINDEX': start_index,
                    'PROPERTYNAME': encoded_property_name
                }
                if cql_filter == '':
                    values['cql_filter'] = raw_search_cql
                else:
                    values['cql_filter'] = cql_filter + ' AND ' + raw_search_cql
                recordsTotal = mapservice_backend.getFeatureCount(request, wfs_url, layer_name, None)
                recordsFiltered = mapservice_backend.getFeatureCount(request, wfs_url, layer_name, cql_filter)
    
            params = urllib.urlencode(values)
            req = requests.Session()
            if 'username' in request.session and 'password' in request.session:
                if request.session['username'] is not None and request.session['password'] is not None:
                    req.auth = (request.session['username'], request.session['password'])
                    #req.auth = ('admin', 'geoserver')
                    
            print wfs_url + "?" + params
            response = req.post(wfs_url, data=values, verify=False)
            jsonString = response.text
            geojson = json.loads(jsonString)
            
            data = []
            for f in geojson['features']:
                row = {}
                for p in f['properties']:
                    row[p] = f['properties'][p]
                row['featureid'] = f['id']
                data.append(row)
                    
            response = {
                'draw': int(draw),
                'recordsTotal': recordsTotal,
                'recordsFiltered': recordsFiltered,
                'data': data
            }
        
        except Exception as e:
            response = {
                'draw': 0,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': []
            }
            pass
        
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


@login_required(login_url='/gvsigonline/auth/login_user/')
def add_layer_lock(request):
    layer_name = None
    try:
        ws_name = request.POST['workspace']
        layer_name = request.POST['layer']
        
        if ":" in layer_name:
            layer_name = layer_name.split(":")[1]
        qualified_layer_name = ws_name + ":" + layer_name
        locks_utils.add_layer_lock(qualified_layer_name, request.user)
        return HttpResponse('{"response": "ok"}', content_type='application/json')
    except Exception as e:
        return HttpResponseNotFound('<h1>Layer is locked: {0}</h1>'.format(layer_name))


@login_required(login_url='/gvsigonline/auth/login_user/')
def remove_layer_lock(request):
    try:
        ws_name = request.POST['workspace']
        layer_name = request.POST['layer']
        if ":" in layer_name:
            layer_name = layer_name.split(":")[1]
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=ws_name)
        locks_utils.remove_layer_lock(layer, request.user, check_writable=True)
        return HttpResponse('{"response": "ok"}', content_type='application/json')
    except Exception as e:
        return HttpResponseNotFound('<h1>Layer not locked: {0}</h1>'.format(layer.id))
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@staff_required
def lock_list(request):
    
    lock_list = None
    if request.user.is_superuser:
        lock_list = LayerLock.objects.all()
    else:
        lock_list = LayerLock.objects.filter(created_by__exact=request.user.username)
        
    response = {
        'locks': lock_list
    }
    return render_to_response('lock_list.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def unlock_layer(request, lock_id):
    lock = LayerLock.objects.get(id=int(lock_id))
    lock.delete()
    return redirect('lock_list')

@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def get_feature_resources(request):
    if request.method == 'POST':      
        query_layer = request.POST.get('query_layer')
        workspace = request.POST.get('workspace')
        fid = request.POST.get('fid')
        try:
            layer = Layer.objects.get(name=query_layer, datastore__workspace__name=workspace)
            layer_resources = LayerResource.objects.filter(layer_id=layer.id).filter(feature=int(fid))
            resources = []
            for lr in layer_resources:
                url = None
                type = None 
                if lr.type == LayerResource.EXTERNAL_IMAGE:
                    type = 'image'
                    url = os.path.join(settings.MEDIA_URL, lr.path)
                    name = lr.path.split('/')[-1]
                elif lr.type == LayerResource.EXTERNAL_PDF:
                    type = 'pdf'
                    url = os.path.join(settings.MEDIA_URL, lr.path)
                    name = lr.path.split('/')[-1]
                elif lr.type == LayerResource.EXTERNAL_DOC:
                    type = 'doc'
                    url = os.path.join(settings.MEDIA_URL, lr.path)
                    name = lr.path.split('/')[-1]
                elif lr.type == LayerResource.EXTERNAL_FILE:
                    type = 'file'
                    url = os.path.join(settings.MEDIA_URL, lr.path)
                    name = lr.path.split('/')[-1]
                elif lr.type == LayerResource.EXTERNAL_VIDEO:
                    type = 'video'
                    url = os.path.join(settings.MEDIA_URL, lr.path)
                    name = lr.path.split('/')[-1]
                elif lr.type == LayerResource.EXTERNAL_ALFRESCO_DIR:
                    type = 'alfresco_dir'
                    url = lr.path
                    
                resource = {
                    'type': type,
                    'url': url,
                    'name': name,
                    'rid': lr.id
                }
                resources.append(resource)

            
        except Exception as e:
            print e.message
                
        response = {
            'resources': resources
        }

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def upload_resources(request):
    if request.method == 'POST':
        ws_name = request.POST.get('workspace')
        layer_name = request.POST.get('layer_name')
        fid = request.POST.get('fid')
        if ":" in layer_name:
            layer_name = layer_name.split(":")[1]
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=ws_name)
        if 'resource' in request.FILES:
            type = None
            resource = request.FILES['resource']
            if 'image/' in resource.content_type:
                type = LayerResource.EXTERNAL_IMAGE
            elif resource.content_type == 'application/pdf':
                type = LayerResource.EXTERNAL_PDF
            elif 'video/' in resource.content_type:
                type = LayerResource.EXTERNAL_VIDEO
            else:
                type = LayerResource.EXTERNAL_FILE
                
            (saved, path) = resource_manager.save_resource(resource, type)
            if saved:
                res = LayerResource()
                res.feature = int(fid)
                res.layer = layer
                res.path = path
                res.title = ''
                res.type = type
                res.created = timezone.now()
                res.save()
                response = {'success': True}
                
            else:
                response = {'success': False}
            
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def delete_resource(request):
    if request.method == 'POST':
        rid = request.POST.get('rid')
        try:
            resource = LayerResource.objects.get(id=int(rid)) 
            resource.delete()
            resource_manager.delete_resource(resource)
            response = {'deleted': True}
            
        except Exception as e:
            response = {'deleted': False}
            pass
        
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def delete_resources(request):
    if request.method == 'POST':      
        query_layer = request.POST.get('query_layer')
        workspace = request.POST.get('workspace')
        fid = request.POST.get('fid')
        try:
            layer = Layer.objects.get(name=query_layer, datastore__workspace__name=workspace)
            layer_resources = LayerResource.objects.filter(layer_id=layer.id).filter(feature=int(fid))
            for resource in layer_resources:
                resource_manager.delete_resource(resource)
                resource.delete()
            response = {'deleted': True}
    
        except Exception as e:
            print e.message
            response = {'deleted': False}
            pass

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
    
@csrf_exempt
def describeFeatureType(request):
    if request.method == 'POST':      
        lyr = request.POST.get('layer')
        workspace = request.POST.get('workspace')
        try:
            layer = Layer.objects.get(name=lyr, datastore__workspace__name=workspace)
            params = json.loads(layer.datastore.connection_params)
            host = params['host']
            port = params['port']
            dbname = params['database']
            user = params['user']
            passwd = params['passwd']
            schema = params.get('schema', 'public')
            i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
            layer_defs = i.get_fields_info(layer.name, schema)
            geom_defs = i.get_geometry_columns_info(layer.name, schema)
            pk_defs = i.get_pk_columns(layer.name, schema)
            
            for layer_def in layer_defs:
                for geom_def in geom_defs:
                    if layer_def['name'] == geom_def[2]:
                        layer_def['type'] = geom_def[5]
                        layer_def['length'] = geom_def[4]
            for layer_def in layer_defs:
                for pk_def in pk_defs:
                    if layer_def['name'] == pk_def:            
                        layer_defs.remove(layer_def)
            
            response = {'fields': layer_defs}

    
        except Exception as e:
            print e.message
            response = {'fields': []}
            pass

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')