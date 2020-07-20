# Copyright 2016 Cloudbase Solutions Srl
# All Rights Reserved.

from oslo_log import log as logging
from webob import exc

from nova_guest import exception
from nova_guest.api import wsgi as api_wsgi
from nova_guest.networking import api

LOG = logging.getLogger(__name__)


class NetworkingController(api_wsgi.Controller):
    def __init__(self):
        self._netw_api = api.API()
        super().__init__()

    @api_wsgi.action('apply-networking')
    def _apply_networking(self, req, instance_id, body):
        context = req.environ['nova_agent.context']
        try:
            success, output = self._netw_api.apply_networking(
                context, instance_id)
            return {
                "apply-networking":
                    {"success": success, "message": output}
            }
        except exception.NotFound as ex:
            raise exc.HTTPNotFound(explanation=ex.msg)
        except exception.InvalidParameterValue as ex:
            raise exc.HTTPNotFound(explanation=ex.msg)
        except exception.NotSupportedOperation as ex:
            raise exc.HTTPConflict(explanation=ex.msg)
        except exception.Conflict as ex:
            raise exc.HTTPConflict(explanation=ex.msg)


def create_resource():
    return api_wsgi.Resource(NetworkingController())
