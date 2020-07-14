from oslo_config import cfg
import oslo_messaging as messaging

from nova_guest import rpc
from nova_guest import utils
from nova_guest import exception

VERSION = "1.0"


worker_opts = [
    cfg.IntOpt("worker_rpc_timeout",
               help="Number of seconds until RPC calls to the worker timeout")
]

CONF = cfg.CONF
CONF.register_opts(worker_opts, 'nova_guest_agent')


class AgentClient(object):
    def __init__(self, timeout=None):
        if CONF.nova_guest_agent.host == "":
            raise exception.NovaGuestException("host config value must be set")
        topic = 'nova_guest_agent_%s' % CONF.nova_guest_agent.host
        target = messaging.Target(topic=topic, version=VERSION)
        if timeout is None:
            timeout = CONF.nova_guest_agent.worker_rpc_timeout
        self._client = rpc.get_client(target, timeout=timeout)
