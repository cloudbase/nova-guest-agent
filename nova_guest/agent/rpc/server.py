import base64

from oslo_config import cfg
import oslo_messaging as messaging

from nova_guest import rpc
from nova_guest import utils
from nova_guest import exception
from nova_guest.agent.libvirt import agent

VERSION = "1.0"


worker_opts = [
    cfg.IntOpt("worker_rpc_timeout",
               help="Number of seconds until RPC calls to the worker timeout"),
    cfg.StrOpt("host",
               help="The hostname of the hypervisor. This value must match the"
               "hostname value used in the nova compute config."),
    cfg.StrOpt("libvirt_url",
               default=None,
               help="Libvirt URL to which we will connect. Leave empty to"
               "connect to localhost.")
]

CONF = cfg.CONF
CONF.register_opts(worker_opts, 'nova_guest_agent')

COMMAND_MAP = {
    agent.OS_TYPE_LINUX: {
        "net_apply": ["/scripts/apply-network-config",],
    },
    agent.OS_TYPE_WINDOWS: {
        "net_apply": ["powershell.exe", "-NonInteractive", "-ExecutionPolicy", "RemoteSigned", "-EncodedCommand"],
    }
}


class AgentServerEndpoint(object):

    def __init__(self, timeout=None):
        if CONF.nova_guest_agent.host == "":
            raise exception.NovaGuestException("host config value must be set")
        self._server = CONF.nova_guest_agent.host
        self._conn = agent.AgentConnection(
            CONF.nova_guest_agent.libvirt_url)

    def _get_netw_command_linux(self, network_config):
        return ()

    def _get_netw_command_windows(self, network_config):
        return ()

    def _get_apply_network_command(self, platform, network_config):
        func = getattr(self, "_get_netw_command_%s" % platform, None)
        if func is None:
            raise exception.NovaGuestException(
                "No network apply method for %r" % platform)
        return func(network_config)

    def apply_networking(self, ctxt, instance_name, network_config):
        dom = self._conn.get_instance_by_name(instance_name)
        if self._conn.is_alive(dom) is False:
            raise exception.NovaGuestException(
                "Guest must be online.")
        
        platform = self._conn.get_guest_platform(dom)
        cmd, parameters = self._get_apply_network_command(platform, network_config)
        output = self._conn.execute_command(dom, cmd, parameters)
        return output
