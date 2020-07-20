import base64
import json

from oslo_config import cfg
import oslo_messaging as messaging

from nova_guest import rpc
from nova_guest import utils
from nova_guest import exception
from nova_guest.agent.libvirt import agent
from nova_guest.agent.rpc.config import CONF

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


VERSION = "1.0"

COMMAND_MAP = {
    agent.OS_TYPE_LINUX: {
        "net_apply": "/scripts/apply-network-config",
    },
    agent.OS_TYPE_WINDOWS: {
        # "net_apply": ["powershell.exe", "-NonInteractive", "-ExecutionPolicy", "RemoteSigned", "-EncodedCommand"],
        "net_apply": "C:\\scripts\\apply-network-config.ps1",
    }
}


class AgentServerEndpoint(object):

    def __init__(self, timeout=None):
        if CONF.nova_guest_agent.host != "":
            self.server = CONF.nova_guest_agent.host
        else:
            self.server = utils.get_hostname()
        self._server = self.server
        self._conn = agent.AgentConnection(
            CONF.nova_guest_agent.libvirt_url)

    def _get_netw_command_linux(self, network_config):
        cmd_path = COMMAND_MAP[agent.OS_TYPE_LINUX]["net_apply"]
        serialized_net_cfg = base64.b64encode(
            json.dumps(network_config).encode()).decode()
        return (cmd_path, [serialized_net_cfg,])

    def _get_netw_command_windows(self, network_config):
        cmd_path = COMMAND_MAP[agent.OS_TYPE_WINDOWS]["net_apply"]
        serialized_net_cfg = base64.b64encode(
            json.dumps(network_config).encode()).decode()
        command = "%s %s" % (cmd_path, serialized_net_cfg)
        params = ["-NonInteractive", "-ExecutionPolicy",
                  "RemoteSigned", "-Command", command]
        return ("powershell.exe", params)

    def _get_apply_network_command(self, platform, network_config):
        func = getattr(self, "_get_netw_command_%s" % platform, None)
        if func is None:
            raise exception.NovaGuestException(
                "No network apply method for %r" % platform)
        return func(network_config)

    def apply_networking(self, ctxt, instance_name, network_config):
        LOG.debug("Got request for instance %s with config %s" % (instance_name, json.dumps(network_config, indent=2)))
        dom = self._conn.get_instance_by_name(instance_name)
        if self._conn.is_alive(dom) is False:
            raise exception.Conflict(
                "Guest must be online.")

        platform = self._conn.get_guest_platform(dom)
        cmd, parameters = self._get_apply_network_command(
            platform, network_config)
        output = self._conn.execute_command(dom, cmd, parameters)
        return output
