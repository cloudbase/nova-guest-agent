# Copyright 2020 Cloudbase Solutions Srl
# All Rights Reserved.

import sys

from oslo_config import cfg

from nova_guest import service
from nova_guest import utils
from nova_guest.agent.rpc import server as rpc_server

CONF = cfg.CONF


def main():
    CONF(sys.argv[1:], project='nova_guest',
         version="1.0.0")
    utils.setup_logging()

    server = service.MessagingService(
        'nova_guest_agent', [rpc_server.AgentServerEndpoint()],
        rpc_server.VERSION)
    launcher = service.service.launch(
        CONF, server, workers=server.get_workers_count())
    launcher.wait()


if __name__ == "__main__":
    main()
