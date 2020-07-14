import socket

from oslo_config import cfg
from oslo_log import log as logging

from nova_guest import exception

CONF = cfg.CONF
logging.register_options(CONF)
LOG = logging.getLogger(__name__)


def get_hostname():
    return socket.gethostname()


def parse_int_value(value):
    try:
        return int(str(value))
    except ValueError:
        raise exception.InvalidInput("Invalid integer: %s" % value)


def setup_logging():
    logging.setup(CONF, 'nova-guest')
