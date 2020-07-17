import socket

from oslo_config import cfg
from oslo_log import log as logging
from webob import exc

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


def bad_request_on_error(error_message):
    def _bad_request_on_error(func):
        def wrapper(*args, **kwargs):
            (is_valid, message) = func(*args, **kwargs)
            if not is_valid:
                raise exc.HTTPBadRequest(explanation=(error_message % message))
            return (is_valid, message)
        return wrapper
    return _bad_request_on_error
