from django.views.generic import TemplateView, FormView
from django.views.generic.base import View
from django.shortcuts import HttpResponse, redirect
from django.http import HttpResponseBadRequest
from django.core.urlresolvers import reverse_lazy
from gvsigol.settings import FILEMANAGER_DIRECTORY
from gvsigol_services.backend_mapservice import backend as mapservice
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from gvsigol_services import rest_geoserver
from forms import DirectoryCreateForm
from core import Filemanager
import logging, sys
import json

class FilemanagerMixin(object):
    def dispatch(self, request, *args, **kwargs):
        params = dict(request.GET)
        params.update(dict(request.POST))

        self.fm = Filemanager()
        if 'path' in params and len(params['path'][0]) > 0:
            self.fm.update_path(params['path'][0])
        if 'popup' in params:
            self.popup = params['popup']

        return super(FilemanagerMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(FilemanagerMixin, self).get_context_data(*args, **kwargs)

        self.fm.patch_context_data(context)

        if hasattr(self, 'popup'):
            context['popup'] = self.popup

        if hasattr(self, 'extra_breadcrumbs') and isinstance(self.extra_breadcrumbs, list):
            context['breadcrumbs'] += self.extra_breadcrumbs

        return context


class BrowserView(FilemanagerMixin, TemplateView):
    template_name = 'browser/filemanager_list.html'

    def dispatch(self, request, *args, **kwargs):
        self.popup = self.request.GET.get('popup', 0) == '1'
        return super(BrowserView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(BrowserView, self).get_context_data(**kwargs)
        
        context['first_level'] = False
        if self.fm.location == FILEMANAGER_DIRECTORY:
            context['first_level'] = True
        context['popup'] = self.popup
        context['files'] = self.fm.directory_list(self.request, context['first_level'])

        return context


class ExportToDatabaseView(FilemanagerMixin, TemplateView):
    template_name = 'browser/export_to_database.html'

    def get_context_data(self, **kwargs):
        context = super(ExportToDatabaseView, self).get_context_data(**kwargs)
        
        (form, template, file_accepts) = mapservice.getUploadForm('v_PostGIS')
        context['form'] = form
        context['file'] = self.fm.file_details()
        
        return context
    
    def post(self, request, *args, **kwargs):
        (form_class, template, file_accepts) = mapservice.getUploadForm('v_PostGIS')
        if form_class is not None:
            form = form_class(request.POST, request.FILES)
            if form.is_valid():
                try:
                    if mapservice.exportShpToPostgis(form.cleaned_data, session=request.session):
                        return redirect("/gvsigonline/filemanager/?path=" + request.POST.get('directory_path'))
                    
                except rest_geoserver.RequestError as e:
                    form.add_error(None, _(e.get_message()))
                    return redirect("/gvsigonline/filemanager/export_to_database/?path=" + request.POST.get('file_path'))
                except Exception as exc:
                    # ensure the ds gets cleaned if we've failed
                    # FIXME: clean up disabled at the moment, as it has security implications
                    # We should ensure which kind of exception we have got before deleting,
                    # otherwise an attacker could use this method
                    # in order to arbitrarily delete existing data stores  
                    #mapservice_backend.deleteDatastore(ds.workspace, ds, "all", session=request.session)
                    exctype, value = sys.exc_info()[:2]
                    # use unicode with error='replace' because owslib sometimes raises exceptions using unexpected encodings
                    exc_msg = unicode(str(exctype), errors='replace')+u" - "+unicode(value)  
                    logging.exception(exc_msg)
                    form.add_error(None, _("Error uploading the layer. Review the file format."))
                    form.add_error(None, exc_msg)
                    return redirect("/gvsigonline/filemanager/export_to_database/?path=" + request.POST.get('file_path'))


class UploadView(FilemanagerMixin, TemplateView):
    template_name = 'filemanager_upload.html'
    extra_breadcrumbs = [{
        'path': '#',
        'label': 'Upload'
    }]


class UploadFileView(FilemanagerMixin, View):
    def post(self, request, *args, **kwargs):
        if len(request.FILES) != 1:
            return HttpResponseBadRequest("Just a single file please.")
        
        file = request.FILES['files']
        extension = file.name.split(".")[1]
        
        if extension == "zip":
            folder = file.name.split(".")[0]
            self.fm.extract_zip(file, folder)
            
        else:
            # TODO: get filepath and validate characters in name, validate mime type and extension
            self.fm.upload_file(filedata = request.FILES['files'])

        return HttpResponse(json.dumps({
            'files': [],
            'path': request.POST.get('path'),
        }))
        
class DeleteFileView(FilemanagerMixin, View):
    def post(self, request, *args, **kwargs):
        if self.fm.delete(request.POST.get('path')):
            return HttpResponse(json.dumps({
                'success': True
            }))
            
        else:
            return HttpResponse(json.dumps({
                'success': False
            }))


class DirectoryCreateView(FilemanagerMixin, FormView):
    template_name = 'filemanager_create_directory.html'
    form_class = DirectoryCreateForm
    extra_breadcrumbs = [{
        'path': '#',
        'label': 'Create directory'
    }]

    def get_success_url(self):
        url = '%s?path=%s' % (reverse_lazy('filemanager:browser'), self.fm.path)
        if hasattr(self, 'popup') and self.popup:
            url += '&popup=1'
        return url

    def form_valid(self, form):
        self.fm.create_directory(form.cleaned_data.get('directory_name'))
        return super(DirectoryCreateView, self).form_valid(form)
