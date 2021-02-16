import functools
import socket
import time
import traceback

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


def get_exception_details():
    return traceback.format_exc()


def retry_on_error(max_attempts=5, sleep_seconds=0,
                   terminal_exceptions=[]):
    def _retry_on_error(func):
        @functools.wraps(func)
        def _exec_retry(*args, **kwargs):
            i = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except KeyboardInterrupt as ex:
                    LOG.debug("Got a KeyboardInterrupt, skip retrying")
                    LOG.exception(ex)
                    raise
                except Exception as ex:
                    if any([isinstance(ex, tex)
                            for tex in terminal_exceptions]):
                        raise

                    i += 1
                    if i < max_attempts:
                        LOG.warn(
                            "Exception occurred, retrying (%d/%d):\n%s",
                            i, max_attempts, get_exception_details())
                        time.sleep(sleep_seconds)
                    else:
                        raise
        return _exec_retry
    return _retry_on_error
