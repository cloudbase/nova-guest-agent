# Copyright 2016 Cloudbase Solutions Srl
# All Rights Reserved.

from oslo_log import log as logging
from webob import exc

from nova_guest import exception
# from coriolis.api.v1 import utils as api_utils
# from coriolis.api.v1.views import replica_view
# from coriolis.api.v1.views import replica_tasks_execution_view
from nova_guest.api import wsgi as api_wsgi
# from coriolis.endpoints import api as endpoints_api
# from coriolis.policies import replicas as replica_policies
# from coriolis.replicas import api

LOG = logging.getLogger(__name__)


class NetworkingController(api_wsgi.Controller):
    def __init__(self):
        # self._replica_api = api.API()
        # self._endpoints_api = endpoints_api.API()
        super().__init__()

    def show(self, req, id):
        # context = req.environ["coriolis.context"]
        # context.can(replica_policies.get_replicas_policy_label("show"))
        # replica = self._replica_api.get_replica(context, id)
        # if not replica:
        #     raise exc.HTTPNotFound()
        # return replica_view.single(req, replica)
        return None

    def index(self, req):
        # show_deleted = api_utils._get_show_deleted(
        #     req.GET.get("show_deleted", None))
        # context = req.environ["coriolis.context"]
        # context.show_deleted = show_deleted
        # context.can(replica_policies.get_replicas_policy_label("list"))
        # return replica_view.collection(
        #     req, self._replica_api.get_replicas(
        #         context, include_tasks_executions=False))
        return None

    def detail(self, req):
        # show_deleted = api_utils._get_show_deleted(
        #     req.GET.get("show_deleted", None))
        # context = req.environ["coriolis.context"]
        # context.show_deleted = show_deleted
        # context.can(
        #     replica_policies.get_replicas_policy_label("show_executions"))
        # return replica_view.collection(
        #     req, self._replica_api.get_replicas(
        #         context, include_tasks_executions=True))
        return None


def create_resource():
    return api_wsgi.Resource(NetworkingController())
