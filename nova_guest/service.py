# Copyright 2016 Cloudbase Solutions Srl
# All Rights Reserved.

import os
import platform

from oslo_concurrency import processutils
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_service import service
from oslo_service import wsgi

from nova_guest import rpc
from nova_guest import utils


service_opts = [
    cfg.StrOpt('api_nova_guest_listen',
               default="0.0.0.0",
               help='IP address on which the Migration API listens'),
    cfg.PortOpt('api_nova_guest_listen_port',
                default=7667,
                help='Port on which the Migration API listens'),
    cfg.IntOpt('api_nova_guest_workers',
               help='Number of workers for the Migration API service. '
                    'The default is equal to the number of CPUs available.'),
    cfg.IntOpt('messaging_workers',
               help='Number of workers for the messaging service. '
                    'The default is equal to the number of CPUs available.'),
]

CONF = cfg.CONF
CONF.register_opts(service_opts)
LOG = logging.getLogger(__name__)


def check_locks_dir_empty():
    """ Checks whether the locks dir is empty and warns otherwise.

    NOTE: external oslo_concurrency locks work based on listing open file
    descriptors so this check is not necessarily conclusive, though all freshly
    started/restarted conductor services should ideally be given a clean slate.
    """
    oslo_concurrency_group = getattr(CONF, 'oslo_concurrency', {})
    if not oslo_concurrency_group:
        LOG.warn("No 'oslo_concurrency' group defined in config file!")
        return

    locks_dir = oslo_concurrency_group.get('lock_path', "")
    if not locks_dir:
        LOG.warn("No locks directory path was configured!")
        return

    if not os.path.exists(locks_dir):
        LOG.warn(
            "Configured 'lock_path' directory '%s' does NOT exist!", locks_dir)
        return

    if not os.path.isdir(locks_dir):
        LOG.warn(
            "Configured 'lock_path' directory '%s' is NOT a directory!",
            locks_dir)
        return

    locks_dir_contents = os.listdir(locks_dir)
    if locks_dir_contents:
        LOG.warn(
            "Configured 'lock_path' directory '%s' is NOT empty: %s",
            locks_dir, locks_dir_contents)
        return

    LOG.info(
        "Successfully checked 'lock_path' directory '%s' exists and is empty.",
        locks_dir)


class WSGIService(service.ServiceBase):
    def __init__(self, name):
        self._host = CONF.api_nova_guest_listen
        self._port = CONF.api_nova_guest_listen_port

        if platform.system() == "Windows":
            self._workers = 1
        else:
            self._workers = (
                CONF.api_nova_guest_workers or processutils.get_worker_count())

        self._loader = wsgi.Loader(CONF)
        self._app = self._loader.load_app(name)

        self._server = wsgi.Server(CONF,
                                   name,
                                   self._app,
                                   host=self._host,
                                   port=self._port)

    def get_workers_count(self):
        return self._workers

    def start(self):
        self._server.start()

    def stop(self):
        self._server.stop()

    def wait(self):
        self._server.wait()

    def reset(self):
        self._server.reset()


class MessagingService(service.ServiceBase):
    def __init__(self, topic, endpoints, version, worker_count=None):
        target = messaging.Target(topic=topic,
                                  server=utils.get_hostname(),
                                  version=version)
        self._server = rpc.get_server(target, endpoints)

        self._workers = (worker_count or CONF.messaging_workers or
                         processutils.get_worker_count())

    def get_workers_count(self):
        return self._workers

    def start(self):
        self._server.start()

    def stop(self):
        self._server.stop()

    def wait(self):
        pass

    def reset(self):
        self._server.reset()
