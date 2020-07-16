# Copyright 2016 Cloudbase Solutions Srl
# All Rights Reserved.

import itertools

from oslo_config import cfg as conf


def _format_service(req, service, keys=None):
    def transform(key, value):
        if keys and key not in keys:
            return
        yield (key, value)
    service_dict = dict(itertools.chain.from_iterable(
        transform(k, v) for k, v in service.items()))
    return service_dict


def single(req, service):
    return {"service": _format_service(req, service)}


def collection(req, services):
    formatted_services = [_format_service(req, m)
                          for m in services]
    return {'services': formatted_services}
