from oslo_config import cfg
import oslo_messaging as messaging

from nova_guest import rpc
from nova_guest import utils
from nova_guest import exception
from nova_guest.metadata import metadata

VERSION = "1.0"

worker_opts = [
    cfg.IntOpt("worker_rpc_timeout",
               help="Number of seconds until RPC calls to the worker timeout")
]

CONF = cfg.CONF
CONF.register_opts(worker_opts, 'nova_guest_agent')


class AgentClient(object):

    def __init__(self, timeout=None):
        target = messaging.Target(
            topic="nova_guest_agent", version=VERSION)
        if timeout is None:
            timeout = CONF.nova_guest_agent.worker_rpc_timeout
        self._client = rpc.get_client(target, timeout=timeout)

    def apply_network_config(self, ctxt, server_id):
        cli = metadata.MetadataWrapper(ctxt)
        server_details = cli.get_instance(server_id)
        if server_details.status != "ACTIVE":
            raise exception.NovaGuestException(
                "Instance must be online. State is"
                ": %s" % server_details.status)

        network_info = cli.get_metadata(server_id)
