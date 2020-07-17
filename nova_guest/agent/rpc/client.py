from oslo_config import cfg
import oslo_messaging as messaging

from nova_guest import rpc
from nova_guest import utils
from nova_guest import exception
from nova_guest.metadata import metadata
from nova_guest.agent.rpc.config import CONF

VERSION = "1.0"
CONF = cfg.CONF


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
            raise exception.Conflict(
                "Instance must be online. State is"
                ": %s" % server_details.status)
        server = getattr(server_details, "OS-EXT-SRV-ATTR:host", None)
        instance_name = getattr(
            server_details, "OS-EXT-SRV-ATTR:instance_name", None)
        if None in (server, instance_name):
            raise exception.NovaGuestException(
                "failed to find required information in instance object")

        rpc_cli = self._client.prepare(server=server)
        network_info = cli.get_metadata(server_id)

        return rpc_cli.call(
            ctxt, "apply_networking", instance_name=instance_name,
            network_config=network_info)
