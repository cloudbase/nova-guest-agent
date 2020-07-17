# Copyright 2016 Cloudbase Solutions Srl
# All Rights Reserved.

from oslo_log import log as logging

from nova_guest import api
from nova_guest.api.v1 import networking

LOG = logging.getLogger(__name__)

class ExtensionManager(object):
    def get_resources(self):
        return []

    def get_controller_extensions(self):
        return []


class APIRouter(api.APIRouter):
    ExtensionManager = ExtensionManager

    def _setup_routes(self, mapper, ext_mgr):
        mapper.redirect("", "/")

        self.resources['networking_actions'] = networking.create_resource()
        endpoint_path = '/{project_id}/networking/{instance_id}/ctions'
        mapper.connect('networking_actions',
                       endpoint_path,
                       controller=self.resources['networking_actions'],
                       action='action',
                       conditions={'method': 'POST'})
