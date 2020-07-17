from oslo_config import cfg

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
