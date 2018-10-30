# -*- coding: utf-8 -*-
CATALOG_BASE_URL = 'http://localhost:8080/geonetwork'
CATALOG_URL = CATALOG_BASE_URL + '/srv/eng/'
CATALOG_USER = 'admin'
CATALOG_PASSWORD = 'admin'
# valid values: 'legacy3.2', 'api0.1'
CATALOG_API_VERSION = 'api0.1'

# Examples:
#CATALOG_FACETS_CONFIG = '{"orgName": {"title": "Organization"}, "sourceCatalog": {"title": "Source Catalog"}, "createDateYear": {"title": "Year"}, "spatialRepresentationType": {"title": "Representation type"}, "maintenanceAndUpdateFrequency": {"title": "Update frequencies"}, "denominator": {"title": "Scale"}, "serviceType": {"title": "Service type"}, "gemetKeyword": {"title": "GEMET keywords"}, "panaceaKeyword": [{"name": "interregMedProjects", "title": "INTERREG Med Projects", "labelPattern": ".* project$"}, {"name": "panaceaWorkingGroups", "title": "Working group", "labelPattern": "^(.(?! project$))+$"}]}'
#CATALOG_FACETS_ORDER = '["panaceaWorkingGroups", "interregMedProjects", "type", "spatialRepresentationType"]'
#CATALOG_DISABLED_FACETS = '["mdActions"]'
CATALOG_FACETS_CONFIG = '{"orgName": {"title": "Organization"}, "sourceCatalog": {"title": "Source Catalog"}, "topicCat": {"title": "Categories"}, "createDateYear": {"title": "Year"}, "spatialRepresentationType": {"title": "Representation type"}, "maintenanceAndUpdateFrequency": {"title": "Update frequencies"}, "denominator": {"title": "Scale"}, "serviceType": {"title": "Service type"}, "gemetKeyword": {"title": "GEMET keywords"}, "panaceaKeyword": [{"name": "interregMedProjects", "title": "INTERREG Med Projects", "labelPattern": ".* project$"}, {"name": "panaceaWorkingGroups", "title": "Working group", "labelPattern": "^(.(?! project$))+$"}]}'
CATALOG_FACETS_ORDER = '[]'
CATALOG_DISABLED_FACETS = '["mdActions"]'
