# Copyright 2020 Cloudbase Solutions Srl
# All Rights Reserved.

from oslo_config import cfg
import oslo_messaging as messaging

from oslo_context import context
import nova_guest.exception

rpc_opts = [
    cfg.StrOpt('messaging_transport_url',
               default="rabbit://guest:guest@127.0.0.1:5672/",
               help='Messaging transport url'),
    cfg.IntOpt('default_messaging_timeout',
               default=60,
               help='Number of seconds for messaging timeouts.')
]

CONF = cfg.CONF
CONF.register_opts(rpc_opts)

ALLOWED_EXMODS = [
    nova_guest.exception.__name__,
]


class RequestContextSerializer(messaging.Serializer):

    def __init__(self, base):
        self._base = base

    def serialize_entity(self, ctxt, entity):
        if not self._base:
            return entity
        return self._base.serialize_entity(ctxt, entity)

    def deserialize_entity(self, ctxt, entity):
        if not self._base:
            return entity
        return self._base.deserialize_entity(ctxt, entity)

    def serialize_context(self, ctxt):
        return ctxt.to_dict()

    def deserialize_context(self, ctxt):
        return context.RequestContext.from_dict(ctxt)


def _get_transport():
    return messaging.get_transport(cfg.CONF, CONF.messaging_transport_url,
                                   allowed_remote_exmods=ALLOWED_EXMODS)


def get_client(target, serializer=None, timeout=None):
    serializer = RequestContextSerializer(serializer)
    if timeout is None:
        timeout = CONF.default_messaging_timeout
    return messaging.RPCClient(
        _get_transport(), target, serializer=serializer, timeout=timeout)


def get_server(target, endpoints, serializer=None):
    serializer = RequestContextSerializer(serializer)
    return messaging.get_rpc_server(_get_transport(), target, endpoints,
                                    executor='eventlet',
                                    serializer=serializer)
